# gui/main_window.py
"""
文件名称: main_window.py
内容摘要: V8Parse GUI 主窗口，组装左右分栏和底部日志面板
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QMessageBox, QApplication,
    QMenuBar, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject, QSettings
from PySide6.QtGui import QCloseEvent, QAction, QActionGroup

from .protocol_panel import ProtocolPanel
from .detail_panel import DetailPanel
from .log_panel import LogPanel
from .themes import get_theme, get_log_panel_style


class ValidateWorker(QObject):
    """后台配置校验工作线程"""
    
    # 信号：单个协议校验完成 (protocol_name, is_valid, errors, warnings)
    protocol_validated = Signal(str, bool, list, list)
    # 信号：所有校验完成
    all_finished = Signal()
    
    def __init__(self, protocols: List[Tuple[str, str]]):
        """
        Args:
            protocols: [(protocol_name, config_path), ...]
        """
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
            # 如果导入失败，逐个标记为未知状态
            for protocol_name, _ in self._protocols:
                if self._should_stop:
                    break
                self.protocol_validated.emit(protocol_name, True, [], [str(e)])
        
        self.all_finished.emit()


class ParseWorker(QObject):
    """解析工作线程"""
    
    # 信号
    started = Signal()
    progress = Signal(int, int)  # current, total
    log_info = Signal(str)
    log_success = Signal(str)
    log_warning = Signal(str)
    log_error = Signal(str)
    finished = Signal(bool, str)  # success, message
    
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
            
            # 执行解析
            protocol.run()
            
            self.log_success.emit("解析完成，结果已保存到 parsed_log/")
            self.progress.emit(100, 100)
            self.finished.emit(True, "解析完成")
                
        except Exception as e:
            self.log_error.emit(f"解析失败: {e}")
            self.finished.emit(False, str(e))


def get_app_dir() -> Path:
    """获取应用程序所在目录（支持打包后的exe）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的可执行文件目录
        return Path(sys.executable).parent
    else:
        # 开发模式：使用当前工作目录
        return Path.cwd()


class MainWindow(QMainWindow):
    """V8Parse GUI 主窗口"""
    
    def __init__(self):
        super().__init__()
        # 使用可执行程序所在目录（支持打包后发布）
        self._app_dir = get_app_dir()
        self._configs_dir = self._app_dir / "configs"
        self._output_dir = self._app_dir / "parsed_log"
        
        self._parse_thread: Optional[QThread] = None
        self._parse_worker: Optional[ParseWorker] = None
        self._validate_thread: Optional[QThread] = None
        self._validate_worker: Optional[ValidateWorker] = None
        
        # 加载保存的设置
        self._settings = QSettings("V8Parse", "V8ParseGUI")
        self._current_theme = self._settings.value("theme", "dark")
        
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._load_protocols()
        self._apply_theme(self._current_theme)
        
        # 默认选择 sinexcel 协议
        self._select_default_protocol("sinexcel")
    
    def _setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("V8Parse - 多协议通信报文解析工具")
        self.setMinimumSize(1100, 1000)
        self.resize(1100, 800)
        
        # 窗口居中显示
        self._center_on_screen()
        
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        self._central_widget = central
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
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
        
        # 整体上下分栏
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        
        # 底部：日志面板
        self.log_panel = LogPanel()
        self.log_panel.setMinimumHeight(150)
        main_splitter.addWidget(self.log_panel)
        
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        
        main_layout.addWidget(main_splitter)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status("就绪")
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        # 主题子菜单
        theme_menu = view_menu.addMenu("界面风格")
        
        # 主题选项组（互斥）
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        
        # 深色主题
        self._dark_action = QAction("深色主题", self)
        self._dark_action.setCheckable(True)
        self._dark_action.setData("dark")
        self._theme_group.addAction(self._dark_action)
        theme_menu.addAction(self._dark_action)
        
        # 浅色主题
        self._light_action = QAction("浅色主题", self)
        self._light_action.setCheckable(True)
        self._light_action.setData("light")
        self._theme_group.addAction(self._light_action)
        theme_menu.addAction(self._light_action)
        
        # 设置当前主题选中状态
        if self._current_theme == "dark":
            self._dark_action.setChecked(True)
        else:
            self._light_action.setChecked(True)
        
        # 连接主题切换信号
        self._theme_group.triggered.connect(self._on_theme_changed)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _on_theme_changed(self, action: QAction):
        """主题切换"""
        theme = action.data()
        if theme != self._current_theme:
            self._current_theme = theme
            self._apply_theme(theme)
            # 保存设置
            self._settings.setValue("theme", theme)
    
    def _apply_theme(self, theme: str):
        """应用主题"""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme(theme))
        # 更新日志面板特殊样式
        self.log_panel.log_text.setStyleSheet(get_log_panel_style(theme))
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 V8Parse",
            "<h3>V8Parse - 多协议通信报文解析工具</h3>"
            "<p>版本: 1.0.0</p>"
            "<p>基于 YAML 配置的现代化协议解析框架</p>"
            "<p>支持零代码扩展新协议</p>"
        )
    
    def _connect_signals(self):
        """连接信号"""
        # 协议选择变化
        self.protocol_panel.protocol_selected.connect(self._on_protocol_selected)
        
        # 操作按钮
        self.detail_panel.parse_clicked.connect(self._on_parse_clicked)
        self.detail_panel.validate_clicked.connect(self._on_validate_clicked)
        self.detail_panel.open_output_dir_clicked.connect(self._open_output_dir)
        self.detail_panel.select_log_clicked.connect(self._on_select_log_clicked)
    
    def _load_protocols(self):
        """加载协议列表"""
        self.protocol_panel.load_protocols(self._configs_dir)
    
    def _start_background_validation(self):
        """启动后台配置校验"""
        # 获取所有协议信息
        protocols_to_validate = []
        for protocol_name in self.protocol_panel._protocols.keys():
            info = self.protocol_panel.get_protocol_info(protocol_name)
            if info:
                protocols_to_validate.append((protocol_name, info['config_path']))
        
        if not protocols_to_validate:
            return
        
        self.log_panel.log_info(f"开始后台校验 {len(protocols_to_validate)} 个协议配置...")
        
        # 创建校验工作线程
        self._validate_thread = QThread()
        self._validate_worker = ValidateWorker(protocols_to_validate)
        self._validate_worker.moveToThread(self._validate_thread)
        
        # 连接信号
        self._validate_thread.started.connect(self._validate_worker.run)
        self._validate_worker.protocol_validated.connect(self._on_protocol_validated)
        self._validate_worker.all_finished.connect(self._on_validation_finished)
        
        # 启动线程
        self._validate_thread.start()
    
    @Slot(str, bool, list, list)
    def _on_protocol_validated(
        self, protocol_name: str, is_valid: bool, errors: list, warnings: list
    ):
        """单个协议校验完成"""
        # 更新协议状态
        self.protocol_panel.update_protocol_status(protocol_name, config_valid=is_valid)
        
        # 输出日志
        if is_valid:
            if warnings:
                self.log_panel.log_warning(
                    f"协议 {protocol_name} 校验通过（{len(warnings)} 个警告）"
                )
            else:
                self.log_panel.log_success(f"协议 {protocol_name} 校验通过")
        else:
            self.log_panel.log_error(
                f"协议 {protocol_name} 校验失败（{len(errors)} 个错误）"
            )
    
    @Slot()
    def _on_validation_finished(self):
        """所有校验完成"""
        if self._validate_thread:
            self._validate_thread.quit()
            self._validate_thread.wait()
            self._validate_thread = None
            self._validate_worker = None
        
        self.log_panel.log_info("后台配置校验完成")
    
    def _select_default_protocol(self, protocol_name: str):
        """选择默认协议"""
        # 查找并选择指定协议
        list_widget = self.protocol_panel.protocol_list.list_widget
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.UserRole) == protocol_name:
                list_widget.setCurrentRow(i)
                return
        # 如果找不到指定协议，选择第一个
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)
    
    def _validate_single_protocol(self, protocol_name: str, config_path: str):
        """校验单个协议配置"""
        try:
            # 确保 src 目录在路径中
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
                else:
                    self.log_panel.log_success(f"协议 {protocol_name} 校验通过")
            else:
                self.log_panel.log_error(
                    f"协议 {protocol_name} 校验失败（{len(validator.errors)} 个错误）"
                )
            return is_valid
        except Exception as e:
            self.log_panel.log_warning(f"校验失败: {e}")
            return True
    
    def _on_protocol_selected(self, protocol_name: str):
        """协议选择变化"""
        info = self.protocol_panel.get_protocol_info(protocol_name)
        if not info:
            return
        
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
                
                # 生成命令列表（只显示CMD数字）
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
        
        self._update_status(f"选中协议: {protocol_name}")
    
    def _on_parse_clicked(self):
        """开始解析"""
        protocol_name = self.protocol_panel.get_selected_protocol()
        if not protocol_name:
            QMessageBox.warning(self, "提示", "请先选择要解析的协议")
            return
        
        info = self.protocol_panel.get_protocol_info(protocol_name)
        if not info:
            return
        
        # 检查日志文件
        if not info['log_exists'] or info['log_size'] == 0:
            QMessageBox.warning(
                self, "提示",
                f"日志文件不存在或为空:\n{info['log_path']}\n\n"
                "请先将日志内容拷贝到该文件。"
            )
            return
        
        # 获取过滤设置
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
        self._update_status(f"正在解析: {protocol_name}")
        
        # 启动线程
        self._parse_thread.start()
    
    @Slot(bool, str)
    def _on_parse_finished(self, success: bool, message: str):
        """解析完成"""
        self.detail_panel.set_parsing(False)
        
        if self._parse_thread:
            self._parse_thread.quit()
            self._parse_thread.wait()
            self._parse_thread = None
            self._parse_worker = None
        
        protocol_name = self.protocol_panel.get_selected_protocol() or ""
        if success:
            self._update_status(
                f"✅ 解析完成 | {protocol_name} | "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            self._update_status(f"❌ 解析失败 | {protocol_name}")
    
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
            # 使用配置验证器
            from src.yaml_config import YamlConfigLoader
            loader = YamlConfigLoader()
            config = loader.load_protocol_config(info['config_path'])
            
            if config:
                self.log_panel.log_success(f"协议 {protocol_name} 配置验证通过")
                self.protocol_panel.update_protocol_status(
                    protocol_name, config_valid=True
                )
                # 刷新详情
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
        
        # 获取上次选择的目录
        last_dir = self._settings.value("last_log_dir", str(Path.home()))
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择 {protocol_name} 协议的日志文件",
            last_dir,
            "日志文件 (*.log *.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            # 保存目录
            self._settings.setValue("last_log_dir", str(Path(file_path).parent))
            
            # 更新协议面板
            self.protocol_panel.set_log_path(protocol_name, file_path)
            
            # 刷新详情显示
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
    
    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.showMessage(message)
    
    def _center_on_screen(self):
        """将窗口居中显示在屏幕中央"""
        screen = QApplication.primaryScreen().geometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)
    
    def closeEvent(self, event: QCloseEvent):
        """窗口关闭事件"""
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
        
        event.accept()
