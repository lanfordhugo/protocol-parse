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
from PySide6.QtCore import QEvent, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper

logger = logging.getLogger(__name__)

# 多级精度（LOD）配置：(阈值, 目标点数)
# 当数据点数超过阈值时，降采样到目标点数
LOD_LEVELS = [
    (5000, 500),      # Level 0: 数据点 > 5000 时降采样到 500
    (20000, 2000),    # Level 1: 数据点 > 20000 时降采样到 2000
    (100000, 5000),   # Level 2: 数据点 > 100000 时降采样到 5000
]
# 最高精度级别索引（使用原始数据）
LOD_MAX_LEVEL = len(LOD_LEVELS)


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


class WaveViewBox(pg.ViewBox):
    """
    自定义 ViewBox

    - 禁用默认滚轮缩放（由 WaveChartWidget 统一处理轴感知缩放）
    - 使用 PanMode（左键拖动平移）
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseMode(pg.ViewBox.PanMode)

    def wheelEvent(self, ev, axis=None):
        """禁用默认滚轮缩放，交给父组件处理"""
        ev.ignore()


class WaveChartWidget(QWidget):
    """
    波形图绘制组件

    功能：
    - 使用 pyqtgraph 绘制多字段波形
    - 轴感知缩放：鼠标在X轴附近滚轮缩放X轴，Y轴附近缩放Y轴
    - 左键拖动平移，禁用框选放大
    - 悬浮吸附 Tooltip：自动找最近数据点，显示字段名、时间、值
    - 图例显示字段名

    信号：
    - field_remove_requested(str): 请求移除字段
    - field_color_change_requested(str): 请求修改字段颜色
    - user_interacted(): 用户手动缩放/平移（通知 Presenter 关闭自动跟踪）
    """

    # 信号
    field_remove_requested = Signal(str)
    field_color_change_requested = Signal(str)
    user_interacted = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 字段 → 绘图曲线映射
        self._plot_items: Dict[str, pg.PlotDataItem] = {}
        # 字段 → 配置映射
        self._field_configs: Dict[str, FieldConfig] = {}
        # 防止程序设置 X 范围时触发 user_interacted
        self._programmatic_update = False
        # 多级精度缓存: {field_path: {lod_level: (x_data, y_data)}}
        self._lod_cache: Dict[str, Dict[int, Tuple[np.ndarray, np.ndarray]]] = {}
        # 原始数据缓存: {field_path: (x_data, y_data)}
        self._raw_data_cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建自定义 ViewBox（PanMode + 禁用默认滚轮）
        vb = WaveViewBox()

        # 创建 pyqtgraph 绘图控件
        self._plot_widget = pg.PlotWidget(
            viewBox=vb,
            axisItems={"bottom": TimeAxisItem(orientation="bottom")},
        )
        self._plot_widget.setBackground("transparent")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel("bottom", "时间")
        self._plot_widget.setLabel("left", "值")

        # Y 轴自动适配（X 轴由 Presenter 的时间窗口控制）
        self._plot_widget.enableAutoRange(axis="y", enable=True)
        self._plot_widget.enableAutoRange(axis="x", enable=False)

        # 检测用户手动平移
        vb.sigRangeChangedManually.connect(self._on_range_changed_manually)

        # 十字光标（吸附到最近数据点）
        self._crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen("#888888", width=1, style=Qt.DashLine),
        )
        self._crosshair_h = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen("#888888", width=1, style=Qt.DashLine),
        )
        self._plot_widget.addItem(self._crosshair_v, ignoreBounds=True)
        self._plot_widget.addItem(self._crosshair_h, ignoreBounds=True)
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)

        # 吸附点标记
        self._snap_marker = pg.ScatterPlotItem(
            size=10, pen=pg.mkPen("w", width=2), brush=pg.mkBrush(255, 255, 0, 180),
        )
        self._snap_marker.setZValue(100)
        self._plot_widget.addItem(self._snap_marker)

        # 悬浮 Tooltip
        self._tooltip = pg.TextItem(
            text="", anchor=(0, 1), fill=pg.mkBrush(0, 0, 0, 180),
            color="w", border=pg.mkPen("#555555"),
        )
        self._tooltip.setZValue(200)
        self._tooltip.setVisible(False)
        self._plot_widget.addItem(self._tooltip, ignoreBounds=True)

        # 鼠标移动事件（更新吸附 Tooltip）
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # 拦截滚轮事件（轴感知缩放）—— 必须安装到 viewport 上，
        # 因为 QGraphicsView 的滚轮事件实际发送到 viewport 子控件
        self._plot_widget.viewport().installEventFilter(self)

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
            # 清空该字段的缓存
            self._lod_cache.pop(field_path, None)
            self._raw_data_cache.pop(field_path, None)
            return

        ts_array = np.array(timestamps, dtype=np.float64)
        val_array = np.array(values, dtype=np.float64)

        # 计算并缓存多级精度数据
        self._compute_lod_cache(field_path, ts_array, val_array)

        # 根据当前视口选择合适的精度级别渲染
        visible_points = self._get_visible_point_count()
        level = self._select_lod_level(visible_points)
        lod_data = self._get_lod_data(field_path, level)

        if lod_data is not None:
            plot_item.setData(lod_data[0], lod_data[1])
        else:
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
        # 清空 LOD 缓存
        self._lod_cache.clear()
        self._raw_data_cache.clear()

    # ============== 多级精度（LOD）=============

    def _select_lod_level(self, visible_points: int) -> int:
        """
        根据可见数据点数选择精度级别

        Args:
            visible_points: 当前视口内可见的数据点数

        Returns:
            精度级别索引（0-2 为降采样级别，3 为原始数据）
        """
        for i, (threshold, _) in enumerate(LOD_LEVELS):
            if visible_points <= threshold:
                return i
        return LOD_MAX_LEVEL

    def _compute_lod_cache(
        self,
        field_path: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
    ) -> None:
        """
        计算并缓存指定字段的多级精度降采样数据

        Args:
            field_path: 字段路径
            x_data: 原始 X 轴数据
            y_data: 原始 Y 轴数据
        """
        # 缓存原始数据
        self._raw_data_cache[field_path] = (x_data.copy(), y_data.copy())

        # 初始化该字段的 LOD 缓存
        if field_path not in self._lod_cache:
            self._lod_cache[field_path] = {}

        n_points = len(x_data)

        # 为每个 LOD 级别计算降采样数据
        for level, (threshold, target) in enumerate(LOD_LEVELS):
            if n_points > threshold:
                # 数据量超过阈值，执行降采样
                sampled_x, sampled_y = lttb_downsample(x_data, y_data, target)
                self._lod_cache[field_path][level] = (sampled_x, sampled_y)
            # 如果数据量不超过阈值，该级别不需要缓存（使用更高级别的数据）

    def _get_lod_data(
        self,
        field_path: str,
        level: int,
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        获取指定字段和精度级别的数据

        Args:
            field_path: 字段路径
            level: 精度级别

        Returns:
            (x_data, y_data) 或 None
        """
        # 原始数据级别
        if level >= LOD_MAX_LEVEL:
            return self._raw_data_cache.get(field_path)

        # 降采样级别
        field_cache = self._lod_cache.get(field_path)
        if field_cache and level in field_cache:
            return field_cache[level]

        # 如果该级别没有缓存，尝试使用更低的精度级别
        for lower_level in range(level + 1, LOD_MAX_LEVEL + 1):
            if lower_level >= LOD_MAX_LEVEL:
                return self._raw_data_cache.get(field_path)
            if field_cache and lower_level in field_cache:
                return field_cache[lower_level]

        # 降级到原始数据
        return self._raw_data_cache.get(field_path)

    def _get_visible_point_count(self) -> int:
        """
        估算当前视口内可见的数据点数

        Returns:
            可见数据点数的最大值
        """
        max_count = 0
        view_range = self._plot_widget.viewRange()
        x_min, x_max = view_range[0]

        for field_path in self._plot_items.keys():
            raw_data = self._raw_data_cache.get(field_path)
            if raw_data is None:
                continue
            x_data, _ = raw_data
            # 计算在视口范围内的数据点数
            mask = (x_data >= x_min) & (x_data <= x_max)
            count = int(np.sum(mask))
            max_count = max(max_count, count)

        return max_count

    def _apply_lod_rendering(self) -> None:
        """
        根据当前视口自动选择精度级别并重新渲染所有曲线
        """
        visible_points = self._get_visible_point_count()
        level = self._select_lod_level(visible_points)

        for field_path, plot_item in self._plot_items.items():
            lod_data = self._get_lod_data(field_path, level)
            if lod_data is not None:
                x_data, y_data = lod_data
                plot_item.setData(x_data, y_data)

    def auto_range(self) -> None:
        """自动调整坐标范围"""
        self._plot_widget.enableAutoRange()

    def auto_fit_all(self) -> None:
        """
        自动适配全部数据

        X轴展示所有数据点，Y轴适配可见数据的值范围。
        适用于数据回放场景的"自动缩放"功能。
        """
        # 1. 收集所有曲线的时间戳范围
        x_min, x_max = None, None
        for plot_item in self._plot_items.values():
            x_data = plot_item.xData
            if x_data is not None and len(x_data) > 0:
                if x_min is None or x_data[0] < x_min:
                    x_min = float(x_data[0])
                if x_max is None or x_data[-1] > x_max:
                    x_max = float(x_data[-1])

        # 2. 设置 X 轴范围
        if x_min is not None and x_max is not None:
            self.set_x_range(x_min, x_max)

        # 3. Y 轴自动适配
        self._plot_widget.enableAutoRange(axis="y", enable=True)
        self._plot_widget.getViewBox().autoRange(items=None)

    def set_x_range(self, x_min: float, x_max: float) -> None:
        """设置X轴范围（程序控制，不触发 user_interacted）"""
        self._programmatic_update = True
        self._plot_widget.setXRange(x_min, x_max, padding=0)
        self._programmatic_update = False

    def get_x_range_width(self) -> float:
        """获取当前X轴显示宽度（秒）"""
        view_range = self._plot_widget.viewRange()
        return max(1.0, view_range[0][1] - view_range[0][0])

    def scroll_to_latest(self) -> None:
        """滚动到最新数据"""
        max_ts = None
        for plot_item in self._plot_items.values():
            x_data = plot_item.xData
            if x_data is not None and len(x_data) > 0:
                ts = x_data[-1]
                if max_ts is None or ts > max_ts:
                    max_ts = ts
        if max_ts is not None:
            width = self.get_x_range_width()
            self.set_x_range(max_ts - width, max_ts)

    # ============== 鼠标交互 ==============

    def _on_range_changed_manually(self) -> None:
        """用户手动拖动平移了图表"""
        if not self._programmatic_update:
            # 触发视口自适应精度切换
            self._apply_lod_rendering()
            self.user_interacted.emit()

    def eventFilter(self, obj, event) -> bool:
        """拦截 PlotWidget 滚轮事件，实现轴感知缩放"""
        if obj is self._plot_widget.viewport() and event.type() == QEvent.Type.Wheel:
            self._handle_wheel(event)
            return True
        return super().eventFilter(obj, event)

    def _handle_wheel(self, event) -> None:
        """
        轴感知滚轮缩放

        - 鼠标在 X 轴标签区域：仅缩放 X 轴
        - 鼠标在 Y 轴标签区域：仅缩放 Y 轴
        - 鼠标在绑图区域内：仅缩放 X 轴（时间序列图以时间缩放为主）
        """
        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 0.8 if delta > 0 else 1.25
        widget_pos = event.position()

        vb = self._plot_widget.plotItem.vb
        plot_item = self._plot_widget.plotItem

        # 获取各区域在 widget 坐标系下的矩形
        vb_scene_rect = vb.sceneBoundingRect()
        x_axis_scene_rect = plot_item.getAxis("bottom").sceneBoundingRect()
        y_axis_scene_rect = plot_item.getAxis("left").sceneBoundingRect()

        # 转换鼠标位置到 scene 坐标
        scene_pos = self._plot_widget.mapToScene(widget_pos.toPoint())

        # 鼠标数据坐标（用于以鼠标为中心缩放）
        mouse_data = vb.mapSceneToView(scene_pos)

        if y_axis_scene_rect.contains(scene_pos):
            # Y 轴区域：仅缩放 Y 轴
            vb.scaleBy((1, factor), center=mouse_data)
        elif x_axis_scene_rect.contains(scene_pos):
            # 仅 X 轴区域：缩放 X 轴（绘图区域不触发缩放）
            vb.scaleBy((factor, 1), center=mouse_data)
            self.user_interacted.emit()

    def _on_mouse_moved(self, scene_pos) -> None:
        """鼠标移动事件 - 吸附到最近数据点，更新十字光标和 Tooltip"""
        vb = self._plot_widget.plotItem.vb
        if not vb.sceneBoundingRect().contains(scene_pos):
            self._crosshair_v.setVisible(False)
            self._crosshair_h.setVisible(False)
            self._tooltip.setVisible(False)
            self._snap_marker.setData([], [])
            return

        mouse_data = vb.mapSceneToView(scene_pos)
        snap = self._find_nearest_point(mouse_data.x(), mouse_data.y())

        if snap is None:
            self._crosshair_v.setVisible(False)
            self._crosshair_h.setVisible(False)
            self._tooltip.setVisible(False)
            self._snap_marker.setData([], [])
            return

        # 十字光标吸附到数据点
        self._crosshair_v.setPos(snap["x"])
        self._crosshair_h.setPos(snap["y"])
        self._crosshair_v.setVisible(True)
        self._crosshair_h.setVisible(True)

        # 吸附标记
        self._snap_marker.setData(
            [snap["x"]], [snap["y"]],
            brush=pg.mkBrush(QColor(snap["color"])),
        )

        # Tooltip 内容
        try:
            ts_str = datetime.fromtimestamp(snap["x"]).strftime("%H:%M:%S.%f")[:-3]
        except (OSError, ValueError, OverflowError):
            ts_str = f"{snap['x']:.3f}"
        tooltip_text = (
            f"{snap['field_name']}\n"
            f"时间: {ts_str}\n"
            f"值: {snap['y']:.4g}"
        )
        self._tooltip.setText(tooltip_text)
        self._tooltip.setPos(snap["x"], snap["y"])
        self._tooltip.setVisible(True)

    def _find_nearest_point(
        self, mouse_x: float, mouse_y: float,
    ) -> Optional[Dict[str, Any]]:
        """
        在所有可见曲线中找到离鼠标最近的数据点

        使用 X 轴二分查找 + 屏幕距离比较。

        Returns:
            最近点信息字典，或 None
        """
        vb = self._plot_widget.plotItem.vb
        best_dist_sq = float("inf")
        best = None

        for field_path, plot_item in self._plot_items.items():
            x_data = plot_item.xData
            y_data = plot_item.yData
            if x_data is None or len(x_data) == 0:
                continue

            # 二分查找最近 X 索引
            idx = int(np.searchsorted(x_data, mouse_x))
            candidates = []
            if idx > 0:
                candidates.append(idx - 1)
            if idx < len(x_data):
                candidates.append(idx)

            for i in candidates:
                # 用屏幕坐标计算距离（避免 X/Y 尺度差异）
                pt_scene = vb.mapViewToScene(QPointF(float(x_data[i]), float(y_data[i])))
                mouse_scene = vb.mapViewToScene(QPointF(mouse_x, mouse_y))
                dx = pt_scene.x() - mouse_scene.x()
                dy = pt_scene.y() - mouse_scene.y()
                dist_sq = dx * dx + dy * dy
                if dist_sq < best_dist_sq:
                    best_dist_sq = dist_sq
                    config = self._field_configs.get(field_path)
                    best = {
                        "field_path": field_path,
                        "field_name": config.display_name if config else field_path,
                        "x": float(x_data[i]),
                        "y": float(y_data[i]),
                        "color": config.color if config else "#ffffff",
                    }

        return best

    def enterEvent(self, event) -> None:
        """鼠标进入"""
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """鼠标离开 - 隐藏十字光标和 Tooltip"""
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)
        self._tooltip.setVisible(False)
        self._snap_marker.setData([], [])
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
