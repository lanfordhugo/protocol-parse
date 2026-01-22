"""
文件名称: normal_parse_page.py
内容摘要: 普通解析页面组件（封装原 MainWindow 逻辑）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-10
"""

import os
import subprocess
import sys
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


class ValidateWorker(QObject):
    """后台配置校验工作线程"""

    # 信号：单个协议校验完成 (protocol_name, is_valid, errors, warnings)
    protocol_validated = Signal(str, bool, list, list)
    # 信号：所有校验完成
    all_finished = Signal()

    def __init__(self, protocols: List[Tuple[str, str]]):
        super().__init__()
        self._protocols = protocols
        self._should_stop = False

    def stop(self):
        """请求停止"""
        self._should_stop = True

    @Slot()
    def run(self):
        """执行校验"""
        try:
            from src.validate_configs import ConfigValidator
            validator = ConfigValidator()

            for protocol_name, config_path in self._protocols:
                if self._should_stop:
                    break

                is_valid = validator.validate_protocol_config(Path(config_path))
                errors = list(validator.errors)
                warnings = list(validator.warnings)

                self.protocol_validated.emit(
                    protocol_name, is_valid, errors, warnings
                )
        except Exception as e:
            for protocol_name, _ in self._protocols:
                if self._should_stop:
                    break
                self.protocol_validated.emit(protocol_name, True, [], [str(e)])

        self.all_finished.emit()


class ParseWorker(QObject):
    """解析工作线程"""

    # 信号
    started = Signal()
    progress = Signal(int, int)
    log_info = Signal(str)
    log_success = Signal(str)
    log_warning = Signal(str)
    log_error = Signal(str)
    finished = Signal(bool, str, str)

    def __init__(
        self,
        protocol_name: str,
        config_path: str,
        log_path: str,
        filter_settings: Dict[str, Any]
    ):
        super().__init__()
        self.protocol_name = protocol_name
        self.config_path = config_path
        self.log_path = log_path
        self.filter_settings = filter_settings
        self._should_stop = False

    def stop(self):
        """请求停止"""
        self._should_stop = True

    @Slot()
    def run(self):
        """执行解析"""
        try:
            self.started.emit()
            self.log_info.emit(f"协议 {self.protocol_name} 配置加载完成")

            # 检查过滤条件
            time_range = self.filter_settings.get('time_range')
            include_cmds = self.filter_settings.get('include_cmds')
            exclude_cmds = self.filter_settings.get('exclude_cmds')

            if time_range:
                start, end = time_range
                self.log_info.emit(
                    f"应用过滤条件: 时间 {start.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"~ {end.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            if include_cmds:
                self.log_info.emit(f"应用过滤条件: 包含命令 {include_cmds}")

            if exclude_cmds:
                self.log_info.emit(f"应用过滤条件: 排除命令 {exclude_cmds}")

            self.log_info.emit(f"开始解析日志文件 {self.log_path} ...")

            # 导入解析器并执行
            from src.yaml_unified_protocol import YamlUnifiedProtocol

            protocol = YamlUnifiedProtocol(
                self.log_path,
                self.config_path
            )

            # 设置过滤条件
            if include_cmds:
                protocol.set_include_cmds([int(c) for c in include_cmds])
            if exclude_cmds:
                protocol.set_exclude_cmds([int(c) for c in exclude_cmds])
            if time_range:
                protocol.set_time_range(time_range[0], time_range[1])

            self.progress.emit(10, 100)
            self.log_info.emit("正在提取数据...")

            # 执行解析
            output_path = protocol.run()

            self.progress.emit(90, 100)

            if output_path:
                self.log_success.emit(f"解析完成，结果已保存到: {output_path}")
                self.progress.emit(100, 100)
                self.finished.emit(True, "解析完成", output_path)
            else:
                self.log_warning.emit("解析完成，但没有生成输出文件（可能没有匹配的数据）")
                self.progress.emit(100, 100)
                self.finished.emit(True, "解析完成（无数据）", "")

        except Exception as e:
            error_msg = self._friendly_error_message(str(e))
            self.log_error.emit(f"解析失败: {error_msg}")
            self.finished.emit(False, error_msg, "")

    def _friendly_error_message(self, error: str) -> str:
        """将技术错误信息转换为友好的中文提示"""
        error_lower = error.lower()

        if "no such file" in error_lower or "找不到" in error_lower:
            return "日志文件不存在，请检查文件路径是否正确"
        if "permission denied" in error_lower or "拒绝访问" in error_lower:
            return "无法访问文件，请检查文件权限或关闭占用该文件的程序"
        if "encoding" in error_lower or "codec" in error_lower:
            return "文件编码错误，请确保日志文件为 UTF-8 或 GBK 编码"

        if "protocol" in error_lower and "not found" in error_lower:
            return "协议配置未找到，请检查 configs 目录下是否存在对应的 protocol.yaml"
        if "yaml" in error_lower:
            return "协议配置文件格式错误，请检查 YAML 语法是否正确"
        if "head" in error_lower or "header" in error_lower:
            return "日志格式不匹配，请确认选择了正确的协议"

        if "no data" in error_lower or "没有数据" in error_lower:
            return "日志文件中没有找到有效的报文数据"
        if "parse" in error_lower or "解析" in error_lower:
            return f"报文解析错误: {error}。请检查日志格式是否与协议匹配"

        return error


def get_app_dir() -> Path:
    """获取应用程序所在目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path.cwd()


class NormalParsePage(QWidget):
    """普通解析页面 - 封装普通解析功能"""

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
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
        self._load_protocols()

        # 启用拖拽支持
        self.setAcceptDrops(True)

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
        """连接信号"""
        self.protocol_panel.protocol_selected.connect(self._on_protocol_selected)
        self.detail_panel.parse_clicked.connect(self._on_parse_clicked)
        self.detail_panel.validate_clicked.connect(self._on_validate_clicked)
        self.detail_panel.open_output_dir_clicked.connect(self._open_output_dir)
        self.detail_panel.select_log_clicked.connect(self._on_select_log_clicked)

    def _load_protocols(self):
        """加载协议列表"""
        self.protocol_panel.load_protocols(self._configs_dir)

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
        """开始解析"""
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
        """解析完成"""
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
                    self._open_file(output_path)
        else:
            self.status_changed.emit(f"❌ 解析失败 | {protocol_name}")

    def _on_validate_clicked(self):
        """验证配置"""
        protocol_name = self.protocol_panel.get_selected_protocol()
        if not protocol_name:
            QMessageBox.warning(self, "提示", "请先选择要验证的协议")
            return

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

    def _on_select_log_clicked(self):
        """选择日志文件"""
        protocol_name = self.protocol_panel.get_selected_protocol()
        if not protocol_name:
            QMessageBox.warning(self, "提示", "请先选择协议")
            return

        if not self._settings:
            # 如果没有设置，使用默认目录
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

    def _open_output_dir(self):
        """打开输出目录"""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._open_directory(self._output_dir)

    def _open_directory(self, path: Path):
        """打开目录（跨平台）"""
        path.mkdir(parents=True, exist_ok=True)

        if sys.platform == 'win32':
            os.startfile(str(path))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(path)])
        else:
            subprocess.run(['xdg-open', str(path)])

    def _open_file(self, file_path: str):
        """打开文件（跨平台）"""
        if sys.platform == 'win32':
            os.startfile(file_path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', file_path])
        else:
            subprocess.run(['xdg-open', file_path])

    def _validate_single_protocol(self, protocol_name: str, config_path: str):
        """校验单个协议配置"""
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
