# log_scanner.py - 日志文件扫描器
"""
日志文件时间范围和统计信息扫描器

功能：
1. 扫描日志文件提取时间范围
2. 统计日志文件信息（总行数、大小等）
3. 支持大文件采样优化
4. 多编码自动检测
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class LogScanResult:
    """日志扫描结果数据类"""

    min_time: Optional[datetime] = None  # 最小时间戳
    max_time: Optional[datetime] = None  # 最大时间戳
    total_lines: int = 0  # 日志总行数
    scanned_lines: int = 0  # 实际扫描的行数
    scan_duration: float = 0.0  # 扫描耗时（秒）
    file_size: int = 0  # 文件大小（字节）

    @property
    def has_valid_range(self) -> bool:
        """是否有有效的时间范围"""
        return self.min_time is not None and self.max_time is not None

    @property
    def time_span_seconds(self) -> float:
        """时间跨度（秒）"""
        if self.has_valid_range:
            return (self.max_time - self.min_time).total_seconds()
        return 0.0

    @property
    def time_span_human(self) -> str:
        """人类可读的时间跨度"""
        span = self.time_span_seconds
        if span < 60:
            return f"{span:.1f}秒"
        elif span < 3600:
            minutes = span / 60
            return f"{minutes:.1f}分钟"
        elif span < 86400:
            hours = span / 3600
            return f"{hours:.1f}小时"
        else:
            days = span / 86400
            return f"{days:.1f}天"

    @property
    def file_size_human(self) -> str:
        """人类可读的文件大小"""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"


class LogScanner:
    """
    日志文件扫描器

    职责：
    - 扫描日志文件提取时间范围
    - 统计日志文件信息
    - 支持采样优化（大文件性能优化）
    """

    # 时间戳正则表达式（支持多种格式）
    # 格式1: [2025-06-30 08:51:52.804]
    # 格式2: [I 2024-10-23 20:41:16:364]
    TIMESTAMP_RE = re.compile(r"\[(?:I\s+)?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{2,3})\]")

    def __init__(self, log_path: str):
        """
        初始化扫描器

        参数:
            log_path: 日志文件路径
        """
        self.log_path = log_path

    def scan(self) -> LogScanResult:
        """
        执行扫描

        返回:
            LogScanResult: 扫描结果
        """
        start_time = time.time()

        # 检查文件是否存在
        log_file = Path(self.log_path)
        if not log_file.exists():
            raise FileNotFoundError(f"日志文件不存在: {self.log_path}")

        # 获取文件大小
        file_size = log_file.stat().st_size

        # 根据文件大小选择扫描策略
        if file_size < 1 * 1024 * 1024:  # < 1MB
            result = self._scan_full(file_size)
        else:
            result = self._scan_sample(file_size)

        # 计算扫描耗时
        result.scan_duration = time.time() - start_time

        return result

    def _scan_full(self, file_size: int) -> LogScanResult:
        """
        全量扫描（小文件）

        参数:
            file_size: 文件大小（字节）

        返回:
            LogScanResult: 扫描结果
        """
        min_time = None
        max_time = None
        total_lines = 0

        # 尝试不同编码
        encodings = ["utf-8", "gbk", "latin-1"]

        for encoding in encodings:
            try:
                with open(self.log_path, "r", encoding=encoding, errors="ignore") as f:
                    for line in f:
                        total_lines += 1
                        ts = self._parse_timestamp(line)
                        if ts:
                            if min_time is None or ts < min_time:
                                min_time = ts
                            if max_time is None or ts > max_time:
                                max_time = ts

                # 成功读取，跳出编码循环
                break

            except UnicodeDecodeError:
                # 当前编码失败，尝试下一个
                continue
            except Exception as e:
                raise RuntimeError(f"读取文件失败（编码 {encoding}）: {str(e)}")

        return LogScanResult(
            min_time=min_time,
            max_time=max_time,
            total_lines=total_lines,
            scanned_lines=total_lines,
            file_size=file_size,
        )

    def _scan_sample(self, file_size: int) -> LogScanResult:
        """
        采样扫描（大文件优化）

        策略：
        - 中文件（1-10MB）：首尾 1000 行 + 中间 5 个采样点
        - 大文件（> 10MB）：首尾 500 行 + 中间 10 个采样点 + 每 1MB 采样

        参数:
            file_size: 文件大小（字节）

        返回:
            LogScanResult: 扫描结果
        """
        min_time = None
        max_time = None
        scanned_lines = 0
        total_lines = 0

        # 计算采样策略
        if file_size < 10 * 1024 * 1024:  # 1-10MB
            sample_lines = 1000  # 首尾各 1000 行
            middle_samples = 5
        else:  # > 10MB
            sample_lines = 500  # 首尾各 500 行
            middle_samples = 10

        # 尝试不同编码
        encodings = ["utf-8", "gbk", "latin-1"]

        for encoding in encodings:
            try:
                with open(self.log_path, "r", encoding=encoding, errors="ignore") as f:
                    # 1. 扫描头部
                    for i, line in enumerate(f):
                        if i >= sample_lines:
                            break
                        total_lines += 1
                        scanned_lines += 1
                        ts = self._parse_timestamp(line)
                        if ts:
                            if min_time is None or ts < min_time:
                                min_time = ts
                            if max_time is None or ts > max_time:
                                max_time = ts

                    # 2. 快速估算总行数（读取到文件末尾）
                    f.seek(0, 2)  # 移动到文件末尾
                    file_end_pos = f.tell()

                    # 3. 扫描尾部（最后 sample_lines 行）
                    f.seek(0, 0)  # 回到文件开头
                    lines_from_end = []
                    for line in f:
                        lines_from_end.append(line)
                        if len(lines_from_end) > sample_lines:
                            lines_from_end.pop(0)

                    # 处理尾部的行
                    for line in lines_from_end:
                        scanned_lines += 1
                        ts = self._parse_timestamp(line)
                        if ts:
                            if min_time is None or ts < min_time:
                                min_time = ts
                            if max_time is None or ts > max_time:
                                max_time = ts

                    # 4. 中间采样（按文件位置均匀分布）
                    for i in range(middle_samples):
                        # 计算采样位置
                        sample_pos = (i + 1) * file_end_pos // (middle_samples + 1)
                        f.seek(sample_pos)

                        # 读取一行（可能不完整，跳过）
                        f.readline()

                        # 读取下一行（完整行）
                        line = f.readline()
                        if line:
                            scanned_lines += 1
                            ts = self._parse_timestamp(line)
                            if ts:
                                if min_time is None or ts < min_time:
                                    min_time = ts
                                if max_time is None or ts > max_time:
                                    max_time = ts

                    # 5. 超大文件：每 1MB 采样一次
                    if file_size >= 10 * 1024 * 1024:
                        mb_size = 1024 * 1024
                        total_mb = file_size // mb_size

                        for mb in range(1, int(total_mb)):
                            # 每隔 1MB 采样一次
                            sample_pos = mb * mb_size
                            f.seek(sample_pos)

                            # 读取到完整行
                            f.readline()
                            line = f.readline()

                            if line:
                                scanned_lines += 1
                                ts = self._parse_timestamp(line)
                                if ts:
                                    if min_time is None or ts < min_time:
                                        min_time = ts
                                    if max_time is None or ts > max_time:
                                        max_time = ts

                # 成功读取，跳出编码循环
                break

            except UnicodeDecodeError:
                # 当前编码失败，尝试下一个
                continue
            except Exception as e:
                raise RuntimeError(f"读取文件失败（编码 {encoding}）: {str(e)}")

        # 估算总行数（基于文件大小和采样密度）
        if scanned_lines > 0:
            # 根据文件大小估算
            avg_line_size = max(100, file_size // scanned_lines)
            total_lines = file_size // avg_line_size

        return LogScanResult(
            min_time=min_time,
            max_time=max_time,
            total_lines=total_lines,
            scanned_lines=scanned_lines,
            file_size=file_size,
        )

    def _parse_timestamp(self, line: str) -> Optional[datetime]:
        """
        从日志行解析时间戳

        支持格式：
        - [2025-06-30 08:51:52.804]
        - [I 2024-10-23 20:41:16:364]
        - [2025-06-30 08:51:52]

        参数:
            line: 日志行

        返回:
            Optional[datetime]: 解析出的时间戳，失败返回 None
        """
        match = self.TIMESTAMP_RE.search(line)
        if not match:
            return None

        ts_str = match.group(1)

        try:
            # 格式1: 2025-06-30 08:51:52.804（点分隔毫秒）
            if "." in ts_str:
                return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")

            # 格式2: 2024-10-23 20:41:16:364（冒号分隔毫秒）
            elif ts_str.count(":") == 3:
                parts = ts_str.split(":")
                # 将最后一部分（毫秒）转为点分隔格式
                ts_str = ":".join(parts[:3]) + "." + parts[3]
                return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")

            # 格式3: 2025-06-30 08:51:52（无毫秒）
            else:
                return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

        except ValueError:
            # 解析失败，返回 None
            return None


def scan_log_file(log_path: str) -> LogScanResult:
    """
    便捷函数：扫描日志文件

    参数:
        log_path: 日志文件路径

    返回:
        LogScanResult: 扫描结果
    """
    scanner = LogScanner(log_path)
    return scanner.scan()
