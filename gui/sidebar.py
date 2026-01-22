"""
文件名称: sidebar.py
内容摘要: 侧边栏导航组件
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-10
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
)
from PySide6.QtCore import Qt, Signal


class Sidebar(QWidget):
    """侧边栏导航组件"""

    # 信号：页面切换请求
    page_requested = Signal(str)  # 'normal' 或 'tcp_server'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 'normal'
        self._normal_btn = None
        self._tcp_btn = None
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 固定宽度：180px（更紧凑）
        self.setFixedWidth(180)
        self.setObjectName("sidebar_container")

        # 标题区域
        title_widget = self._create_title_widget()
        layout.addWidget(title_widget)

        # 导航按钮区域
        nav_group = QGroupBox("功能导航")
        nav_layout = QVBoxLayout(nav_group)
        nav_layout.setSpacing(4)
        nav_layout.setContentsMargins(8, 8, 8, 8)

        # 普通解析按钮
        self._normal_btn = self._create_nav_button(
            icon="📋",
            text="普通解析",
            description="批量解析日志文件",
            checked=True
        )
        nav_layout.addWidget(self._normal_btn)

        # TCP 服务端按钮
        self._tcp_btn = self._create_nav_button(
            icon="🌐",
            text="TCP 服务端",
            description="实时接收并解析报文"
        )
        nav_layout.addWidget(self._tcp_btn)

        layout.addWidget(nav_group)

        # 底部信息区域（可选）
        layout.addStretch()

        # 版本信息
        version_label = QLabel("V8Parse v1.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #888; font-size: 11px; padding: 8px;")
        layout.addWidget(version_label)

    def _create_title_widget(self) -> QWidget:
        """创建标题区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 12, 8, 8)

        title = QLabel("V8Parse")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #6c8cd5;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("多协议通信报文解析工具")
        subtitle.setStyleSheet("font-size: 11px; color: #a8b4ce;")
        subtitle.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        return widget

    def _create_nav_button(self, icon: str, text: str, description: str, checked: bool = False) -> QWidget:
        """创建导航按钮（自定义样式）"""
        widget = QWidget()
        widget.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # 图标 + 文本
        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")

        text_label = QLabel(text)
        text_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        top_row.addWidget(icon_label)
        top_row.addWidget(text_label)
        top_row.addStretch()

        # 描述文本
        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 10px; color: #888;")

        layout.addLayout(top_row)
        layout.addWidget(desc_label)

        # 设置对象名称用于样式定制
        widget.setObjectName(f"nav_{text}")

        # 选中状态管理
        if checked:
            widget.setProperty("selected", True)

        # 点击事件
        widget.mousePressEvent = lambda e: self._on_nav_clicked(widget, text)

        return widget

    def _on_nav_clicked(self, widget: QWidget, text: str, emit_signal: bool = True):
        """导航按钮点击处理

        Args:
            widget: 被点击的按钮 widget
            text: 按钮文本
            emit_signal: 是否发射页面切换信号（避免循环调用）
        """
        # 取消所有按钮选中状态
        for child in self.findChildren(QWidget):
            if child.objectName().startswith("nav_"):
                child.setProperty("selected", False)
                child.style().unpolish(child)
                child.style().polish(child)

        # 设置当前按钮选中
        widget.setProperty("selected", True)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

        # 发送页面切换信号（如果不是程序调用）
        if emit_signal:
            if text == "普通解析":
                self.page_requested.emit('normal')
            elif text == "TCP 服务端":
                self.page_requested.emit('tcp_server')

    def set_current_page(self, page: str):
        """设置当前页面（外部调用，不发射信号）"""
        self._current_page = page
        # 更新按钮状态（不发射信号，避免循环）
        if page == 'normal':
            self._on_nav_clicked(self._normal_btn, "普通解析", emit_signal=False)
        elif page == 'tcp_server':
            self._on_nav_clicked(self._tcp_btn, "TCP 服务端", emit_signal=False)
