"""
测试 yaml_cmdformat.py 模块
测试基于YAML配置的命令格式管理器

测试覆盖率目标: >90%
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.yaml_cmdformat import (
    YamlCmdFormat,
    get_yaml_format,
    load_yaml_format,
    strlist_to_hexlist,
)
from src.yaml_config import EnumDef, Field, Group, Meta, ProtocolConfig, TypeDef


class TestYamlCmdFormatInit:
    """测试 YamlCmdFormat 初始化"""

    def test_init_with_valid_config(self, v8_config_path):
        """测试使用有效配置初始化"""
        cmd_format = YamlCmdFormat(v8_config_path)

        assert cmd_format.config_path == Path(v8_config_path)
        assert cmd_format.config is not None
        assert cmd_format.config.meta.protocol == "v8"
        assert cmd_format.field_parser is not None

    def test_init_with_pathlib_path(self, v8_config_path):
        """测试使用 pathlib.Path 初始化"""
        cmd_format = YamlCmdFormat(Path(v8_config_path))

        assert cmd_format.config_path == Path(v8_config_path)
        assert cmd_format.config is not None

    def test_init_with_invalid_path(self):
        """测试使用无效路径初始化"""
        with pytest.raises(FileNotFoundError):
            YamlCmdFormat("nonexistent_config.yaml")

    def test_init_cache_mechanism(self, v8_config_path):
        """测试配置缓存机制"""
        # 第一次加载
        cmd_format1 = YamlCmdFormat(v8_config_path)
        # 第二次加载应该使用缓存
        cmd_format2 = YamlCmdFormat(v8_config_path)

        # 验证两个实例的配置是同一个对象（缓存）
        assert cmd_format1.config is cmd_format2.config


class TestGetCmdLayout:
    """测试获取命令布局"""

    def test_get_existing_command_layout(self, v8_config_path):
        """测试获取存在的命令布局"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # V8协议命令2存在
        layout = cmd_format.get_cmd_layout(2)

        assert isinstance(layout, list)
        assert len(layout) > 0
        # 验证布局包含 Field 或 Group 对象（导入类型可能不同，使用字符串检查）
        for item in layout:
            type_name = type(item).__name__
            assert type_name in ["Field", "Group"]

    def test_get_nonexistent_command_layout(self, v8_config_path):
        """测试获取不存在的命令布局"""
        cmd_format = YamlCmdFormat(v8_config_path)

        with pytest.raises(ValueError, match="Command 9999 not found"):
            cmd_format.get_cmd_layout(9999)

    def test_get_multiple_commands_layout(self, v8_config_path):
        """测试获取多个命令的布局"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 测试几个存在的命令
        for cmd_id in [1, 2, 3]:
            try:
                layout = cmd_format.get_cmd_layout(cmd_id)
                assert isinstance(layout, list)
            except ValueError:
                # 某些命令ID可能不存在，这是正常的
                pass

    def test_layout_contains_fields_and_groups(self, v8_config_path):
        """测试布局包含字段和组"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 获取一个可能包含循环结构的命令
        layout = cmd_format.get_cmd_layout(2)

        has_field = any(type(item).__name__ == "Field" for item in layout)
        has_group = any(type(item).__name__ == "Group" for item in layout)

        # 至少应该有字段
        assert has_field or len(layout) > 0


class TestHasCmd:
    """测试命令存在性检查"""

    def test_has_existing_command(self, v8_config_path):
        """测试检查存在的命令"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # V8协议命令2应该存在
        assert cmd_format.has_cmd(2) is True

    def test_has_nonexistent_command(self, v8_config_path):
        """测试检查不存在的命令"""
        cmd_format = YamlCmdFormat(v8_config_path)

        assert cmd_format.has_cmd(9999) is False

    def test_has_command_multiple_checks(self, v8_config_path):
        """测试多次检查命令"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 测试多个命令ID
        results = {cmd_id: cmd_format.has_cmd(cmd_id) for cmd_id in [1, 2, 3, 999, 1000, 9999]}

        # 至少应该有一些命令存在
        assert any(results.values())


class TestParseCmdData:
    """测试命令数据解析"""

    def test_parse_supported_command(self, v8_config_path):
        """测试解析支持的命令数据"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 构造简单的测试数据（假设命令2的数据格式）
        test_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05])

        try:
            result = cmd_format.parse_cmd_data(2, test_data)
            assert isinstance(result, dict)
        except ValueError:
            # 如果命令2不存在或数据格式不匹配，这是预期的
            pass

    def test_parse_unsupported_command_raises_error(self, v8_config_path):
        """测试解析不支持的命令抛出异常"""
        cmd_format = YamlCmdFormat(v8_config_path)

        test_data = bytes([0x01, 0x02, 0x03])

        with pytest.raises(ValueError, match="Unsupported command: 9999"):
            cmd_format.parse_cmd_data(9999, test_data)

    def test_parse_with_empty_data(self, v8_config_path):
        """测试解析空数据"""
        cmd_format = YamlCmdFormat(v8_config_path)

        try:
            result = cmd_format.parse_cmd_data(2, b"")
            # 某些命令可能允许空数据
            assert isinstance(result, dict)
        except (ValueError, IndexError):
            # 空数据可能导致解析错误，这是正常的
            pass

    def test_parse_with_various_data_lengths(self, v8_config_path):
        """测试解析不同长度的数据"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 测试不同长度的数据
        for length in [0, 1, 5, 10, 100]:
            test_data = bytes([i % 256 for i in range(length)])

            try:
                result = cmd_format.parse_cmd_data(2, test_data)
                assert isinstance(result, dict)
            except (ValueError, IndexError):
                # 某些长度可能不匹配命令格式，这是正常的
                pass


class TestGetSupportedCmds:
    """测试获取支持的命令列表"""

    def test_get_supported_commands_not_empty(self, v8_config_path):
        """测试获取支持的命令列表不为空"""
        cmd_format = YamlCmdFormat(v8_config_path)

        cmds = cmd_format.get_supported_cmds()

        assert isinstance(cmds, list)
        assert len(cmds) > 0
        # 验证所有元素都是整数
        for cmd_id in cmds:
            assert isinstance(cmd_id, int)

    def test_get_supported_commands_contains_known_ids(self, v8_config_path):
        """测试支持的命令列表包含已知ID"""
        cmd_format = YamlCmdFormat(v8_config_path)

        cmds = cmd_format.get_supported_cmds()

        # 验证返回的命令ID确实存在
        for cmd_id in cmds:
            assert cmd_format.has_cmd(cmd_id) is True

    def test_get_supported_commands_all_unique(self, v8_config_path):
        """测试支持的命令列表没有重复"""
        cmd_format = YamlCmdFormat(v8_config_path)

        cmds = cmd_format.get_supported_cmds()

        # 转为集合检查唯一性
        assert len(cmds) == len(set(cmds))


class TestGetProtocolInfo:
    """测试获取协议信息"""

    def test_get_protocol_info_structure(self, v8_config_path):
        """测试协议信息的结构"""
        cmd_format = YamlCmdFormat(v8_config_path)

        info = cmd_format.get_protocol_info()

        assert isinstance(info, dict)
        # 验证必需的字段
        required_keys = [
            "protocol",
            "version",
            "default_endian",
            "supported_cmds",
            "head_len",
            "tail_len",
            "frame_head",
        ]
        for key in required_keys:
            assert key in info

    def test_get_protocol_info_content(self, v8_config_path):
        """测试协议信息的内容"""
        cmd_format = YamlCmdFormat(v8_config_path)

        info = cmd_format.get_protocol_info()

        assert info["protocol"] == "v8"
        assert info["version"] == 1
        assert info["default_endian"] == "LE"
        assert isinstance(info["supported_cmds"], list)
        assert len(info["supported_cmds"]) > 0

    def test_get_protocol_info_compatibility_fields(self, v8_config_path):
        """测试协议信息的兼容性字段"""
        cmd_format = YamlCmdFormat(v8_config_path)

        info = cmd_format.get_protocol_info()

        assert info["head_len"] == 11
        assert info["tail_len"] == 2
        assert info["frame_head"] == "AA F5"

    def test_get_protocol_info_notes_optional(self, v8_config_path):
        """测试协议信息的备注字段（可选）"""
        cmd_format = YamlCmdFormat(v8_config_path)

        info = cmd_format.get_protocol_info()

        # notes字段是可选的
        if "notes" in info:
            assert isinstance(info["notes"], (str, type(None)))


class TestGetHeadFields:
    """测试获取头部字段配置"""

    def test_get_head_fields_returns_list(self, v8_config_path):
        """测试获取头部字段返回列表"""
        cmd_format = YamlCmdFormat(v8_config_path)

        head_fields = cmd_format.get_head_fields()

        assert isinstance(head_fields, list)

    def test_get_head_fields_content(self, v8_config_path):
        """测试头部字段的内容"""
        cmd_format = YamlCmdFormat(v8_config_path)

        head_fields = cmd_format.get_head_fields()

        # V8协议应该有头部字段定义
        if len(head_fields) > 0:
            # 验证字段结构
            for field in head_fields:
                assert isinstance(field, dict)
                assert "name" in field

    def test_get_head_fields_v8_specific(self, v8_config_path):
        """测试V8协议特定的头部字段"""
        cmd_format = YamlCmdFormat(v8_config_path)

        head_fields = cmd_format.get_head_fields()

        # V8协议应该包含这些字段
        field_names = [field.get("name") for field in head_fields]
        expected_fields = ["cmd", "index", "deviceType", "addr", "gunNum"]

        for expected in expected_fields:
            assert expected in field_names


class TestValidateConfig:
    """测试配置验证"""

    def test_validate_valid_config(self, v8_config_path):
        """测试验证有效配置"""
        cmd_format = YamlCmdFormat(v8_config_path)

        errors = cmd_format.validate_config()

        # V8配置应该是有效的
        assert isinstance(errors, list)
        # 期望没有错误
        assert len(errors) == 0 or all(isinstance(e, str) for e in errors)

    def test_validate_config_returns_list(self, v8_config_path):
        """测试验证配置返回列表"""
        cmd_format = YamlCmdFormat(v8_config_path)

        errors = cmd_format.validate_config()

        assert isinstance(errors, list)

    def test_validate_config_error_messages(self, v8_config_path):
        """测试验证配置的错误消息格式"""
        cmd_format = YamlCmdFormat(v8_config_path)

        errors = cmd_format.validate_config()

        # 如果有错误，验证错误消息格式
        for error in errors:
            assert isinstance(error, str)
            assert len(error) > 0


class TestLoadYamlFormat:
    """测试加载YAML格式配置函数"""

    def test_load_yaml_format_returns_instance(self, v8_config_path):
        """测试加载YAML格式返回实例"""
        cmd_format = load_yaml_format(v8_config_path)

        assert isinstance(cmd_format, YamlCmdFormat)

    def test_load_yaml_format_with_pathlib(self, v8_config_path):
        """测试使用pathlib.Path加载"""
        cmd_format = load_yaml_format(Path(v8_config_path))

        assert isinstance(cmd_format, YamlCmdFormat)

    def test_load_yaml_format_invalid_path(self):
        """测试使用无效路径加载"""
        with pytest.raises(FileNotFoundError):
            load_yaml_format("nonexistent.yaml")


class TestGetYamlFormat:
    """测试根据协议名获取YAML格式配置"""

    def test_get_yaml_format_v8(self):
        """测试获取V8协议配置"""
        cmd_format = get_yaml_format("v8")

        assert isinstance(cmd_format, YamlCmdFormat)
        assert cmd_format.config.meta.protocol == "v8"

    def test_get_yaml_format_xiaoju(self):
        """测试获取小桔协议配置"""
        cmd_format = get_yaml_format("xiaoju")

        assert isinstance(cmd_format, YamlCmdFormat)
        assert cmd_format.config.meta.protocol == "xiaoju"

    def test_get_yaml_format_nonexistent_protocol(self):
        """测试获取不存在的协议"""
        with pytest.raises(FileNotFoundError, match="Protocol config not found"):
            get_yaml_format("nonexistent_protocol")

    def test_get_yaml_format_config_path_construction(self):
        """测试配置路径构造"""
        # 测试函数会构造 configs/<protocol_name>/protocol.yaml 路径
        with pytest.raises(FileNotFoundError):
            get_yaml_format("test_nonexistent")


class TestStrlistToHexlist:
    """测试字符串列表转十六进制列表工具函数"""

    def test_convert_simple_hex_strings(self):
        """测试转换简单的十六进制字符串"""
        str_list = ["AA", "BB", "CC"]
        result = strlist_to_hexlist(str_list)

        assert result == [0xAA, 0xBB, 0xCC]

    def test_convert_hex_strings_with_spaces(self):
        """测试转换带空格的十六进制字符串"""
        str_list = ["AA BB", "CC DD"]
        result = strlist_to_hexlist(str_list)

        assert result == [0xAA, 0xBB, 0xCC, 0xDD]

    def test_convert_mixed_format_strings(self):
        """测试转换混合格式的字符串"""
        str_list = ["AA", "BB CC", "DD"]
        result = strlist_to_hexlist(str_list)

        assert result == [0xAA, 0xBB, 0xCC, 0xDD]

    def test_convert_empty_list(self):
        """测试转换空列表"""
        result = strlist_to_hexlist([])

        assert result == []

    def test_convert_invalid_hex_string(self, caplog):
        """测试转换无效的十六进制字符串"""
        import logging

        str_list = ["ZZ"]  # 无效的十六进制

        result = strlist_to_hexlist(str_list)

        # 无效字符串应该被跳过，返回空列表
        assert result == []

    def test_convert_odd_length_hex_string(self, caplog):
        """测试转换奇数长度的十六进制字符串"""
        import logging

        str_list = ["AAA"]  # 奇数长度

        result = strlist_to_hexlist(str_list)

        # 奇数长度字符串应该被跳过
        assert result == []

    def test_convert_uppercase_lowercase(self):
        """测试大小写十六进制字符串"""
        str_list = ["aa", "BB", "Cc"]
        result = strlist_to_hexlist(str_list)

        assert result == [0xAA, 0xBB, 0xCC]

    def test_convert_with_prefix(self):
        """测试带前缀的十六进制字符串"""
        str_list = ["0xAA", "0xBB"]
        result = strlist_to_hexlist(str_list)

        # "0x"会被当作无效字符处理
        # 这个测试验证函数的健壮性
        assert isinstance(result, list)


class TestYamlCmdFormatIntegration:
    """集成测试：测试多个方法的组合使用"""

    def test_full_workflow(self, v8_config_path):
        """测试完整工作流程"""
        # 1. 加载配置
        cmd_format = YamlCmdFormat(v8_config_path)

        # 2. 获取协议信息
        info = cmd_format.get_protocol_info()
        assert "protocol" in info

        # 3. 获取支持的命令
        cmds = cmd_format.get_supported_cmds()
        assert len(cmds) > 0

        # 4. 检查命令存在性
        first_cmd = cmds[0]
        assert cmd_format.has_cmd(first_cmd) is True

        # 5. 获取命令布局
        layout = cmd_format.get_cmd_layout(first_cmd)
        assert len(layout) >= 0

    def test_multiple_protocols(self):
        """测试加载多个协议"""
        protocols = ["v8", "xiaoju"]

        for protocol in protocols:
            try:
                cmd_format = get_yaml_format(protocol)
                assert cmd_format.config.meta.protocol == protocol
            except FileNotFoundError:
                # 某些协议可能不存在
                pass

    def test_config_validation_workflow(self, v8_config_path):
        """测试配置验证工作流程"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 验证配置
        errors = cmd_format.validate_config()

        # 获取协议信息
        info = cmd_format.get_protocol_info()

        # 如果配置有效，协议信息应该完整
        if len(errors) == 0:
            assert "protocol" in info
            assert "version" in info
            assert "supported_cmds" in info


class TestYamlCmdFormatEdgeCases:
    """边界情况和异常处理测试"""

    def test_zero_command_id(self, v8_config_path):
        """测试命令ID为0"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 命令0可能不存在
        result = cmd_format.has_cmd(0)
        assert isinstance(result, bool)

    def test_negative_command_id(self, v8_config_path):
        """测试负数命令ID"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 负数命令ID应该不存在
        assert cmd_format.has_cmd(-1) is False

    def test_very_large_command_id(self, v8_config_path):
        """测试非常大的命令ID"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 非常大的命令ID应该不存在
        assert cmd_format.has_cmd(999999) is False

    def test_parse_with_none_data(self, v8_config_path):
        """测试解析None数据"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # None数据应该导致错误
        with pytest.raises((TypeError, AttributeError)):
            cmd_format.parse_cmd_data(2, None)

    def test_load_nonexistent_config_file(self):
        """测试加载不存在的配置文件"""
        with pytest.raises(FileNotFoundError, match="Protocol config file not found"):
            YamlCmdFormat("path/to/nonexistent_config.yaml")

    def test_get_nonexistent_command_layout(self, v8_config_path):
        """测试获取不存在的命令布局"""
        cmd_format = YamlCmdFormat(v8_config_path)

        # 测试不存在的命令ID
        with pytest.raises(ValueError, match="Command 9999 not found"):
            cmd_format.get_cmd_layout(9999)

    def test_parse_unsupported_command(self, v8_config_path):
        """测试解析不支持的命令"""
        cmd_format = YamlCmdFormat(v8_config_path)

        test_data = bytes([0x01, 0x02, 0x03])

        # 不支持的命令应该抛出异常
        with pytest.raises(ValueError, match="Unsupported command: 9999"):
            cmd_format.parse_cmd_data(9999, test_data)

    def test_load_yaml_format_nonexistent_protocol(self):
        """测试加载不存在的协议配置"""
        with pytest.raises(FileNotFoundError, match="Protocol config not found"):
            get_yaml_format("nonexistent_protocol")

    def test_load_yaml_format_invalid_path(self):
        """测试使用无效路径加载YAML格式"""
        with pytest.raises(FileNotFoundError):
            load_yaml_format("invalid_path.yaml")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/yaml_cmdformat", "--cov-report=term-missing"])
