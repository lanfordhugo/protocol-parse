"""
文件名称: color_schemes.py
内容摘要: GUI 主题颜色方案映射字典
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from typing import Dict

# 导入各个主题样式
from .dark_theme import DARK_THEME
from .light_theme import LIGHT_THEME
from .log_panel_styles import LOG_PANEL_DARK_STYLE, LOG_PANEL_LIGHT_STYLE

# 主题颜色方案映射
COLOR_SCHEMES: Dict[str, str] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}

# 日志面板样式映射
LOG_PANEL_STYLES: Dict[str, str] = {
    "dark": LOG_PANEL_DARK_STYLE,
    "light": LOG_PANEL_LIGHT_STYLE,
}
