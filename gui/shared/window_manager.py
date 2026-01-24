"""
文件名称: window_manager.py
内容摘要: 窗口管理混入类 - 提供可复用的窗口管理功能
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-24
"""

from typing import Optional
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent


class ThemeManagerMixin:
    """主题管理混入类"""

    def _setup_theme_manager(
        self,
        settings: QSettings,
        theme_getter_func,
        default_theme: str = "dark"
    ) -> None:
        """
        初始化主题管理器

        Args:
            settings: QSettings 实例
            theme_getter_func: 获取主题样式的函数,签名为 (theme: str) -> str
            default_theme: 默认主题,默认为 "dark"
        """
        self._settings = settings
        self._current_theme = settings.value("theme", default_theme)
        self._theme_getter_func = theme_getter_func
        self._theme_group: Optional[QActionGroup] = None

        # 子类应该调用此方法后在菜单中添加主题选项
        # 然后调用 _create_theme_menu_actions() 创建主题菜单

    def _create_theme_menu_actions(self, menu, themes: list = None) -> None:
        """
        创建主题菜单动作

        Args:
            menu: 要添加主题动作的菜单对象
            themes: 主题列表,默认为 ["dark", "light"]
        """
        if themes is None:
            themes = ["dark", "light"]

        self._theme_group = QActionGroup(self)

        theme_names = {
            "dark": "深色主题",
            "light": "浅色主题"
        }

        for theme in themes:
            action = QAction(theme_names.get(theme, theme), self)
            action.setCheckable(True)
            action.setData(theme)
            self._theme_group.addAction(action)
            menu.addAction(action)

            # 设置当前主题选中状态
            if theme == self._current_theme:
                action.setChecked(True)

        # 连接主题切换信号
        self._theme_group.triggered.connect(self._on_theme_changed)

    def _on_theme_changed(self, action: QAction) -> None:
        """
        主题切换回调

        Args:
            action: 被触发的主题动作
        """
        theme = action.data()
        if theme != self._current_theme:
            self._current_theme = theme
            self._apply_theme(theme)
            self._settings.setValue("theme", theme)

    def _apply_theme(self, theme: str) -> None:
        """
        应用主题样式

        Args:
            theme: 主题名称 ("dark" 或 "light")
        """
        app = QApplication.instance()
        if app and hasattr(self, '_theme_getter_func'):
            app.setStyleSheet(self._theme_getter_func(theme))


class WindowStateMixin:
    """窗口状态管理混入类"""

    def _setup_window_state_manager(
        self,
        settings: QSettings,
        default_width: int = 1200,
        default_height: int = 800
    ) -> None:
        """
        初始化窗口状态管理器

        Args:
            settings: QSettings 实例
            default_width: 默认窗口宽度
            default_height: 默认窗口高度
        """
        self._settings = settings
        self._default_width = default_width
        self._default_height = default_height

    def _restore_window_state(self) -> None:
        """恢复窗口状态"""
        # 尝试恢复窗口几何信息
        geometry = self._settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # 默认大小和居中
            self.resize(self._default_width, self._default_height)
            self._center_on_screen()

    def _save_window_state(self) -> None:
        """保存窗口状态"""
        self._settings.setValue("window/geometry", self.saveGeometry())

    def _center_on_screen(self) -> None:
        """将窗口居中显示在屏幕中央"""
        screen = QApplication.primaryScreen().geometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        窗口关闭事件

        Args:
            event: 关闭事件对象
        """
        # 保存窗口状态
        self._save_window_state()
        # 调用父类的 closeEvent (如果存在)
        if hasattr(super(), 'closeEvent'):
            super().closeEvent(event)
        else:
            event.accept()


class DialogHelperMixin:
    """对话框辅助混入类"""

    def _show_about_dialog(
        self,
        title: str = "关于 V8Parse",
        version: str = "1.0.0",
        extra_info: str = ""
    ) -> None:
        """
        显示关于对话框

        Args:
            title: 对话框标题
            version: 版本号
            extra_info: 额外信息(HTML格式)
        """
        content = f"""
        <h3>{title}</h3>
        <p>版本: {version}</p>
        <p>基于 YAML 配置的现代化协议解析框架</p>
        <p>支持零代码扩展新协议</p>
        {extra_info}
        """

        QMessageBox.about(
            self,
            f"关于 {title}",
            content
        )
