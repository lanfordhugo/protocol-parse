"""
文件名称: protocol_detail_widget.py
内容摘要: 协议详情显示组件
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import Optional
from PySide6.QtWidgets import (
    QGroupBox, QLabel, QGridLayout, QFrame, QHBoxLayout,
    QSizePolicy, QPushButton, QWidget
)


class ProtocolDetailWidget(QGroupBox):
    """协议详情显示组件

    职责：
    - 显示协议基本信息（名称、配置文件、日志文件）
    - 显示配置和日志状态
    - 显示统计信息（命令数、枚举数、类型数）
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("协议详情", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
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
    ) -> None:
        """更新协议详情

        Args:
            name: 协议名称
            config_path: 配置文件路径
            config_valid: 配置是否有效
            log_path: 日志文件路径
            log_exists: 日志是否存在
            log_size: 日志文件大小
            cmd_count: 命令数量
            enum_count: 枚举数量
            type_count: 类型数量
        """
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
        """格式化文件大小

        Args:
            size: 文件大小（字节）

        Returns:
            格式化后的文件大小字符串
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def clear(self) -> None:
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
