"""
文件名称: __init__.py
内容摘要: GUI共享工具模块包
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-24
"""

from .time_utils import (
    format_time_range_smart,
    format_time_smart,
    format_time_span_smart,
    validate_time_range
)
from .window_manager import (
    ThemeManagerMixin,
    WindowStateMixin,
    DialogHelperMixin
)
from .app_helpers import (
    get_app_dir,
    open_directory,
    open_file
)

__all__ = [
    # 时间工具
    'format_time_range_smart',
    'format_time_smart',
    'format_time_span_smart',
    'validate_time_range',
    # 窗口管理混入类
    'ThemeManagerMixin',
    'WindowStateMixin',
    'DialogHelperMixin',
    # 应用辅助函数
    'get_app_dir',
    'open_directory',
    'open_file'
]
