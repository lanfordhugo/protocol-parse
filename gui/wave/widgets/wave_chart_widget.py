"""
文件名称: wave_chart_widget.py
内容摘要: 波形图绘制组件，基于 pyqtgraph 实现多字段波形叠加显示
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QPointF, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper
from gui.wave.utils.downsample import LOD_LEVELS, LOD_MAX_LEVEL, lttb_downsample

logger = logging.getLogger(__name__)

MIN_X_WINDOW_WIDTH_S = 0.01  # 10ms：窗口最小时间宽度（继续放大无意义）


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
        # LOD 缓存/控制
        self._last_lod_level: Optional[int] = None
        self._last_x_range_width: Optional[float] = None
        # 鼠标移动节流，避免高频重算
        self._last_mouse_move_ts: float = 0.0
        self._mouse_move_interval = 0.03  # 30ms
        # 交互状态标记（拖拽/缩放时禁用 Tooltip）
        self._is_interacting: bool = False
        self._resume_ui_timer = QTimer(self)
        self._resume_ui_timer.setSingleShot(True)
        self._resume_ui_timer.timeout.connect(self._resume_ui_after_interaction)
        # 数据时间范围（用于缩放限制）
        self._data_time_range: Optional[Tuple[float, float]] = None

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

        # 操作提示文字（鼠标离开时显示）
        self._hint_text = pg.TextItem(
            text="滚轮缩放时间轴 | 左键拖动平移",
            anchor=(0.5, 1),  # 底部居中
            color="#888888",
        )
        self._hint_text.setZValue(300)
        self._plot_widget.addItem(self._hint_text, ignoreBounds=True)

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

        # pyqtgraph 内建裁剪+降采样（peak=min/max）能显著提升大数据量平移/缩放流畅度
        # 与本组件的 LOD 缓存并不冲突：即使某些场景暂时回退到较多点数，也能避免无谓绘制
        try:
            plot_item.setClipToView(True)
            plot_item.setDownsampling(auto=True, method="peak")
        except Exception as e:
            logger.debug("PlotDataItem setClipToView/setDownsampling failed: %s", e)

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
        self._last_lod_level = level
        if self._last_x_range_width is None:
            self._last_x_range_width = self.get_x_range_width()
        lod_data = self._get_lod_data(field_path, level)

        if lod_data is not None:
            plot_item.setData(lod_data[0], lod_data[1])
        else:
            plot_item.setData(ts_array, val_array)

        # 更新数据时间范围
        self._update_data_time_range()
        # 更新提示位置
        self._update_hint_position()

    def update_all_data(
        self,
        plot_data: Dict[str, Tuple[List[float], List[Optional[float]]]],
    ) -> None:
        """
        批量更新所有字段的数据

        Args:
            plot_data: {field_path: (timestamps, values)}
        """
        if not plot_data:
            return

        # 第一遍：计算并缓存所有字段的 LOD 数据
        field_arrays: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        for field_path, (timestamps, values) in plot_data.items():
            plot_item = self._plot_items.get(field_path)
            if not plot_item:
                continue

            if not timestamps or not values:
                plot_item.setData([], [])
                self._lod_cache.pop(field_path, None)
                self._raw_data_cache.pop(field_path, None)
                continue

            ts_array = np.array(timestamps, dtype=np.float64)
            val_array = np.array(values, dtype=np.float64)
            self._compute_lod_cache(field_path, ts_array, val_array)
            field_arrays[field_path] = (ts_array, val_array)

        if not field_arrays:
            return

        # 第二遍：根据当前视口一次性选择 LOD 并渲染
        visible_points = self._get_visible_point_count()
        level = self._select_lod_level(visible_points)
        self._last_lod_level = level
        if self._last_x_range_width is None:
            self._last_x_range_width = self.get_x_range_width()

        for field_path, (ts_array, val_array) in field_arrays.items():
            plot_item = self._plot_items.get(field_path)
            if not plot_item:
                continue
            lod_data = self._get_lod_data(field_path, level)
            if lod_data is not None:
                plot_item.setData(lod_data[0], lod_data[1])
            else:
                plot_item.setData(ts_array, val_array)

        # 更新数据时间范围
        self._update_data_time_range()
        # 更新提示位置
        self._update_hint_position()

    def clear(self) -> None:
        """清空所有数据（保留字段配置）"""
        for plot_item in self._plot_items.values():
            plot_item.setData([], [])
        self._last_lod_level = None
        self._last_x_range_width = None
        self._data_time_range = None

    def _update_data_time_range(self) -> None:
        """更新数据时间范围（用于缩放限制）"""
        x_min, x_max = None, None
        for raw_data in self._raw_data_cache.values():
            if raw_data is None:
                continue
            x_data, _ = raw_data
            if len(x_data) == 0:
                continue
            if x_min is None or x_data[0] < x_min:
                x_min = float(x_data[0])
            if x_max is None or x_data[-1] > x_max:
                x_max = float(x_data[-1])
        self._data_time_range = (x_min, x_max) if x_min is not None else None

    def clear_all(self) -> None:
        """清空所有字段和数据"""
        for field_path in list(self._plot_items.keys()):
            self.remove_field(field_path)
        # 清空 LOD 缓存
        self._lod_cache.clear()
        self._raw_data_cache.clear()
        self._last_lod_level = None
        self._last_x_range_width = None

    # ============== 多级精度（LOD）=============

    def _select_lod_level(self, visible_points: int) -> int:
        """
        根据可见数据点数和像素宽度自适应选择精度级别

        Args:
            visible_points: 当前视口内可见的数据点数

        Returns:
            精度级别索引（0-2 为降采样级别，3 为原始数据）
        """
        # 像素自适应：每像素最多显示 2 个数据点
        pixel_width = max(1, self._plot_widget.width())
        max_points_for_pixels = pixel_width * 2

        # 如果可见点数在像素容量内，使用原始数据
        if visible_points <= max_points_for_pixels:
            return LOD_MAX_LEVEL

        # 根据数据密度选择降采样级别
        for i, (threshold, target) in enumerate(LOD_LEVELS):
            if visible_points <= threshold:
                return i

        return LOD_MAX_LEVEL - 1  # 超大数据量使用最粗精度

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
        # 这里的 x_data/y_data 由调用方新建（np.array），无需额外 copy，避免不必要的内存与耗时
        self._raw_data_cache[field_path] = (x_data, y_data)

        # 初始化该字段的 LOD 缓存
        if field_path not in self._lod_cache:
            self._lod_cache[field_path] = {}

        # 数据更新后先清空旧的 LOD 缓存，按需（lazy）在 _get_lod_data 中计算。
        # 这样能显著降低一次性加载/刷新时的阻塞时间，缩放时再逐级补齐缓存。
        self._lod_cache[field_path].clear()

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

        raw_data = self._raw_data_cache.get(field_path)
        if raw_data is None:
            return None
        raw_x, raw_y = raw_data

        # 降采样级别：按需（lazy）计算并写入缓存
        field_cache = self._lod_cache.setdefault(field_path, {})
        if level in field_cache:
            return field_cache[level]

        target = LOD_LEVELS[level][1]
        if len(raw_x) <= target:
            return raw_data

        try:
            sampled_x, sampled_y = lttb_downsample(raw_x, raw_y, target)
            field_cache[level] = (sampled_x, sampled_y)
            return field_cache[level]
        except Exception as e:
            logger.debug("LOD downsample failed (field=%s level=%s): %s", field_path, level, e)
            return raw_data

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
            # 计算在视口范围内的数据点数（使用二分查找，避免全量扫描）
            left = int(np.searchsorted(x_data, x_min, side="left"))
            right = int(np.searchsorted(x_data, x_max, side="right"))
            count = max(0, right - left)
            max_count = max(max_count, count)

        return max_count

    def _apply_lod_rendering(self) -> None:
        """
        根据当前视口自动选择精度级别并重新渲染所有曲线
        """
        # 仅在缩放变化时尝试切换 LOD，平移无需重算
        width = self.get_x_range_width()
        if self._last_x_range_width is not None:
            if abs(width - self._last_x_range_width) < 1e-6:
                return
        self._last_x_range_width = width

        visible_points = self._get_visible_point_count()
        level = self._select_lod_level(visible_points)
        if level == self._last_lod_level:
            return
        self._last_lod_level = level

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
        # 更新提示位置
        self._update_hint_position()

    def get_x_range_width(self) -> float:
        """获取当前X轴显示宽度（秒）"""
        view_range = self._plot_widget.viewRange()
        return max(1e-9, view_range[0][1] - view_range[0][0])

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
            # 进入交互状态，隐藏 UI 元素释放 CPU
            self._enter_interaction_mode()

            # 触发视口自适应精度切换
            self._apply_lod_rendering()
            self.user_interacted.emit()

            # 延迟恢复 UI 元素（100ms 无操作后恢复）
            self._schedule_resume_ui()

    def _enter_interaction_mode(self) -> None:
        """进入交互模式，禁用 Tooltip 和十字光标"""
        if self._is_interacting:
            return
        self._is_interacting = True
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)
        self._tooltip.setVisible(False)
        self._snap_marker.setData([], [])

    def _schedule_resume_ui(self) -> None:
        """安排延迟恢复 UI 元素"""
        # 连续交互时重置计时器，避免过早恢复导致抖动/额外 CPU
        self._resume_ui_timer.start(100)

    def _resume_ui_after_interaction(self) -> None:
        """交互结束后恢复 UI 元素"""
        self._is_interacting = False
        # 更新提示位置
        self._update_hint_position()

    def _update_hint_position(self) -> None:
        """更新操作提示位置（视口底部居中）"""
        if not self._hint_text.isVisible():
            return
        view_range = self._plot_widget.viewRange()
        x_center = (view_range[0][0] + view_range[0][1]) / 2
        y_bottom = view_range[1][0]
        self._hint_text.setPos(x_center, y_bottom)

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
        - X 轴缩放有范围限制：最小 10ms；缩小到能覆盖全部数据点后不再继续缩小
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
            return

        # X 轴缩放：X 轴标签区域 + 绘图区域
        if not (x_axis_scene_rect.contains(scene_pos) or vb_scene_rect.contains(scene_pos)):
            return

        current_width = self.get_x_range_width()
        new_width = current_width * factor

        # 放大（窗口更窄）到 10ms 后不再继续放大
        if factor < 1:
            if current_width <= MIN_X_WINDOW_WIDTH_S:
                return
            if new_width < MIN_X_WINDOW_WIDTH_S:
                vb.scaleBy((MIN_X_WINDOW_WIDTH_S / current_width, 1), center=mouse_data)
                self.user_interacted.emit()
                return

        # 缩小（窗口更宽）到能覆盖全部数据点后不再继续缩小，并贴齐全量数据范围
        if factor > 1 and self._data_time_range:
            data_min, data_max = self._data_time_range
            data_width = data_max - data_min
            if data_width > 0 and new_width >= data_width:
                self._plot_widget.setXRange(data_min, data_max, padding=0)
                self.user_interacted.emit()
                return

        vb.scaleBy((factor, 1), center=mouse_data)
        self.user_interacted.emit()

    def _on_mouse_moved(self, scene_pos) -> None:
        """鼠标移动事件 - 吸附到最近数据点，更新十字光标和 Tooltip"""
        # 交互模式下跳过，释放 CPU
        if self._is_interacting:
            return

        vb = self._plot_widget.plotItem.vb
        if not vb.sceneBoundingRect().contains(scene_pos):
            self._crosshair_v.setVisible(False)
            self._crosshair_h.setVisible(False)
            self._tooltip.setVisible(False)
            self._snap_marker.setData([], [])
            return

        # 30ms 节流，减少高频重算
        now = time.monotonic()
        if now - self._last_mouse_move_ts < self._mouse_move_interval:
            return
        self._last_mouse_move_ts = now
        if not self._plot_items:
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
        mouse_scene = vb.mapViewToScene(QPointF(float(mouse_x), float(mouse_y)))
        mouse_scene_x = mouse_scene.x()
        mouse_scene_y = mouse_scene.y()

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
                dx = pt_scene.x() - mouse_scene_x
                dy = pt_scene.y() - mouse_scene_y
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
        """鼠标进入 - 隐藏操作提示"""
        self._hint_text.setVisible(False)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """鼠标离开 - 隐藏十字光标和 Tooltip，显示操作提示"""
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)
        self._tooltip.setVisible(False)
        self._snap_marker.setData([], [])
        self._hint_text.setVisible(True)
        self._update_hint_position()
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
