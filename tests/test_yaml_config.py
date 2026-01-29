"""
测试YAML配置加载和验证
"""

import sys
from pathlib import Path

import pytest

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yaml_config import ProtocolConfig, yaml_loader, TypeDef, BitfieldGroup, Group


class TestYamlConfig:
    """YAML配置测试类"""

    def test_load_v8_config(self):
        """测试加载v8配置"""
        config_path = Path("configs/v8/protocol.yaml")
        config = yaml_loader.load_protocol_config(config_path)

        assert config.meta.protocol == "v8"
        assert config.meta.version == 1
        assert config.meta.default_endian == "LE"
        assert len(config.types) > 0
        assert len(config.cmds) > 0
        assert config.head_len == 11
        assert config.tail_len == 2
        assert config.frame_head == "AA F5"

    def test_load_xiaoju_config(self):
        """测试加载xiaoju配置"""
        config_path = Path("configs/xiaoju/protocol.yaml")
        config = yaml_loader.load_protocol_config(config_path)

        assert config.meta.protocol == "xiaoju"
        assert config.meta.version == 1
        assert config.head_len == 14
        assert config.tail_len == 1
        assert config.frame_head == "7D D0"

    def test_validate_all_configs(self):
        """测试验证所有配置"""
        protocols = ["v8", "xiaoju", "yunwei", "sinexcel"]

        for protocol in protocols:
            config_path = Path(f"configs/{protocol}/protocol.yaml")
            if config_path.exists():
                config = yaml_loader.load_protocol_config(config_path)
                errors = yaml_loader.validate_config(config)
                assert len(errors) == 0, f"Protocol {protocol} has validation errors: {errors}"

    def test_get_cmd_layout(self):
        """测试获取命令布局"""
        config_path = Path("configs/v8/protocol.yaml")
        config = yaml_loader.load_protocol_config(config_path)

        # 测试存在的命令
        layout = yaml_loader.get_cmd_layout(config, 2)
        assert len(layout) > 0

        # 测试不存在的命令
        with pytest.raises(ValueError):
            yaml_loader.get_cmd_layout(config, 9999)

    def test_type_definitions(self):
        """测试类型定义"""
        config_path = Path("configs/v8/protocol.yaml")
        config = yaml_loader.load_protocol_config(config_path)

        # 检查基本类型
        assert "uint8" in config.types
        assert "uint16" in config.types
        assert "uint32" in config.types
        assert "ascii" in config.types

        # 检查类型属性
        uint8_type = config.types["uint8"]
        assert uint8_type.base == "uint"
        assert uint8_type.bytes == 1
        assert uint8_type.signed == False

    def test_enum_definitions(self):
        """测试枚举定义"""
        config_path = Path("configs/v8/protocol.yaml")
        config = yaml_loader.load_protocol_config(config_path)

        # 检查枚举存在
        assert "login_result" in config.enums

        # 检查枚举值
        login_result = config.enums["login_result"]
        assert 0 in login_result.values
        assert 1 in login_result.values
        assert login_result.values[0] == "失败"
        assert login_result.values[1] == "成功"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

class TestTypeDefValidation:
    """测试 TypeDef 参数验证"""

    def test_uint_missing_bytes(self):
        """验证 uint 类型缺少 bytes 参数"""
        with pytest.raises(ValueError, match=r"Type uint requires 'bytes' parameter"):
            TypeDef(base="uint", bytes=None)

    def test_int_missing_bytes(self):
        """验证 int 类型缺少 bytes 参数"""
        with pytest.raises(ValueError, match=r"Type int requires 'bytes' parameter"):
            TypeDef(base="int", bytes=None)

    def test_bitset_missing_bits(self):
        """验证 bitset 类型缺少 bits 参数"""
        with pytest.raises(ValueError, match=r"Bitset type requires 'bits' parameter"):
            TypeDef(base="bitset", bits=None)

    def test_bitfield_missing_bytes(self):
        """验证 bitfield 类型缺少 bytes 参数"""
        with pytest.raises(ValueError, match=r"Bitfield type requires 'bytes' parameter"):
            TypeDef(base="bitfield", bytes=None)


class TestGroupValidation:
    """测试 Group 验证逻辑"""

    def test_no_repeat_params(self):
        """验证无循环条件"""
        with pytest.raises(ValueError, match=r"Group must specify either repeat_by or repeat_const"):
            Group(fields=[], repeat_by=None, repeat_const=None)

    def test_both_repeat_params(self):
        """验证同时设置两个循环条件"""
        with pytest.raises(ValueError, match=r"Group cannot specify both repeat_by and repeat_const"):
            Group(fields=[], repeat_by="count", repeat_const=10)

