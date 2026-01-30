"""
文件名称: unified_main_window.py
内容摘要: 统一主窗口 - 带侧边栏导航的整合窗口（MVP 架构）
当前版本: v2.0.0
作者: lanford
创建日期: 2025-01-10
更新日期: 2026-01-29（集成 MVP 架构）
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QStatusBar, QMessageBox, QApplication,
    QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QShortcut, QKeySequence

from .sidebar import Sidebar
from .normal_parse_page import NormalParsePage
from shared import get_unified_theme
from tcp_log.server_panel import TcpServerPage
from gui.shared import ThemeManagerMixin, WindowStateMixin, DialogHelperMixin

# MVP 架构导入
from gui.managers import ProtocolManager, ParseManager, ValidationManager
from gui.presenters import NormalParsePagePresenter


class UnifiedMainWindow(
    QMainWindow,
    ThemeManagerMixin,
    WindowStateMixin,
    DialogHelperMixin
):
    """统一主窗口 - 带侧边栏导航的整合窗口"""

    def __init__(self):
        super().__init__()
        self._current_page = 'normal'

        # 加载设置
        self._settings = QSettings("V8Parse", "UnifiedGUI")
        self._current_theme = self._settings.value("theme", "dark")

        # 初始化窗口管理混入类
        self._setup_window_state_manager(self._settings)
        self._setup_theme_manager(self._settings, get_unified_theme, "dark")

        # === MVP 架构：创建 Manager 层 ===
        from gui.shared import get_app_dir
        app_dir = get_app_dir()
        configs_dir = app_dir / "configs"
        output_dir = app_dir / "parsed_log"

        self.protocol_manager = ProtocolManager(configs_dir)
        self.parse_manager = ParseManager(output_dir)
        self.validation_manager = ValidationManager()

        # 创建页面（先创建 View）
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

        # === MVP 架构：创建普通解析页面 ===
        # 1. 先创建 View（不传入 Presenter，使用关键字参数）
        self._normal_page = NormalParsePage(presenter=None, parent=None)
        self._normal_page.set_settings(self._settings)
        self._normal_page.status_changed.connect(self._update_status)

        # 2. 创建 Presenter（传入 View 和 Manager）
        self.presenter = NormalParsePagePresenter(
            view=self._normal_page,
            parse_manager=self.parse_manager
        )

        # 3. 将 Presenter 设置回 View
        self._normal_page._presenter = self.presenter

        # 4. 调用 Presenter 初始化方法
        self.presenter.initialize()

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
        self._create_theme_menu_actions(theme_menu)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about_dialog)
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
        """切换到下一个页面(Ctrl+Tab)"""
        if self._current_page == 'normal':
            self._on_page_requested('tcp_server')
        else:
            self._on_page_requested('normal')

    def _update_status(self, message: str) -> None:
        """更新状态栏"""
        self.status_bar.showMessage(message)

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        # 清理页面资源
        if self._normal_page and hasattr(self._normal_page, 'cleanup'):
            self._normal_page.cleanup()

        if self._tcp_server_page and hasattr(self._tcp_server_page, 'cleanup'):
            self._tcp_server_page.cleanup()

        # 调用Mixin的closeEvent保存窗口状态
        super().closeEvent(event)
