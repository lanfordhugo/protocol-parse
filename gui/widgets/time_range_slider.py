# gui/widgets/time_range_slider.py
"""
文件名称: time_range_slider.py
内容摘要: 时间范围滑块组件，支持拖拽选择时间范围
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-23
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from PySide6.QtCore import Signal, Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget


class TimeRangeSlider(QWidget):
    """
    时间范围滑块组件

    职责：
    - 自定义绘制时间轴
    - 双滑块手柄拖拽交互
    - 自动刻度生成（根据时间跨度）
    - 时间 ↔ 位置转换算法
    """

    # 信号：范围变化 (start_time, end_time)
    range_changed = Signal(datetime, datetime)

    # 样式常量
    HANDLE_SIZE = 16  # 手柄大小
    HANDLE_RADIUS = 8  # 手柄圆角
    TRACK_HEIGHT = 6  # 轨道高度
    MARGIN = 30  # 左右边距

    def __init__(self, parent: Optional[QWidget] = None):
        """初始化时间范围滑块"""
        super().__init__(parent)

        # 时间范围
        self._min_time: Optional[datetime] = None
        self._max_time: Optional[datetime] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

        # 拖拽状态
        self._dragging = None  # 'start', 'end', 'range', None
        self._drag_start_pos = QPointF()
        self._drag_start_time = None

        # UI 设置
        self.setMouseTracking(True)  # 启用鼠标追踪
        self.setMinimumHeight(60)
        self.setMinimumWidth(300)

    def set_time_range(self, min_time: datetime, max_time: datetime):
        """
        设置可用时间范围（日志的最小/最大时间）

        Args:
            min_time: 最小时间
            max_time: 最大时间
        """
        self._min_time = min_time
        self._max_time = max_time

        # 默认选择全部范围
        self._start_time = min_time
        self._end_time = max_time

        self.update()

    def set_selection(self, start: datetime, end: datetime):
        """
        设置当前选择的时间范围

        Args:
            start: 起始时间
            end: 结束时间
        """
        if self._min_time and self._max_time:
            # 限制在可用范围内
            self._start_time = max(min(start, end), self._min_time)
            self._end_time = min(max(start, end), self._max_time)
            self.update()

    def get_selection(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取当前选择的时间范围

        Returns:
            Tuple[起始时间, 结束时间]
        """
        return (self._start_time, self._end_time)

    def paintEvent(self, event):
        """自定义绘制事件"""
        if not self._min_time or not self._max_time:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算绘制区域
        track_rect = QRectF(
            self.MARGIN,
            self.height() / 2 - self.TRACK_HEIGHT / 2,
            self.width() - 2 * self.MARGIN,
            self.TRACK_HEIGHT
        )

        # 1. 绘制轨道背景
        self._draw_track(painter, track_rect)

        # 2. 绘制选择区域（高亮）
        if self._start_time and self._end_time:
            self._draw_selection(painter, track_rect)

        # 3. 绘制刻度和标签
        self._draw_ticks(painter, track_rect)

        # 4. 绘制滑块手柄
        if self._start_time and self._end_time:
            start_pos = self._time_to_pos(self._start_time)
            end_pos = self._time_to_pos(self._end_time)
            center_y = track_rect.center().y()

            self._draw_handle(painter, start_pos, center_y, True)   # 左手柄
            self._draw_handle(painter, end_pos, center_y, False)    # 右手柄

    def _draw_track(self, painter: QPainter, rect: QRectF):
        """绘制轨道背景"""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#3c3c3c"))  # 深色主题轨道
        painter.drawRoundedRect(rect, 3, 3)

    def _draw_selection(self, painter: QPainter, rect: QRectF):
        """绘制选择区域（高亮）"""
        if not self._start_time or not self._end_time:
            return

        start_pos = self._time_to_pos(self._start_time)
        end_pos = self._time_to_pos(self._end_time)

        selection_rect = QRectF(
            start_pos,
            rect.top(),
            end_pos - start_pos,
            rect.height()
        )

        # 半透明蓝色高亮
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(86, 156, 214, 102))  # #569cd6, alpha=0.4
        painter.drawRoundedRect(selection_rect, 3, 3)

    def _draw_ticks(self, painter: QPainter, rect: QRectF):
        """绘制刻度和标签"""
        if not self._min_time or not self._max_time:
            return

        span_seconds = (self._max_time - self._min_time).total_seconds()

        # 根据时间跨度决定刻度间隔
        if span_seconds < 3600:  # < 1小时：每分钟
            interval = 60
            fmt = "%H:%M"
        elif span_seconds < 86400:  # < 1天：每小时
            interval = 3600
            fmt = "%H:%M"
        elif span_seconds < 86400 * 30:  # < 30天：每天
            interval = 86400
            fmt = "%m-%d %H:%M"
        else:  # >= 30天：每周或每月
            interval = 86400 * 7
            fmt = "%Y-%m-%d"

        # 计算刻度数量
        num_ticks = int(span_seconds / interval) + 1
        max_ticks = 10  # 最多显示 10 个刻度
        step = max(1, num_ticks // max_ticks)

        painter.setPen(QColor("#888888"))
        painter.setFont(QFont("Arial", 8))

        # 绘制刻度
        for i in range(0, num_ticks, step):
            offset = i * interval * step
            if offset > span_seconds:
                break

            dt = self._min_time + timedelta(seconds=offset)
            pos = self._time_to_pos(dt)

            # 绘制刻度线
            tick_top = int(rect.bottom() + 2)
            tick_bottom = int(rect.bottom() + 6)
            painter.drawLine(int(pos), tick_top, int(pos), tick_bottom)

            # 绘制标签
            label = dt.strftime(fmt)
            painter.drawText(int(pos - 20), int(rect.bottom() + 20), label)

    def _draw_handle(self, painter: QPainter, x: float, y: float, is_start: bool):
        """
        绘制手柄

        Args:
            painter: 绘制器
            x: X 坐标
            y: Y 坐标（中心）
            is_start: 是否为起始手柄
        """
        handle_rect = QRectF(
            x - self.HANDLE_SIZE / 2,
            y - self.HANDLE_SIZE / 2,
            self.HANDLE_SIZE,
            self.HANDLE_SIZE
        )

        # 渐变色
        gradient = QLinearGradient(handle_rect.topLeft(), handle_rect.bottomRight())
        gradient.setColorAt(0, QColor("#5c5c5c"))
        gradient.setColorAt(1, QColor("#3c3c3c"))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#569cd6"), 2))
        painter.drawRoundedRect(handle_rect, self.HANDLE_RADIUS, self.HANDLE_RADIUS)

    def _time_to_pos(self, dt: datetime) -> float:
        """
        时间转换为像素位置

        Args:
            dt: 时间

        Returns:
            float: 像素位置
        """
        if not self._min_time or not self._max_time:
            return self.MARGIN

        total_span = (self._max_time - self._min_time).total_seconds()
        if total_span == 0:
            return self.MARGIN

        offset = (dt - self._min_time).total_seconds()
        ratio = offset / total_span
        ratio = max(0, min(1, ratio))  # 限制在 [0, 1]

        return self.MARGIN + ratio * (self.width() - 2 * self.MARGIN)

    def _pos_to_time(self, pos: float) -> Optional[datetime]:
        """
        像素位置转换为时间

        Args:
            pos: 像素位置

        Returns:
            Optional[datetime]: 转换后的时间
        """
        if not self._min_time or not self._max_time:
            return None

        available_width = self.width() - 2 * self.MARGIN
        if available_width <= 0:
            return self._min_time

        ratio = (pos - self.MARGIN) / available_width
        ratio = max(0, min(1, ratio))  # 限制在 [0, 1]

        total_span = (self._max_time - self._min_time).total_seconds()
        offset = ratio * total_span

        return self._min_time + timedelta(seconds=offset)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if not self._min_time or not self._max_time:
            return

        pos = event.position().x()
        start_pos = self._time_to_pos(self._start_time) if self._start_time else 0
        end_pos = self._time_to_pos(self._end_time) if self._end_time else 0

        # 判断点击位置
        handle_threshold = self.HANDLE_SIZE

        # 点击左手柄
        if abs(pos - start_pos) < handle_threshold:
            self._dragging = 'start'
            self._drag_start_pos = event.position()
            self._drag_start_time = self._start_time

        # 点击右手柄
        elif abs(pos - end_pos) < handle_threshold:
            self._dragging = 'end'
            self._drag_start_pos = event.position()
            self._drag_start_time = self._end_time

        # 点击选择区域（整体移动）
        elif start_pos < pos < end_pos:
            self._dragging = 'range'
            self._drag_start_pos = event.position()
            self._drag_start_time = self._start_time
            self._drag_end_time = self._end_time

    def mouseMoveEvent(self, event):
        """鼠标移动事件（拖拽）"""
        if not self._dragging or not self._min_time or not self._max_time:
            return

        pos = event.position().x()
        new_time = self._pos_to_time(pos)

        if not new_time:
            return

        if self._dragging == 'start':
            # 拖拽起始手柄
            new_time = min(new_time, self._end_time) if self._end_time else new_time
            self._start_time = max(new_time, self._min_time)
            self.update()
            self.range_changed.emit(self._start_time, self._end_time)

        elif self._dragging == 'end':
            # 拖拽结束手柄
            new_time = max(new_time, self._start_time) if self._start_time else new_time
            self._end_time = min(new_time, self._max_time)
            self.update()
            self.range_changed.emit(self._start_time, self._end_time)

        elif self._dragging == 'range':
            # 整体移动
            if self._drag_start_time and self._drag_end_time:
                # 计算偏移量
                offset_px = pos - self._drag_start_pos.x()

                # 转换为时间偏移
                available_width = self.width() - 2 * self.MARGIN
                if available_width > 0:
                    ratio = offset_px / available_width
                    total_span = (self._max_time - self._min_time).total_seconds()
                    offset_seconds = ratio * total_span

                    # 应用偏移
                    new_start = self._drag_start_time + timedelta(seconds=offset_seconds)
                    new_end = self._drag_end_time + timedelta(seconds=offset_seconds)

                    # 限制在范围内
                    span = (self._drag_end_time - self._drag_start_time).total_seconds()

                    if new_start < self._min_time:
                        new_start = self._min_time
                        new_end = new_start + timedelta(seconds=span)
                    elif new_end > self._max_time:
                        new_end = self._max_time
                        new_start = new_end - timedelta(seconds=span)

                    self._start_time = new_start
                    self._end_time = new_end
                    self.update()
                    self.range_changed.emit(self._start_time, self._end_time)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._dragging = None
        self._drag_start_pos = QPointF()
        self._drag_start_time = None
