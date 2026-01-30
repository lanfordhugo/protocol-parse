"""
文件名称: normal_parse_page.py
内容摘要: 普通解析页面 MVP 架构 - View 层
当前版本: v2.0.0
作者: lanford
创建日期: 2025-01-10
更新日期: 2026-01-29
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QApplication, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from .protocol_panel import ProtocolPanel
from .detail_panel import DetailPanel
from .log_panel import LogPanel
from gui.workers import ValidateWorker, ParseWorker
from gui.shared import get_app_dir, open_directory, open_file
from gui.views import INormalParsePageView
from gui.presenters import NormalParsePagePresenter


class NormalParsePage(QWidget, INormalParsePageView):
    """普通解析页面（MVP 架构 - View 层）

    职责：
    - 协调协议面板、详情面板、日志面板的布局和显示
    - 捕获页面级用户事件并转发给 Presenter
    - 响应 Presenter 的指令更新 UI 状态

    TODO: Phase 2 逐步将业务逻辑迁移到 Presenter
    """

    # === 信号：用户事件（向 Presenter 发送） ===
    protocol_selected = Signal(str)  # 协议选择变化
    parse_requested = Signal(str, dict)  # 请求解析 (protocol_name, filter_settings)
    stop_requested = Signal()  # 请求停止
    validate_requested = Signal(str)  # 请求验证 (protocol_name)
    open_output_dir_requested = Signal()  # 请求打开输出目录
    select_log_requested = Signal(str)  # 请求选择日志 (protocol_name)

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    def __init__(self, presenter: NormalParsePagePresenter, parent=None):
        """初始化页面

        Args:
            presenter: 业务逻辑协调器（依赖注入）
            parent: 父窗口
        """
        super().__init__(parent)
        self._presenter = presenter
        self._app_dir = get_app_dir()
        self._configs_dir = self._app_dir / "configs"
        self._output_dir = self._app_dir / "parsed_log"

        self._parse_thread: Optional[QThread] = None
        self._parse_worker: Optional[ParseWorker] = None
        self._validate_thread: Optional[QThread] = None
        self._validate_worker: Optional[ValidateWorker] = None

        self._settings = None  # 由主窗口传入

        self._setup_ui()
        self._connect_signals()

        # 启用拖拽支持
        self.setAcceptDrops(True)

        # 请求 Presenter 加载协议列表并初始化（如果 Presenter 已注入）
        if self._presenter is not None:
            self._presenter.initialize()
            # 默认选择 sinexcel 协议
            self._select_default_protocol("sinexcel")

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 使用 Splitter 布局
        main_splitter = QSplitter(Qt.Vertical)

        # 上部分：左右分栏
        top_splitter = QSplitter(Qt.Horizontal)

        # 左侧：协议列表
        self.protocol_panel = ProtocolPanel()
        self.protocol_panel.setMinimumWidth(250)
        self.protocol_panel.setMaximumWidth(350)
        top_splitter.addWidget(self.protocol_panel)

        # 右侧：详情面板
        self.detail_panel = DetailPanel()
        top_splitter.addWidget(self.detail_panel)

        top_splitter.setStretchFactor(0, 0)
        top_splitter.setStretchFactor(1, 1)

        # 底部：日志面板
        self.log_panel = LogPanel()
        self.log_panel.setMinimumHeight(150)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.log_panel)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)

        layout.addWidget(main_splitter)

    def set_settings(self, settings):
        """设置 QSettings（由主窗口传入）"""
        self._settings = settings

    def _connect_signals(self):
        """连接信号（转发到 Presenter）"""
        # 子面板信号 -> View 信号 -> Presenter
        self.protocol_panel.protocol_selected.connect(
            lambda name: self.protocol_selected.emit(name)
        )
        self.detail_panel.parse_clicked.connect(self._on_parse_clicked)
        self.detail_panel.stop_clicked.connect(
            lambda: self.stop_requested.emit()
        )
        self.detail_panel.validate_clicked.connect(
            lambda: self.validate_requested.emit(
                self.protocol_panel.get_selected_protocol() or ""
            )
        )
        self.detail_panel.open_output_dir_clicked.connect(
            lambda: self.open_output_dir_requested.emit()
        )
        self.detail_panel.select_log_clicked.connect(
            lambda: self.select_log_requested.emit(
                self.protocol_panel.get_selected_protocol() or ""
            )
        )

        # TODO: Phase 2 连接 Presenter 信号到 View
        # 临时：直接连接到处理方法
        self.validate_requested.connect(self._handle_validate_requested)
        self.select_log_requested.connect(self._handle_select_log_requested)
        self.open_output_dir_requested.connect(self._handle_open_output_dir_requested)

    def _on_protocol_selected(self, protocol_name: str):
        """协议选择变化"""
        info = self.protocol_panel.get_protocol_info(protocol_name)
        if not info:
            return

        # 尝试恢复上次使用的日志文件路径
        if not info['log_path'] and self._settings:
            last_log = self._settings.value(f"last_log/{protocol_name}", "")
            if last_log and Path(last_log).exists():
                self.protocol_panel.set_log_path(protocol_name, last_log)
                info = self.protocol_panel.get_protocol_info(protocol_name)
                self.log_panel.log_info(f"已恢复上次使用的日志文件: {last_log}")

        # 校验当前选中的协议
        self._validate_single_protocol(protocol_name, info['config_path'])

        # 加载协议配置获取统计信息
        cmd_count = 0
        enum_count = 0
        type_count = 0
        commands: List[Tuple[str, str]] = []

        try:
            from src.yaml_config import YamlConfigLoader
            loader = YamlConfigLoader()
            config = loader.load_protocol_config(info['config_path'])

            if config:
                cmd_count = len(config.cmds) if config.cmds else 0
                enum_count = len(config.enums) if config.enums else 0
                type_count = len(config.types) if config.types else 0

                if config.cmds:
                    for cmd_id in config.cmds.keys():
                        commands.append((str(cmd_id), str(cmd_id)))
        except Exception as e:
            self.log_panel.log_warning(f"加载配置统计失败: {e}")

        # 更新详情面板
        self.detail_panel.update_protocol_info(
            name=protocol_name,
            config_path=info['config_path'],
            config_valid=info.get('config_valid', True),
            log_path=info['log_path'],
            log_exists=info['log_exists'],
            log_size=info['log_size'],
            cmd_count=cmd_count,
            enum_count=enum_count,
            type_count=type_count,
            commands=commands
        )

        self.status_changed.emit(f"选中协议: {protocol_name}")

    def _on_parse_clicked(self):
        """开始解析（向 Presenter 发送请求）"""
        # TODO: Phase 2 完全迁移到 Presenter
        protocol_name = self.protocol_panel.get_selected_protocol()
        if not protocol_name:
            QMessageBox.warning(self, "提示", "请先选择要解析的协议")
            return

        info = self.protocol_panel.get_protocol_info(protocol_name)
        if not info:
            return

        if not info['log_exists'] or info['log_size'] == 0:
            QMessageBox.warning(
                self, "提示",
                f"日志文件不存在或为空:\n{info['log_path']}\n\n"
                "请先将日志内容拷贝到该文件。"
            )
            return

        filter_settings = self.detail_panel.get_filter_settings()

        # 发送解析请求到 Presenter
        self.parse_requested.emit(protocol_name, filter_settings)

        # 临时：直接创建工作线程（Phase 2 迁移到 Presenter）
        self._start_parse_worker(protocol_name, info, filter_settings)

    def _start_parse_worker(self, protocol_name: str, info: dict, filter_settings: dict):
        """启动解析工作线程（TODO: Phase 2 迁移到 Presenter）"""
        # 创建工作线程
        self._parse_thread = QThread()
        self._parse_worker = ParseWorker(
            protocol_name,
            info['config_path'],
            info['log_path'],
            filter_settings
        )
        self._parse_worker.moveToThread(self._parse_thread)

        # 连接信号
        self._parse_thread.started.connect(self._parse_worker.run)
        self._parse_worker.log_info.connect(self.log_panel.log_info)
        self._parse_worker.log_success.connect(self.log_panel.log_success)
        self._parse_worker.log_warning.connect(self.log_panel.log_warning)
        self._parse_worker.log_error.connect(self.log_panel.log_error)
        self._parse_worker.progress.connect(self.log_panel.set_progress)
        self._parse_worker.finished.connect(self._on_parse_finished)

        # 更新UI状态
        self.detail_panel.set_parsing(True)
        self.log_panel.reset_progress()
        self.status_changed.emit(f"正在解析: {protocol_name}")

        # 启动线程
        self._parse_thread.start()

    def _on_parse_finished(self, success: bool, message: str, output_path: str):
        """解析完成（TODO: Phase 2 迁移到 Presenter）"""
        self.detail_panel.set_parsing(False)

        if self._parse_thread:
            self._parse_thread.quit()
            self._parse_thread.wait()
            self._parse_thread = None
            self._parse_worker = None

        protocol_name = self.protocol_panel.get_selected_protocol() or ""
        if success:
            self.status_changed.emit(
                f"✅ 解析完成 | {protocol_name} | "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            if output_path:
                reply = QMessageBox.question(
                    self,
                    "解析完成",
                    f"解析结果已保存到:\n{output_path}\n\n是否立即打开查看？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    open_file(output_path)
        else:
            self.status_changed.emit(f"❌ 解析失败 | {protocol_name}")

    # TODO: Phase 2 以下方法迁移到 Presenter
    # _on_validate_clicked, _on_select_log_clicked, _open_output_dir
    # 已通过信号转发机制连接到 Presenter

    def _validate_single_protocol(self, protocol_name: str, config_path: str):
        """校验单个协议配置（TODO: Phase 2 迁移到 Presenter）"""
        try:
            import sys
            src_path = str(self._app_dir / "src")
            if src_path not in sys.path:
                sys.path.insert(0, src_path)

            from validate_configs import ConfigValidator
            validator = ConfigValidator()
            is_valid = validator.validate_protocol_config(Path(config_path))

            if is_valid:
                if validator.warnings:
                    self.log_panel.log_warning(
                        f"协议 {protocol_name} 校验通过（{len(validator.warnings)} 个警告）"
                    )
                    for warning in validator.warnings:
                        self.log_panel.log_warning(f"  ↳ {warning}")
                else:
                    self.log_panel.log_success(f"协议 {protocol_name} 校验通过")
            else:
                self.log_panel.log_error(
                    f"协议 {protocol_name} 校验失败（{len(validator.errors)} 个错误）"
                )
                for error in validator.errors:
                    self.log_panel.log_error(f"  ↳ {error}")
            return is_valid
        except Exception as e:
            self.log_panel.log_warning(f"校验失败: {e}")
            return True

    # === 临时处理方法（Presenter 信号转发） ===
    # TODO: Phase 2 删除这些方法，改为从 Presenter 接收指令

    def _handle_validate_requested(self, protocol_name: str):
        """处理验证请求（临时）"""
        info = self.protocol_panel.get_protocol_info(protocol_name)
        if not info:
            return

        self.log_panel.log_info(f"开始验证协议 {protocol_name} 的配置...")

        try:
            from src.yaml_config import YamlConfigLoader
            loader = YamlConfigLoader()
            config = loader.load_protocol_config(info['config_path'])

            if config:
                self.log_panel.log_success(f"协议 {protocol_name} 配置验证通过")
                self.protocol_panel.update_protocol_status(
                    protocol_name, config_valid=True
                )
                self._on_protocol_selected(protocol_name)
            else:
                self.log_panel.log_error(f"协议 {protocol_name} 配置加载失败")
                self.protocol_panel.update_protocol_status(
                    protocol_name, config_valid=False
                )
        except Exception as e:
            self.log_panel.log_error(f"验证失败: {e}")
            self.protocol_panel.update_protocol_status(
                protocol_name, config_valid=False
            )

    def _handle_select_log_requested(self, protocol_name: str):
        """处理选择日志请求（临时）"""
        if not protocol_name:
            QMessageBox.warning(self, "提示", "请先选择协议")
            return

        if not self._settings:
            last_dir = str(Path.home())
        else:
            last_dir = self._settings.value("last_log_dir", str(Path.home()))

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择 {protocol_name} 协议的日志文件",
            last_dir,
            "日志文件 (*.log *.txt);;所有文件 (*.*)"
        )

        if file_path:
            if self._settings:
                self._settings.setValue("last_log_dir", str(Path(file_path).parent))
                self._settings.setValue(f"last_log/{protocol_name}", file_path)

            self.protocol_panel.set_log_path(protocol_name, file_path)
            self._on_protocol_selected(protocol_name)
            self.log_panel.log_info(f"已选择日志文件: {file_path}")

    def _handle_open_output_dir_requested(self):
        """处理打开输出目录请求（临时）"""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        open_directory(self._output_dir)

    def _select_default_protocol(self, protocol_name: str):
        """选择默认协议"""
        list_widget = self.protocol_panel.protocol_list.list_widget
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.UserRole) == protocol_name:
                list_widget.setCurrentRow(i)
                return
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)

    # === INormalParsePageView 接口实现 ===

    def set_parse_state(self, is_parsing: bool) -> None:
        """设置解析状态

        Args:
            is_parsing: 是否正在解析
        """
        self.detail_panel.set_parsing(is_parsing)

    def show_error_message(self, title: str, message: str) -> None:
        """显示错误消息对话框

        Args:
            title: 标题
            message: 消息内容
        """
        QMessageBox.critical(self, title, message)

    def show_info_message(self, title: str, message: str) -> None:
        """显示信息消息对话框

        Args:
            title: 标题
            message: 消息内容
        """
        QMessageBox.information(self, title, message)

    def show_warning_message(self, title: str, message: str) -> None:
        """显示警告消息对话框

        Args:
            title: 标题
            message: 消息内容
        """
        QMessageBox.warning(self, title, message)

    def get_protocol_panel_view(self):
        """获取协议面板 View 接口

        Returns:
            IProtocolPanelView 实例
        """
        # TODO: Phase 2 ProtocolPanel 实现接口后返回
        return self.protocol_panel

    def get_detail_panel_view(self):
        """获取详情面板 View 接口

        Returns:
            IDetailPanelView 实例
        """
        # TODO: Phase 2 DetailPanel 实现接口后返回
        return self.detail_panel

    def get_log_panel_view(self):
        """获取日志面板 View 接口

        Returns:
            ILogPanelView 实例
        """
        # TODO: Phase 2 LogPanel 实现接口后返回
        return self.log_panel

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith(('.log', '.txt')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        protocol_name = self.protocol_panel.get_selected_protocol()
        if not protocol_name:
            QMessageBox.warning(self, "提示", "请先选择一个协议，再拖入日志文件")
            return

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.log', '.txt')):
                self.protocol_panel.set_log_path(protocol_name, file_path)
                if self._settings:
                    self._settings.setValue(f"last_log/{protocol_name}", file_path)
                self._on_protocol_selected(protocol_name)
                self.log_panel.log_info(f"已通过拖拽加载日志文件: {file_path}")
                break

    def cleanup(self) -> None:
        """清理资源(停止工作线程)"""
        # 停止校验线程
        if self._validate_worker:
            self._validate_worker.stop()
        if self._validate_thread and self._validate_thread.isRunning():
            self._validate_thread.quit()
            self._validate_thread.wait(1000)

        # 停止解析线程
        if self._parse_worker:
            self._parse_worker.stop()
        if self._parse_thread and self._parse_thread.isRunning():
            self._parse_thread.quit()
            self._parse_thread.wait(1000)

        # 清理详情面板的扫描线程
        self.detail_panel.cleanup()
