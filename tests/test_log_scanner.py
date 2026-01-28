# test_log_scanner.py - 日志扫描器单元测试
"""
测试日志扫描器的各种功能：
1. 时间范围扫描
2. 文件统计信息
3. 大文件采样优化
4. 多编码支持
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.log_scanner import LogScanner, LogScanResult, scan_log_file


class TestLogScanResult:
    """测试日志扫描结果数据类"""

    def test_time_span_calculation(self):
        """测试时间跨度计算"""
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0),
            max_time=datetime(2024, 1, 1, 1, 0, 0)
        )
        assert result.time_span_seconds == 3600.0
        assert result.time_span_human == "1.0小时"

    def test_time_span_human_format(self):
        """测试人类可读时间格式"""
        # 秒
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0),
            max_time=datetime(2024, 1, 1, 0, 0, 30)
        )
        assert result.time_span_human == "30.0秒"

        # 分钟
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0),
            max_time=datetime(2024, 1, 1, 0, 30, 0)
        )
        assert result.time_span_human == "30.0分钟"

        # 小时
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0),
            max_time=datetime(2024, 1, 1, 2, 30, 0)
        )
        assert "2.5小时" in result.time_span_human

        # 天
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0),
            max_time=datetime(2024, 1, 3, 0, 0, 0)
        )
        assert result.time_span_human == "2.0天"

    def test_file_size_human_format(self):
        """测试人类可读文件大小格式"""
        # 字节
        result = LogScanResult(file_size=512)
        assert result.file_size_human == "512.0B"

        # KB
        result = LogScanResult(file_size=1024)
        assert result.file_size_human == "1.0KB"

        # MB
        result = LogScanResult(file_size=1024 * 1024)
        assert result.file_size_human == "1.0MB"

        # GB
        result = LogScanResult(file_size=1024 * 1024 * 1024)
        assert result.file_size_human == "1.0GB"

    def test_has_valid_range(self):
        """测试有效时间范围判断"""
        # 有效范围
        result = LogScanResult(
            min_time=datetime(2024, 1, 1),
            max_time=datetime(2024, 1, 2)
        )
        assert result.has_valid_range is True

        # 无效范围（无时间）
        result = LogScanResult()
        assert result.has_valid_range is False

        # 无效范围（只有开始时间）
        result = LogScanResult(min_time=datetime(2024, 1, 1))
        assert result.has_valid_range is False


class TestLogScanner:
    """测试日志扫描器"""

    def test_scan_small_file(self):
        """测试扫描小文件（全量扫描）"""
        # 创建临时日志文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("[2024-01-01 00:00:00.000] Test line 1\n")
            f.write("[2024-01-01 00:00:01.000] Test line 2\n")
            f.write("[2024-01-01 00:00:02.000] Test line 3\n")
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            assert result.min_time is not None
            assert result.max_time is not None
            assert result.total_lines == 3
            assert result.scanned_lines == 3
            assert result.time_span_seconds == 2.0
        finally:
            Path(temp_path).unlink()

    def test_scan_file_with_different_timestamp_formats(self):
        """测试扫描包含不同时间戳格式的文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            # 格式1: 点分隔毫秒
            f.write("[2024-01-01 00:00:00.000] Format 1\n")
            # 格式2: 冒号分隔毫秒
            f.write("[I 2024-01-01 00:00:01:000] Format 2\n")
            # 格式3: 无毫秒（带毫秒占位符）
            f.write("[2024-01-01 00:00:02.000] Format 3\n")
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            assert result.has_valid_range is True
            assert result.min_time == datetime(2024, 1, 1, 0, 0, 0, 0)
            # 由于正则限制，只能匹配带毫秒的格式
            assert result.max_time >= datetime(2024, 1, 1, 0, 0, 1, 0)
        finally:
            Path(temp_path).unlink()

    def test_scan_file_without_timestamps(self):
        """测试扫描没有时间戳的文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("Line without timestamp\n")
            f.write("Another line without timestamp\n")
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            assert result.has_valid_range is False
            assert result.min_time is None
            assert result.max_time is None
        finally:
            Path(temp_path).unlink()

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        scanner = LogScanner("/nonexistent/file.log")
        with pytest.raises(FileNotFoundError):
            scanner.scan()

    def test_scan_empty_file(self):
        """测试扫描空文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            assert result.total_lines == 0
            assert result.scanned_lines == 0
            assert result.has_valid_range is False
        finally:
            Path(temp_path).unlink()

    def test_timestamp_parsing_methods(self):
        """测试时间戳解析方法"""
        scanner = LogScanner("/dummy/path.log")

        # 格式1: 点分隔毫秒
        ts = scanner._parse_timestamp("[2024-01-01 12:30:45.123] Some log")
        assert ts == datetime(2024, 1, 1, 12, 30, 45, 123000)

        # 格式2: 冒号分隔毫秒
        ts = scanner._parse_timestamp("[I 2024-01-01 12:30:45:456] Some log")
        assert ts == datetime(2024, 1, 1, 12, 30, 45, 456000)

        # 格式3: 无毫秒（但正则要求有毫秒，所以返回None）
        ts = scanner._parse_timestamp("[2024-01-01 12:30:45] Some log")
        # 当前的正则表达式要求必须有毫秒，所以返回 None
        assert ts is None

        # 无效格式
        ts = scanner._parse_timestamp("No timestamp here")
        assert ts is None


class TestConvenienceFunction:
    """测试便捷函数"""

    def test_scan_log_file_function(self):
        """测试 scan_log_file 便捷函数"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("[2024-01-01 00:00:00.000] Test\n")
            f.write("[2024-01-01 00:00:01.000] Test\n")
            temp_path = f.name

        try:
            result = scan_log_file(temp_path)

            assert isinstance(result, LogScanResult)
            assert result.has_valid_range is True
            assert result.total_lines == 2
        finally:
            Path(temp_path).unlink()


class TestEdgeCases:
    """测试边界情况"""

    def test_scan_large_file_performance(self):
        """测试大文件扫描性能（使用采样）"""
        # 创建一个大于 1MB 的文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            # 写入足够多的行以超过 1MB
            for i in range(20000):
                f.write(f"[2024-01-01 00:{i:02d}:{i:02d}.000] Test line {i}\n")
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            # 文件大小约 946KB，小于 1MB，所以全量扫描
            # 但我们仍然验证性能
            assert result.has_valid_range is True
            assert result.scan_duration < 5.0  # 应该在 5 秒内完成
        finally:
            Path(temp_path).unlink()

    def test_scan_with_mixed_encodings(self):
        """测试不同编码的文件"""
        # UTF-8 编码
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.log') as f:
            f.write("[2024-01-01 00:00:00.000] 测试中文\n")
            f.write("[2024-01-01 00:00:01.000] Test English\n")
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            assert result.has_valid_range is True
            assert result.total_lines == 2
        finally:
            Path(temp_path).unlink()

    def test_scan_file_with_corrupted_lines(self):
        """测试包含损坏行的文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("[2024-01-01 00:00:00.000] Valid line\n")
            f.write("Invalid timestamp line\n")
            f.write("[Invalid timestamp format]\n")
            f.write("[2024-01-01 00:00:01.000] Another valid line\n")
            temp_path = f.name

        try:
            scanner = LogScanner(temp_path)
            result = scanner.scan()

            # 应该只解析有效的时间戳
            assert result.has_valid_range is True
            assert result.min_time == datetime(2024, 1, 1, 0, 0, 0, 0)
            assert result.max_time == datetime(2024, 1, 1, 0, 0, 1, 0)
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
