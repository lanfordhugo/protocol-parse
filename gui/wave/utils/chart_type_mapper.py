"""
文件名称: chart_type_mapper.py
内容摘要: 图表类型映射器，根据字段类型选择合适的图表绘制方式
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

from enum import Enum, auto
from typing import Any, Dict, Optional

from .field_type_detector import FieldType


class ChartType(Enum):
    """图表类型枚举"""
    LINE = auto()       # 折线图（数值型）
    STEP = auto()       # 阶梯图（布尔型）
    SCATTER = auto()    # 散点图（枚举型）


# 默认颜色调色板（区分度高的颜色序列）
DEFAULT_COLORS = [
    "#2196F3",  # 蓝色
    "#F44336",  # 红色
    "#4CAF50",  # 绿色
    "#FF9800",  # 橙色
    "#9C27B0",  # 紫色
    "#00BCD4",  # 青色
    "#FFEB3B",  # 黄色
    "#E91E63",  # 粉色
    "#8BC34A",  # 浅绿
    "#FF5722",  # 深橙
    "#3F51B5",  # 靛蓝
    "#009688",  # 水鸭色
]


class ChartTypeMapper:
    """
    图表类型映射器

    根据字段类型自动选择合适的 pyqtgraph 绘制方式。
    """

    # 字段类型 → 图表类型映射
    _TYPE_MAP: Dict[FieldType, ChartType] = {
        FieldType.NUMERIC: ChartType.LINE,
        FieldType.BOOLEAN: ChartType.STEP,
        FieldType.ENUM: ChartType.SCATTER,
    }

    @classmethod
    def get_chart_type(cls, field_type: FieldType) -> Optional[ChartType]:
        """
        根据字段类型获取图表类型

        Args:
            field_type: 字段类型

        Returns:
            图表类型，STRING类型返回None（暂不支持）
        """
        return cls._TYPE_MAP.get(field_type)

    @classmethod
    def is_chartable(cls, field_type: FieldType) -> bool:
        """
        判断字段类型是否可绘图

        Args:
            field_type: 字段类型

        Returns:
            是否支持绘图
        """
        return field_type in cls._TYPE_MAP

    @classmethod
    def get_color(cls, index: int) -> str:
        """
        根据索引获取颜色

        Args:
            index: 字段索引

        Returns:
            颜色字符串（#RRGGBB）
        """
        return DEFAULT_COLORS[index % len(DEFAULT_COLORS)]

    @classmethod
    def get_pyqtgraph_config(cls, chart_type: ChartType) -> Dict[str, Any]:
        """
        获取 pyqtgraph PlotDataItem 的配置参数

        Args:
            chart_type: 图表类型

        Returns:
            pyqtgraph 绘制参数字典
        """
        if chart_type == ChartType.LINE:
            return {
                "connect": "finite",
                # 大数据量场景抗锯齿开销较高，默认关闭（需要更高画质时可按需开启）
                "antialias": False,
            }
        elif chart_type == ChartType.STEP:
            return {
                "stepMode": "center",
                "fillLevel": 0,
            }
        elif chart_type == ChartType.SCATTER:
            return {
                "pen": None,
                "symbol": "o",
                "symbolSize": 8,
            }
        return {}
