"""
协议数据提取器测试
测试 ProtocolDataExtractor 类的数据提取功能
"""

from pathlib import Path

import pytest

from src.protocol_data_extractor import ProtocolDataExtractor


class TestProtocolDataExtractorInit:
    """测试协议数据提取器初始化"""

    def test_init_with_pattern(self):
        """测试使用帧头模式初始化"""
        pattern = r"68"
        extractor = ProtocolDataExtractor(pattern)
        assert extractor.frame_head_pattern == pattern
        assert extractor._byte_sequence_re is not None
        assert extractor._info_line_re is not None
        assert extractor._direction_re is not None
        assert extractor._terminal_id_re is not None

    def test_set_frame_head_pattern(self):
        """测试更新帧头匹配模式"""
        extractor = ProtocolDataExtractor(r"68")
        new_pattern = r"AA BB"
        extractor.set_frame_head_pattern(new_pattern)
        assert extractor.frame_head_pattern == new_pattern


class TestExtractFromFile:
    """测试从文件提取数据"""

    @pytest.fixture
    def sample_log_file(self, tmp_path):
        """创建示例日志文件"""
        content = """
2024-01-28 10:30:45.123 Send [1] TX:
68 12 34 56 78 90 AB CD EF

2024-01-28 10:30:46.456 Recv [2] RX:
68 AA BB CC DD EE FF

// 这是注释行，应该被跳过
2024-01-28 10:30:47.789 Send [3] TX:
68 11 22 33 44 55
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")
        return str(log_file)

    @pytest.fixture
    def empty_log_file(self, tmp_path):
        """创建空日志文件"""
        log_file = tmp_path / "empty.log"
        log_file.write_text("")
        return str(log_file)

    @pytest.fixture
    def log_with_empty_lines(self, tmp_path):
        """创建包含空行的日志文件"""
        content = """

2024-01-28 10:30:45.123 Send [1] TX:
68 12 34 56 78


68 AA BB CC DD

"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")
        return str(log_file)

    def test_extract_basic_data(self, sample_log_file):
        """测试基本数据提取"""
        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(sample_log_file)

        # 应该提取到3组数据
        assert len(data_groups) == 3

        # 验证第一组数据
        first_group = data_groups[0]
        assert first_group["time"] == "2024-01-28 10:30:45.123"
        assert first_group["direction"] == "Send"
        assert first_group["terminal_id"] == 1
        assert "68 12 34 56 78 90 AB CD EF" in first_group["data"]

    def test_extract_with_comments(self, sample_log_file):
        """测试跳过注释行"""
        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(sample_log_file)

        # 注释行应该被跳过，仍然只有3组数据
        assert len(data_groups) == 3

        # 验证没有包含注释内容
        for group in data_groups:
            assert "注释" not in group.get("data", "")

    def test_extract_empty_file(self, empty_log_file):
        """测试空文件提取"""
        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(empty_log_file)

        # 空文件应该返回空列表
        assert len(data_groups) == 0

    def test_extract_with_empty_lines(self, log_with_empty_lines):
        """测试包含空行的文件提取"""
        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(log_with_empty_lines)

        # 应该提取到1组数据（两行数据被合并）
        assert len(data_groups) == 1

    def test_extract_direction_variants(self, tmp_path):
        """测试不同方向标识的提取"""
        content = """
2024-01-28 10:30:45.123 Send [1] TX:
68 12 34

2024-01-28 10:30:46.456 Recv [2] RX:
68 AA BB

2024-01-28 10:30:47.789 TX [3] TX:
68 56 78

2024-01-28 10:30:48.012 RX [4] RX:
68 90 AB
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        assert len(data_groups) == 4
        assert data_groups[0]["direction"] == "Send"
        assert data_groups[1]["direction"] == "Recv"
        assert data_groups[2]["direction"] == "TX"
        assert data_groups[3]["direction"] == "RX"

    def test_extract_without_direction(self, tmp_path):
        """测试没有方向信息的提取"""
        content = """
2024-01-28 10:30:45.123 Some other text:
68 12 34 56

2024-01-28 10:30:46.456 No direction marker:
68 AA BB CC
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        assert len(data_groups) == 2
        # 方向信息应该为空字符串
        assert data_groups[0]["direction"] == ""
        assert data_groups[1]["direction"] == ""

    def test_extract_terminal_id(self, tmp_path):
        """测试终端ID提取"""
        content = """
2024-01-28 10:30:45.123 Send [1] TX:
68 12 34

2024-01-28 10:30:46.456 Recv [999] RX:
68 AA BB

2024-01-28 10:30:47.789 No terminal:
68 56 78
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        assert len(data_groups) == 3
        assert data_groups[0]["terminal_id"] == 1
        assert data_groups[1]["terminal_id"] == 999
        assert data_groups[2]["terminal_id"] is None

    def test_extract_multiline_data(self, tmp_path):
        """测试多行数据提取"""
        content = """
2024-01-28 10:30:45.123 Send [1] TX:
68 12 34
56 78 90
AA BB CC

2024-01-28 10:30:46.456 Recv [2] RX:
68 DD EE FF
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        assert len(data_groups) == 2
        # 第一组应该包含所有行
        assert "68 12 34 56 78 90 AA BB CC" in data_groups[0]["data"]
        # 第二组应该只有一行
        assert "68 DD EE FF" in data_groups[1]["data"]

    def test_extract_with_byte_sequence_trigger(self, tmp_path):
        """测试字节序列触发数据收集"""
        content = """
2024-01-28 10:30:45.123 Send [1] TX:
Some preamble text 68 12 34 56
more data here

2024-01-28 10:30:46.456 Recv [2] RX:
Another preamble AA BB
not starting with 68
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        # 第一组包含68的数据,第二组虽然不包含68但也会被创建(因为有时间戳)
        # 不过第二组的数据会被过滤掉(因为不包含有效数据)
        assert len(data_groups) == 2
        assert "68 12 34 56" in data_groups[0]["data"]
        # 第二组只包含"68"(从匹配的"68"触发点开始收集)
        assert (
            "Another preamble" in data_groups[1]["data"]
            or "68" == data_groups[1]["data"].strip()
        )

    def test_extract_nonexistent_file(self):
        """测试不存在的文件"""
        extractor = ProtocolDataExtractor(r"68")

        with pytest.raises(IOError):
            extractor.extract_from_file("nonexistent_file.log")


class TestTimestampFormats:
    """测试不同时间戳格式"""

    @pytest.mark.parametrize(
        "timestamp_format,expected_time",
        [
            ("2024-01-28 10:30:45.123", "2024-01-28 10:30:45.123"),
            ("2024-01-28 10:30:45:123", "2024-01-28 10:30:45:123"),
            ("2024-01-28 10:30:45.12", "2024-01-28 10:30:45.12"),
        ],
        ids=["milliseconds_with_dot", "milliseconds_with_colon", "milliseconds_short"],
    )
    def test_different_timestamp_formats(self, timestamp_format, expected_time, tmp_path):
        """测试支持的时间戳格式"""
        content = f"""
{timestamp_format} Send [1] TX:
68 12 34
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        assert len(data_groups) == 1
        assert data_groups[0]["time"] == expected_time


class TestDataFiltering:
    """测试数据过滤"""

    def test_filter_empty_data_groups(self, tmp_path):
        """测试过滤空数据组"""
        content = """
2024-01-28 10:30:45.123 Send [1] TX:
No hex data here

2024-01-28 10:30:46.456 Recv [2] RX:
68 12 34
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(content, encoding="utf-8")

        extractor = ProtocolDataExtractor(r"68")
        data_groups = extractor.extract_from_file(str(log_file))

        # 只有包含68的组被返回
        assert len(data_groups) == 1
        assert "68 12 34" in data_groups[0]["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
