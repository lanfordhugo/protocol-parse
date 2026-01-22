"""
文件名称: unified_main_window.py
内容摘要: 统一主窗口 - 带侧边栏导航的整合窗口
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-10
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QStatusBar, QMessageBox, QApplication,
    QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QActionGroup, QShortcut, QKeySequence

from .sidebar import Sidebar
from .normal_parse_page import NormalParsePage
from shared import get_unified_theme
from tcp_log.server_panel import TcpServerPage


class PlaceholderPage(QWidget):
    """占位页面（临时使用）"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        from PySide6.QtWidgets import QLabel
        label = QLabel(f"{title}\n\n功能开发中...")
        label.setStyleSheet("font-size: 24px; color: #888;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)


class UnifiedMainWindow(QMainWindow):
    """统一主窗口 - 带侧边栏导航的整合窗口"""

    def __init__(self):
        super().__init__()
        self._current_page = 'normal'

        # 加载设置
        self._settings = QSettings("V8Parse", "UnifiedGUI")
        self._current_theme = self._settings.value("theme", "dark")

        # 创建页面
        self._normal_page = None
        self._tcp_server_page = None

        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._apply_theme(self._current_theme)

        # 恢复上次打开的页面
        last_page = self._settings.value("last_page", "normal")
        self._switch_to_page(last_page)

    def _setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("V8Parse - 多协议通信报文解析工具")
        self.setMinimumSize(1200, 800)

        # 恢复窗口状态
        self._restore_window_state()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 左侧：侧边栏 ===
        self._sidebar = Sidebar()
        self._sidebar.page_requested.connect(self._on_page_requested)
        main_layout.addWidget(self._sidebar)

        # === 右侧：内容区域 ===
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)

        # 页面堆叠（切换显示）
        self._stacked_widget = QStackedWidget()

        # 页面 1：普通解析
        self._normal_page = NormalParsePage()
        self._normal_page.set_settings(self._settings)
        self._normal_page.status_changed.connect(self._update_status)
        self._stacked_widget.addWidget(self._normal_page)

        # 页面 2：TCP 服务端
        self._tcp_server_page = TcpServerPage()
        self._tcp_server_page.status_changed.connect(self._update_status)
        self._stacked_widget.addWidget(self._tcp_server_page)

        content_layout.addWidget(self._stacked_widget)

        main_layout.addWidget(content_widget, 1)  # 拉伸因子 1

        # 状态栏（共享）
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status("就绪")

    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        # 页面切换
        normal_action = QAction("普通解析(&1)", self)
        normal_action.setShortcut("Ctrl+1")
        normal_action.triggered.connect(lambda: self._on_page_requested('normal'))
        view_menu.addAction(normal_action)

        tcp_action = QAction("TCP 服务端(&2)", self)
        tcp_action.setShortcut("Ctrl+2")
        tcp_action.triggered.connect(lambda: self._on_page_requested('tcp_server'))
        view_menu.addAction(tcp_action)

        view_menu.addSeparator()

        # 主题子菜单
        theme_menu = view_menu.addMenu("界面风格")

        # 主题选项组（互斥）
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)

        # 深色主题
        dark_action = QAction("深色主题", self)
        dark_action.setCheckable(True)
        dark_action.setData("dark")
        self._theme_group.addAction(dark_action)
        theme_menu.addAction(dark_action)

        # 浅色主题
        light_action = QAction("浅色主题", self)
        light_action.setCheckable(True)
        light_action.setData("light")
        self._theme_group.addAction(light_action)
        theme_menu.addAction(light_action)

        # 设置当前主题选中状态
        if self._current_theme == "dark":
            dark_action.setChecked(True)
        else:
            light_action.setChecked(True)

        # 连接主题切换信号
        self._theme_group.triggered.connect(self._on_theme_changed)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+Tab: 顺序切换页面
        shortcut_tab = QShortcut(QKeySequence("Ctrl+Tab"), self)
        shortcut_tab.activated.connect(self._on_next_page)

    def _on_page_requested(self, page: str):
        """页面切换请求"""
        if page == self._current_page:
            return

        self._switch_to_page(page)

        # 保存设置
        self._settings.setValue("last_page", page)

    def _switch_to_page(self, page: str):
        """切换到指定页面"""
        if page == 'normal':
            self._stacked_widget.setCurrentWidget(self._normal_page)
            self._sidebar.set_current_page('normal')
            self._current_page = 'normal'
            self._update_status("普通解析")
        elif page == 'tcp_server':
            self._stacked_widget.setCurrentWidget(self._tcp_server_page)
            self._sidebar.set_current_page('tcp_server')
            self._current_page = 'tcp_server'
            self._update_status("TCP 服务端")

    def _on_next_page(self):
        """切换到下一个页面（Ctrl+Tab）"""
        if self._current_page == 'normal':
            self._on_page_requested('tcp_server')
        else:
            self._on_page_requested('normal')

    def _on_theme_changed(self, action: QAction):
        """主题切换"""
        theme = action.data()
        if theme != self._current_theme:
            self._current_theme = theme
            self._apply_theme(theme)
            self._settings.setValue("theme", theme)

    def _apply_theme(self, theme: str):
        """应用主题"""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_unified_theme(theme))

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 V8Parse",
            "<h3>V8Parse - 多协议通信报文解析工具</h3>"
            "<p>版本: 1.0.0</p>"
            "<p>基于 YAML 配置的现代化协议解析框架</p>"
            "<p>支持零代码扩展新协议</p>"
            "<p>功能模块：</p>"
            "<ul>"
            "<li>📋 普通解析 - 批量解析日志文件</li>"
            "<li>🌐 TCP 服务端 - 实时接收并解析报文</li>"
            "</ul>"
        )

    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.showMessage(message)

    def _restore_window_state(self):
        """恢复窗口状态"""
        # 尝试恢复窗口几何信息
        geometry = self._settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # 默认大小和居中
            self.resize(1200, 800)
            self._center_on_screen()

    def _save_window_state(self):
        """保存窗口状态"""
        self._settings.setValue("window/geometry", self.saveGeometry())

    def _center_on_screen(self):
        """将窗口居中显示在屏幕中央"""
        screen = QApplication.primaryScreen().geometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 保存窗口状态
        self._save_window_state()
        event.accept()
