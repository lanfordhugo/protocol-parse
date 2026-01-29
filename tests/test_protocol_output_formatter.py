"""
协议输出格式化器测试
测试 ProtocolOutputFormatter 类的输出格式化功能
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.protocol_output_formatter import ProtocolOutputFormatter


class TestProtocolOutputFormatterInit:
    """测试协议输出格式化器初始化"""

    def test_init(self, mock_yaml_format):
        """测试初始化"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)
        assert formatter.yaml_format == mock_yaml_format
        assert formatter.yaml_config == mock_yaml_format.config


class TestFormatAndSave:
    """测试格式化和保存"""

    def test_format_and_save_success(self, mock_yaml_format, tmp_path):
        """测试成功格式化和保存"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        # 准备测试数据
        parse_data = [
            {
                "timestamp": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "cmd": 0x0102,
                "content": {"field1": "value1", "field2": 100},
            }
        ]

        perf_stats = {
            "total": [1.5],
            "extract": [0.5],
            "parse": [0.8],
            "screen": [0.2],
            "cmd_counts": {0x0102: 1},
            "errors": 0,
        }

        # 保存到临时目录
        result_path = formatter.format_and_save(parse_data, perf_stats, output_dir=str(tmp_path))

        # 验证文件存在
        assert result_path is not None
        assert os.path.exists(result_path)

        # 验证文件内容
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "成功解析 1 条数据" in content
        assert "协议: test_protocol v1" in content
        assert "cmd258: 1 条" in content  # 0x0102 = 258
        assert "2024-01-28 10:30:45.123" in content
        assert "终端ID: 1" in content
        assert "field1: value1" in content
        assert "性能统计摘要" in content

    def test_format_and_save_empty_data(self, mock_yaml_format):
        """测试空数据"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        result = formatter.format_and_save([], {})

        # 空数据应该返回 None
        assert result is None

    def test_format_and_save_without_terminal_id(self, mock_yaml_format, tmp_path):
        """测试没有终端ID的数据"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        parse_data = [
            {
                "timestamp": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": None,
                "cmd": 0x0102,
                "content": {"field1": "value1"},
            }
        ]

        perf_stats = {}

        result_path = formatter.format_and_save(parse_data, perf_stats, output_dir=str(tmp_path))

        assert result_path is not None
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 不应该包含终端ID
        assert "终端ID:" not in content

    def test_format_and_save_with_parse_error(self, mock_yaml_format, tmp_path):
        """测试包含解析错误的数据"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        parse_data = [
            {
                "timestamp": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "cmd": 0x0102,
                "content": {"raw": "6868AABB"},
                "parse_error": "Test parse error",
            }
        ]

        perf_stats = {"cmd_counts": {0x0102: 1}, "errors": 1}

        result_path = formatter.format_and_save(parse_data, perf_stats, output_dir=str(tmp_path))

        assert result_path is not None
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "解析错误: Test parse error" in content
        assert "解析失败: 1 次" in content

    def test_format_and_save_multiple_items(self, mock_yaml_format, tmp_path):
        """测试多个数据项"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        parse_data = [
            {
                "timestamp": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "cmd": 0x0102,
                "content": {"field1": "value1"},
            },
            {
                "timestamp": "2024-01-28 10:30:46.456",
                "direction": "Recv",
                "terminal_id": 2,
                "cmd": 0x0304,
                "content": {"field2": "value2"},
            },
        ]

        perf_stats = {"cmd_counts": {0x0102: 1, 0x0304: 1}, "errors": 0}

        result_path = formatter.format_and_save(parse_data, perf_stats, output_dir=str(tmp_path))

        assert result_path is not None
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "成功解析 2 条数据" in content
        assert "=== 数据项 1 ===" in content
        assert "=== 数据项 2 ===" in content
        assert "cmd258: 1 条" in content
        assert "cmd772: 1 条" in content  # 0x0304 = 772


class TestBuildOutputLines:
    """测试输出行构建"""

    def test_build_output_lines_basic(self, mock_yaml_format):
        """测试基本输出行构建"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        parse_data = [
            {
                "timestamp": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "cmd": 0x0102,
                "content": {"field1": "value1"},
            }
        ]

        protocol_info = {"protocol": "test_protocol", "version": "1", "supported_cmds": [0x0102]}

        perf_stats = {
            "total": [1.5],
            "extract": [0.5],
            "parse": [0.8],
            "screen": [0.2],
            "cmd_counts": {0x0102: 1},
            "errors": 0,
        }

        output_lines = formatter._build_output_lines(parse_data, protocol_info, perf_stats)

        assert len(output_lines) > 0
        assert any("成功解析 1 条数据" in line for line in output_lines)
        assert any("协议: test_protocol v1" in line for line in output_lines)


class TestCollectContentLines:
    """测试内容行收集"""

    def test_collect_content_lines_simple_dict(self, mock_yaml_format):
        """测试简单字典内容"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        content = {"field1": "value1", "field2": 100}
        output_lines = []

        formatter._collect_content_lines(content, output_lines, indent=0)

        assert len(output_lines) == 2
        assert any("field1: value1" in line for line in output_lines)
        assert any("field2: 100" in line for line in output_lines)

    def test_collect_content_lines_nested_dict(self, mock_yaml_format):
        """测试嵌套字典内容"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        content = {"outer": {"inner1": "value1", "inner2": "value2"}}
        output_lines = []

        formatter._collect_content_lines(content, output_lines, indent=0)

        assert len(output_lines) == 3
        assert any("outer:" in line for line in output_lines)
        assert any("inner1: value1" in line for line in output_lines)
        assert any("inner2: value2" in line for line in output_lines)

    def test_collect_content_lines_list(self, mock_yaml_format):
        """测试列表内容"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        content = {"items": [10, 20, 30]}
        output_lines = []

        formatter._collect_content_lines(content, output_lines, indent=0)

        assert len(output_lines) == 4  # 1行标题 + 3行数据
        assert any("items: [3 项]" in line for line in output_lines)

    def test_collect_content_lines_enum_value(self, mock_yaml_format):
        """测试枚举值"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        content = {"status": {"value": 1, "name": "Online"}}
        output_lines = []

        formatter._collect_content_lines(content, output_lines, indent=0)

        assert len(output_lines) == 1
        assert "status: 1 (Online)" in output_lines[0]


class TestFormatFloat:
    """测试浮点数格式化"""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1.0, "1"),
            (1.5, "1.5"),
            (1.23456789, "1.23457"),
            (100.0, "100"),
            (0.00001, "0.00001"),
        ],
        ids=["integer", "decimal", "rounded", "hundred", "scientific_notation"],
    )
    def test_format_float(self, mock_yaml_format, value, expected):
        """测试浮点数格式化"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        result = formatter._format_float(value)

        assert result == expected

    def test_format_float_non_float(self, mock_yaml_format):
        """测试非浮点数输入"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        result = formatter._format_float("string")

        assert result == "string"


class TestBuildPerfStatsLines:
    """测试性能统计行构建"""

    def test_build_perf_stats_lines_with_data(self, mock_yaml_format):
        """测试有数据的性能统计"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        perf_stats = {
            "total": [1.5, 2.0],
            "extract": [0.5, 0.6],
            "parse": [0.8, 1.0],
            "screen": [0.2, 0.4],
            "cmd_counts": {0x0102: 10, 0x0304: 5},
            "errors": 1,
        }

        lines = formatter._build_perf_stats_lines(perf_stats)

        assert len(lines) > 0
        assert any("=== 性能统计摘要 ===" in line for line in lines)
        assert any("总耗时:" in line for line in lines)
        assert any("CMD 258: 10 条" in line for line in lines)
        assert any("解析失败: 1 次" in line for line in lines)

    def test_build_perf_stats_lines_empty(self, mock_yaml_format):
        """测试空性能统计"""
        formatter = ProtocolOutputFormatter(mock_yaml_format)

        perf_stats = {}

        lines = formatter._build_perf_stats_lines(perf_stats)

        # 应该包含性能统计标题和结束标记
        assert any("=== 性能统计摘要 ===" in line for line in lines)
        assert any("====================" in line for line in lines)


# Fixtures
@pytest.fixture
def mock_yaml_format():
    """创建Mock的YamlCmdFormat对象"""
    mock = Mock()
    mock.config = Mock()
    mock.config.head_len = 4
    mock.config.tail_len = 0
    mock.config.frame_head = r"68"
    mock.get_protocol_info.return_value = {
        "protocol": "test_protocol",
        "version": "1",
        "supported_cmds": [0x0102, 0x0304],
    }
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
