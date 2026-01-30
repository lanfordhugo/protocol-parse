"""
GUI 主题模块

本模块提供完整的主题管理系统，包括颜色方案、主题管理器和主题 Mixin 类。

主要组件:
    - color_schemes: 定义深色/浅色主题的颜色方案
    - theme_manager: 主题管理器，提供主题切换和应用功能
    - theme_mixins: 为控件和窗口提供主题支持的 Mixin 类

使用示例:
    >>> from gui.themes import ThemeManager
    >>> manager = ThemeManager("dark")
    >>> manager.apply_theme_to_app(app)

    >>> from gui.themes import ThemedWindowMixin
    >>> class MyWindow(QMainWindow, ThemedWindowMixin):
    ...     pass
"""

# 从 color_schemes 模块导出颜色方案
from .color_schemes import (
    COLOR_SCHEMES,
    DARK_THEME,
    LIGHT_THEME,
    LOG_PANEL_DARK_STYLE,
    LOG_PANEL_LIGHT_STYLE,
    LOG_PANEL_STYLES,
)

# 从 theme_manager 模块导出主题管理器和便捷函数
from .theme_manager import ThemeManager, get_log_panel_style, get_theme

# 从 theme_mixins 模块导出 Mixin 类
from .theme_mixins import ThemedWindowMixin, ThemedWidgetMixin

# 版本信息
__version__ = "1.0.0"
__author__ = "lanford"

# 公共接口定义
__all__ = [
    # 颜色方案
    "DARK_THEME",
    "LIGHT_THEME",
    "COLOR_SCHEMES",
    "LOG_PANEL_DARK_STYLE",
    "LOG_PANEL_LIGHT_STYLE",
    "LOG_PANEL_STYLES",
    # 主题管理器和便捷函数
    "ThemeManager",
    "get_theme",
    "get_log_panel_style",
    # Mixin 类
    "ThemedWidgetMixin",
    "ThemedWindowMixin",
    # 版本信息
    "__version__",
    "__author__",
]
