"""
文件名称: real_time_presenter.py
内容摘要: 实时波形 Presenter，处理TCP数据流的实时波形显示逻辑
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from gui.wave.models.wave_data_manager import WaveDataManager
from gui.wave.presenters.wave_presenter_base import WavePresenterBase
from gui.wave.views.i_wave_view import IRealTimeWaveView

logger = logging.getLogger(__name__)

# 默认图表刷新间隔（毫秒）
DEFAULT_REFRESH_INTERVAL_MS = 100

# 默认显示时间窗口（秒）
DEFAULT_DISPLAY_WINDOW_SECONDS = 60.0


class RealTimeWavePresenter(QObject, WavePresenterBase):
    """
    实时波形 Presenter

    职责：
    - 接收 TCP 服务端解析后的数据
    - 定时刷新图表（避免高频数据导致过度刷新）
    - 管理暂停/继续状态
    - 管理显示时间窗口

    数据流：
    TcpServerPresenter.entry_parsed → on_entry_parsed() → WaveDataManager
    QTimer → _on_refresh_timer() → View.update_all_chart_data()
    """

    # 信号：有新数据到达（供外部监听）
    data_updated = Signal()

    def __init__(
        self,
        view: IRealTimeWaveView,
        data_manager: WaveDataManager,
        refresh_interval_ms: int = DEFAULT_REFRESH_INTERVAL_MS,
        display_window_seconds: float = DEFAULT_DISPLAY_WINDOW_SECONDS,
    ):
        """
        初始化实时波形 Presenter

        Args:
            view: 实时波形 View 接口
            data_manager: 波形数据管理器
            refresh_interval_ms: 图表刷新间隔（毫秒）
            display_window_seconds: 显示时间窗口（秒）
        """
        super().__init__(data_manager=data_manager)

        self._view = view
        self._paused = False
        self._display_window = display_window_seconds
        self._has_new_data = False

        # 刷新定时器（避免高频数据导致UI卡顿）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(refresh_interval_ms)
        self._refresh_timer.timeout.connect(self._on_refresh_timer)

    def _get_view(self):
        """返回 View 接口实例"""
        return self._view

    # ============== 生命周期 ==============

    def start(self) -> None:
        """启动实时监控"""
        self._refresh_timer.start()
        self._view.update_status("实时监控已启动")
        logger.info("实时波形监控已启动")

    def stop(self) -> None:
        """停止实时监控"""
        self._refresh_timer.stop()
        self._view.update_status("实时监控已停止")
        logger.info("实时波形监控已停止")

    # ============== TCP数据接收 ==============

    def on_entry_parsed(
        self,
        timestamp_str: str,
        parsed_content: Optional[Dict[str, Any]],
        cmd_id: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> None:
        """
        接收已解析的数据条目

        由 TcpServerPresenter 解析后转发调用。
        自动发现新字段并更新字段树，仅记录用户已勾选的字段数据。

        Args:
            timestamp_str: 时间戳字符串
            parsed_content: 解析后的内容字典
            cmd_id: 命令ID
            direction: 数据方向
        """
        point, new_configs = self._data_manager.add_entry(
            timestamp_str, parsed_content, cmd_id, direction
        )

        # 新发现的字段添加到字段树（默认不勾选）
        if new_configs:
            for config in new_configs:
                self._view.add_field_to_tree(config)

        if point:
            self._has_new_data = True

    # ============== 用户交互 ==============

    def on_pause_toggled(self, paused: bool) -> None:
        """
        暂停/继续切换

        Args:
            paused: 是否暂停
        """
        self._paused = paused
        self._view.set_paused(paused)
        if paused:
            self._view.update_status("已暂停")
        else:
            self._view.update_status("实时监控中")
            # 恢复时立即刷新
            self._on_refresh_timer()

    def on_time_window_changed(self, seconds: float) -> None:
        """
        显示时间窗口变更

        Args:
            seconds: 新的时间窗口（秒）
        """
        self._display_window = seconds
        self._view.set_time_window(seconds)
        # 立即刷新
        self._refresh_with_window()

    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._paused

    def on_field_enabled_changed(self, field_path: str, enabled: bool) -> None:
        """
        字段启用状态变更（用户勾选/取消勾选）

        勾选 → 开始记录该字段数据 + 添加到图表
        取消勾选 → 停止记录 + 从图表移除

        Args:
            field_path: 字段路径
            enabled: 是否启用
        """
        self._data_manager.update_field_enabled(field_path, enabled)
        if enabled:
            self._data_manager.start_recording(field_path)
            config = self._data_manager.get_field_config(field_path)
            if config:
                self._view.add_chart_field(config)
            # 立即刷新已有数据
            self._refresh_field_data(field_path)
        else:
            self._data_manager.stop_recording(field_path)
            self._view.remove_chart_field(field_path)

    # ============== 内部方法 ==============

    def _on_refresh_timer(self) -> None:
        """定时刷新回调"""
        if self._paused:
            return

        if not self._has_new_data:
            return

        self._has_new_data = False
        self._refresh_with_window()

    def _refresh_with_window(self) -> None:
        """
        按当前时间窗口刷新图表

        核心逻辑：
        - 将所有已记录的数据传给图表（由图表组件的降采样处理性能）
        - 时间窗口仅控制 X 轴显示范围（滚动窗口），不裁剪数据
        """
        configs = self._data_manager.get_enabled_field_configs()
        if not configs:
            return

        # 获取所有已记录数据（不按时间窗口过滤）
        plot_data = {}
        max_ts = None
        for config in configs:
            timestamps, values = self._data_manager.get_plot_data(
                config.field_path
            )
            if timestamps:
                plot_data[config.field_path] = (timestamps, values)
                ts_last = timestamps[-1]
                if max_ts is None or ts_last > max_ts:
                    max_ts = ts_last

        if not plot_data:
            return

        self._view.update_all_chart_data(plot_data)
        self._view.update_data_count(self._data_manager.data_count)

        # 时间窗口仅控制 X 轴显示范围
        if max_ts is not None:
            self._view.set_x_range(
                max_ts - self._display_window, max_ts
            )

        self.data_updated.emit()

    def cleanup(self) -> None:
        """清理资源"""
        self._refresh_timer.stop()
