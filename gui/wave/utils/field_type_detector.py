"""
文件名称: field_type_detector.py
内容摘要: 字段类型检测器，根据字段值和YAML配置判断字段类型
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """字段类型枚举"""
    NUMERIC = auto()    # 数值型（int/float）
    BOOLEAN = auto()    # 布尔型
    ENUM = auto()       # 枚举型（带 name/value 的字典）
    STRING = auto()     # 字符串/复杂类型（暂不支持绘图）


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
