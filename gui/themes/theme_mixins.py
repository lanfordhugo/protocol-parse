"""
文件名称: theme_mixins.py
内容摘要: GUI 主题相关的 Mixin 类，为控件和窗口提供主题支持
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget

from .theme_manager import ThemeManager


class ThemedWidgetMixin:
    """主题控件 Mixin

    为 QWidget 及其子类提供自动应用主题的能力。

    Examples:
        >>> class MyWidget(QWidget, ThemedWidgetMixin):
        ...     def __init__(self):
        ...         super().__init__()
        ...         self.apply_current_theme()
    """

    def __init__(self, *args, **kwargs):
        """初始化 Mixin

        注意：此 Mixin 需要与 QWidget 或其子类配合使用。
        """
        # 不要调用 super().__init__()，让主类负责初始化
        self._theme_manager: Optional[ThemeManager] = None

    def get_theme_manager(self) -> ThemeManager:
        """获取主题管理器实例

        如果当前控件没有主题管理器，会创建一个新的默认实例。

        Returns:
            ThemeManager 实例
        """
        if self._theme_manager is None:
            self._theme_manager = ThemeManager()
        return self._theme_manager

    def set_theme_manager(self, manager: ThemeManager) -> None:
        """设置主题管理器

        Args:
            manager: 主题管理器实例
        """
        self._theme_manager = manager

    def apply_current_theme(self, theme_name: Optional[str] = None) -> None:
        """应用当前主题到控件

        Args:
            theme_name: 主题名称，如果为 None 则使用主题管理器的当前主题
        """
        if not isinstance(self, QWidget):
            raise TypeError(
                f"{self.__class__.__name__} 必须继承自 QWidget 才能使用此方法"
            )

        manager = self.get_theme_manager()
        manager.apply_theme(self, theme_name)

    def apply_theme_to_children(
        self, theme_name: Optional[str] = None, recursive: bool = True
    ) -> None:
        """为主题应用到所有子控件

        Args:
            theme_name: 主题名称，如果为 None 则使用主题管理器的当前主题
            recursive: 是否递归应用到所有后代控件，默认为 True
        """
        if not isinstance(self, QWidget):
            raise TypeError(
                f"{self.__class__.__name__} 必须继承自 QWidget 才能使用此方法"
            )

        manager = self.get_theme_manager()
        style = manager.get_theme(theme_name)

        # 应用到直接子控件
        for child in self.findChildren(QWidget):
            # 只处理直接子控件
            if child.parent() == self or not recursive:
                child.setStyleSheet(style)

            # 如果需要递归，继续处理子控件的子控件
            if recursive and hasattr(child, "apply_theme_to_children"):
                child.apply_theme_to_children(theme_name, recursive)

    def set_theme(self, theme_name: str) -> None:
        """设置并应用新主题

        Args:
            theme_name: 主题名称（"dark" 或 "light"）
        """
        manager = self.get_theme_manager()
        manager.set_theme(theme_name)
        self.apply_current_theme()

    def toggle_theme(self) -> str:
        """切换主题（深色/浅色互换）

        Returns:
            切换后的主题名称
        """
        manager = self.get_theme_manager()
        new_theme = manager.toggle_theme()
        self.apply_current_theme()
        return new_theme

    def is_dark_theme(self) -> bool:
        """判断当前是否为深色主题

        Returns:
            如果是深色主题返回 True，否则返回 False
        """
        manager = self.get_theme_manager()
        return manager.is_dark_theme()


class ThemedWindowMixin:
    """主题窗口 Mixin

    为 QMainWindow 及其子类提供全局主题管理能力。
    与 ThemedWidgetMixin 不同，此类会将主题应用到整个应用程序。

    Examples:
        >>> class MyWindow(QMainWindow, ThemedWindowMixin):
        ...     def __init__(self):
        ...         super().__init__()
        ...         self.apply_app_theme()
    """

    def __init__(self, *args, **kwargs):
        """初始化 Mixin

        注意：此 Mixin 需要与 QMainWindow 或其子类配合使用。
        """
        # 不要调用 super().__init__()，让主类负责初始化
        self._app_theme_manager: Optional[ThemeManager] = None

    def get_app_theme_manager(self) -> ThemeManager:
        """获取应用程序主题管理器实例

        如果当前窗口没有主题管理器，会创建一个新的默认实例。

        Returns:
            ThemeManager 实例
        """
        if self._app_theme_manager is None:
            self._app_theme_manager = ThemeManager()
        return self._app_theme_manager

    def set_app_theme_manager(self, manager: ThemeManager) -> None:
        """设置应用程序主题管理器

        Args:
            manager: 主题管理器实例
        """
        self._app_theme_manager = manager

    def apply_app_theme(self, theme_name: Optional[str] = None) -> None:
        """应用主题到整个应用程序

        Args:
            theme_name: 主题名称，如果为 None 则使用主题管理器的当前主题

        Raises:
            RuntimeError: 如果没有 QApplication 实例
        """
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("没有 QApplication 实例，无法应用主题")

        manager = self.get_app_theme_manager()
        manager.apply_theme_to_app(app, theme_name)

    def set_app_theme(self, theme_name: str) -> None:
        """设置并应用程序新主题

        Args:
            theme_name: 主题名称（"dark" 或 "light"）
        """
        manager = self.get_app_theme_manager()
        manager.set_theme(theme_name)
        self.apply_app_theme()

    def toggle_app_theme(self) -> str:
        """切换应用程序主题（深色/浅色互换）

        Returns:
            切换后的主题名称
        """
        manager = self.get_app_theme_manager()
        new_theme = manager.toggle_theme()
        self.apply_app_theme()
        return new_theme

    def is_app_dark_theme(self) -> bool:
        """判断应用程序当前是否为深色主题

        Returns:
            如果是深色主题返回 True，否则返回 False
        """
        manager = self.get_app_theme_manager()
        return manager.is_dark_theme()

    def get_log_panel_style(self) -> str:
        """获取日志面板样式

        Returns:
            日志面板样式表字符串
        """
        manager = self.get_app_theme_manager()
        return manager.get_log_panel_style()
