"""
测试bitfield功能
"""

import struct

import pytest

from src.yaml_config import BitfieldGroup, ProtocolConfig, TypeDef, yaml_loader
from src.yaml_field_parser import YamlFieldParser


class TestBitfield:
    """测试bitfield解析功能"""

    def setup_method(self):
        """设置测试环境"""
        # 创建测试用的协议配置
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "pump_status_field": {
                    "base": "bitfield",
                    "bytes": 1,
                    "order": "lsb0",
                    "groups": [
                        {"name": "液冷泵1状态", "start_bit": 0, "width": 4, "enum": "pump_status"},
                        {"name": "液冷泵2状态", "start_bit": 4, "width": 4, "enum": "pump_status"},
                    ],
                },
                "mixed_bitfield": {
                    "base": "bitfield",
                    "bytes": 2,
                    "order": "lsb0",
                    "groups": [
                        {"name": "A", "start_bit": 0, "width": 2},
                        {"name": "B", "start_bit": 2, "width": 4},
                        {"name": "C", "start_bit": 6, "width": 4},
                        {"name": "D", "start_bit": 10, "width": 6},
                    ],
                },
            },
            "enums": {"pump_status": {0: "正常", 1: "故障", 2: "手动"}},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }

        return yaml_loader._parse_config(config_data)

    def test_bitfield_group_validation(self):
        """测试位段组验证"""
        # 测试有效的位段组
        type_def = self.config.types["pump_status_field"]
        groups = type_def.get_bitfield_groups()
        assert len(groups) == 2
        assert groups[0].name == "液冷泵1状态"
        assert groups[0].start_bit == 0
        assert groups[0].width == 4
        assert groups[1].name == "液冷泵2状态"
        assert groups[1].start_bit == 4
        assert groups[1].width == 4

    def test_bitfield_parse_basic(self):
        """测试基本的bitfield解析"""
        # 测试数据：0x21 = 0010 0001
        # 低4位(液冷泵1状态) = 0001 = 1 (故障)
        # 高4位(液冷泵2状态) = 0010 = 2 (手动)
        test_data = b"\x21"

        type_def = self.config.types["pump_status_field"]
        from src.yaml_config import Field

        field = Field(len=1, name="test", type="pump_status_field")

        result = self.parser._parse_bitfield(test_data, type_def, field)

        assert "液冷泵1状态" in result
        assert "液冷泵2状态" in result
        assert result["液冷泵1状态"] == "故障"  # 枚举文本
        assert result["液冷泵2状态"] == "手动"  # 枚举文本

    def test_bitfield_parse_without_enum(self):
        """测试不带枚举的bitfield解析"""
        # 测试数据：0x1234 (小端序)
        test_data = b"\x34\x12"

        type_def = self.config.types["mixed_bitfield"]
        from src.yaml_config import Field

        field = Field(len=2, name="test", type="mixed_bitfield")

        result = self.parser._parse_bitfield(test_data, type_def, field)

        # 0x1234 = 0001 0010 0011 0100
        # A (bit 0-1): 00 = 0
        # B (bit 2-5): 1101 = 13
        # C (bit 6-9): 1000 = 8
        # D (bit 10-15): 000100 = 4

        assert result["A"] == 0
        assert result["B"] == 13
        assert result["C"] == 8
        assert result["D"] == 4

    def test_bitfield_edge_cases(self):
        """测试边界情况"""
        # 测试全0
        test_data = b"\x00"
        type_def = self.config.types["pump_status_field"]
        from src.yaml_config import Field

        field = Field(len=1, name="test", type="pump_status_field")

        result = self.parser._parse_bitfield(test_data, type_def, field)
        assert result["液冷泵1状态"] == "正常"
        assert result["液冷泵2状态"] == "正常"

        # 测试全1
        test_data = b"\xFF"
        result = self.parser._parse_bitfield(test_data, type_def, field)
        # 0xFF = 1111 1111
        # 低4位 = 1111 = 15，不在枚举中
        # 高4位 = 1111 = 15，不在枚举中
        assert "Unknown(15)" in result["液冷泵1状态"]
        assert "Unknown(15)" in result["液冷泵2状态"]

    def test_bitfield_validation_errors(self):
        """测试bitfield验证错误"""
        # 测试位段重叠
        with pytest.raises(ValueError, match="overlaps"):
            invalid_config = {
                "base": "bitfield",
                "bytes": 1,
                "groups": [
                    {"name": "A", "start_bit": 0, "width": 4},
                    {"name": "B", "start_bit": 2, "width": 4},  # 与A重叠
                ],
            }
            TypeDef(**invalid_config)

        # 测试超出范围
        with pytest.raises(ValueError, match="exceeds total bits"):
            invalid_config = {
                "base": "bitfield",
                "bytes": 1,
                "groups": [{"name": "A", "start_bit": 0, "width": 10}],  # 超出8位
            }
            TypeDef(**invalid_config)

    def test_bytes_to_int(self):
        """测试字节到整数的转换"""
        # 测试小端序
        data = b"\x34\x12"
        result = self.parser._bytes_to_int(data, "LE")
        assert result == 0x1234

        # 测试大端序
        result = self.parser._bytes_to_int(data, "BE")
        assert result == 0x3412

        # 测试单字节
        data = b"\x42"
        result = self.parser._bytes_to_int(data, "LE")
        assert result == 0x42


if __name__ == "__main__":
    pytest.main([__file__])
