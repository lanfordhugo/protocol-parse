# gui/detail_panel.py
"""
文件名称: detail_panel.py
内容摘要: 右侧详情面板，包含协议详情、过滤设置和操作按钮
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QCheckBox, QGridLayout, QFrame, QScrollArea,
    QSizePolicy, QDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from .widgets.datetime_picker import DateTimePickerWidget
from .widgets.multi_select_combo import MultiSelectComboBox
from .widgets.log_time_scanner import LogTimeScanner, TimeScanResult
from gui.shared.time_utils import format_time_range_smart
from gui.views import IDetailPanelView


class ProtocolDetailWidget(QGroupBox):
    """协议详情显示组件"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("协议详情", parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        layout.setColumnStretch(1, 1)
        
        # 协议名称
        layout.addWidget(QLabel("协议名称:"), 0, 0)
        self.name_label = QLabel("-")
        self.name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.name_label, 0, 1)
        
        # 配置文件
        layout.addWidget(QLabel("配置文件:"), 1, 0)
        self.config_label = QLabel("-")
        self.config_label.setWordWrap(True)
        layout.addWidget(self.config_label, 1, 1)
        
        # 配置状态
        layout.addWidget(QLabel("配置状态:"), 2, 0)
        self.config_status_label = QLabel("-")
        layout.addWidget(self.config_status_label, 2, 1)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line, 3, 0, 1, 2)
        
        # 日志文件（带选择按钮）
        layout.addWidget(QLabel("日志文件:"), 4, 0)
        log_row = QHBoxLayout()
        self.log_label = QLabel("未选择")
        self.log_label.setWordWrap(True)
        self.log_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        log_row.addWidget(self.log_label)
        self.select_log_btn = QPushButton("📂 选择")
        self.select_log_btn.setFixedWidth(85)
        log_row.addWidget(self.select_log_btn)
        log_container = QWidget()
        log_container.setLayout(log_row)
        layout.addWidget(log_container, 4, 1)
        
        # 日志状态
        layout.addWidget(QLabel("日志状态:"), 5, 0)
        self.log_status_label = QLabel("⚠️ 请选择日志文件")
        self.log_status_label.setStyleSheet("color: #f39c12;")
        layout.addWidget(self.log_status_label, 5, 1)
        
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2, 6, 0, 1, 2)
        
        # 统计信息
        layout.addWidget(QLabel("支持命令:"), 7, 0)
        self.cmd_count_label = QLabel("-")
        layout.addWidget(self.cmd_count_label, 7, 1)
        
        layout.addWidget(QLabel("枚举定义:"), 8, 0)
        self.enum_count_label = QLabel("-")
        layout.addWidget(self.enum_count_label, 8, 1)
        
        layout.addWidget(QLabel("自定义类型:"), 9, 0)
        self.type_count_label = QLabel("-")
        layout.addWidget(self.type_count_label, 9, 1)
    
    def update_info(
        self,
        name: str,
        config_path: str,
        config_valid: bool,
        log_path: str,
        log_exists: bool,
        log_size: int,
        cmd_count: int = 0,
        enum_count: int = 0,
        type_count: int = 0
    ):
        """更新协议详情"""
        self.name_label.setText(name)
        self.config_label.setText(config_path)
        
        if config_valid:
            self.config_status_label.setText("✅ 验证通过")
            self.config_status_label.setStyleSheet("color: #27ae60;")
        else:
            self.config_status_label.setText("❌ 验证失败")
            self.config_status_label.setStyleSheet("color: #e74c3c;")
        
        if log_path:
            self.log_label.setText(log_path)
            if log_exists and log_size > 0:
                size_str = self._format_size(log_size)
                self.log_status_label.setText(f"✅ 已选择 ({size_str})")
                self.log_status_label.setStyleSheet("color: #27ae60;")
            elif log_exists:
                self.log_status_label.setText("⚠️ 文件为空")
                self.log_status_label.setStyleSheet("color: #f39c12;")
            else:
                self.log_status_label.setText("❌ 文件不存在")
                self.log_status_label.setStyleSheet("color: #e74c3c;")
        else:
            self.log_label.setText("未选择")
            self.log_status_label.setText("⚠️ 请选择日志文件")
            self.log_status_label.setStyleSheet("color: #f39c12;")
        
        self.cmd_count_label.setText(f"{cmd_count} 个")
        self.enum_count_label.setText(f"{enum_count} 个")
        self.type_count_label.setText(f"{type_count} 个")
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    def clear(self):
        """清空显示"""
        self.name_label.setText("-")
        self.config_label.setText("-")
        self.config_status_label.setText("-")
        self.config_status_label.setStyleSheet("")
        self.log_label.setText("未选择")
        self.log_status_label.setText("⚠️ 请选择日志文件")
        self.log_status_label.setStyleSheet("color: #f39c12;")
        self.cmd_count_label.setText("-")
        self.enum_count_label.setText("-")
        self.type_count_label.setText("-")


class FilterWidget(QGroupBox):
    """过滤设置组件"""

    # 信号：通知过滤器变化
    time_range_changed = Signal(object, object)  # (start, end)
    command_filter_changed = Signal(object, object)  # (include_cmds, exclude_cmds)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("过滤设置（可选）", parent)

        # 日志时间扫描器（后台线程）
        self._scanner: Optional[LogTimeScanner] = None
        self._scan_result: Optional[TimeScanResult] = None

        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 复选框统一样式
        checkbox_style = """
            QCheckBox {
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox:unchecked {
                background-color: #34495e;
                color: #ecf0f1;
            }
            QCheckBox:checked {
                background-color: #3498db;
                color: white;
            }
            QCheckBox:hover {
                background-color: #2980b9;
            }
        """
        
        # 时间过滤
        self.time_filter_check = QCheckBox("启用时间过滤")
        self.time_filter_check.setStyleSheet(checkbox_style)
        layout.addWidget(self.time_filter_check)

        time_layout = QGridLayout()
        time_layout.setContentsMargins(20, 0, 0, 0)

        # 日志时间范围显示
        time_layout.addWidget(QLabel("📅 日志范围:"), 0, 0)
        self.log_range_label = QLabel("未加载")
        self.log_range_label.setStyleSheet("color: #888; font-size: 11px;")
        time_layout.addWidget(self.log_range_label, 0, 1)

        # 当前选择显示
        time_layout.addWidget(QLabel("🕒 当前选择:"), 1, 0)
        self.current_range_label = QLabel("未选择")
        self.current_range_label.setStyleSheet("color: #569cd6; font-size: 11px;")
        time_layout.addWidget(self.current_range_label, 1, 1)

        # 可视化选择按钮
        self.open_visual_picker_btn = QPushButton("📊 可视化选择时间范围...")
        self.open_visual_picker_btn.setEnabled(False)
        self.open_visual_picker_btn.clicked.connect(self._open_visual_time_picker)
        time_layout.addWidget(self.open_visual_picker_btn, 2, 0, 1, 2)

        layout.addLayout(time_layout)

        # 保留原有的 DateTimePickerWidget（用于内部存储，设为不可见）
        self.start_time_picker = DateTimePickerWidget()
        self.start_time_picker.setVisible(False)
        self.end_time_picker = DateTimePickerWidget()
        self.end_time_picker.setVisible(False)
        
        # 命令过滤
        self.cmd_filter_check = QCheckBox("启用命令过滤")
        self.cmd_filter_check.setStyleSheet(checkbox_style)
        layout.addWidget(self.cmd_filter_check)
        
        cmd_layout = QGridLayout()
        cmd_layout.setContentsMargins(20, 0, 0, 0)
        
        cmd_layout.addWidget(QLabel("包含:"), 0, 0)
        self.include_cmd_combo = MultiSelectComboBox("选择要包含的命令...")
        self.include_cmd_combo.setEnabled(False)
        cmd_layout.addWidget(self.include_cmd_combo, 0, 1)
        
        cmd_layout.addWidget(QLabel("排除:"), 1, 0)
        self.exclude_cmd_combo = MultiSelectComboBox("选择要排除的命令...")
        self.exclude_cmd_combo.setEnabled(False)
        cmd_layout.addWidget(self.exclude_cmd_combo, 1, 1)
        
        layout.addLayout(cmd_layout)
    
    def _connect_signals(self):
        """连接信号"""
        self.time_filter_check.toggled.connect(self._on_time_filter_toggled)
        self.cmd_filter_check.toggled.connect(self._on_cmd_filter_toggled)
    
    def _on_time_filter_toggled(self, checked: bool):
        """时间过滤启用状态变化"""
        # 启用/禁用可视化选择按钮
        # 只有当扫描完成后才启用按钮
        if checked and self._scan_result and self._scan_result.has_valid_range:
            self.open_visual_picker_btn.setEnabled(True)
        else:
            self.open_visual_picker_btn.setEnabled(False)

        # 发射信号（禁用时传递 None）
        if not checked:
            self.time_range_changed.emit(None, None)

    def _on_cmd_filter_toggled(self, checked: bool):
        """命令过滤启用状态变化"""
        self.include_cmd_combo.setEnabled(checked)
        self.exclude_cmd_combo.setEnabled(checked)

        # 发射信号（禁用时传递 None）
        if not checked:
            self.command_filter_changed.emit(None, None)
    
    def set_commands(self, commands: List[Tuple[str, str]]):
        """设置可用的命令列表 [(cmd_id, display_text), ...]"""
        self.include_cmd_combo.set_items(commands)
        self.exclude_cmd_combo.set_items(commands)

        # 连接选择变化信号
        self.include_cmd_combo.selection_changed.connect(
            lambda: self._emit_command_filter_changed()
        )
        self.exclude_cmd_combo.selection_changed.connect(
            lambda: self._emit_command_filter_changed()
        )

    def _emit_command_filter_changed(self):
        """发射命令过滤变化信号"""
        if self.cmd_filter_check.isChecked():
            include = self.get_include_cmds()
            exclude = self.get_exclude_cmds()
            self.command_filter_changed.emit(include, exclude)
    
    def get_time_filter(self) -> Optional[Tuple[datetime, datetime]]:
        """获取时间过滤条件"""
        if not self.time_filter_check.isChecked():
            return None
        start = self.start_time_picker.get_datetime()
        end = self.end_time_picker.get_datetime()
        if start and end:
            return (start, end)
        return None
    
    def get_include_cmds(self) -> Optional[List[str]]:
        """获取包含的命令列表"""
        if not self.cmd_filter_check.isChecked():
            return None
        selected = self.include_cmd_combo.get_selected()
        return selected if selected else None
    
    def get_exclude_cmds(self) -> Optional[List[str]]:
        """获取排除的命令列表"""
        if not self.cmd_filter_check.isChecked():
            return None
        selected = self.exclude_cmd_combo.get_selected()
        return selected if selected else None
    
    def clear(self):
        """清空过滤设置"""
        self.time_filter_check.setChecked(False)
        self.cmd_filter_check.setChecked(False)
        self.start_time_picker.set_datetime(None)
        self.end_time_picker.set_datetime(None)
        self.include_cmd_combo.clear_selection()
        self.exclude_cmd_combo.clear_selection()

        # 清空显示标签
        self.log_range_label.setText("未加载")
        self.log_range_label.setStyleSheet("color: #888; font-size: 11px;")
        self.current_range_label.setText("未选择")

        # 清理扫描状态
        self._scan_result = None
        if hasattr(self, '_last_scanned_path'):
            delattr(self, '_last_scanned_path')

    def cleanup(self):
        """清理资源（停止扫描线程）"""
        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()
            self._scanner.wait()

    def set_log_path(self, log_path: Optional[str]):
        """
        设置日志文件路径（用于加载时间范围）

        Args:
            log_path: 日志文件路径
        """
        self._log_path = log_path

        # 如果路径有效，自动触发后台扫描
        if log_path:
            self._start_background_scan()

    def _start_background_scan(self):
        """启动后台日志时间扫描"""
        if not hasattr(self, '_log_path') or not self._log_path:
            return

        # 如果已有扫描结果且路径未变，不重复扫描
        if self._scan_result and hasattr(self, '_last_scanned_path'):
            if self._last_scanned_path == self._log_path:
                return

        # 更新 UI 状态：正在扫描
        self.log_range_label.setText("🔄 正在扫描日志时间范围...")
        self.log_range_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        self.open_visual_picker_btn.setEnabled(False)  # 扫描期间禁用按钮

        # 启动后台扫描线程
        self._scanner = LogTimeScanner(self._log_path, self)
        self._scanner.progress.connect(self._on_scan_progress)
        self._scanner.finished.connect(self._on_scan_finished)
        self._scanner.error.connect(self._on_scan_error)
        self._scanner.start()

    def _on_scan_progress(self, current: int, total: int):
        """扫描进度更新（可选显示，避免频繁刷新）"""
        # 每 10% 更新一次显示
        if total > 0 and current % (total // 10) == 0:
            progress = int(current * 100 / total)
            self.log_range_label.setText(f"🔄 正在扫描... {progress}%")

    def _on_scan_finished(self, result: TimeScanResult):
        """扫描完成"""
        self._scan_result = result
        self._last_scanned_path = self._log_path

        if result.has_valid_range:
            # 显示日志时间范围（智能格式化 + 时间跨度）
            range_str = format_time_range_smart(result.min_time, result.max_time)
            span_str = result.time_span_human
            self.log_range_label.setText(f"{range_str} (跨度: {span_str})")
            self.log_range_label.setStyleSheet("color: #27ae60; font-size: 11px;")

            # 如果时间过滤已启用，则启用可视化选择按钮
            if self.time_filter_check.isChecked():
                self.open_visual_picker_btn.setEnabled(True)
        else:
            # 没有找到有效时间戳
            self.log_range_label.setText("⚠️ 未找到有效时间戳")
            self.log_range_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def _on_scan_error(self, error_msg: str):
        """扫描错误"""
        self.log_range_label.setText(f"❌ 扫描失败")
        self.log_range_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def _open_visual_time_picker(self):
        """打开可视化时间选择对话框"""
        if not hasattr(self, '_log_path') or not self._log_path:
            QMessageBox.warning(self, "提示", "请先选择日志文件")
            return

        # 获取当前选择
        current_range = self.get_time_filter()

        # 导入并打开对话框
        try:
            from .widgets.visual_time_picker_dialog import VisualTimePickerDialog

            dialog = VisualTimePickerDialog(
                self._log_path,
                current_range,
                self
            )

            if dialog.exec() == QDialog.Accepted:
                range_result = dialog.get_time_range()
                if range_result:
                    start, end = range_result
                    self.start_time_picker.set_datetime(start)
                    self.end_time_picker.set_datetime(end)
                    self._update_display_labels()

        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"打开可视化时间选择器失败:\n{str(e)}"
            )

    def _update_display_labels(self):
        """更新显示标签"""
        start = self.start_time_picker.get_datetime()
        end = self.end_time_picker.get_datetime()

        if start and end:
            # 显示当前选择（智能格式化）
            range_str = format_time_range_smart(start, end)
            self.current_range_label.setText(range_str)
            # 发射信号
            self.time_range_changed.emit(start, end)
        else:
            self.current_range_label.setText("未选择")


class ActionWidget(QGroupBox):
    """操作按钮组件"""

    # 信号
    parse_clicked = Signal()
    stop_clicked = Signal()  # 新增：停止信号
    validate_clicked = Signal()
    open_output_dir_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("操作", parent)
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 第一行按钮
        row1 = QHBoxLayout()
        self.parse_btn = QPushButton("▶ 开始解析")
        self.parse_btn.setMinimumHeight(36)
        self.parse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.parse_btn.clicked.connect(self.parse_clicked.emit)
        row1.addWidget(self.parse_btn)

        # 停止按钮（初始隐藏）
        self.stop_btn = QPushButton("⏹ 停止解析")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.stop_btn.setVisible(False)
        row1.addWidget(self.stop_btn)

        self.validate_btn = QPushButton("✓ 验证配置")
        self.validate_btn.setMinimumHeight(36)
        self.validate_btn.clicked.connect(self.validate_clicked.emit)
        row1.addWidget(self.validate_btn)
        layout.addLayout(row1)

        # 第二行按钮
        row2 = QHBoxLayout()
        self.output_dir_btn = QPushButton("📁 打开输出目录")
        self.output_dir_btn.clicked.connect(self.open_output_dir_clicked.emit)
        row2.addWidget(self.output_dir_btn)
        layout.addLayout(row2)

    def set_parsing(self, parsing: bool):
        """设置解析状态"""
        if parsing:
            # 解析中：隐藏开始按钮，显示停止按钮
            self.parse_btn.setVisible(False)
            self.stop_btn.setVisible(True)
            self.stop_btn.setEnabled(True)
            self.validate_btn.setEnabled(False)
        else:
            # 未解析：显示开始按钮，隐藏停止按钮
            self.parse_btn.setVisible(True)
            self.parse_btn.setEnabled(True)
            self.stop_btn.setVisible(False)
            self.validate_btn.setEnabled(True)


class DetailPanel(QWidget, IDetailPanelView):
    """右侧详情面板

    实现 IDetailPanelView 接口，组合三个子组件：
    - ProtocolDetailWidget: 协议详情显示
    - FilterWidget: 过滤设置
    - ActionWidget: 操作按钮

    多重继承：
    - QWidget: 提供 Qt 组件功能
    - IDetailPanelView: 定义接口契约
    """

    # 信号：由 IDetailPanelView 接口定义
    # 注意：需要连接子组件的信号到这些信号
    parse_clicked = Signal()
    stop_clicked = Signal()
    validate_clicked = Signal()
    open_output_dir_clicked = Signal()
    select_log_clicked = Signal()
    time_range_changed = Signal(object, object)  # (start, end)
    command_filter_changed = Signal(list)  # (include_cmds, exclude_cmds)
    terminal_filter_changed = Signal(str)  # terminal_id

    def __init__(self, parent: Optional[QWidget] = None):
        # 多重继承：先初始化 QWidget，再初始化 IDetailPanelView
        QWidget.__init__(self, parent)
        IDetailPanelView.__init__(self)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """初始化UI"""
        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        
        # 协议详情
        self.detail_widget = ProtocolDetailWidget()
        layout.addWidget(self.detail_widget)
        
        # 过滤设置
        self.filter_widget = FilterWidget()
        layout.addWidget(self.filter_widget)
        
        # 操作按钮
        self.action_widget = ActionWidget()
        layout.addWidget(self.action_widget)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _connect_signals(self):
        """连接信号"""
        # ActionWidget 信号
        self.action_widget.parse_clicked.connect(self.parse_clicked.emit)
        self.action_widget.stop_clicked.connect(self.stop_clicked.emit)
        self.action_widget.validate_clicked.connect(self.validate_clicked.emit)
        self.action_widget.open_output_dir_clicked.connect(
            self.open_output_dir_clicked.emit
        )

        # ProtocolDetailWidget 信号
        self.detail_widget.select_log_btn.clicked.connect(
            self.select_log_clicked.emit
        )

        # FilterWidget 信号
        self.filter_widget.time_range_changed.connect(self.time_range_changed.emit)
        self.filter_widget.command_filter_changed.connect(
            self._on_command_filter_changed
        )

    # === IDetailPanelView 接口方法实现 ===

    def update_protocol_info(
        self,
        name: str,
        config_path: str,
        config_valid: bool,
        log_path: str,
        log_exists: bool,
        log_size: int,
        cmd_count: int = 0,
        enum_count: int = 0,
        type_count: int = 0,
        commands: Optional[List[Tuple[str, str]]] = None
    ) -> None:
        """更新协议详情显示（接口方法）"""
        self.detail_widget.update_info(
            name, config_path, config_valid,
            log_path, log_exists, log_size,
            cmd_count, enum_count, type_count
        )

        # 更新命令过滤选项
        if commands:
            self.filter_widget.set_commands(commands)

        # 传递日志路径到 FilterWidget，触发自动扫描
        if log_path and log_exists:
            self.filter_widget.set_log_path(log_path)

    def set_parse_button_enabled(self, enabled: bool) -> None:
        """启用/禁用解析按钮（接口方法）"""
        self.action_widget.parse_btn.setEnabled(enabled)

    def set_stop_button_enabled(self, enabled: bool) -> None:
        """启用/禁用停止按钮（接口方法）"""
        self.action_widget.stop_btn.setEnabled(enabled)

    def set_progress(self, current: int, total: int) -> None:
        """设置解析进度（接口方法）

        TODO: Phase 2 实现进度显示
        当前实现：暂无进度条组件
        """
        # TODO: Phase 2 添加进度条组件
        pass

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前过滤设置（接口方法）"""
        return {
            'time_range': self.filter_widget.get_time_filter(),
            'include_cmds': self.filter_widget.get_include_cmds(),
            'exclude_cmds': self.filter_widget.get_exclude_cmds(),
        }

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径（接口方法）"""
        self.filter_widget.set_log_path(path)

    def set_commands(self, commands: List[Tuple[str, str]]) -> None:
        """设置命令列表（接口方法）"""
        self.filter_widget.set_commands(commands)

    def reset_progress(self) -> None:
        """重置进度条（接口方法）

        TODO: Phase 2 实现进度显示
        """
        # TODO: Phase 2 添加进度条组件
        pass

    # === 私有方法 ===

    def _on_command_filter_changed(self, include: Optional[List[str]], exclude: Optional[List[str]]) -> None:
        """处理命令过滤变化信号

        将 FilterWidget 的双参数信号转换为接口要求的单参数信号
        """
        filter_data = {
            'include_cmds': include,
            'exclude_cmds': exclude
        }
        self.command_filter_changed.emit(filter_data)

    def set_parsing(self, parsing: bool) -> None:
        """设置解析状态（遗留方法，保留向后兼容）"""
        self.action_widget.set_parsing(parsing)

    def clear(self) -> None:
        """清空面板（遗留方法，保留向后兼容）"""
        self.detail_widget.clear()
        self.filter_widget.clear()

    def cleanup(self) -> None:
        """清理资源（遗留方法，保留向后兼容）"""
        self.filter_widget.cleanup()

