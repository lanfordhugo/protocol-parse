"""
文件名称: real_time_presenter.py
内容摘要: 实时波形 Presenter，处理TCP数据流的实时波形显示逻辑
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from gui.config import PROJECT_ROOT
from gui.wave.models.wave_data_manager import WaveDataManager
from gui.wave.presenters.wave_presenter_base import WavePresenterBase
from gui.wave.views.i_wave_view import IRealTimeWaveView

logger = logging.getLogger(__name__)

# 默认图表刷新间隔（毫秒）
DEFAULT_REFRESH_INTERVAL_MS = 100

# 默认显示时间窗口（秒）—— 3分钟
DEFAULT_DISPLAY_WINDOW_SECONDS = 180.0

# 波形数据输出目录
WAVE_OUTPUT_DIR = PROJECT_ROOT / "wave_output"


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
        super().__init__(view=view, data_manager=data_manager)

        self._paused = False
        self._display_window = display_window_seconds
        self._has_new_data = False
        self._auto_follow = True

        # 刷新定时器（避免高频数据导致UI卡顿）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(refresh_interval_ms)
        self._refresh_timer.timeout.connect(self._on_refresh_timer)

        # 自动输出定时器（1秒周期）
        self._auto_output_timer = QTimer(self)
        self._auto_output_timer.setInterval(1000)
        self._auto_output_timer.timeout.connect(self._on_auto_output_timer)
        self._auto_output_file: Optional[str] = None
        self._auto_output_last_count = 0

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
        """暂停/继续切换"""
        self._paused = paused
        self._view.set_paused(paused)
        if paused:
            self._view.update_status("已暂停")
        else:
            self._view.update_status("实时监控中")
            self._on_refresh_timer()

    def on_auto_follow_changed(self, follow: bool) -> None:
        """用户切换自动跟踪"""
        self._auto_follow = follow
        self._view.set_auto_follow(follow)
        if follow:
            self._refresh_with_window()

    def on_user_interacted(self) -> None:
        """用户手动缩放/平移图表 → 关闭自动跟踪"""
        if self._auto_follow:
            self._auto_follow = False
            self._view.set_auto_follow(False)

    @property
    def display_window(self) -> float:
        """当前显示时间窗口（秒）"""
        return self._display_window

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
            # 批量合并刷新（select_all 场景下避免重复遍历）
            self._queue_enable_field(field_path)
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
        刷新图表数据

        核心逻辑：
        - 将所有已记录的数据传给图表（降采样由图表组件处理）
        - 自动跟踪模式下：X 轴始终滚动到最新数据
        - 手动模式下：仅更新数据，不动 X 轴
        """
        configs = self._data_manager.get_enabled_field_configs()
        if not configs:
            return

        # 只取显示窗口内的数据，避免每次把全量缓存数据传给图表
        points = self._data_manager.get_latest_data(self._display_window)
        if not points:
            return

        field_paths = [c.field_path for c in configs]
        plot_data = self._data_manager.get_plot_data_batch_from_points(field_paths, points)
        if not plot_data:
            return

        max_ts = points[-1].timestamp.timestamp()

        self._view.update_all_chart_data(plot_data)
        self._view.update_data_count(self._data_manager.data_count)

        # 自动跟踪模式：滚动到最新数据
        if self._auto_follow and max_ts is not None:
            self._view.set_x_range(
                max_ts - self._display_window, max_ts
            )

        self.data_updated.emit()

    # ============== 保存功能 ==============

    def on_save_data(self, file_path: str) -> None:
        """手动保存缓存数据到指定文件"""
        try:
            if file_path.endswith(".csv"):
                count = self._data_manager.export_to_csv(file_path)
            else:
                count = self._data_manager.export_to_json(file_path)
            self._view.show_save_result(True, file_path, count)
            logger.info("已保存 %d 个数据点到 %s", count, file_path)
        except Exception as e:
            logger.error("保存失败: %s", e)
            self._view.show_save_result(False, str(e), 0)

    def on_auto_output_toggled(self, enabled: bool, base_name: str) -> None:
        """自动输出开关"""
        if enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_name}_{timestamp}.json"
            save_dir = WAVE_OUTPUT_DIR
            save_dir.mkdir(parents=True, exist_ok=True)
            self._auto_output_file = str(save_dir / filename)
            self._auto_output_last_count = 0
            self._auto_output_timer.start()
            self._view.update_status(f"自动输出: {self._auto_output_file}")
            logger.info("自动输出已启动: %s", self._auto_output_file)
        else:
            self._auto_output_timer.stop()
            # 停止前最后刷新一次
            if self._auto_output_file:
                self._do_auto_output()
            self._view.update_status("自动输出已停止")
            logger.info("自动输出已停止")
            self._auto_output_file = None

    def _on_auto_output_timer(self) -> None:
        """自动输出定时器回调（1秒周期）"""
        self._do_auto_output()

    def _do_auto_output(self) -> None:
        """执行自动输出：仅在有新数据时写入"""
        if not self._auto_output_file:
            return
        current_count = self._data_manager.data_count
        if current_count == self._auto_output_last_count:
            return
        try:
            self._data_manager.export_to_json(self._auto_output_file)
            self._auto_output_last_count = current_count
        except Exception as e:
            logger.error("自动输出失败: %s", e)

    def on_wave_cache_size_changed(self, size: int) -> None:
        """
        用户调整波形缓存大小

        Args:
            size: 新的最大数据点数
        """
        self._data_manager.set_max_data_points(size)
        logger.info("波形缓存大小已调整为 %d", size)

    def cleanup(self) -> None:
        """清理资源"""
        self._refresh_timer.stop()
        if self._auto_output_timer.isActive():
            self._auto_output_timer.stop()
            self._do_auto_output()
