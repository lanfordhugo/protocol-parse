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
    QSizePolicy
)
from PySide6.QtCore import Signal, Qt

from .widgets.datetime_picker import DateTimePickerWidget
from .widgets.multi_select_combo import MultiSelectComboBox


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
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("过滤设置（可选）", parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 时间过滤
        self.time_filter_check = QCheckBox("启用时间过滤")
        layout.addWidget(self.time_filter_check)
        
        time_layout = QGridLayout()
        time_layout.setContentsMargins(20, 0, 0, 0)
        
        time_layout.addWidget(QLabel("起始:"), 0, 0)
        self.start_time_picker = DateTimePickerWidget()
        self.start_time_picker.setEnabled(False)
        time_layout.addWidget(self.start_time_picker, 0, 1)
        
        time_layout.addWidget(QLabel("结束:"), 1, 0)
        self.end_time_picker = DateTimePickerWidget()
        self.end_time_picker.setEnabled(False)
        time_layout.addWidget(self.end_time_picker, 1, 1)
        
        layout.addLayout(time_layout)
        
        # 命令过滤
        self.cmd_filter_check = QCheckBox("启用命令过滤")
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
        self.start_time_picker.setEnabled(checked)
        self.end_time_picker.setEnabled(checked)
    
    def _on_cmd_filter_toggled(self, checked: bool):
        """命令过滤启用状态变化"""
        self.include_cmd_combo.setEnabled(checked)
        self.exclude_cmd_combo.setEnabled(checked)
    
    def set_commands(self, commands: List[Tuple[str, str]]):
        """设置可用的命令列表 [(cmd_id, display_text), ...]"""
        self.include_cmd_combo.set_items(commands)
        self.exclude_cmd_combo.set_items(commands)
    
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


class ActionWidget(QGroupBox):
    """操作按钮组件"""
    
    # 信号
    parse_clicked = Signal()
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
        self.parse_btn.setEnabled(not parsing)
        self.validate_btn.setEnabled(not parsing)
        if parsing:
            self.parse_btn.setText("⏳ 解析中...")
        else:
            self.parse_btn.setText("▶ 开始解析")


class DetailPanel(QWidget):
    """右侧详情面板"""
    
    # 信号
    parse_clicked = Signal()
    validate_clicked = Signal()
    open_output_dir_clicked = Signal()
    select_log_clicked = Signal()  # 选择日志文件
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
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
        self.action_widget.parse_clicked.connect(self.parse_clicked.emit)
        self.action_widget.validate_clicked.connect(self.validate_clicked.emit)
        self.action_widget.open_output_dir_clicked.connect(
            self.open_output_dir_clicked.emit
        )
        # 日志选择按钮
        self.detail_widget.select_log_btn.clicked.connect(
            self.select_log_clicked.emit
        )
    
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
    ):
        """更新协议信息"""
        self.detail_widget.update_info(
            name, config_path, config_valid,
            log_path, log_exists, log_size,
            cmd_count, enum_count, type_count
        )
        
        # 更新命令过滤选项
        if commands:
            self.filter_widget.set_commands(commands)
    
    def get_filter_settings(self) -> Dict[str, Any]:
        """获取过滤设置"""
        return {
            'time_range': self.filter_widget.get_time_filter(),
            'include_cmds': self.filter_widget.get_include_cmds(),
            'exclude_cmds': self.filter_widget.get_exclude_cmds(),
        }
    
    def set_parsing(self, parsing: bool):
        """设置解析状态"""
        self.action_widget.set_parsing(parsing)
    
    def clear(self):
        """清空面板"""
        self.detail_widget.clear()
        self.filter_widget.clear()
