"""
文件名称: field_type_detector.py
内容摘要: 字段类型检测器，根据字段值和YAML配置判断字段类型
当前版本: v1.1.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from src.yaml_config import Field, TypeDef

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """字段类型枚举"""
    NUMERIC = auto()    # 数值型（int/float）→ 折线图
    BOOLEAN = auto()    # 布尔型 → 阶梯图
    ENUM = auto()       # 枚举型（带 name/value 的字典）→ 阶梯图/散点图
    STRING = auto()     # 字符串/复杂类型（暂不支持绘图）


# YAML type base → FieldType 映射
TYPE_BASE_TO_FIELD_TYPE: Dict[str, FieldType] = {
    # 数值型 → NUMERIC（折线图）
    "uint": FieldType.NUMERIC,
    "int": FieldType.NUMERIC,
    # 字符串型 → STRING（不绘图）
    "str": FieldType.STRING,
    "hex": FieldType.STRING,
    "bcd": FieldType.STRING,
    "binary_str": FieldType.STRING,
    # bitfield/bitset → ENUM（散点图，子字段）
    "bitfield": FieldType.ENUM,
    "bitset": FieldType.ENUM,
    # 时间类型 → STRING（不绘图）
    "time.cp56time2a": FieldType.STRING,
    "time.bcd7": FieldType.STRING,
    "time.bcd8": FieldType.STRING,
    "time.bin7": FieldType.STRING,
    "time.unix": FieldType.STRING,
    "time.unix_ms": FieldType.STRING,
}


class FieldTypeDetector:
    """
    字段类型检测器

    根据字段值和可选的YAML协议配置检测字段类型。
    检测优先级：bool > enum(dict with name/value) > numeric > string
    """

    def __init__(self, protocol_config: Optional[Any] = None):
        """
        初始化检测器

        Args:
            protocol_config: 可选的协议配置对象（YamlCmdFormat实例），
                           用于查找枚举定义
        """
        self._protocol_config = protocol_config

    def detect(self, value: Any) -> FieldType:
        """
        检测单个值的字段类型

        Args:
            value: 字段值

        Returns:
            检测到的字段类型
        """
        if isinstance(value, bool):
            return FieldType.BOOLEAN

        if isinstance(value, (int, float)):
            return FieldType.NUMERIC

        # 枚举类型：解析结果中 enum 字段表现为 {"value": x, "name": "xxx"}
        if isinstance(value, dict):
            if "value" in value and "name" in value:
                return FieldType.ENUM
            return FieldType.STRING

        if isinstance(value, str):
            return FieldType.STRING

        return FieldType.STRING

    def detect_from_samples(self, values: List[Any]) -> FieldType:
        """
        从多个样本值检测字段类型（取众数）

        Args:
            values: 字段值列表

        Returns:
            检测到的字段类型
        """
        if not values:
            return FieldType.STRING

        # 统计每种类型出现的次数
        type_counts: Dict[FieldType, int] = {}
        for val in values:
            if val is None:
                continue
            field_type = self.detect(val)
            type_counts[field_type] = type_counts.get(field_type, 0) + 1

        if not type_counts:
            return FieldType.STRING

        # 返回出现次数最多的类型
        return max(type_counts, key=type_counts.get)

    def extract_numeric_value(self, value: Any, field_type: FieldType) -> Optional[float]:
        """
        从字段值中提取可绘图的数值

        Args:
            value: 原始字段值
            field_type: 已知的字段类型

        Returns:
            数值，无法提取时返回 None
        """
        if value is None:
            return None

        if field_type == FieldType.NUMERIC:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        if field_type == FieldType.BOOLEAN:
            return 1.0 if value else 0.0

        if field_type == FieldType.ENUM:
            if isinstance(value, dict) and "value" in value:
                try:
                    return float(value["value"])
                except (TypeError, ValueError):
                    return None

        return None

    def detect_from_yaml(
        self,
        type_def: Optional["TypeDef"],
        field: Optional["Field"] = None,
    ) -> Optional[FieldType]:
        """
        根据 YAML 配置检测字段类型

        检测优先级：
        1. 有 enum 定义 → ENUM（阶梯图）
        2. 有 bit_groups 定义 → ENUM（散点图）
        3. 根据 type base 判断 → NUMERIC/STRING
        4. 无配置 → 返回 None，调用方应回退到 detect()

        Args:
            type_def: YAML 类型定义（TypeDef 实例）
            field: YAML 字段定义（Field 实例），可选

        Returns:
            检测到的字段类型，无法判断时返回 None
        """
        # 1. 有 enum 定义 → ENUM（阶梯图）
        if field is not None and field.enum:
            return FieldType.ENUM

        # 2. 有 bit_groups 定义 → ENUM（散点图）
        if field is not None and field.bit_groups:
            return FieldType.ENUM
        if type_def is not None and type_def.groups:
            return FieldType.ENUM

        # 3. 根据 type base 判断
        if type_def is not None:
            field_type = TYPE_BASE_TO_FIELD_TYPE.get(type_def.base)
            if field_type:
                return field_type

        # 4. 无配置 → 返回 None
        return None

    def detect_with_fallback(
        self,
        value: Any,
        type_def: Optional["TypeDef"] = None,
        field: Optional["Field"] = None,
    ) -> FieldType:
        """
        混合检测：优先 YAML 配置，回退值类型检测

        Args:
            value: 字段值
            type_def: YAML 类型定义
            field: YAML 字段定义

        Returns:
            检测到的字段类型
        """
        # 优先尝试 YAML 配置检测
        yaml_type = self.detect_from_yaml(type_def, field)
        if yaml_type:
            return yaml_type

        # 回退到值类型检测
        return self.detect(value)
