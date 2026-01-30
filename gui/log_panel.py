# gui/log_panel.py
"""
文件名称: log_panel.py
内容摘要: 底部日志输出面板，包含实时日志显示和进度条（MVP 架构 - View 层）
当前版本: v1.1.0
作者: lanford
创建日期: 2024-12-24
"""

from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit,
    QProgressBar, QPushButton, QLabel
)
from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtGui import QTextCursor, QColor

from gui.views import ILogPanelView


class LogPanel(QWidget, ILogPanelView):
    """日志面板（MVP 架构 - View 层）

    只负责日志显示和用户交互，不处理业务逻辑
    """

    # === 信号：用户事件（向 Presenter 发送） ===
    clear_clicked = Signal()  # 点击清空按钮

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 日志输出分组
        group = QGroupBox("输出日志")
        group_layout = QVBoxLayout(group)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        group_layout.addWidget(self.log_text)
        
        # 进度条和操作
        bottom_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        bottom_layout.addWidget(self.progress_bar, 1)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        bottom_layout.addWidget(self.clear_btn)
        
        group_layout.addLayout(bottom_layout)
        
        layout.addWidget(group)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%H:%M:%S")
    
    def _append_html(self, html: str):
        """追加HTML内容"""
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertHtml(html)
        self.log_text.insertPlainText("\n")
        self.log_text.moveCursor(QTextCursor.End)
    
    @Slot(str)
    def log_info(self, message: str) -> None:
        """输出信息日志

        Args:
            message: 日志消息
        """
        timestamp = self._get_timestamp()
        html = f'<span style="color: #569cd6;">[{timestamp}]</span> {message}'
        self._append_html(html)

    @Slot(str)
    def log_success(self, message: str) -> None:
        """输出成功日志（绿色）

        Args:
            message: 日志消息
        """
        timestamp = self._get_timestamp()
        html = f'<span style="color: #569cd6;">[{timestamp}]</span> <span style="color: #4ec9b0;">✅ {message}</span>'
        self._append_html(html)

    @Slot(str)
    def log_warning(self, message: str) -> None:
        """输出警告日志（橙色）

        Args:
            message: 日志消息
        """
        timestamp = self._get_timestamp()
        html = f'<span style="color: #569cd6;">[{timestamp}]</span> <span style="color: #dcdcaa;">⚠️ {message}</span>'
        self._append_html(html)

    @Slot(str)
    def log_error(self, message: str) -> None:
        """输出错误日志（红色）

        Args:
            message: 日志消息
        """
        timestamp = self._get_timestamp()
        html = f'<span style="color: #569cd6;">[{timestamp}]</span> <span style="color: #f14c4c;">❌ {message}</span>'
        self._append_html(html)
    
    @Slot(int, int)
    def set_progress(self, current: int, total: int) -> None:
        """设置进度条

        Args:
            current: 当前进度值
            total: 总进度值
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{current}/{total} ({percentage}%)")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0%")

    @Slot(int)
    def set_progress_value(self, value: int) -> None:
        """直接设置进度值（百分比）

        Args:
            value: 进度百分比 (0-100)
        """
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{value}%")

    @Slot()
    def reset_progress(self) -> None:
        """重置进度条（归零）"""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")

    @Slot()
    def clear_log(self) -> None:
        """清空日志"""
        self.log_text.clear()
        self.reset_progress()

    def set_log_text(self, text: str) -> None:
        """直接设置日志文本

        Args:
            text: 日志文本内容
        """
        self.log_text.setPlainText(text)

    @Slot()
    def _on_clear_clicked(self) -> None:
        """处理清空按钮点击事件（内部方法）

        发射信号给 Presenter 处理
        """
        self.clear_clicked.emit()
