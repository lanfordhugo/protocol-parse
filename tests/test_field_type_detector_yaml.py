"""
文件名称: test_field_type_detector_yaml.py
内容摘要: 测试 FieldTypeDetector 的 YAML 配置检测功能
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-25
"""

import pytest
from gui.wave.utils.field_type_detector import (
    FieldType,
    FieldTypeDetector,
    TYPE_BASE_TO_FIELD_TYPE,
)
from src.yaml_config import TypeDef, Field


class TestTypeBaseToFieldTypeMapping:
    """测试 YAML type base 到 FieldType 的映射"""

    def test_uint_maps_to_numeric(self):
        """uint 类型应映射到 NUMERIC"""
        assert TYPE_BASE_TO_FIELD_TYPE["uint"] == FieldType.NUMERIC

    def test_int_maps_to_numeric(self):
        """int 类型应映射到 NUMERIC"""
        assert TYPE_BASE_TO_FIELD_TYPE["int"] == FieldType.NUMERIC

    def test_hex_maps_to_string(self):
        """hex 类型应映射到 STRING"""
        assert TYPE_BASE_TO_FIELD_TYPE["hex"] == FieldType.STRING

    def test_bcd_maps_to_string(self):
        """bcd 类型应映射到 STRING"""
        assert TYPE_BASE_TO_FIELD_TYPE["bcd"] == FieldType.STRING

    def test_bitfield_maps_to_enum(self):
        """bitfield 类型应映射到 ENUM"""
        assert TYPE_BASE_TO_FIELD_TYPE["bitfield"] == FieldType.ENUM

    def test_bitset_maps_to_enum(self):
        """bitset 类型应映射到 ENUM"""
        assert TYPE_BASE_TO_FIELD_TYPE["bitset"] == FieldType.ENUM


class TestDetectFromYaml:
    """测试 detect_from_yaml 方法"""

    @pytest.fixture
    def detector(self):
        return FieldTypeDetector()

    def test_enum_field_returns_enum(self, detector):
        """有 enum 定义的 field 应返回 ENUM"""
        field = Field(len=1, name="工作状态", type="uint8", enum="work_status")
        type_def = TypeDef(base="uint", bytes=1, signed=False)

        result = detector.detect_from_yaml(type_def, field)
        assert result == FieldType.ENUM

    def test_bit_groups_field_returns_enum(self, detector):
        """有 bit_groups 定义的 field 应返回 ENUM"""
        field = Field(
            len=2,
            name="终端充电状态",
            type="bitfield16",
            bit_groups=[{"name": "插枪信号", "start_bit": 0, "width": 1}],
        )
        type_def = TypeDef(base="bitfield", bytes=2)

        result = detector.detect_from_yaml(type_def, field)
        assert result == FieldType.ENUM

    def test_type_def_groups_returns_enum(self, detector):
        """TypeDef 有 groups 定义应返回 ENUM"""
        field = Field(len=2, name="状态", type="bitfield16")
        type_def = TypeDef(
            base="bitfield",
            bytes=2,
            groups=[{"name": "状态位", "start_bit": 0, "width": 1}],
        )

        result = detector.detect_from_yaml(type_def, field)
        assert result == FieldType.ENUM

    def test_uint_type_returns_numeric(self, detector):
        """uint 类型应返回 NUMERIC"""
        field = Field(len=1, name="温度", type="uint8")
        type_def = TypeDef(base="uint", bytes=1, signed=False)

        result = detector.detect_from_yaml(type_def, field)
        assert result == FieldType.NUMERIC

    def test_int_type_returns_numeric(self, detector):
        """int 类型应返回 NUMERIC"""
        field = Field(len=2, name="电压", type="int16")
        type_def = TypeDef(base="int", bytes=2, signed=True)

        result = detector.detect_from_yaml(type_def, field)
        assert result == FieldType.NUMERIC

    def test_hex_type_returns_string(self, detector):
        """hex 类型应返回 STRING"""
        field = Field(len=4, name="枪故障状态", type="hex")
        type_def = TypeDef(base="hex")

        result = detector.detect_from_yaml(type_def, field)
        assert result == FieldType.STRING

    def test_no_config_returns_none(self, detector):
        """无配置时应返回 None"""
        result = detector.detect_from_yaml(None, None)
        assert result is None

    def test_enum_priority_over_bit_groups(self, detector):
        """enum 定义优先级高于 bit_groups"""
        field = Field(
            len=1,
            name="状态",
            type="uint8",
            enum="status_enum",
            bit_groups=[{"name": "bit0", "start_bit": 0, "width": 1}],
        )
        type_def = TypeDef(base="uint", bytes=1, signed=False)

        result = detector.detect_from_yaml(type_def, field)
        # enum 优先，返回 ENUM
        assert result == FieldType.ENUM


class TestDetectWithFallback:
    """测试 detect_with_fallback 混合检测"""

    @pytest.fixture
    def detector(self):
        return FieldTypeDetector()

    def test_yaml_config_takes_priority(self, detector):
        """YAML 配置优先于值类型检测"""
        # 值是 int，但 YAML 定义了 enum
        field = Field(len=1, name="工作状态", type="uint8", enum="work_status")
        type_def = TypeDef(base="uint", bytes=1, signed=False)

        result = detector.detect_with_fallback(123, type_def, field)
        assert result == FieldType.ENUM

    def test_fallback_to_value_detection(self, detector):
        """无 YAML 配置时回退到值类型检测"""
        result = detector.detect_with_fallback(123, None, None)
        assert result == FieldType.NUMERIC

        result = detector.detect_with_fallback(True, None, None)
        assert result == FieldType.BOOLEAN

        result = detector.detect_with_fallback({"value": 1, "name": "test"}, None, None)
        assert result == FieldType.ENUM

        result = detector.detect_with_fallback("hello", None, None)
        assert result == FieldType.STRING

    def test_bitfield_yaml_overrides_dict_value(self, detector):
        """bitfield YAML 配置应覆盖 dict 值检测"""
        # bitfield 解析结果是 dict，但 YAML 配置应返回 ENUM
        field = Field(
            len=2,
            name="状态",
            type="bitfield16",
            bit_groups=[{"name": "bit0", "start_bit": 0, "width": 1}],
        )
        type_def = TypeDef(base="bitfield", bytes=2)

        # 模拟 bitfield 解析结果（普通 dict，非枚举格式）
        bitfield_value = {"bit0": 1, "bit1": 0}

        result = detector.detect_with_fallback(bitfield_value, type_def, field)
        assert result == FieldType.ENUM

    def test_hex_type_not_plotable(self, detector):
        """hex 类型应返回 STRING（不可绘图）"""
        field = Field(len=4, name="枪故障状态", type="hex")
        type_def = TypeDef(base="hex")

        result = detector.detect_with_fallback("ABCD1234", type_def, field)
        assert result == FieldType.STRING


class TestFieldTypeEnum:
    """测试 FieldType 枚举值"""

    def test_field_type_values(self):
        """验证 FieldType 枚举值存在"""
        assert hasattr(FieldType, "NUMERIC")
        assert hasattr(FieldType, "BOOLEAN")
        assert hasattr(FieldType, "ENUM")
        assert hasattr(FieldType, "STRING")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
