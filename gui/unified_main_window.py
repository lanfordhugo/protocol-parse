"""
文件名称: unified_main_window.py
内容摘要: 统一主窗口 - 带侧边栏导航的整合窗口（MVP 组装点）
当前版本: v2.0.0
作者: lanford
创建日期: 2025-01-10
修改日期: 2025-02-08
修改说明: 添加 MVP 组装逻辑
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
from .wave_replay_page import WaveReplayPage
from shared import get_unified_theme
from tcp_log.server_panel import TcpServerPage
from gui.shared import ThemeManagerMixin, WindowStateMixin, DialogHelperMixin
from gui.config import CONFIGS_DIR, TCP_OUTPUT_DIR
from gui.models.protocol_model import ProtocolModel
from gui.models.parse_model import ParseModel
from gui.presenters.normal_parse_presenter import NormalParsePresenter
from gui.wave.models.wave_data_manager import WaveDataManager
from gui.wave.presenters.replay_presenter import ReplayPresenter
from tcp_log.models.tcp_server_model import TcpServerModel
from tcp_log.presenters.tcp_server_presenter import TcpServerPresenter


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

        # 创建页面
        self._normal_page = None
        self._tcp_server_page = None
        self._wave_replay_page = None

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
        self._normal_page.status_changed.connect(self._update_status)
        self._stacked_widget.addWidget(self._normal_page)

        # 页面 2：TCP 服务端
        self._tcp_server_page = TcpServerPage()
        self._tcp_server_page.status_changed.connect(self._update_status)
        self._stacked_widget.addWidget(self._tcp_server_page)

        # 页面 3：数据回放
        self._wave_replay_page = WaveReplayPage()
        self._wave_replay_page.status_changed.connect(self._update_status)
        self._stacked_widget.addWidget(self._wave_replay_page)

        content_layout.addWidget(self._stacked_widget)

        main_layout.addWidget(content_widget, 1)  # 拉伸因子 1

        # 状态栏（共享）—— 必须在 MVP 组装之前创建，因为 Presenter 初始化会触发状态更新
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status("就绪")

        # MVP 组装：创建 Model 和 Presenter，注入 View（放在 status_bar 之后）
        self._setup_mvp()

    def _setup_mvp(self):
        """组装 MVP 架构：创建 Model 和 Presenter，注入 View"""
        # NormalParsePage MVP
        protocol_model = ProtocolModel(CONFIGS_DIR)
        parse_model = ParseModel()
        self._normal_presenter = NormalParsePresenter(
            view=self._normal_page,
            protocol_model=protocol_model,
            parse_model=parse_model,
            settings=self._settings,
        )
        self._normal_page.set_presenter(self._normal_presenter)

        # TcpServerPage MVP
        tcp_model = TcpServerModel(
            configs_dir=CONFIGS_DIR,
            save_dir=TCP_OUTPUT_DIR,
        )
        self._tcp_presenter = TcpServerPresenter(
            view=self._tcp_server_page,
            model=tcp_model,
            server=self._tcp_server_page._server,
        )
        self._tcp_server_page.set_presenter(self._tcp_presenter)

        # WaveReplayPage MVP
        replay_data_manager = WaveDataManager()
        self._replay_presenter = ReplayPresenter(
            view=self._wave_replay_page,
            data_manager=replay_data_manager,
        )
        self._wave_replay_page.set_presenter(self._replay_presenter)

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

        replay_action = QAction("数据回放(&3)", self)
        replay_action.setShortcut("Ctrl+3")
        replay_action.triggered.connect(lambda: self._on_page_requested('wave_replay'))
        view_menu.addAction(replay_action)

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
        elif page == 'wave_replay':
            self._stacked_widget.setCurrentWidget(self._wave_replay_page)
            self._sidebar.set_current_page('wave_replay')
            self._current_page = 'wave_replay'
            self._update_status("数据回放")

    def _on_next_page(self):
        """切换到下一个页面(Ctrl+Tab)"""
        pages = ['normal', 'tcp_server', 'wave_replay']
        idx = pages.index(self._current_page) if self._current_page in pages else 0
        next_page = pages[(idx + 1) % len(pages)]
        self._on_page_requested(next_page)

    def _update_status(self, message: str) -> None:
        """更新状态栏"""
        self.status_bar.showMessage(message)

    # ============== 数据回放页面快捷接口 ==============

    def switch_to_wave_replay_with_entries(
        self,
        entries,
        source_name: str = "外部数据",
    ) -> int:
        """
        切换到数据回放页面并加载数据

        Args:
            entries: 解析条目列表 [(timestamp_str, content, cmd_id, direction), ...]
            source_name: 数据源名称

        Returns:
            加载的数据点数量
        """
        self._on_page_requested('wave_replay')
        return self._wave_replay_page.load_entries(entries, source_name)

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        # 清理页面资源
        if self._normal_page and hasattr(self._normal_page, 'cleanup'):
            self._normal_page.cleanup()

        if self._tcp_server_page and hasattr(self._tcp_server_page, 'cleanup'):
            self._tcp_server_page.cleanup()

        if self._wave_replay_page and hasattr(self._wave_replay_page, 'cleanup'):
            self._wave_replay_page.cleanup()

        # 调用Mixin的closeEvent保存窗口状态
        super().closeEvent(event)
