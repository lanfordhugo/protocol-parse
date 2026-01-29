"""
协议解析器测试
测试 ProtocolParser 类的解析功能
"""

from collections import defaultdict
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.protocol_parser import ProtocolParser


class TestProtocolParserInit:
    """测试协议解析器初始化"""

    def test_init(self, mock_yaml_format):
        """测试初始化"""
        parser = ProtocolParser(mock_yaml_format)
        assert parser.yaml_format == mock_yaml_format
        assert parser.yaml_config == mock_yaml_format.config
        assert isinstance(parser.perf_stats, dict)
        assert "cmd_counts" in parser.perf_stats
        assert "errors" in parser.perf_stats

    def test_reset_stats(self, mock_yaml_format):
        """测试重置统计数据"""
        parser = ProtocolParser(mock_yaml_format)
        parser.perf_stats["cmd_counts"][1] = 100
        parser.perf_stats["errors"] = 5

        parser.reset_stats()

        assert parser.perf_stats["cmd_counts"] == defaultdict(int)
        assert parser.perf_stats["errors"] == 0


class TestSetFilters:
    """测试过滤器设置"""

    def test_set_include_cmds(self, mock_yaml_format):
        """测试设置包含命令列表"""
        parser = ProtocolParser(mock_yaml_format)
        cmd_list = [1, 2, 3]

        parser.set_filters(include_cmds=cmd_list)

        assert parser._include_cmds == cmd_list

    def test_set_exclude_cmds(self, mock_yaml_format):
        """测试设置排除命令列表"""
        parser = ProtocolParser(mock_yaml_format)
        cmd_list = [4, 5, 6]

        parser.set_filters(exclude_cmds=cmd_list)

        assert parser._exclude_cmds == cmd_list

    def test_set_time_range(self, mock_yaml_format):
        """测试设置时间范围"""
        parser = ProtocolParser(mock_yaml_format)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 12, 31, 23, 59, 59)

        parser.set_filters(time_range=(start_time, end_time))

        assert parser._time_range == (start_time, end_time)

    def test_set_all_filters(self, mock_yaml_format):
        """测试设置所有过滤器"""
        parser = ProtocolParser(mock_yaml_format)
        cmd_list = [1, 2]
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 12, 31)

        parser.set_filters(
            include_cmds=cmd_list, exclude_cmds=[3, 4], time_range=(start_time, end_time)
        )

        assert parser._include_cmds == cmd_list
        assert parser._exclude_cmds == [3, 4]
        assert parser._time_range == (start_time, end_time)


class TestParseHeader:
    """测试头部解析"""

    def test_parse_header_success(self, mock_yaml_format):
        """测试成功解析头部"""
        parser = ProtocolParser(mock_yaml_format)

        # 模拟头部字段
        mock_yaml_format.get_head_fields.return_value = [
            {
                "name": "head",
                "offset": 0,
                "length": 2,
                "endian": "big",
                "type": "const",
                "const_value": 0x6868,
                "required": True,
            },
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"},
        ]

        # 构造测试数据（68 68 01 02）
        header_data = bytes([0x68, 0x68, 0x01, 0x02])

        result = parser._parse_header(header_data)

        assert result is not None
        assert result["head"] == 0x6868
        assert result["cmd"] == 0x0102

    def test_parse_header_const_check_failed(self, mock_yaml_format):
        """测试头部常量检查失败"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.get_head_fields.return_value = [
            {
                "name": "head",
                "offset": 0,
                "length": 2,
                "endian": "big",
                "type": "const",
                "const_value": 0x6868,
                "required": True,
            }
        ]

        # 使用错误的常量值
        header_data = bytes([0xAA, 0xAA])

        result = parser._parse_header(header_data)

        # 常量检查失败应该返回 None
        assert result is None

    def test_parse_header_const_not_required(self, mock_yaml_format):
        """测试头部非常量字段"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.get_head_fields.return_value = [
            {"name": "head", "offset": 0, "length": 2, "endian": "big", "type": "uint"},
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"},
        ]

        header_data = bytes([0x68, 0x68, 0x01, 0x02])

        result = parser._parse_header(header_data)

        assert result is not None
        assert result["head"] == 0x6868
        assert result["cmd"] == 0x0102

    def test_parse_header_hex_field(self, mock_yaml_format):
        """测试解析十六进制字段"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.get_head_fields.return_value = [
            {"name": "data", "offset": 0, "length": 4, "endian": "big", "type": "hex"}
        ]

        header_data = bytes([0x12, 0x34, 0x56, 0x78])

        result = parser._parse_header(header_data)

        assert result is not None
        assert result["data"] == "12345678"

    def test_parse_header_ascii_field(self, mock_yaml_format):
        """测试解析ASCII字段"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.get_head_fields.return_value = [
            {"name": "text", "offset": 0, "length": 5, "endian": "big", "type": "ascii"}
        ]

        header_data = b"HELLO\x00"

        result = parser._parse_header(header_data)

        assert result is not None
        assert result["text"] == "HELLO"

    def test_parse_header_out_of_bounds(self, mock_yaml_format):
        """测试字段超出边界"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.get_head_fields.return_value = [
            {"name": "head", "offset": 0, "length": 2, "endian": "big", "type": "uint"},
            {"name": "cmd", "offset": 10, "length": 2, "endian": "big", "type": "uint"},
        ]

        header_data = bytes([0x68, 0x68, 0x01, 0x02])

        result = parser._parse_header(header_data)

        # 超出边界的字段应该被跳过
        assert result is not None
        assert "head" in result
        assert "cmd" not in result


class TestParseUintField:
    """测试无符号整数字段解析"""

    def test_parse_uint1_little_endian(self, mock_yaml_format):
        """测试1字节无符号整数（小端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(bytes([0xFF]), "little")
        assert result == 255

    def test_parse_uint1_big_endian(self, mock_yaml_format):
        """测试1字节无符号整数（大端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(bytes([0xFF]), "big")
        assert result == 255

    def test_parse_uint2_little_endian(self, mock_yaml_format):
        """测试2字节无符号整数（小端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(bytes([0x34, 0x12]), "little")
        assert result == 0x1234

    def test_parse_uint2_big_endian(self, mock_yaml_format):
        """测试2字节无符号整数（大端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(bytes([0x12, 0x34]), "big")
        assert result == 0x1234

    def test_parse_uint4_little_endian(self, mock_yaml_format):
        """测试4字节无符号整数（小端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(bytes([0x78, 0x56, 0x34, 0x12]), "little")
        assert result == 0x12345678

    def test_parse_uint4_big_endian(self, mock_yaml_format):
        """测试4字节无符号整数（大端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(bytes([0x12, 0x34, 0x56, 0x78]), "big")
        assert result == 0x12345678

    def test_parse_uint8_little_endian(self, mock_yaml_format):
        """测试8字节无符号整数（小端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(
            bytes([0x00, 0xEF, 0xCD, 0xAB, 0x78, 0x56, 0x34, 0x12]), "little"
        )
        assert result == 0x12345678ABCDEF00

    def test_parse_uint8_big_endian(self, mock_yaml_format):
        """测试8字节无符号整数（大端序）"""
        parser = ProtocolParser(mock_yaml_format)

        result = parser._parse_uint_field(
            bytes([0x12, 0x34, 0x56, 0x78, 0xAB, 0xCD, 0xEF, 0x00]), "big"
        )
        assert result == 0x12345678ABCDEF00

    def test_parse_uint_unsupported_size(self, mock_yaml_format):
        """测试不支持的大小"""
        parser = ProtocolParser(mock_yaml_format)

        with pytest.raises(ValueError, match="不支持的 uint 大小"):
            parser._parse_uint_field(bytes([0x01, 0x02, 0x03]), "big")


class TestCheckCmdFilter:
    """测试命令过滤检查"""

    def test_check_cmd_filter_no_filter(self, mock_yaml_format):
        """测试没有设置过滤器"""
        parser = ProtocolParser(mock_yaml_format)

        # 没有设置任何过滤器，所有命令都应该通过
        assert parser._check_cmd_filter(1) is True
        assert parser._check_cmd_filter(999) is True

    def test_check_cmd_filter_include(self, mock_yaml_format):
        """测试包含过滤器"""
        parser = ProtocolParser(mock_yaml_format)
        parser.set_filters(include_cmds=[1, 2, 3])

        assert parser._check_cmd_filter(1) is True
        assert parser._check_cmd_filter(2) is True
        assert parser._check_cmd_filter(3) is True
        assert parser._check_cmd_filter(4) is False

    def test_check_cmd_filter_exclude(self, mock_yaml_format):
        """测试排除过滤器"""
        parser = ProtocolParser(mock_yaml_format)
        parser.set_filters(exclude_cmds=[4, 5, 6])

        assert parser._check_cmd_filter(1) is True
        assert parser._check_cmd_filter(4) is False
        assert parser._check_cmd_filter(5) is False

    def test_check_cmd_filter_include_and_exclude(self, mock_yaml_format):
        """测试同时设置包含和排除"""
        parser = ProtocolParser(mock_yaml_format)
        parser.set_filters(include_cmds=[1, 2, 3, 4], exclude_cmds=[5, 6])

        # 包含过滤器优先
        assert parser._check_cmd_filter(1) is True
        assert parser._check_cmd_filter(4) is True
        assert parser._check_cmd_filter(5) is False


class TestCheckTimeFilter:
    """测试时间过滤检查"""

    def test_check_time_filter_no_filter(self, mock_yaml_format):
        """测试没有设置时间过滤器"""
        parser = ProtocolParser(mock_yaml_format)

        assert parser._check_time_filter("2024-01-28 10:30:45.123") is True

    def test_check_time_filter_in_range(self, mock_yaml_format):
        """测试时间在范围内"""
        parser = ProtocolParser(mock_yaml_format)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 12, 31, 23, 59, 59)
        parser.set_filters(time_range=(start_time, end_time))

        assert parser._check_time_filter("2024-06-15 12:00:00.000") is True

    def test_check_time_filter_out_of_range(self, mock_yaml_format):
        """测试时间超出范围"""
        parser = ProtocolParser(mock_yaml_format)
        start_time = datetime(2024, 6, 1, 0, 0, 0)
        end_time = datetime(2024, 6, 30, 23, 59, 59)
        parser.set_filters(time_range=(start_time, end_time))

        assert parser._check_time_filter("2024-01-15 12:00:00.000") is False

    def test_check_time_filter_invalid_format(self, mock_yaml_format):
        """测试无效的时间格式"""
        parser = ProtocolParser(mock_yaml_format)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 12, 31, 23, 59, 59)
        parser.set_filters(time_range=(start_time, end_time))

        # 无效格式应该默认通过
        assert parser._check_time_filter("invalid") is True


class TestParseDataGroups:
    """测试数据组解析"""

    def test_parse_data_groups_success(self, mock_yaml_format):
        """测试成功解析数据组"""
        parser = ProtocolParser(mock_yaml_format)

        # 设置 mock
        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 2
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        mock_yaml_format.parse_cmd_data.return_value = {"field1": "value1"}

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02 AA BB",
            }
        ]

        result = parser.parse_data_groups(data_groups)

        assert len(result) == 1
        assert result[0]["timestamp"] == "2024-01-28 10:30:45.123"
        assert result[0]["cmd"] == 0x0102
        assert result[0]["content"] == {"field1": "value1"}

    def test_parse_data_groups_with_include_filter(self, mock_yaml_format):
        """测试使用包含过滤器解析"""
        parser = ProtocolParser(mock_yaml_format)
        parser.set_filters(include_cmds=[0x0102])

        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 0
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        mock_yaml_format.parse_cmd_data.return_value = {}

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02",
            },
            {
                "time": "2024-01-28 10:30:46.456",
                "direction": "Recv",
                "terminal_id": 2,
                "data": "68 68 03 04",
            },
        ]

        result = parser.parse_data_groups(data_groups)

        # 只有 cmd=0x0102 的数据被解析
        assert len(result) == 1
        assert result[0]["cmd"] == 0x0102

    def test_parse_data_groups_with_exclude_filter(self, mock_yaml_format):
        """测试使用排除过滤器解析"""
        parser = ProtocolParser(mock_yaml_format)
        parser.set_filters(exclude_cmds=[0x0102])

        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 0
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        mock_yaml_format.parse_cmd_data.return_value = {}

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02",
            },
            {
                "time": "2024-01-28 10:30:46.456",
                "direction": "Recv",
                "terminal_id": 2,
                "data": "68 68 03 04",
            },
        ]

        result = parser.parse_data_groups(data_groups)

        # cmd=0x0102 的数据被排除
        assert len(result) == 1
        assert result[0]["cmd"] == 0x0304

    def test_parse_data_groups_with_time_filter(self, mock_yaml_format):
        """测试使用时间过滤器解析"""
        parser = ProtocolParser(mock_yaml_format)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 31, 23, 59, 59)
        parser.set_filters(time_range=(start_time, end_time))

        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 0
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        mock_yaml_format.parse_cmd_data.return_value = {}

        data_groups = [
            {
                "time": "2024-01-15 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02",
            },
            {
                "time": "2024-02-15 10:30:46.456",
                "direction": "Recv",
                "terminal_id": 2,
                "data": "68 68 03 04",
            },
        ]

        result = parser.parse_data_groups(data_groups)

        # 只有1月的数据被解析
        assert len(result) == 1
        assert result[0]["timestamp"] == "2024-01-15 10:30:45.123"

    def test_parse_data_groups_insufficient_length(self, mock_yaml_format):
        """测试数据长度不足"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.config.head_len = 10
        mock_yaml_format.config.tail_len = 0

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02",
            }
        ]

        result = parser.parse_data_groups(data_groups)

        # 数据长度不足，应该被跳过
        assert len(result) == 0

    def test_parse_data_groups_with_stop_callback(self, mock_yaml_format):
        """测试停止回调"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 0
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        mock_yaml_format.parse_cmd_data.return_value = {}

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02",
            },
            {
                "time": "2024-01-28 10:30:46.456",
                "direction": "Recv",
                "terminal_id": 2,
                "data": "68 68 03 04",
            },
        ]

        # 第一次回调后返回 True 停止
        call_count = [0]

        def stop_callback():
            call_count[0] += 1
            return call_count[0] >= 1

        result = parser.parse_data_groups(data_groups, should_stop_callback=stop_callback)

        # 应该在处理第一个数据组后停止
        assert len(result) == 0  # 第一个数据组还未完成解析就被停止

    def test_parse_data_groups_parse_error(self, mock_yaml_format):
        """测试解析错误"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 0
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        mock_yaml_format.parse_cmd_data.side_effect = Exception("Parse error")

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02 AA BB",
            }
        ]

        result = parser.parse_data_groups(data_groups)

        # 解析错误时应该包含原始数据和错误信息
        assert len(result) == 1
        assert "parse_error" in result[0]
        assert result[0]["parse_error"] == "Parse error"
        assert "raw" in result[0]["content"]


class TestProtocolParserExceptions:
    """测试协议解析器的异常处理"""

    def test_parse_uint_unsupported_size(self, mock_yaml_format):
        """测试不支持的大小"""
        parser = ProtocolParser(mock_yaml_format)

        # 3字节不被支持
        with pytest.raises(ValueError, match="不支持的 uint 大小: 3"):
            parser._parse_uint_field(bytes([0x01, 0x02, 0x03]), "big")

    def test_parse_header_with_invalid_data(self, mock_yaml_format):
        """测试解析无效的头部数据"""
        parser = ProtocolParser(mock_yaml_format)

        # 设置需要常量校验的头部字段
        mock_yaml_format.get_head_fields.return_value = [
            {
                "name": "head",
                "offset": 0,
                "length": 2,
                "endian": "big",
                "type": "const",
                "const_value": 0x6868,
                "required": True,
            }
        ]

        # 使用错误的常量值
        header_data = bytes([0xAA, 0xAA])

        result = parser._parse_header(header_data)

        # 常量校验失败应该返回 None
        assert result is None

    def test_parse_data_groups_insufficient_length(self, mock_yaml_format):
        """测试数据长度不足"""
        parser = ProtocolParser(mock_yaml_format)

        # 设置头部和尾部长度
        mock_yaml_format.config.head_len = 10
        mock_yaml_format.config.tail_len = 2

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02",  # 只有4字节，小于head_len
            }
        ]

        result = parser.parse_data_groups(data_groups)

        # 数据长度不足应该被跳过
        assert len(result) == 0

    def test_parse_data_groups_with_parse_error(self, mock_yaml_format):
        """测试解析错误处理"""
        parser = ProtocolParser(mock_yaml_format)

        mock_yaml_format.config.head_len = 4
        mock_yaml_format.config.tail_len = 0
        mock_yaml_format.get_head_fields.return_value = [
            {"name": "cmd", "offset": 2, "length": 2, "endian": "big", "type": "uint"}
        ]
        mock_yaml_format.has_cmd.return_value = True
        # 模拟解析错误
        mock_yaml_format.parse_cmd_data.side_effect = Exception("解析失败")

        data_groups = [
            {
                "time": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "data": "68 68 01 02 AA BB",
            }
        ]

        result = parser.parse_data_groups(data_groups)

        # 解析错误时应该包含原始数据和错误信息
        assert len(result) == 1
        assert "parse_error" in result[0]
        assert result[0]["parse_error"] == "解析失败"
        assert "raw" in result[0]["content"]

    def test_check_cmd_filter_with_invalid_ranges(self, mock_yaml_format):
        """测试命令过滤器的边界情况"""
        parser = ProtocolParser(mock_yaml_format)

        # 测试极端值
        assert parser._check_cmd_filter(0) is True
        assert parser._check_cmd_filter(-1) is True
        assert parser._check_cmd_filter(999999) is True

        # 设置过滤器后测试
        parser.set_filters(include_cmds=[1, 2, 3])
        assert parser._check_cmd_filter(0) is False
        assert parser._check_cmd_filter(-1) is False

    def test_check_time_filter_with_invalid_time_format(self, mock_yaml_format):
        """测试无效时间格式的处理"""
        parser = ProtocolParser(mock_yaml_format)

        from datetime import datetime
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 12, 31, 23, 59, 59)
        parser.set_filters(time_range=(start_time, end_time))

        # 无效格式应该默认通过（不抛出异常）
        assert parser._check_time_filter("invalid_time") is True
        assert parser._check_time_filter("") is True
        assert parser._check_time_filter("2024-13-45 99:99:99") is True


# Fixtures
@pytest.fixture
def mock_yaml_format():
    """创建Mock的YamlCmdFormat对象"""
    mock = Mock()
    mock.config = Mock()
    mock.config.head_len = 4
    mock.config.tail_len = 0
    mock.config.frame_head = r"68"
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
