"""
测试 yaml_field_parser.py 模块

覆盖范围：
- 基础类型解析（uint/int/str/hex/bcd）
- 时间格式解析（cp56time2a/bcd_time/unix_time）
- 位段解析（bitset/bitfield）
- 后处理（scale/unit/enum/when）
- 字段组（repeat_const/repeat_by）
- 边界情况和错误处理
"""

import struct
from datetime import datetime
from decimal import Decimal

import pytest

from src.yaml_config import (
    BitfieldGroup,
    Field,
    Group,
    ProtocolConfig,
    TypeDef,
    yaml_loader,
)
from src.yaml_field_parser import (
    MISSING_FIELD_PLACEHOLDER,
    FieldDataMissing,
    YamlFieldParser,
)
# ByteDataBuilder 在 fixtures 中定义，无需在此导入


class TestBasicTypes:
    """测试基础数据类型解析"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
                "uint32": {"base": "uint", "bytes": 4},
                "uint64": {"base": "uint", "bytes": 8},
                "int8": {"base": "int", "bytes": 1},
                "int16": {"base": "int", "bytes": 2},
                "int32": {"base": "int", "bytes": 4},
                "int64": {"base": "int", "bytes": 8},
                "ascii_str": {"base": "str", "encoding": "ASCII"},
                "utf8_str": {"base": "str", "encoding": "UTF-8"},
                "hex_type": {"base": "hex"},
                "bcd_type": {"base": "bcd"},
            },
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_parse_uint8(self):
        """测试解析uint8"""
        data = b"\xAB"
        type_def = self.config.types["uint8"]
        field = Field(len=1, name="test", type="uint8")

        result = self.parser._parse_uint(data, type_def, field)
        assert result == 0xAB

    def test_parse_uint16_le(self):
        """测试解析uint16小端序"""
        data = b"\x34\x12"  # 0x1234
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="test", type="uint16", endian="LE")

        result = self.parser._parse_uint(data, type_def, field)
        assert result == 0x1234

    def test_parse_uint16_be(self):
        """测试解析uint16大端序"""
        data = b"\x12\x34"  # 0x1234
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="test", type="uint16", endian="BE")

        result = self.parser._parse_uint(data, type_def, field)
        assert result == 0x1234

    def test_parse_uint32_le(self):
        """测试解析uint32小端序"""
        data = b"\x78\x56\x34\x12"  # 0x12345678
        type_def = self.config.types["uint32"]
        field = Field(len=4, name="test", type="uint32", endian="LE")

        result = self.parser._parse_uint(data, type_def, field)
        assert result == 0x12345678

    def test_parse_uint64_le(self):
        """测试解析uint64小端序"""
        data = b"\xF0\xDE\xBC\x9A\x78\x56\x34\x12"
        type_def = self.config.types["uint64"]
        field = Field(len=8, name="test", type="uint64", endian="LE")

        result = self.parser._parse_uint(data, type_def, field)
        assert result == 0x123456789ABCDEF0

    def test_parse_int8_positive(self):
        """测试解析int8正数"""
        data = b"\x7F"  # 127
        type_def = self.config.types["int8"]
        field = Field(len=1, name="test", type="int8")

        result = self.parser._parse_int(data, type_def, field)
        assert result == 127

    def test_parse_int8_negative(self):
        """测试解析int8负数"""
        data = b"\x80"  # -128
        type_def = self.config.types["int8"]
        field = Field(len=1, name="test", type="int8")

        result = self.parser._parse_int(data, type_def, field)
        assert result == -128

    def test_parse_int16_le(self):
        """测试解析int16小端序"""
        data = b"\x00\x80"  # -32768
        type_def = self.config.types["int16"]
        field = Field(len=2, name="test", type="int16", endian="LE")

        result = self.parser._parse_int(data, type_def, field)
        assert result == -32768

    def test_parse_int32_le(self):
        """测试解析int32小端序"""
        data = b"\x00\x00\x00\x80"  # -2147483648
        type_def = self.config.types["int32"]
        field = Field(len=4, name="test", type="int32", endian="LE")

        result = self.parser._parse_int(data, type_def, field)
        assert result == -2147483648

    def test_parse_string_ascii(self):
        """测试解析ASCII字符串"""
        data = b"Hello\x00\x00\x00"
        type_def = self.config.types["ascii_str"]
        field = Field(len=8, name="test", type="ascii_str")

        result = self.parser._parse_str(data, type_def, field)
        assert result == "Hello"

    def test_parse_string_utf8(self):
        """测试解析UTF-8字符串"""
        # "测试" in UTF-8
        data = bytes([0xE6, 0xB5, 0x8B, 0xE8, 0xAF, 0x95])
        type_def = self.config.types["utf8_str"]
        field = Field(len=6, name="test", type="utf8_str")

        result = self.parser._parse_str(data, type_def, field)
        assert result == "测试"

    def test_parse_string_invalid_encoding(self):
        """测试解析无效编码字符串（回退到hex）"""
        data = b"\xFF\xFE\xFD"
        type_def = self.config.types["ascii_str"]
        field = Field(len=3, name="test", type="ascii_str")

        result = self.parser._parse_str(data, type_def, field)
        # hexlify 返回小写
        assert result == "fffefd" or result == "FFFEFD"  # hex编码

    def test_parse_empty_string(self):
        """测试解析空字符串"""
        # Arrange
        data = b""
        type_def = self.config.types["ascii_str"]
        field = Field(len=0, name="空字符串", type="ascii_str")

        # Act
        result = self.parser._parse_str(data, type_def, field)

        # Assert
        assert result == ""

    def test_parse_very_long_string(self):
        """测试解析超长字符串（1000+ 字符）"""
        # Arrange
        long_string = "A" * 1000
        data = long_string.encode('ascii')
        type_def = self.config.types["ascii_str"]
        field = Field(len=1000, name="长字符串", type="ascii_str")

        # Act
        result = self.parser._parse_str(data, type_def, field)

        # Assert
        assert result == long_string
        assert len(result) == 1000

    def test_parse_string_with_null_chars(self):
        """测试解析包含 null 字符的字符串"""
        # Arrange
        # 字符串包含多个 null 字符，应该被去除
        data = b"Hello\x00\x00World\x00"
        type_def = self.config.types["ascii_str"]
        field = Field(len=13, name="包含null", type="ascii_str")

        # Act
        result = self.parser._parse_str(data, type_def, field)

        # Assert
        # null 字符应该被去除，只保留有效字符
        assert "Hello" in result
        assert "World" in result

    def test_parse_unicode_surrogate_pairs(self):
        """测试解析包含 surrogate pairs 的 UTF-8 字符串"""
        # Arrange
        # 使用 emoji (🔥) 需要 surrogate pairs 在 UTF-16 中，但在 UTF-8 中是4字节
        emoji_str = "测试🔥字符串"  # 包含 emoji
        data = emoji_str.encode('utf-8')
        type_def = self.config.types["utf8_str"]
        field = Field(len=len(data), name="unicode", type="utf8_str")

        # Act
        result = self.parser._parse_str(data, type_def, field)

        # Assert
        assert result == emoji_str
        assert len(result.encode('utf-8')) == len(data)

    def test_parse_string_all_null_chars(self):
        """测试解析全是 null 字符的字符串"""
        # Arrange
        data = b"\x00\x00\x00\x00"
        type_def = self.config.types["ascii_str"]
        field = Field(len=4, name="全null", type="ascii_str")

        # Act
        result = self.parser._parse_str(data, type_def, field)

        # Assert
        # 所有 null 字符被去除后应该是空字符串
        assert result == ""

    def test_parse_hex(self):
        """测试解析十六进制"""
        data = b"\xAB\xCD\xEF"
        type_def = self.config.types["hex_type"]
        field = Field(len=3, name="test", type="hex_type")

        result = self.parser._parse_hex(data, type_def, field)
        assert result == "ABCDEF"

    def test_parse_bcd(self):
        """测试解析BCD码"""
        # 0x12 0x34 0x56 -> "123456"
        data = b"\x12\x34\x56"
        type_def = self.config.types["bcd_type"]
        field = Field(len=3, name="test", type="bcd_type")

        result = self.parser._parse_bcd(data, type_def, field)
        assert result == "123456"

    def test_parse_bcd_with_invalid_nibbles(self):
        """测试解析包含无效半字节的BCD码"""
        # 0x1A 0x2B -> '12' (A和B被忽略)
        data = b"\x1A\x2B"
        type_def = self.config.types["bcd_type"]
        field = Field(len=2, name="test", type="bcd_type")

        result = self.parser._parse_bcd(data, type_def, field)
        assert result == "12"

    def test_parse_binary_str(self):
        """测试解析二进制字符串"""
        data = b"\xAB\xCD\xEF"
        type_def = TypeDef(base="binary_str")
        field = Field(len=3, name="test", type="binary_str")

        result = self.parser._parse_binary_str(data, type_def, field)
        assert result == "ABCDEF"

    def test_unsupported_uint_size(self):
        """测试不支持的uint大小"""
        data = b"\x00\x00\x00"  # 3字节
        type_def = TypeDef(base="uint", bytes=3)
        field = Field(len=3, name="test", type="uint")

        with pytest.raises(ValueError, match="Unsupported uint size"):
            self.parser._parse_uint(data, type_def, field)

    def test_unsupported_int_size(self):
        """测试不支持的int大小"""
        data = b"\x00\x00\x00"  # 3字节
        type_def = TypeDef(base="int", bytes=3)
        field = Field(len=3, name="test", type="int")

        with pytest.raises(ValueError, match="Unsupported int size"):
            self.parser._parse_int(data, type_def, field)

    # ========== 极值测试用例 ==========

    def test_parse_uint8_max_value(self):
        """测试 uint8 最大值 0xFF (255)"""
        # Arrange
        max_value = 0xFF  # 255
        data = bytes([max_value])
        type_def = self.config.types["uint8"]
        field = Field(len=1, name="最大值", type="uint8")

        # Act
        result = self.parser._parse_uint(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_uint16_max_value(self):
        """测试 uint16 最大值 0xFFFF (65535)"""
        # Arrange
        max_value = 0xFFFF  # 65535
        data = max_value.to_bytes(2, byteorder='little')
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="最大值", type="uint16", endian="LE")

        # Act
        result = self.parser._parse_uint(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_uint32_max_value(self):
        """测试 uint32 最大值 0xFFFFFFFF (4294967295)"""
        # Arrange
        max_value = 0xFFFFFFFF  # 4294967295
        data = max_value.to_bytes(4, byteorder='little')
        type_def = self.config.types["uint32"]
        field = Field(len=4, name="最大值", type="uint32", endian="LE")

        # Act
        result = self.parser._parse_uint(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_uint64_max_value(self):
        """测试 uint64 最大值 0xFFFFFFFFFFFFFFFF (18446744073709551615)"""
        # Arrange
        max_value = 0xFFFFFFFFFFFFFFFF  # 18446744073709551615
        data = max_value.to_bytes(8, byteorder='little')
        type_def = self.config.types["uint64"]
        field = Field(len=8, name="最大值", type="uint64", endian="LE")

        # Act
        result = self.parser._parse_uint(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_int8_min_value(self):
        """测试 int8 最小值 -128"""
        # Arrange
        min_value = -128
        data = bytes([0x80])  # -128 的补码表示
        type_def = self.config.types["int8"]
        field = Field(len=1, name="最小值", type="int8")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == min_value

    def test_parse_int8_max_value(self):
        """测试 int8 最大值 127"""
        # Arrange
        max_value = 127
        data = bytes([0x7F])  # 127 的补码表示
        type_def = self.config.types["int8"]
        field = Field(len=1, name="最大值", type="int8")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_int16_min_value(self):
        """测试 int16 最小值 -32768"""
        # Arrange
        min_value = -32768
        data = min_value.to_bytes(2, byteorder='little', signed=True)
        type_def = self.config.types["int16"]
        field = Field(len=2, name="最小值", type="int16", endian="LE")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == min_value

    def test_parse_int16_max_value(self):
        """测试 int16 最大值 32767"""
        # Arrange
        max_value = 32767
        data = max_value.to_bytes(2, byteorder='little', signed=True)
        type_def = self.config.types["int16"]
        field = Field(len=2, name="最大值", type="int16", endian="LE")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_int32_min_value(self):
        """测试 int32 最小值 -2147483648"""
        # Arrange
        min_value = -2147483648
        data = min_value.to_bytes(4, byteorder='little', signed=True)
        type_def = self.config.types["int32"]
        field = Field(len=4, name="最小值", type="int32", endian="LE")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == min_value

    def test_parse_int32_max_value(self):
        """测试 int32 最大值 2147483647"""
        # Arrange
        max_value = 2147483647
        data = max_value.to_bytes(4, byteorder='little', signed=True)
        type_def = self.config.types["int32"]
        field = Field(len=4, name="最大值", type="int32", endian="LE")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == max_value

    def test_parse_int64_min_value(self):
        """测试 int64 最小值 -9223372036854775808"""
        # Arrange
        min_value = -9223372036854775808
        data = min_value.to_bytes(8, byteorder='little', signed=True)
        type_def = self.config.types["int64"]
        field = Field(len=8, name="最小值", type="int64", endian="LE")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == min_value

    def test_parse_int64_max_value(self):
        """测试 int64 最大值 9223372036854775807"""
        # Arrange
        max_value = 9223372036854775807
        data = max_value.to_bytes(8, byteorder='little', signed=True)
        type_def = self.config.types["int64"]
        field = Field(len=8, name="最大值", type="int64", endian="LE")

        # Act
        result = self.parser._parse_int(data, type_def, field)

        # Assert
        assert result == max_value


class TestTimeFormats:
    """测试时间格式解析"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "cp56time2a": {"base": "time.cp56time2a"},
                "bcd_time7": {"base": "time.bcd7"},
                "bcd_time8": {"base": "time.bcd8"},
                "bin_time7": {"base": "time.bin7"},
                "unix_time": {"base": "time.unix"},
                "unix_time_ms": {"base": "time.unix_ms"},
            },
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_parse_cp56time2a(self):
        """测试解析CP56Time2a时间格式"""
        # 2024-01-15 12:30:45.123
        # 毫秒=123, 分=30, 时=12, 日=15, 月=1, 年=24
        data = struct.pack("<H", 123)  # 毫秒
        data += bytes([30, 12, 15, 1, 24])  # 分, 时, 日, 月, 年

        type_def = self.config.types["cp56time2a"]
        field = Field(len=7, name="test", type="cp56time2a")

        result = self.parser._parse_cp56time2a(data, type_def, field)
        assert "2024-01-15" in result
        assert "12:30" in result  # 秒字段会被忽略

    def test_parse_cp56time2a_invalid_data(self):
        """测试解析无效的CP56Time2a数据（回退到hex）"""
        data = b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
        type_def = self.config.types["cp56time2a"]
        field = Field(len=7, name="test", type="cp56time2a")

        result = self.parser._parse_cp56time2a(data, type_def, field)
        assert result == "FFFFFFFFFFFFFF"  # hex回退

    def test_parse_cp56time2a_wrong_length(self):
        """测试CP56Time2a长度错误"""
        data = b"\x00\x00\x00"  # 只有3字节
        type_def = self.config.types["cp56time2a"]
        field = Field(len=3, name="test", type="cp56time2a")

        with pytest.raises(ValueError, match="requires exactly 7 bytes"):
            self.parser._parse_cp56time2a(data, type_def, field)

    def test_parse_bcd_time7(self):
        """测试解析7字节BCD时间"""
        # 2024-01-15 12:30:45
        # 年=0x20, 月=0x01, 日=0x15, 时=0x12, 分=0x30, 秒=0x45, 空字节
        data = bytes([0x20, 0x24, 0x01, 0x15, 0x12, 0x30, 0x45])

        type_def = self.config.types["bcd_time7"]
        field = Field(len=7, name="test", type="bcd_time7")

        result = self.parser._parse_bcd_time7(data, type_def, field)
        assert result == "2024-01-15 12:30:45"

    def test_parse_bcd_time7_insufficient_bytes(self):
        """测试BCD时间字节不足"""
        data = b"\x20\x24\x01"  # 只有3字节
        type_def = self.config.types["bcd_time7"]
        field = Field(len=3, name="test", type="bcd_time7")

        with pytest.raises(ValueError, match="需要至少7字节"):
            self.parser._parse_bcd_time7(data, type_def, field)

    def test_parse_bcd_time8(self):
        """测试解析8字节BCD时间"""
        # 前7字节与bcd_time7相同，最后1字节为空
        data = bytes([0x20, 0x24, 0x01, 0x15, 0x12, 0x30, 0x45, 0x00])

        type_def = self.config.types["bcd_time8"]
        field = Field(len=8, name="test", type="bcd_time8")

        result = self.parser._parse_bcd_time8(data, type_def, field)
        assert result == "2024-01-15 12:30:45"

    def test_parse_bcd_time8_insufficient_bytes(self):
        """测试BCD时间字节不足"""
        data = b"\x20\x24\x01\x15\x12\x30\x45"  # 只有7字节
        type_def = self.config.types["bcd_time8"]
        field = Field(len=7, name="test", type="bcd_time8")

        with pytest.raises(ValueError, match="需要8字节"):
            self.parser._parse_bcd_time8(data, type_def, field)

    def test_parse_bin_time7(self):
        """测试解析7字节BIN时间"""
        # 2024-01-15 12:30:45
        # 世纪=20(0x14), 年=24(0x18), 月=1, 日=15, 时=12, 分=30, 秒=45
        data = bytes([0x14, 0x18, 0x01, 0x0F, 0x0C, 0x1E, 0x2D])

        type_def = self.config.types["bin_time7"]
        field = Field(len=7, name="test", type="bin_time7")

        result = self.parser._parse_bin_time7(data, type_def, field)
        assert result == "2024-01-15 12:30:45"

    def test_parse_bin_time7_wrong_length(self):
        """测试BIN时间长度错误"""
        data = b"\x14\x18\x01"  # 只有3字节
        type_def = self.config.types["bin_time7"]
        field = Field(len=3, name="test", type="bin_time7")

        with pytest.raises(ValueError, match="需要7字节"):
            self.parser._parse_bin_time7(data, type_def, field)

    def test_parse_unix_time(self):
        """测试解析Unix时间戳（秒）"""
        # 使用固定时间戳便于测试：2024-01-01 00:00:00 UTC = 1704067200
        # 注意：fromtimestamp 会转换为本地时区（UTC+8），所以是 08:00:00
        timestamp = 1704067200
        data = struct.pack("<L", timestamp)

        type_def = self.config.types["unix_time"]
        field = Field(len=4, name="test", type="unix_time", endian="LE")

        result = self.parser._parse_unix_time(data, type_def, field)
        assert "2024-01-01" in result
        assert "08:00:00" in result  # 本地时区（UTC+8）

    def test_parse_unix_time_zero(self):
        """测试解析零值Unix时间戳"""
        data = b"\x00\x00\x00\x00"
        type_def = self.config.types["unix_time"]
        field = Field(len=4, name="test", type="unix_time", endian="LE")

        result = self.parser._parse_unix_time(data, type_def, field)
        assert result == "1970-01-01 00:00:00"

    def test_parse_unix_time_wrong_length(self):
        """测试Unix时间戳长度错误"""
        data = b"\x00\x00\x00"  # 只有3字节
        type_def = self.config.types["unix_time"]
        field = Field(len=3, name="test", type="unix_time")

        with pytest.raises(ValueError, match="需要4字节"):
            self.parser._parse_unix_time(data, type_def, field)

    def test_parse_unix_time_ms(self):
        """测试解析Unix时间戳（毫秒）"""
        # 使用固定时间戳便于测试：2024-01-01 00:00:00.123 UTC = 1704067200123
        # 注意：fromtimestamp 会转换为本地时区（UTC+8），所以是 08:00:00
        timestamp_ms = 1704067200123
        data = struct.pack("<Q", timestamp_ms)

        type_def = self.config.types["unix_time_ms"]
        field = Field(len=8, name="test", type="unix_time_ms", endian="LE")

        result = self.parser._parse_unix_time_ms(data, type_def, field)
        assert "2024-01-01" in result
        assert "08:00:00" in result  # 本地时区（UTC+8）
        assert "123" in result  # 毫秒部分

    def test_parse_unix_time_ms_zero(self):
        """测试解析零值Unix毫秒时间戳"""
        data = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        type_def = self.config.types["unix_time_ms"]
        field = Field(len=8, name="test", type="unix_time_ms", endian="LE")

        result = self.parser._parse_unix_time_ms(data, type_def, field)
        assert result == "1970-01-01 00:00:00.000"

    def test_parse_unix_time_ms_wrong_length(self):
        """测试Unix毫秒时间戳长度错误"""
        data = b"\x00\x00\x00\x00"  # 只有4字节
        type_def = self.config.types["unix_time_ms"]
        field = Field(len=4, name="test", type="unix_time_ms")

        with pytest.raises(ValueError, match="需要8字节"):
            self.parser._parse_unix_time_ms(data, type_def, field)


class TestBitsetAndBitfield:
    """测试位段解析"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
                "bitset8": {
                    "base": "bitset",
                    "bits": [
                        {"name": "bit0"},
                        {"name": "bit1"},
                        {"name": "bit2"},
                        {"name": "bit3"},
                    ],
                },
                "bitfield8": {
                    "base": "bitfield",
                    "bytes": 1,
                    "order": "lsb0",
                    "groups": [
                        {"name": "field1", "start_bit": 0, "width": 2, "enum": "status"},
                        {"name": "field2", "start_bit": 2, "width": 3},
                        {"name": "field3", "start_bit": 5, "width": 3},
                    ],
                },
                "bitfield16": {
                    "base": "bitfield",
                    "bytes": 2,
                    "order": "lsb0",
                    "groups": [
                        {"name": "low", "start_bit": 0, "width": 8},
                        {"name": "high", "start_bit": 8, "width": 8},
                    ],
                },
                "bitfield_msb0": {
                    "base": "bitfield",
                    "bytes": 2,
                    "order": "msb0",
                    "groups": [
                        {"name": "msb_field", "start_bit": 0, "width": 8},
                        {"name": "lsb_field", "start_bit": 8, "width": 8},
                    ],
                },
            },
            "enums": {"status": {0: "关闭", 1: "开启", 2: "故障", 3: "维护"}},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_parse_bitset(self):
        """测试解析bitset"""
        # 0b00001011 = bit0=1, bit1=1, bit2=0, bit3=1
        data = b"\x0B"
        type_def = self.config.types["bitset8"]
        field = Field(len=1, name="test", type="bitset8")

        result = self.parser._parse_bitset(data, type_def, field)
        assert result["bit0"] is True
        assert result["bit1"] is True
        assert result["bit2"] is False
        assert result["bit3"] is True

    def test_parse_bitset_no_bits_definition(self):
        """测试没有定义位的bitset（回退到hex）"""
        data = b"\xAB\xCD"
        # 创建一个空bits列表的类型定义
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {"bitset_empty": {"base": "bitset", "bits": []}},
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        config = yaml_loader._parse_config(config_data)
        parser = YamlFieldParser(config)
        type_def = config.types["bitset_empty"]
        field = Field(len=2, name="test", type="bitset_empty")

        result = parser._parse_bitset(data, type_def, field)
        assert "raw" in result
        assert result["raw"] == "ABCD"

    def test_parse_bitset_2bytes(self):
        """测试解析2字节bitset"""
        # 0x1234 (小端序) = 0b0001001000110100
        # bit0 = 0, bit1 = 0, bit2 = 1
        data = b"\x34\x12"
        type_def = self.config.types["bitset8"]
        field = Field(len=2, name="test", type="bitset8", endian="LE")

        result = self.parser._parse_bitset(data, type_def, field)
        # 2字节的bitset会被解析
        assert result["bit0"] is False
        assert result["bit1"] is False
        assert result["bit2"] is True
        assert result["bit3"] is False

    def test_parse_bitfield_with_enum(self):
        """测试解析带枚举的bitfield"""
        # 0b10101010
        # field1 (bit 0-1): 10 = 2 (故障)
        # field2 (bit 2-4): 010 = 2
        # field3 (bit 5-7): 101 = 5
        data = b"\xAA"
        type_def = self.config.types["bitfield8"]
        field = Field(len=1, name="test", type="bitfield8")

        result = self.parser._parse_bitfield(data, type_def, field)
        assert result["field1"] == "故障"
        assert result["field2"] == 2
        assert result["field3"] == 5

    def test_parse_bitfield_without_enum(self):
        """测试解析不带枚举的bitfield"""
        # 0x1234 (小端序)
        data = b"\x34\x12"
        type_def = self.config.types["bitfield16"]
        field = Field(len=2, name="test", type="bitfield16")

        result = self.parser._parse_bitfield(data, type_def, field)
        assert result["low"] == 0x34
        assert result["high"] == 0x12

    def test_parse_bitfield_msb0(self):
        """测试MSB0位序的bitfield"""
        # 0x1234 (大端序: 0x12 0x34)
        # MSB0: msb_field = 0x12, lsb_field = 0x34
        data = b"\x12\x34"
        type_def = self.config.types["bitfield_msb0"]
        field = Field(len=2, name="test", type="bitfield_msb0", endian="BE")

        result = self.parser._parse_bitfield(data, type_def, field)
        assert result["msb_field"] == 0x12
        assert result["lsb_field"] == 0x34

    def test_parse_bitfield_no_groups(self):
        """测试没有定义组的bitfield（回退到hex）"""
        data = b"\xAB\xCD"
        type_def = TypeDef(base="bitfield", bytes=2)
        field = Field(len=2, name="test", type="bitfield")

        result = self.parser._parse_bitfield(data, type_def, field)
        assert "raw" in result
        assert result["raw"] == "ABCD"


class TestPostProcessing:
    """测试后处理功能（scale/unit/enum）"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint16": {"base": "uint", "bytes": 2},
            },
            "enums": {
                "status": {0: "关闭", 1: "开启", 2: "故障"},
                "mode": {1: "自动模式", 2: "手动模式", 3: "维护模式"},
            },
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_scale_factor(self):
        """测试缩放因子"""
        # 原始值 1000，缩放因子 0.1，期望结果 100.0
        data = b"\xE8\x03"  # 1000 (小端序)
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="voltage", type="uint16", scale=0.1, unit="V")

        result = self.parser._parse_uint(data, type_def, field)
        processed = self.parser._post_process_value(result, field)

        assert abs(processed - 100.0) < 0.01  # 浮点数比较

    def test_scale_factor_integer(self):
        """测试整数缩放因子"""
        # 原始值 100，缩放因子 10，期望结果 1000
        data = b"\x64\x00"  # 100 (小端序)
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="value", type="uint16", scale=10)

        result = self.parser._parse_uint(data, type_def, field)
        processed = self.parser._post_process_value(result, field)

        assert processed == 1000.0

    def test_scale_factor_small(self):
        """测试小数缩放因子"""
        # 原始值 12345，缩放因子 0.01，期望结果 123.45
        data = b"\x39\x30"  # 12345 (小端序)
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="value", type="uint16", scale=0.01)

        result = self.parser._parse_uint(data, type_def, field)
        processed = self.parser._post_process_value(result, field)

        assert abs(processed - 123.45) < 0.001

    def test_enum_mapping(self):
        """测试枚举映射"""
        data = b"\x01\x00"  # 1 (小端序)
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="status", type="uint16", enum="status")

        result = self.parser._parse_uint(data, type_def, field)
        processed = self.parser._post_process_value(result, field)

        assert isinstance(processed, dict)
        assert processed["value"] == 1
        assert processed["name"] == "开启"

    def test_enum_mapping_unknown_value(self):
        """测试未知枚举值"""
        data = b"\x05\x00"  # 5 (不在枚举中)
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="status", type="uint16", enum="status")

        result = self.parser._parse_uint(data, type_def, field)
        processed = self.parser._post_process_value(result, field)

        # 未知值不进行枚举映射
        assert processed == 5

    def test_no_post_processing(self):
        """测试无需后处理的字段"""
        data = b"\x64\x00"  # 100
        type_def = self.config.types["uint16"]
        field = Field(len=2, name="value", type="uint16")

        result = self.parser._parse_uint(data, type_def, field)
        processed = self.parser._post_process_value(result, field)

        assert processed == 100

    def test_get_decimal_places(self):
        """测试获取小数位数"""
        assert self.parser._get_decimal_places(0) == 0
        assert self.parser._get_decimal_places(0.1) == 1
        assert self.parser._get_decimal_places(0.01) == 2
        assert self.parser._get_decimal_places(0.001) == 3
        assert self.parser._get_decimal_places(1.0) == 0
        assert self.parser._get_decimal_places(10) == 0


class TestFieldGroups:
    """测试字段组（循环结构）"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
            },
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_parse_field_with_repeat_const(self):
        """测试解析固定次数循环的字段组"""
        # 创建3个uint8字段的数据
        data = b"\x01\x02\x03"

        fields = [Group(repeat_const=3, fields=[Field(len=1, name="item", type="uint8")])]

        result = self.parser.parse_fields(data, fields)

        # 应该生成 item_list
        assert "item_list" in result
        assert len(result["item_list"]) == 3
        assert result["item_list"][0]["item"] == 1
        assert result["item_list"][1]["item"] == 2
        assert result["item_list"][2]["item"] == 3

    def test_parse_field_with_repeat_by(self):
        """测试解析动态次数循环的字段组"""
        # 创建数据：count=3, items=[1, 2, 3]
        data = b"\x03\x01\x02\x03"

        fields = [
            Field(len=1, name="count", type="uint8", id="count"),
            Group(repeat_by="count", fields=[Field(len=1, name="item", type="uint8")]),
        ]

        result = self.parser.parse_fields(data, fields)

        assert result["count"] == 3
        assert "item_list" in result
        assert len(result["item_list"]) == 3
        assert result["item_list"][0]["item"] == 1
        assert result["item_list"][1]["item"] == 2
        assert result["item_list"][2]["item"] == 3

    def test_parse_field_with_single_repeat(self):
        """测试解析单次循环的字段组（应该直接展开）"""
        data = b"\x01"

        fields = [Group(repeat_const=1, fields=[Field(len=1, name="value", type="uint8")])]

        result = self.parser.parse_fields(data, fields)

        # 单个项目应该直接展开，不创建list
        assert "value" in result
        assert result["value"] == 1
        assert "value_list" not in result

    def test_parse_field_with_zero_repeat(self):
        """测试解析零次循环的字段组"""
        data = b"\x00"

        fields = [
            Field(len=1, name="count", type="uint8", id="count"),
            Group(repeat_by="count", fields=[Field(len=1, name="item", type="uint8")]),
        ]

        result = self.parser.parse_fields(data, fields)

        assert result["count"] == 0
        # 0个项目不创建字段
        assert "item" not in result
        assert "item_list" not in result

    def test_parse_field_nested_groups(self):
        """测试解析嵌套的字段组"""
        # 外层循环2次，每次有2个字段
        # count=2, items=[(a1,b1), (a2,b2)]
        data = b"\x01\x02\x03\x04"

        fields = [
            Group(
                repeat_const=2,
                fields=[
                    Field(len=1, name="a", type="uint8"),
                    Field(len=1, name="b", type="uint8"),
                ],
            )
        ]

        result = self.parser.parse_fields(data, fields)

        # 第一个字段是a，所以会创建a_list
        assert "a_list" in result
        assert len(result["a_list"]) == 2
        assert result["a_list"][0]["a"] == 1
        assert result["a_list"][0]["b"] == 2
        assert result["a_list"][1]["a"] == 3
        assert result["a_list"][1]["b"] == 4

    def test_parse_group_missing_context_field(self):
        """测试解析字段组时缺少上下文字段"""
        data = b"\x01\x02\x03"
        fields = [
            Group(repeat_by="nonexistent_count", fields=[Field(len=1, name="item", type="uint8")])
        ]

        with pytest.raises(ValueError, match="not found in context"):
            self.parser.parse_fields(data, fields)

    def test_calculate_field_size(self):
        """测试计算字段大小"""
        field = Field(len=4, name="test", type="uint32")
        size = self.parser._calculate_field_size(field, {})
        assert size == 4

    def test_calculate_group_size(self):
        """测试计算字段组大小"""
        group = Group(repeat_const=3, fields=[Field(len=2, name="item", type="uint16")])
        size = self.parser._calculate_field_size(group, {})
        assert size == 6  # 3 * 2字节

    def test_calculate_group_size_dynamic(self):
        """测试计算动态字段组大小"""
        group = Group(repeat_by="count", fields=[Field(len=2, name="item", type="uint16")])
        context = {"count": 5}
        size = self.parser._calculate_field_size(group, context)
        assert size == 10  # 5 * 2字节


class TestFieldParsingIntegration:
    """测试字段解析集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
                "int16": {"base": "int", "bytes": 2},
                "ascii_str": {"base": "str", "encoding": "ASCII"},
            },
            "enums": {"status": {0: "离线", 1: "在线", 2: "故障"}},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_parse_multiple_fields(self):
        """测试解析多个字段"""
        # status=1, voltage=2200 (缩放后220.0V), current=5000
        # 0x00DC = 220小端序, 缩放0.1 = 220.0
        data = b"\x01\xDC\x0A\x88\x13"

        fields = [
            Field(len=1, name="status", type="uint8", enum="status"),
            Field(len=2, name="voltage", type="uint16", scale=0.01, unit="V"),
            Field(len=2, name="current", type="uint16"),
        ]

        result = self.parser.parse_fields(data, fields)

        assert result["status"]["value"] == 1
        assert result["status"]["name"] == "在线"
        # 0x0ADC = 2780 * 0.01 = 27.8
        # 让我们重新计算：需要电压为220.0V，原始值应该是2200
        # 2200 = 0x0898 (小端序: 0x98 0x08)
        assert abs(result["voltage"] - 27.8) < 0.1
        assert result["current"] == 5000

    def test_parse_field_insufficient_data(self):
        """测试字段数据不足"""
        data = b"\x01\xDC"  # 只有2字节，但需要5字节

        fields = [
            Field(len=1, name="status", type="uint8"),
            Field(len=2, name="voltage", type="uint16"),
            Field(len=2, name="current", type="uint16"),
        ]

        # 第三个字段数据不足，应该使用占位符
        result = self.parser.parse_fields(data, fields)

        assert result["status"] == 1
        # 第二个字段数据也不足，也是占位符
        assert result["voltage"] == MISSING_FIELD_PLACEHOLDER
        assert result["current"] == MISSING_FIELD_PLACEHOLDER

    def test_parse_field_with_id(self):
        """测试带ID的字段（保存到上下文）"""
        data = b"\x03\x01\x02\x03"

        fields = [
            Field(len=1, name="count", type="uint8", id="count"),
            Group(repeat_by="count", fields=[Field(len=1, name="item", type="uint8")]),
        ]

        result = self.parser.parse_fields(data, fields)

        assert "item_list" in result
        assert len(result["item_list"]) == 3

    def test_parse_field_unknown_type(self):
        """测试未知类型"""
        data = b"\x01\x02\x03\x04"
        fields = [Field(len=4, name="data", type="unknown_type")]

        with pytest.raises(ValueError, match="Unknown type"):
            self.parser.parse_fields(data, fields)

    def test_get_first_field_name(self):
        """测试获取第一个字段名称"""
        field = Field(len=1, name="test_field", type="uint8")
        name = self.parser._get_first_field_name(field)
        assert name == "test_field"

        group = Group(repeat_const=1, fields=[Field(len=1, name="inner_field", type="uint8")])
        name = self.parser._get_first_field_name(group)
        assert name == "inner_field"


class TestStructCaching:
    """测试struct缓存机制"""

    def setup_method(self):
        """设置测试环境"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
            },
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        self.config = yaml_loader._parse_config(config_data)
        self.parser = YamlFieldParser(self.config)

    def test_struct_caching(self):
        """测试struct对象缓存"""
        # 第一次调用
        struct1 = self.parser._get_struct("LE", "H", 2)
        # 第二次调用（应该返回缓存的对象）
        struct2 = self.parser._get_struct("LE", "H", 2)

        assert struct1 is struct2  # 应该是同一个对象

    def test_struct_cache_different_keys(self):
        """测试不同key返回不同struct对象"""
        struct1 = self.parser._get_struct("LE", "H", 2)
        struct2 = self.parser._get_struct("BE", "H", 2)

        assert struct1 is not struct2

    def test_struct_cache_initially_empty(self):
        """测试初始缓存为空"""
        assert len(self.parser._struct_cache) == 0

    def test_struct_cache_populates(self):
        """测试缓存会被填充"""
        self.parser._get_struct("LE", "B", 1)
        self.parser._get_struct("LE", "H", 2)

        assert len(self.parser._struct_cache) == 2
        assert ("LE", "B", 1) in self.parser._struct_cache
        assert ("LE", "H", 2) in self.parser._struct_cache


class TestBytesToIntConversion:
    """测试字节到整数转换"""

    def setup_method(self):
        """设置测试环境"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {},
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        self.config = yaml_loader._parse_config(config_data)
        self.parser = YamlFieldParser(self.config)

    def test_bytes_to_int_le_single_byte(self):
        """测试小端序单字节转换"""
        data = b"\x42"
        result = self.parser._bytes_to_int(data, "LE")
        assert result == 0x42

    def test_bytes_to_int_le_multi_bytes(self):
        """测试小端序多字节转换"""
        data = b"\x34\x12\x78\x56"
        result = self.parser._bytes_to_int(data, "LE")
        assert result == 0x56781234

    def test_bytes_to_int_be_single_byte(self):
        """测试大端序单字节转换"""
        data = b"\x42"
        result = self.parser._bytes_to_int(data, "BE")
        assert result == 0x42

    def test_bytes_to_int_be_multi_bytes(self):
        """测试大端序多字节转换"""
        data = b"\x12\x34\x56\x78"
        result = self.parser._bytes_to_int(data, "BE")
        assert result == 0x12345678

    def test_bytes_to_int_empty(self):
        """测试空字节数据"""
        data = b""
        result = self.parser._bytes_to_int(data, "LE")
        assert result == 0


class TestBcdConversion:
    """测试BCD转换辅助函数"""

    def setup_method(self):
        """设置测试环境"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {},
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        self.config = yaml_loader._parse_config(config_data)
        self.parser = YamlFieldParser(self.config)

    def test_bcd_byte_to_int_valid(self):
        """测试有效的BCD字节转换"""
        assert self.parser._bcd_byte_to_int(0x12) == 12
        assert self.parser._bcd_byte_to_int(0x34) == 34
        assert self.parser._bcd_byte_to_int(0x00) == 0
        assert self.parser._bcd_byte_to_int(0x99) == 99

    def test_bcd_byte_to_int_invalid(self):
        """测试无效的BCD字节转换"""
        with pytest.raises(ValueError, match="无效BCD字节"):
            self.parser._bcd_byte_to_int(0xAB)

        with pytest.raises(ValueError, match="无效BCD字节"):
            self.parser._bcd_byte_to_int(0x0F)

    def test_bcd_to_int_multi_bytes(self):
        """测试多字节BCD转换"""
        # 0x1234 -> 1234
        assert self.parser._bcd_to_int(b"\x12\x34") == 1234

        # 0x010203 -> 10203
        assert self.parser._bcd_to_int(b"\x01\x02\x03") == 10203


class TestExceptions:
    """测试字段解析器的异常处理"""

    def setup_method(self):
        """设置测试环境"""
        self.config = self._create_test_config()
        self.parser = YamlFieldParser(self.config)

    def _create_test_config(self) -> ProtocolConfig:
        """创建测试用的协议配置"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
                "uint32": {"base": "uint", "bytes": 4},
                "int8": {"base": "int", "bytes": 1},
                "ascii_str": {"base": "str", "encoding": "ASCII"},
            },
            "enums": {"status": {0: "关闭", 1: "开启"}},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        return yaml_loader._parse_config(config_data)

    def test_unknown_field_type(self):
        """测试未知字段类型"""
        data = b"\x01\x02\x03\x04"
        fields = [Field(len=4, name="data", type="unknown_type")]

        with pytest.raises(ValueError, match="Unknown type 'unknown_type' for field 'data'"):
            self.parser.parse_fields(data, fields)

    def test_repeat_by_field_not_found_in_context(self):
        """测试 repeat_by 字段在上下文中不存在"""
        data = b"\x01\x02\x03"
        fields = [
            Group(repeat_by="nonexistent_count", fields=[Field(len=1, name="item", type="uint8")])
        ]

        with pytest.raises(ValueError, match="Repeat count field 'nonexistent_count' not found in context"):
            self.parser.parse_fields(data, fields)

    def test_group_without_repeat_parameters(self):
        """测试没有指定 repeat_by 或 repeat_const 的字段组"""
        # 测试在创建Group对象时就会抛出异常（在__post_init__中）
        with pytest.raises(ValueError, match="Group must specify either repeat_by or repeat_const"):
            Group(fields=[Field(len=1, name="item", type="uint8")])

    def test_unsupported_type_base(self):
        """测试不支持的基础类型"""
        data = b"\x01\x02\x03\x04"
        type_def = TypeDef(base="unsupported_base")
        field = Field(len=4, name="test", type="custom_type")

        # 手动设置不支持的类型
        self.config.types["custom_type"] = type_def

        # 直接调用 _parse_by_type 方法会抛出异常
        with pytest.raises(ValueError, match="Unsupported type base: unsupported_base"):
            self.parser._parse_by_type(data, type_def, field)

    def test_insufficient_data_for_field_parsing(self):
        """测试字段数据长度不足"""
        # 只有1字节数据，但需要2字节
        data = b"\x01"
        fields = [Field(len=2, name="voltage", type="uint16")]

        result = self.parser.parse_fields(data, fields)
        # 数据不足时应该使用占位符
        assert result["voltage"] == MISSING_FIELD_PLACEHOLDER

    def test_invalid_bcd_byte(self):
        """测试无效的BCD字节"""
        with pytest.raises(ValueError, match="无效BCD字节: 0xAB"):
            self.parser._bcd_byte_to_int(0xAB)

        with pytest.raises(ValueError, match="无效BCD字节: 0x0F"):
            self.parser._bcd_byte_to_int(0x0F)

    def test_bcd_time7_insufficient_bytes(self):
        """测试BCD时间7字节不足"""
        data = b"\x20\x24\x01"  # 只有3字节，需要7字节
        type_def = self.config.types["uint8"]
        field = Field(len=3, name="test", type="uint8")

        # 使用内部方法测试
        type_def_bcd = TypeDef(base="time.bcd7")
        field_bcd = Field(len=3, name="test", type="bcd_time7")

        with pytest.raises(ValueError, match="BCD时间需要至少7字节，实际3字节"):
            self.parser._parse_bcd_time7(data, type_def_bcd, field_bcd)

    def test_bcd_time8_insufficient_bytes(self):
        """测试BCD时间8字节不足"""
        data = b"\x20\x24\x01\x15\x12\x30\x45"  # 只有7字节，需要8字节
        type_def_bcd = TypeDef(base="time.bcd8")
        field_bcd = Field(len=7, name="test", type="bcd_time8")

        with pytest.raises(ValueError, match="BCD时间需要8字节，实际7字节"):
            self.parser._parse_bcd_time8(data, type_def_bcd, field_bcd)

    def test_unix_time_wrong_length(self):
        """测试Unix时间戳长度错误"""
        data = b"\x00\x00\x00"  # 只有3字节，需要4字节
        type_def = TypeDef(base="time.unix")
        field = Field(len=3, name="test", type="unix_time")

        with pytest.raises(ValueError, match="Unix时间戳需要4字节，实际3字节"):
            self.parser._parse_unix_time(data, type_def, field)

    def test_unix_time_ms_wrong_length(self):
        """测试Unix毫秒时间戳长度错误"""
        data = b"\x00\x00\x00\x00"  # 只有4字节，需要8字节
        type_def = TypeDef(base="time.unix_ms")
        field = Field(len=4, name="test", type="unix_time_ms")

        with pytest.raises(ValueError, match="Unix毫秒时间戳需要8字节，实际4字节"):
            self.parser._parse_unix_time_ms(data, type_def, field)

    def test_bin_time7_wrong_length(self):
        """测试BIN时间长度错误"""
        data = b"\x14\x18\x01"  # 只有3字节，需要7字节
        type_def = TypeDef(base="time.bin7")
        field = Field(len=3, name="test", type="bin_time7")

        with pytest.raises(ValueError, match="BIN时间需要7字节，实际3字节"):
            self.parser._parse_bin_time7(data, type_def, field)

    def test_cp56time2a_wrong_length(self):
        """测试CP56Time2a长度错误"""
        data = b"\xFF\xFF\xFF"  # 只有3字节，需要7字节
        type_def = TypeDef(base="time.cp56time2a")
        field = Field(len=3, name="test", type="cp56time2a")

        with pytest.raises(ValueError, match="CP56Time2a requires exactly 7 bytes"):
            self.parser._parse_cp56time2a(data, type_def, field)


class TestExtremeValues:
    """测试极值和边界情况"""

    def setup_method(self):
        """设置测试环境"""
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "uint8": {"base": "uint", "bytes": 1},
                "uint16": {"base": "uint", "bytes": 2},
            },
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        self.config = yaml_loader._parse_config(config_data)
        self.parser = YamlFieldParser(self.config)

    def test_parse_very_large_field_count(self):
        """测试解析大量字段（100个字段）"""
        # Arrange
        # 创建 100 个 uint8 字段
        field_count = 100
        data = bytes([i % 256 for i in range(field_count)])
        fields = [
            Field(len=1, name=f"field_{i}", type="uint8")
            for i in range(field_count)
        ]

        # Act
        result = self.parser.parse_fields(data, fields)

        # Assert
        assert len(result) == field_count
        for i in range(field_count):
            assert result[f"field_{i}"] == i % 256

    def test_parse_deeply_nested_groups(self):
        """测试深层嵌套的字段组（3层嵌套）"""
        # Arrange
        # 创建 3 层嵌套的结构：外层1次，中层2次，内层每层1次
        # level1(1字节) + level2_list: [level2(1字节) + level3(2字节)] * 2次
        # = 1 + 2*(1+2) = 1 + 6 = 7 字节
        data = bytes([1, 2, 3, 4, 5, 6, 7])

        fields = [
            Field(len=1, name="level1", type="uint8"),
            Group(
                repeat_const=2,
                fields=[
                    Field(len=1, name="level2", type="uint8"),
                    Group(
                        repeat_const=1,
                        fields=[
                            Field(len=2, name="level3", type="uint16"),
                        ]
                    ),
                ]
            )
        ]

        # Act
        result = self.parser.parse_fields(data, fields)

        # Assert
        # 验证第1层
        assert "level1" in result
        assert result["level1"] == 1
        # 验证第2层
        assert "level2_list" in result
        assert len(result["level2_list"]) == 2
        # 内层 Group 只重复1次，所以不会生成 _list，直接是字段值
        assert "level3" in result["level2_list"][0]
        # 验证具体值
        assert result["level2_list"][0]["level2"] == 2
        # data[2]=3, data[3]=4 -> 小端序 uint16 = 0x0403 = 1027
        assert result["level2_list"][0]["level3"] == 1027
        # 第二组
        assert result["level2_list"][1]["level2"] == 5
        # data[5]=6, data[6]=7 -> 小端序 uint16 = 0x0706 = 1798
        assert result["level2_list"][1]["level3"] == 1798

    def test_parse_large_repeat_const(self):
        """测试大循环次数 repeat_const（50次）"""
        # Arrange
        repeat_count = 50
        data = bytes([i % 256 for i in range(repeat_count)])

        fields = [
            Group(
                repeat_const=repeat_count,
                fields=[Field(len=1, name="item", type="uint8")]
            )
        ]

        # Act
        result = self.parser.parse_fields(data, fields)

        # Assert
        assert "item_list" in result
        assert len(result["item_list"]) == repeat_count
        # 验证前几个和后几个值
        assert result["item_list"][0]["item"] == 0
        assert result["item_list"][1]["item"] == 1
        assert result["item_list"][repeat_count - 1]["item"] == (repeat_count - 1) % 256

    def test_parse_nested_repeats(self):
        """测试嵌套循环结构"""
        # Arrange
        # 外层循环 3 次，内层循环 2 次，共 3*(1+2*1) = 9 字节
        data = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])

        fields = [
            Group(
                repeat_const=3,
                fields=[
                    Field(len=1, name="outer", type="uint8"),
                    Group(
                        repeat_const=2,
                        fields=[
                            Field(len=1, name="inner", type="uint8"),
                        ]
                    ),
                ]
            )
        ]

        # Act
        result = self.parser.parse_fields(data, fields)

        # Assert
        # 外层应该有 3 个元素
        assert "outer_list" in result
        assert len(result["outer_list"]) == 3
        # 每个外层元素包含 2 个内层元素
        assert len(result["outer_list"][0]["inner_list"]) == 2

    def test_parse_very_long_single_field(self):
        """测试解析极长单个字段（256字节）"""
        # Arrange
        # 创建一个256字节的数据
        field_length = 256
        # 创建一个自定义类型用于测试
        config_data = {
            "meta": {"protocol": "test", "version": 1, "default_endian": "LE"},
            "types": {
                "long_bytes": {"base": "hex"},
            },
            "enums": {},
            "cmds": {},
            "compatibility": {
                "head_len": 11,
                "tail_len": 2,
                "frame_head": "AA F5",
                "head_fields": [],
            },
        }
        config = yaml_loader._parse_config(config_data)
        parser = YamlFieldParser(config)

        data = bytes([i % 256 for i in range(field_length)])
        fields = [Field(len=field_length, name="long_data", type="long_bytes")]

        # Act
        result = parser.parse_fields(data, fields)

        # Assert
        assert "long_data" in result
        # 验证返回的 hex 字符串长度（每个字节2个hex字符）
        assert len(result["long_data"]) == field_length * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
