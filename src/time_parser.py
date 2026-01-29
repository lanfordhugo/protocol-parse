# time_parser.py - 时间范围解析器
"""
时间范围解析器模块，支持绝对时间和相对时间的解析。

功能：
1. 解析绝对时间（YYYY-MM-DD HH:MM:SS）
2. 解析相对时间（如 1h, 24h, 7d）
3. 时间格式验证
4. 时间范围计算
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


class TimeParser:
    """时间解析器类，支持多种时间格式"""

    # 绝对时间格式（支持多种变体）
    ABSOLUTE_TIME_PATTERNS = [
        # YYYY-MM-DD HH:MM:SS
        re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})$"),
        # YYYY-MM-DD HH:MM
        re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})$"),
        # YYYY-MM-DD
        re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"),
    ]

    # 相对时间格式（数字+单位）
    RELATIVE_TIME_PATTERN = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)

    # 时间单位映射（单位 -> 秒数）
    TIME_UNITS = {
        "s": 1,  # 秒
        "m": 60,  # 分钟
        "h": 3600,  # 小时
        "d": 86400,  # 天
    }

    @staticmethod
    def parse_absolute_time(time_str: str) -> Optional[datetime]:
        """
        解析绝对时间字符串

        参数:
            time_str: 时间字符串，支持格式：
                      - "YYYY-MM-DD HH:MM:SS"
                      - "YYYY-MM-DD HH:MM"
                      - "YYYY-MM-DD"

        返回:
            datetime 对象，解析失败返回 None
        """
        for pattern in TimeParser.ABSOLUTE_TIME_PATTERNS:
            match = pattern.match(time_str.strip())
            if match:
                groups = match.groups()
                try:
                    # 根据匹配的组数确定时间格式
                    if len(groups) == 6:  # YYYY-MM-DD HH:MM:SS
                        year, month, day, hour, minute, second = groups
                        year, month, day = int(year), int(month), int(day)
                        hour, minute, second = int(hour), int(minute), int(second)
                        return datetime(year, month, day, hour, minute, second)
                    elif len(groups) == 5:  # YYYY-MM-DD HH:MM
                        year, month, day, hour, minute = groups
                        year, month, day = int(year), int(month), int(day)
                        hour, minute = int(hour), int(minute)
                        return datetime(year, month, day, hour, minute, 0)
                    elif len(groups) == 3:  # YYYY-MM-DD
                        year, month, day = groups
                        return datetime(int(year), int(month), int(day), 0, 0, 0)
                except ValueError:
                    # 日期时间值不合法（如 2024-13-01）
                    return None

        return None

    @staticmethod
    def parse_relative_time(time_str: str) -> Optional[Tuple[datetime, datetime]]:
        """
        解析相对时间字符串，计算时间范围

        参数:
            time_str: 相对时间字符串，格式："<数字><单位>"
                     单位支持：s（秒）、m（分）、h（小时）、d（天）
                     例如："1h", "24h", "7d", "30d"

        返回:
            (start_time, end_time) 元组
            start_time: 当前时间减去指定时间间隔
            end_time: 当前时间
            解析失败返回 None
        """
        match = TimeParser.RELATIVE_TIME_PATTERN.match(time_str.strip().lower())
        if not match:
            return None

        amount_str, unit = match.groups()
        try:
            amount = int(amount_str)
        except ValueError:
            return None

        if unit not in TimeParser.TIME_UNITS:
            return None

        # 计算时间间隔（秒）
        seconds = amount * TimeParser.TIME_UNITS[unit]
        delta = timedelta(seconds=seconds)

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - delta

        return start_time, end_time

    @staticmethod
    def parse_time_range(
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        time_last: Optional[str] = None,
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        解析时间范围参数（支持绝对时间和相对时间）

        参数:
            time_start: 开始时间（绝对时间）
            time_end: 结束时间（绝对时间）
            time_last: 相对时间（与 time_start/time_end 互斥）

        返回:
            (start_time, end_time) 元组
            解析失败返回 None

        互斥规则：
        - time_start/time_end 和 time_last 不能同时使用
        - 使用 time_last 时，自动计算结束时间为当前时间
        """
        # 检查互斥参数
        if time_last and (time_start or time_end):
            print("错误: --time-last 不能与 --time-start/--time-end 同时使用")
            return None

        # 模式 1: 相对时间（--time-last）
        if time_last:
            return TimeParser.parse_relative_time(time_last)

        # 模式 2: 绝对时间范围（--time-start 和 --time-end）
        if time_start or time_end:
            start_time = None
            end_time = None

            if time_start:
                start_time = TimeParser.parse_absolute_time(time_start)
                if not start_time:
                    print(f"错误: 无法解析开始时间: {time_start}")
                    return None

            if time_end:
                end_time = TimeParser.parse_absolute_time(time_end)
                if not end_time:
                    print(f"错误: 无法解析结束时间: {time_end}")
                    return None

            # 只提供了开始时间，结束时间设为当前时间
            if start_time and not end_time:
                end_time = datetime.now()

            # 只提供了结束时间，开始时间设为 epoch
            if end_time and not start_time:
                start_time = datetime(1970, 1, 1)

            # 验证时间范围
            if start_time and end_time and start_time > end_time:
                print("错误: 开始时间不能晚于结束时间")
                return None

            return start_time, end_time

        # 没有提供任何时间参数
        return None

    @staticmethod
    def format_time_range(start_time: datetime, end_time: datetime) -> str:
        """
        格式化时间范围为可读字符串

        参数:
            start_time: 开始时间
            end_time: 结束时间

        返回:
            格式化的时间范围字符串
        """
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        delta = end_time - start_time
        total_seconds = int(delta.total_seconds())

        # 智能格式化时间跨度
        if total_seconds < 60:
            duration = f"{total_seconds} 秒"
        elif total_seconds < 3600:
            duration = f"{total_seconds // 60} 分钟"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            duration = f"{hours} 小时 {minutes} 分钟"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            duration = f"{days} 天 {hours} 小时"

        return f"{start_str} 至 {end_str} (跨度: {duration})"


def parse_command_ids(cmd_str: str) -> list:
    """
    解析命令ID字符串（逗号分隔）

    参数:
        cmd_str: 命令ID字符串，例如："2,3,5" 或 "2, 3, 5"

    返回:
        命令ID列表，例如：[2, 3, 5]
        解析失败返回空列表
    """
    if not cmd_str:
        return []

    try:
        # 分割字符串并转换为整数
        cmd_ids = []
        for part in cmd_str.split(","):
            part = part.strip()
            if part:
                cmd_id = int(part)
                if cmd_id < 0:
                    print(f"警告: 命令ID不能为负数，已忽略: {cmd_id}")
                    continue
                cmd_ids.append(cmd_id)

        return cmd_ids

    except ValueError:
        print(f"错误: 命令ID格式不正确: {cmd_str}")
        print("提示: 命令ID应为逗号分隔的整数，例如：2,3,5")
        return []
