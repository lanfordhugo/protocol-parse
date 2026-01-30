"""
文件名称: theme_manager.py
内容摘要: GUI 主题管理器，提供主题切换和应用功能
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget

from .color_schemes import COLOR_SCHEMES, LOG_PANEL_STYLES


class ThemeManager:
    """主题管理器

    负责管理应用程序主题，包括主题切换、应用主题等功能。
    支持深色和浅色两种主题模式。

    Attributes:
        current_theme: 当前主题名称（"dark" 或 "light"）
    """

    # 支持的主题列表
    AVAILABLE_THEMES = ["dark", "light"]

    def __init__(self, default_theme: str = "dark") -> None:
        """初始化主题管理器

        Args:
            default_theme: 默认主题名称，默认为 "dark"

        Raises:
            ValueError: 当默认主题不在支持列表中时
        """
        if default_theme not in self.AVAILABLE_THEMES:
            raise ValueError(
                f"不支持的主题: {default_theme}。"
                f"可用主题: {', '.join(self.AVAILABLE_THEMES)}"
            )

        self.current_theme = default_theme

    def get_theme(self, theme_name: Optional[str] = None) -> str:
        """获取主题样式表

        Args:
            theme_name: 主题名称，如果为 None 则使用当前主题

        Returns:
            主题样式表字符串

        Examples:
            >>> manager = ThemeManager()
            >>> style = manager.get_theme("dark")
            >>> widget.setStyleSheet(style)
        """
        if theme_name is None:
            theme_name = self.current_theme

        return COLOR_SCHEMES.get(theme_name, COLOR_SCHEMES["dark"])

    def get_log_panel_style(self, theme_name: Optional[str] = None) -> str:
        """获取日志面板专用样式表

        Args:
            theme_name: 主题名称，如果为 None 则使用当前主题

        Returns:
            日志面板样式表字符串

        Examples:
            >>> manager = ThemeManager()
            >>> style = manager.get_log_panel_style("dark")
            >>> log_text_edit.setStyleSheet(style)
        """
        if theme_name is None:
            theme_name = self.current_theme

        return LOG_PANEL_STYLES.get(theme_name, LOG_PANEL_STYLES["dark"])

    def set_theme(self, theme_name: str) -> None:
        """设置当前主题

        Args:
            theme_name: 主题名称

        Raises:
            ValueError: 当主题名称不在支持列表中时

        Examples:
            >>> manager = ThemeManager()
            >>> manager.set_theme("light")
        """
        if theme_name not in self.AVAILABLE_THEMES:
            raise ValueError(
                f"不支持的主题: {theme_name}。"
                f"可用主题: {', '.join(self.AVAILABLE_THEMES)}"
            )

        self.current_theme = theme_name

    def apply_theme(self, widget: QWidget, theme_name: Optional[str] = None) -> None:
        """为主题应用样式表

        Args:
            widget: 要应用样式的控件
            theme_name: 主题名称，如果为 None 则使用当前主题

        Examples:
            >>> manager = ThemeManager()
            >>> manager.apply_theme(main_window, "dark")
        """
        style = self.get_theme(theme_name)
        widget.setStyleSheet(style)

    def apply_theme_to_app(self, app: QApplication, theme_name: Optional[str] = None) -> None:
        """为应用程序应用主题

        Args:
            app: QApplication 实例
            theme_name: 主题名称，如果为 None 则使用当前主题

        Examples:
            >>> app = QApplication([])
            >>> manager = ThemeManager()
            >>> manager.apply_theme_to_app(app, "dark")
        """
        style = self.get_theme(theme_name)
        app.setStyle("Fusion")
        app.setStyleSheet(style)

    def toggle_theme(self) -> str:
        """切换主题（深色/浅色互换）

        Returns:
            切换后的主题名称

        Examples:
            >>> manager = ThemeManager("dark")
            >>> new_theme = manager.toggle_theme()  # 返回 "light"
        """
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme

    @classmethod
    def get_available_themes(cls) -> list[str]:
        """获取所有可用主题列表

        Returns:
            主题名称列表

        Examples:
            >>> themes = ThemeManager.get_available_themes()
            >>> print(themes)  # ['dark', 'light']
        """
        return cls.AVAILABLE_THEMES.copy()

    def is_dark_theme(self) -> bool:
        """判断当前是否为深色主题

        Returns:
            如果是深色主题返回 True，否则返回 False

        Examples:
            >>> manager = ThemeManager("dark")
            >>> manager.is_dark_theme()  # True
        """
        return self.current_theme == "dark"

    def is_light_theme(self) -> bool:
        """判断当前是否为浅色主题

        Returns:
            如果是浅色主题返回 True，否则返回 False

        Examples:
            >>> manager = ThemeManager("light")
            >>> manager.is_light_theme()  # True
        """
        return self.current_theme == "light"


# 全局便捷函数（向后兼容）
def get_theme(theme_name: str) -> str:
    """获取主题样式表（便捷函数）

    这是一个向后兼容的便捷函数，用于替代原来的 get_theme() 函数。

    Args:
        theme_name: 主题名称（"dark" 或 "light"）

    Returns:
        主题样式表字符串

    Examples:
        >>> style = get_theme("dark")
        >>> widget.setStyleSheet(style)
    """
    return COLOR_SCHEMES.get(theme_name, COLOR_SCHEMES["dark"])


def get_log_panel_style(theme_name: str) -> str:
    """获取日志面板专用样式表（便捷函数）

    这是一个向后兼容的便捷函数，用于替代原来的 get_log_panel_style() 函数。

    Args:
        theme_name: 主题名称（"dark" 或 "light"）

    Returns:
        日志面板样式表字符串

    Examples:
        >>> style = get_log_panel_style("dark")
        >>> log_text_edit.setStyleSheet(style)
    """
    return LOG_PANEL_STYLES.get(theme_name, LOG_PANEL_STYLES["dark"])
