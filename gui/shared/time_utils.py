"""
文件名称: time_utils.py
内容摘要: 统一时间处理工具集
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-24
"""

from datetime import datetime
from typing import Optional


# ==================== 时间范围格式化 ====================

def format_time_range_smart(
    start: datetime,
    end: datetime,
    *,
    separator: str = " ~ "
) -> str:
    """
    智能格式化时间范围显示字符串

    根据时间跨度自动调整显示格式(始终包含秒):
    - 同一天: HH:MM:SS ~ HH:MM:SS
    - 跨天同年: MM-DD HH:MM:SS ~ MM-DD HH:MM:SS
    - 跨年: YYYY-MM-DD HH:MM:SS ~ YYYY-MM-DD HH:MM:SS

    Args:
        start: 起始时间
        end: 结束时间
        separator: 分隔符,默认 " ~ "

    Returns:
        str: 格式化后的时间范围字符串

    Raises:
        ValueError: 当 start 或 end 为 None,或 start > end 时

    Examples:
        >>> start = datetime(2025, 1, 23, 8, 0, 0)
        >>> end = datetime(2025, 1, 23, 18, 0, 0)
        >>> format_time_range_smart(start, end)
        '08:00:00 ~ 18:00:00'
    """
    # 参数验证
    if start is None:
        raise ValueError("起始时间不能为 None")
    if end is None:
        raise ValueError("结束时间不能为 None")
    if start > end:
        raise ValueError(f"起始时间 {start} 不能晚于结束时间 {end}")

    # 同一个时间点: 使用完整格式
    if start == end:
        return _format_single_time(start)

    # 判断时间跨度
    is_same_day = start.date() == end.date()
    is_same_year = start.year == end.year

    # 选择格式(始终包含秒)
    if is_same_day:
        # 同一天: 只显示时分秒
        fmt = "%H:%M:%S"
    elif is_same_year:
        # 跨天但同年: 显示月日+时分秒
        fmt = "%m-%d %H:%M:%S"
    else:
        # 跨年: 显示完整日期+时分秒
        fmt = "%Y-%m-%d %H:%M:%S"

    start_str = start.strftime(fmt)
    end_str = end.strftime(fmt)

    return f"{start_str}{separator}{end_str}"


def format_time_smart(
    dt: datetime,
    *,
    reference: Optional[datetime] = None
) -> str:
    """
    格式化单个时间点(可选择性包含日期)

    Args:
        dt: 要格式化的时间
        reference: 参考时间(用于判断是否需要显示日期)
                  如果为 None,显示完整格式

    Returns:
        str: 格式化的时间字符串

    Examples:
        >>> dt = datetime(2025, 1, 23, 12, 30, 45)
        >>> format_time_smart(dt)
        '2025-01-23 12:30:45'
    """
    if reference is None:
        # 无参考点,显示完整格式
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # 根据与参考时间的关系决定格式
    is_same_day = dt.date() == reference.date()

    if is_same_day:
        # 同一天: 只显示时间
        return dt.strftime("%H:%M:%S")
    elif dt.year == reference.year:
        # 同年: 显示月日+时间
        return dt.strftime("%m-%d %H:%M:%S")
    else:
        # 不同年: 显示完整日期
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_single_time(dt: datetime) -> str:
    """
    格式化单个时间点

    策略: 始终使用完整格式(包含日期)
    因为单个时间点无法判断是否需要日期信息

    Args:
        dt: 要格式化的时间

    Returns:
        str: 完整格式的时间字符串
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ==================== 时间跨度格式化 ====================

def format_time_span_smart(seconds: float) -> str:
    """
    格式化时间跨度为人类可读字符串

    Args:
        seconds: 时间跨度(秒)

    Returns:
        str: 格式化后的时间跨度字符串

    Examples:
        >>> format_time_span_smart(45)
        '45秒'
        >>> format_time_span_smart(150)
        '2.5分钟'
        >>> format_time_span_smart(7200)
        '2.0小时'
        >>> format_time_span_smart(172800)
        '2.0天'
    """
    if seconds < 60:
        return f"{seconds:.0f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}小时"
    else:
        days = seconds / 86400
        return f"{days:.1f}天"


# ==================== 时间范围验证 ====================

def validate_time_range(start: datetime, end: datetime) -> bool:
    """
    验证时间范围是否有效

    Args:
        start: 起始时间
        end: 结束时间

    Returns:
        bool: 如果时间范围有效返回 True,否则返回 False

    Examples:
        >>> start = datetime(2025, 1, 23, 8, 0, 0)
        >>> end = datetime(2025, 1, 23, 18, 0, 0)
        >>> validate_time_range(start, end)
        True
    """
    if start is None or end is None:
        return False
    return start <= end
