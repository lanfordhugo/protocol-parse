"""
文件名称: wave_chart_widget.py
内容摘要: 波形图绘制组件，基于 pyqtgraph 实现多字段波形叠加显示
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper

logger = logging.getLogger(__name__)

# 降采样阈值：超过此数据点数时自动触发 LTTB 降采样
DOWNSAMPLE_THRESHOLD = 10000
# 降采样后保留的数据点数
DOWNSAMPLE_TARGET = 2000


def lttb_downsample(
    x: np.ndarray,
    y: np.ndarray,
    target_points: int,
) -> tuple:
    """
    LTTB（Largest Triangle Three Buckets）降采样算法

    在保留视觉特征的前提下减少数据点数量。

    Args:
        x: X轴数据（时间戳）
        y: Y轴数据（值）
        target_points: 目标数据点数

    Returns:
        (降采样后的x, 降采样后的y)
    """
    n = len(x)
    if n <= target_points or target_points < 3:
        return x, y

    # 始终保留首尾点
    sampled_indices = [0]

    bucket_size = (n - 2) / (target_points - 2)

    a_index = 0  # 上一个选中的点

    for i in range(1, target_points - 1):
        # 当前桶的范围
        bucket_start = int((i - 1) * bucket_size) + 1
        bucket_end = int(i * bucket_size) + 1
        bucket_end = min(bucket_end, n)

        # 下一个桶的平均值
        next_bucket_start = int(i * bucket_size) + 1
        next_bucket_end = int((i + 1) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)

        avg_x = np.mean(x[next_bucket_start:next_bucket_end])
        avg_y = np.mean(y[next_bucket_start:next_bucket_end])

        # 在当前桶中找面积最大的三角形
        max_area = -1.0
        max_index = bucket_start

        for j in range(bucket_start, bucket_end):
            # 三角形面积 = 0.5 * |x_a*(y_j - avg_y) + x_j*(avg_y - y_a) + avg_x*(y_a - y_j)|
            area = abs(
                (x[a_index] - avg_x) * (y[j] - y[a_index])
                - (x[a_index] - x[j]) * (avg_y - y[a_index])
            )
            if area > max_area:
                max_area = area
                max_index = j

        sampled_indices.append(max_index)
        a_index = max_index

    sampled_indices.append(n - 1)

    indices = np.array(sampled_indices)
    return x[indices], y[indices]


class TimeAxisItem(pg.AxisItem):
    """
    时间轴控件

    将 epoch 时间戳格式化为可读的时间字符串。
    """

    def tickStrings(self, values, scale, spacing):
        """将时间戳转换为格式化字符串"""
        strings = []
        for v in values:
            try:
                dt = datetime.fromtimestamp(v)
                if spacing > 3600:
                    fmt = "%m-%d %H:%M"
                elif spacing > 60:
                    fmt = "%H:%M:%S"
                else:
                    fmt = "%H:%M:%S.%f"
                    s = dt.strftime(fmt)
                    # 截取毫秒到3位
                    s = s[:-3]
                    strings.append(s)
                    continue
                strings.append(dt.strftime(fmt))
            except (OSError, ValueError, OverflowError):
                strings.append("")
        return strings


class WaveChartWidget(QWidget):
    """
    波形图绘制组件

    功能：
    - 使用 pyqtgraph 绘制多字段波形
    - 支持缩放、拖动、十字光标
    - 自动适配字段类型（折线/阶梯/散点）
    - 图例显示字段名
    - 右键菜单（删除字段、修改颜色）

    信号：
    - field_remove_requested(str): 请求移除字段
    - field_color_change_requested(str): 请求修改字段颜色
    """

    # 信号
    field_remove_requested = Signal(str)
    field_color_change_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 字段 → 绘图曲线映射
        self._plot_items: Dict[str, pg.PlotDataItem] = {}
        # 字段 → 配置映射
        self._field_configs: Dict[str, FieldConfig] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建 pyqtgraph 绘图控件
        self._plot_widget = pg.PlotWidget(
            axisItems={"bottom": TimeAxisItem(orientation="bottom")},
        )
        self._plot_widget.setBackground("transparent")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel("bottom", "时间")
        self._plot_widget.setLabel("left", "值")

        # 启用鼠标交互
        self._plot_widget.setMouseEnabled(x=True, y=True)
        self._plot_widget.enableAutoRange(axis="y", enable=True)

        # 添加十字光标
        self._crosshair_v = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen("#888888", width=1, style=Qt.DashLine)
        )
        self._crosshair_h = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen("#888888", width=1, style=Qt.DashLine)
        )
        self._plot_widget.addItem(self._crosshair_v, ignoreBounds=True)
        self._plot_widget.addItem(self._crosshair_h, ignoreBounds=True)
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)

        # 鼠标移动事件
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # 添加图例
        self._legend = self._plot_widget.addLegend(
            offset=(10, 10),
            brush=pg.mkBrush(0, 0, 0, 100),
            pen=pg.mkPen("#555555"),
        )

        layout.addWidget(self._plot_widget)

    # ============== 字段管理 ==============

    def add_field(self, config: FieldConfig) -> None:
        """
        添加字段到图表

        Args:
            config: 字段配置
        """
        if config.field_path in self._plot_items:
            return

        self._field_configs[config.field_path] = config

        # 根据图表类型创建绘图项
        pen_color = QColor(config.color)
        pg_config = ChartTypeMapper.get_pyqtgraph_config(config.chart_type)

        if config.chart_type == ChartType.LINE:
            plot_item = self._plot_widget.plot(
                name=config.display_name,
                pen=pg.mkPen(pen_color, width=2),
                **pg_config,
            )
        elif config.chart_type == ChartType.STEP:
            plot_item = self._plot_widget.plot(
                name=config.display_name,
                pen=pg.mkPen(pen_color, width=2),
                **pg_config,
            )
        elif config.chart_type == ChartType.SCATTER:
            plot_item = self._plot_widget.plot(
                name=config.display_name,
                symbolBrush=pen_color,
                symbolPen=pg.mkPen(pen_color, width=1),
                **pg_config,
            )
        else:
            return

        self._plot_items[config.field_path] = plot_item
        logger.debug("已添加图表字段: %s", config.display_name)

    def remove_field(self, field_path: str) -> None:
        """
        从图表移除字段

        Args:
            field_path: 字段路径
        """
        plot_item = self._plot_items.pop(field_path, None)
        if plot_item:
            self._plot_widget.removeItem(plot_item)
            # 从图例中移除
            if self._legend is not None:
                self._legend.removeItem(plot_item)
        self._field_configs.pop(field_path, None)
        logger.debug("已移除图表字段: %s", field_path)

    def update_field_color(self, field_path: str, color: str) -> None:
        """
        更新字段颜色

        Args:
            field_path: 字段路径
            color: 新颜色（#RRGGBB）
        """
        plot_item = self._plot_items.get(field_path)
        config = self._field_configs.get(field_path)
        if not plot_item or not config:
            return

        pen_color = QColor(color)
        config.color = color

        if config.chart_type in (ChartType.LINE, ChartType.STEP):
            plot_item.setPen(pg.mkPen(pen_color, width=2))
        elif config.chart_type == ChartType.SCATTER:
            plot_item.setSymbolBrush(pen_color)
            plot_item.setSymbolPen(pg.mkPen(pen_color, width=1))

    # ============== 数据更新 ==============

    def update_data(
        self,
        field_path: str,
        timestamps: List[float],
        values: List[Optional[float]],
    ) -> None:
        """
        更新指定字段的数据

        Args:
            field_path: 字段路径
            timestamps: 时间戳列表（epoch秒数）
            values: 值列表
        """
        plot_item = self._plot_items.get(field_path)
        if not plot_item:
            return

        if not timestamps or not values:
            plot_item.setData([], [])
            return

        ts_array = np.array(timestamps, dtype=np.float64)
        val_array = np.array(values, dtype=np.float64)

        # 超过阈值时自动降采样
        if len(ts_array) > DOWNSAMPLE_THRESHOLD:
            ts_array, val_array = lttb_downsample(
                ts_array, val_array, DOWNSAMPLE_TARGET
            )

        plot_item.setData(ts_array, val_array)

    def update_all_data(
        self,
        plot_data: Dict[str, Tuple[List[float], List[Optional[float]]]],
    ) -> None:
        """
        批量更新所有字段的数据

        Args:
            plot_data: {field_path: (timestamps, values)}
        """
        for field_path, (timestamps, values) in plot_data.items():
            self.update_data(field_path, timestamps, values)

    def clear(self) -> None:
        """清空所有数据（保留字段配置）"""
        for plot_item in self._plot_items.values():
            plot_item.setData([], [])

    def clear_all(self) -> None:
        """清空所有字段和数据"""
        for field_path in list(self._plot_items.keys()):
            self.remove_field(field_path)

    # ============== 视图控制 ==============

    def auto_range(self) -> None:
        """自动调整坐标范围"""
        self._plot_widget.enableAutoRange()

    def set_x_range(self, x_min: float, x_max: float) -> None:
        """设置X轴范围（实时滚动时不留padding）"""
        self._plot_widget.setXRange(x_min, x_max, padding=0)

    def scroll_to_latest(self) -> None:
        """滚动到最新数据"""
        # 获取所有数据中的最大时间戳
        max_ts = None
        for plot_item in self._plot_items.values():
            x_data = plot_item.xData
            if x_data is not None and len(x_data) > 0:
                ts = x_data[-1]
                if max_ts is None or ts > max_ts:
                    max_ts = ts

        if max_ts is not None:
            # 获取当前 X 轴范围的宽度
            view_range = self._plot_widget.viewRange()
            x_range = view_range[0]
            width = x_range[1] - x_range[0]
            if width <= 0:
                width = 60  # 默认60秒
            self._plot_widget.setXRange(max_ts - width, max_ts, padding=0)

    # ============== 鼠标事件 ==============

    def _on_mouse_moved(self, pos) -> None:
        """鼠标移动事件 - 更新十字光标"""
        plot_area = self._plot_widget.plotItem.vb
        if plot_area.sceneBoundingRect().contains(pos):
            mouse_point = plot_area.mapSceneToView(pos)
            self._crosshair_v.setPos(mouse_point.x())
            self._crosshair_h.setPos(mouse_point.y())
            self._crosshair_v.setVisible(True)
            self._crosshair_h.setVisible(True)
        else:
            self._crosshair_v.setVisible(False)
            self._crosshair_h.setVisible(False)

    def enterEvent(self, event) -> None:
        """鼠标进入"""
        self._crosshair_v.setVisible(True)
        self._crosshair_h.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """鼠标离开"""
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)
        super().leaveEvent(event)

    # ============== 主题适配 ==============

    def apply_theme(self, is_dark: bool) -> None:
        """
        应用主题

        Args:
            is_dark: 是否深色主题
        """
        if is_dark:
            self._plot_widget.setBackground("#1e1e1e")
            axis_color = "#cccccc"
            grid_alpha = 0.2
        else:
            self._plot_widget.setBackground("#ffffff")
            axis_color = "#333333"
            grid_alpha = 0.15

        # 设置坐标轴颜色
        for axis_name in ("bottom", "left"):
            axis = self._plot_widget.getAxis(axis_name)
            axis.setPen(pg.mkPen(axis_color))
            axis.setTextPen(pg.mkPen(axis_color))

        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
