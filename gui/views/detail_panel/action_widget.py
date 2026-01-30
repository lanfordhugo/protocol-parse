"""
文件名称: action_widget.py
内容摘要: 操作按钮组件
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import Optional
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Signal


class ActionWidget(QGroupBox):
    """操作按钮组件

    职责：
    - 提供解析/停止按钮
    - 提供验证配置按钮
    - 提供打开输出目录按钮
    - 管理按钮状态（解析中/未解析）

    信号：
    - parse_clicked: 点击解析按钮
    - stop_clicked: 点击停止按钮
    - validate_clicked: 点击验证按钮
    - open_output_dir_clicked: 点击打开输出目录
    """

    # 信号
    parse_clicked = Signal()
    stop_clicked = Signal()
    validate_clicked = Signal()
    open_output_dir_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("操作", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
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

    def set_parsing(self, parsing: bool) -> None:
        """设置解析状态

        Args:
            parsing: 是否正在解析
        """
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
