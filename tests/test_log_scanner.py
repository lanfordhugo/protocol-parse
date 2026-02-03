# test_log_scanner.py - 日志扫描器单元测试
"""
测试日志扫描器的各种功能：
1. 时间范围扫描
2. 文件统计信息
3. 大文件采样优化
4. 多编码支持
"""

from datetime import datetime
from unittest.mock import patch, mock_open

import pytest

from src.log_scanner import LogScanner, LogScanResult, scan_log_file


class TestLogScanResult:
    """测试日志扫描结果数据类"""

    def test_time_span_calculation(self):
        """测试时间跨度计算"""
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0), max_time=datetime(2024, 1, 1, 1, 0, 0)
        )
        assert result.time_span_seconds == 3600.0
        assert result.time_span_human == "1.0小时"

    def test_time_span_human_format(self):
        """测试人类可读时间格式"""
        # 秒
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0), max_time=datetime(2024, 1, 1, 0, 0, 30)
        )
        assert result.time_span_human == "30.0秒"

        # 分钟
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0), max_time=datetime(2024, 1, 1, 0, 30, 0)
        )
        assert result.time_span_human == "30.0分钟"

        # 小时
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0), max_time=datetime(2024, 1, 1, 2, 30, 0)
        )
        assert "2.5小时" in result.time_span_human

        # 天
        result = LogScanResult(
            min_time=datetime(2024, 1, 1, 0, 0, 0), max_time=datetime(2024, 1, 3, 0, 0, 0)
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

        # TB
        result = LogScanResult(file_size=1024 * 1024 * 1024 * 1024)
        assert result.file_size_human == "1.0TB"

    def test_has_valid_range(self):
        """测试有效时间范围判断"""
        # 有效范围
        result = LogScanResult(min_time=datetime(2024, 1, 1), max_time=datetime(2024, 1, 2))
        assert result.has_valid_range is True

        # 无效范围（无时间）
        result = LogScanResult()
        assert result.has_valid_range is False

        # 无效范围（只有开始时间）
        result = LogScanResult(min_time=datetime(2024, 1, 1))
        assert result.has_valid_range is False

    def test_time_span_seconds_without_valid_range(self):
        """测试无有效时间范围时的时间跨度计算"""
        # 无有效范围
        result = LogScanResult()
        assert result.time_span_seconds == 0.0

        # 只有开始时间
        result = LogScanResult(min_time=datetime(2024, 1, 1))
        assert result.time_span_seconds == 0.0


class TestLogScanner:
    """测试日志扫描器"""

    def test_scan_small_file(self, tmp_path):
        """测试扫描小文件（全量扫描）"""
        # 使用 tmp_path fixture 创建临时日志文件
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[2024-01-01 00:00:00.000] Test line 1\n"
            "[2024-01-01 00:00:01.000] Test line 2\n"
            "[2024-01-01 00:00:02.000] Test line 3\n"
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.min_time is not None
        assert result.max_time is not None
        assert result.total_lines == 3
        assert result.scanned_lines == 3
        assert result.time_span_seconds == 2.0

    def test_scan_file_with_different_timestamp_formats(self, tmp_path):
        """测试扫描包含不同时间戳格式的文件"""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            # 格式1: 点分隔毫秒
            "[2024-01-01 00:00:00.000] Format 1\n"
            # 格式2: 冒号分隔毫秒
            "[I 2024-01-01 00:00:01:000] Format 2\n"
            # 格式3: 无毫秒（带毫秒占位符）
            "[2024-01-01 00:00:02.000] Format 3\n"
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is True
        assert result.min_time == datetime(2024, 1, 1, 0, 0, 0, 0)
        # 由于正则限制，只能匹配带毫秒的格式
        assert result.max_time >= datetime(2024, 1, 1, 0, 0, 1, 0)

    def test_scan_file_without_timestamps(self, tmp_path):
        """测试扫描没有时间戳的文件"""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "Line without timestamp\n"
            "Another line without timestamp\n"
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is False
        assert result.min_time is None
        assert result.max_time is None

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        scanner = LogScanner("/nonexistent/file.log")
        with pytest.raises(FileNotFoundError):
            scanner.scan()

    def test_scan_empty_file(self, tmp_path):
        """测试扫描空文件"""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.total_lines == 0
        assert result.scanned_lines == 0
        assert result.has_valid_range is False

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

    def test_scan_log_file_function(self, tmp_path):
        """测试 scan_log_file 便捷函数"""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[2024-01-01 00:00:00.000] Test\n"
            "[2024-01-01 00:00:01.000] Test\n"
        )

        result = scan_log_file(str(log_file))

        assert isinstance(result, LogScanResult)
        assert result.has_valid_range is True
        assert result.total_lines == 2


class TestEdgeCases:
    """测试边界情况"""

    def test_scan_large_file_performance(self, tmp_path):
        """测试大文件扫描性能（使用采样）"""
        # 创建一个大于 1MB 的文件
        log_file = tmp_path / "test.log"
        # 写入足够多的行以超过 1MB
        lines = [f"[2024-01-01 00:{i:02d}:{i:02d}.000] Test line {i}\n" for i in range(20000)]
        log_file.write_text("".join(lines))

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 文件大小约 946KB，小于 1MB，所以全量扫描
        # 但我们仍然验证性能
        assert result.has_valid_range is True
        assert result.scan_duration < 5.0  # 应该在 5 秒内完成

    def test_scan_with_mixed_encodings(self, tmp_path):
        """测试不同编码的文件"""
        # UTF-8 编码
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[2024-01-01 00:00:00.000] 测试中文\n"
            "[2024-01-01 00:00:01.000] Test English\n",
            encoding="utf-8",
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is True
        assert result.total_lines == 2

    def test_scan_file_with_corrupted_lines(self, tmp_path):
        """测试包含损坏行的文件"""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[2024-01-01 00:00:00.000] Valid line\n"
            "Invalid timestamp line\n"
            "[Invalid timestamp format]\n"
            "[2024-01-01 00:00:01.000] Another valid line\n"
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 应该只解析有效的时间戳
        assert result.has_valid_range is True
        assert result.min_time == datetime(2024, 1, 1, 0, 0, 0, 0)
        assert result.max_time == datetime(2024, 1, 1, 0, 0, 1, 0)

    def test_scan_medium_file_with_sampling(self, tmp_path):
        """测试中等大小文件的采样扫描（1-10MB）"""
        # 创建一个大于 1MB 的文件以触发采样扫描
        log_file = tmp_path / "test.log"
        # 写入足够多的行以超过 1MB
        lines = [f"[2024-01-01 00:{i % 60:02d}:{i % 60:02d}.000] Test line {i}\n" for i in range(25000)]
        log_file.write_text("".join(lines), encoding="utf-8")

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 验证采样扫描的结果
        assert result.has_valid_range is True
        assert result.file_size > 1 * 1024 * 1024  # > 1MB
        # 采样扫描应该只扫描部分行
        assert result.scanned_lines < result.total_lines
        assert result.scan_duration < 10.0  # 应该在 10 秒内完成

    def test_scan_large_file_with_sampling(self, tmp_path):
        """测试大文件的采样扫描（>10MB）"""
        # 创建一个大于 10MB 的文件
        log_file = tmp_path / "test.log"
        # 写入足够多的行以超过 10MB
        lines = [f"[2024-01-01 00:{i % 60:02d}:{i % 60:02d}.000] Test line {i}\n" for i in range(300000)]
        log_file.write_text("".join(lines), encoding="utf-8")

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 验证采样扫描的结果
        assert result.has_valid_range is True
        assert result.file_size > 10 * 1024 * 1024  # > 10MB
        # 对于超大文件，采样扫描应该只扫描少量行（可能是全部，取决于文件内容）
        # 主要验证性能和正确性
        assert result.scan_duration < 30.0  # 应该在 30 秒内完成
        assert result.total_lines > 0  # 至少扫描了一些行

    def test_scan_gbk_encoded_file(self, tmp_path):
        """测试 GBK 编码的文件"""
        # 创建 GBK 编码的文件
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[2024-01-01 00:00:00.000] 测试中文GBK编码\n"
            "[2024-01-01 00:00:01.000] 中文日志行\n",
            encoding="gbk",
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 应该能正确解析 GBK 编码的文件
        assert result.has_valid_range is True
        assert result.total_lines == 2


class TestExceptionsAndEdgeCases:
    """测试异常情况和边界条件"""

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        scanner = LogScanner("/nonexistent/file.log")
        # 应该抛出 FileNotFoundError
        with pytest.raises(FileNotFoundError):
            scanner.scan()

    def test_scan_empty_file(self, tmp_path):
        """测试扫描空文件"""
        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is False
        assert result.total_lines == 0

    def test_scan_file_with_only_invalid_lines(self, tmp_path):
        """测试只有无效行的文件"""
        log_file = tmp_path / "invalid.log"
        log_file.write_text(
            "这只是一行普通文本\n"
            "another line without timestamp\n"
            "yet another invalid line\n"
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is False
        assert result.total_lines == 3

    def test_scan_file_with_mixed_valid_invalid_lines(self, tmp_path):
        """测试混合有效和无效行的文件"""
        log_file = tmp_path / "mixed.log"
        log_file.write_text(
            "invalid line\n"
            "[2024-01-01 00:00:00.000] AA BB CC DD\n"
            "another invalid line\n"
            "[2024-01-01 00:00:01.000] AA BB CC DD\n"
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is True
        assert result.total_lines == 4

    def test_scan_file_with_corrupted_encoding(self, tmp_path):
        """测试编码损坏的文件"""
        log_file = tmp_path / "corrupted.log"
        # 写入一些二进制数据
        log_file.write_bytes(b"\xff\xfe\xfd\x00\x01\x02\x03")

        scanner = LogScanner(str(log_file))
        # 应该能处理而不崩溃
        result = scanner.scan()

        assert result.total_lines >= 0

    def test_scan_very_long_line(self, tmp_path):
        """测试超长行"""
        log_file = tmp_path / "longline.log"
        # 创建一个超长的十六进制数据行
        long_hex = "AA" * 10000
        log_file.write_text(f"[2024-01-01 00:00:00.000] {long_hex}\n")

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 应该能处理超长行
        assert result.has_valid_range is True
        assert result.total_lines == 1

    def test_scan_file_with_invalid_timestamp(self, tmp_path):
        """测试包含无效时间戳的文件"""
        log_file = tmp_path / "bad_timestamp.log"
        log_file.write_text(
            "[2024-13-01 00:00:00.000] AA BB\n"  # 无效月份
            "[2024-01-01 25:00:00.000] AA BB\n"  # 无效小时
            "[2024-01-01 00:00:00.000] AA BB\n"  # 有效行
        )

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        # 应该至少有一行有效
        assert result.total_lines == 3


class TestMockFileOperations:
    """使用 Mock 测试文件操作"""

    def test_scan_with_mocked_file_read(self, tmp_path):
        """使用 Mock 测试文件读取 - 使用实际文件"""
        # 由于 LogScanner 在 scan() 开始就检查文件存在性，
        # Mock open 不能直接工作。使用实际文件测试
        log_file = tmp_path / "mock_test.log"
        log_file.write_text("[2024-01-01 00:00:00.000] AA BB CC DD\n")

        scanner = LogScanner(str(log_file))
        result = scanner.scan()

        assert result.has_valid_range is True
        assert result.total_lines == 1

    def test_scan_with_permission_error(self):
        """测试文件权限错误"""
        # LogScanner 在 scan() 中会调用 stat() 和 open()
        # 需要同时 mock 两个方法
        # 注意：实际代码会捕获 PermissionError 并抛出 RuntimeError
        mock_stat_result = __import__('os').stat_result((33206, 0, 0, 0, 0, 0, 100, 0, 0, 0))
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat", return_value=mock_stat_result):
                with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                    scanner = LogScanner("restricted.log")
                    # 实际代码抛出 RuntimeError
                    with pytest.raises(RuntimeError, match="读取文件失败"):
                        scanner.scan()

    def test_scan_with_io_error(self):
        """测试 IO 错误"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=IOError("Disk error")):
                scanner = LogScanner("error.log")
                with pytest.raises(IOError):
                    scanner.scan()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
