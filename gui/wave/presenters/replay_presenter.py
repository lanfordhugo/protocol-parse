"""
文件名称: replay_presenter.py
内容摘要: 数据回放 Presenter，处理多数据源的波形回放逻辑（不依赖YAML协议配置）
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-11
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gui.wave.models.wave_data_manager import WaveDataManager
from gui.wave.presenters.wave_presenter_base import WavePresenterBase
from gui.wave.views.i_wave_view import IHistoryWaveView

logger = logging.getLogger(__name__)


class ReplayPresenter(WavePresenterBase):
    """
    数据回放 Presenter

    职责：
    - 从多种数据源加载已解析数据（不依赖YAML协议配置）
    - 提供时间范围选择
    - 数据导出（JSON/CSV）

    支持的数据源：
    1. 波形JSON文件（import_from_json）
    2. TCP服务器解析结果（load_from_entries）
    3. 普通解析结果（load_from_entries）

    数据流：
    外部数据 → load_from_entries() / import_from_json() → WaveDataManager
    时间范围变化 → on_time_range_changed() → View.update_all_chart_data()
    """

    def __init__(
        self,
        view: IHistoryWaveView,
        data_manager: WaveDataManager,
    ):
        """
        初始化数据回放 Presenter

        Args:
            view: 波形 View 接口
            data_manager: 波形数据管理器
        """
        super().__init__(data_manager)
        self._view = view

        # 当前查看的时间范围
        self._view_start: Optional[datetime] = None
        self._view_end: Optional[datetime] = None

        # 数据源标记
        self._data_source: str = ""

    def _get_view(self):
        """返回 View 接口实例"""
        return self._view

    # ============== 数据加载 ==============

    def load_from_entries(
        self,
        entries: List[Tuple[str, Optional[Dict[str, Any]], Optional[int], Optional[str]]],
        source_name: str = "外部数据",
    ) -> int:
        """
        从解析条目列表加载数据（通用入口）

        适用于TCP服务器解析结果和普通解析结果。

        Args:
            entries: 列表，每项为 (timestamp_str, parsed_content, cmd_id, direction)
            source_name: 数据源名称（用于状态栏显示）

        Returns:
            成功加载的数据点数量
        """
        # 根据数据源尝试应用协议配置（用于按 YAML 顺序展示字段）
        self._apply_protocol_config_from_source(source_name)

        # 完整重置旧数据（含字段配置和录制状态）
        self._data_manager.reset()
        self._view.clear_chart()

        # 历史加载模式：记录所有字段数据
        self._data_manager.set_record_all(True)
        count = self._data_manager.add_entries(entries)

        self._data_source = source_name

        if count > 0:
            self._setup_after_load()

        self._view.update_status(f"已从 {source_name} 加载 {count} 个数据点")
        logger.info("数据回放加载完成（%s）: %d 个数据点", source_name, count)
        return count

    def import_from_json(self, file_path: str) -> int:
        """
        从 JSON 文件导入数据

        Args:
            file_path: 文件路径

        Returns:
            导入的数据点数量
        """
        try:
            # JSON 回放来源未知，清空协议顺序映射，按文件中记录的 field_order 恢复。
            self._data_manager.set_protocol_config(None)

            # 完整重置旧数据（含字段配置和录制状态）
            self._data_manager.reset()
            self._view.clear_chart()

            # 历史加载模式：记录所有字段数据
            self._data_manager.set_record_all(True)
            count = self._data_manager.import_from_json(file_path)

            self._data_source = "JSON文件"

            if count > 0:
                self._setup_after_load()
            self._view.update_status(f"已从 JSON 导入 {count} 个数据点")
            return count
        except Exception as e:
            logger.error("JSON 导入失败: %s", e)
            self._view.update_status(f"导入失败: {e}")
            return 0

    def _apply_protocol_config_from_source(self, source_name: str) -> None:
        """
        尝试从数据源名称推断协议并加载 YAML 配置。

        目前约定 source_name 格式：`普通解析- <protocol_name>`
        """
        self._data_manager.set_protocol_config(None)

        # 支持两种格式："普通解析 - v8" 和 "普通解析-v8"
        marker1 = "普通解析 - "
        marker2 = "普通解析-"

        if marker1 in source_name:
            protocol_name = source_name.split(marker1, 1)[1].strip()
        elif marker2 in source_name:
            protocol_name = source_name.split(marker2, 1)[1].strip()
        else:
            return
        if not protocol_name:
            return

        config_path = Path("configs") / protocol_name / "protocol.yaml"
        if not config_path.exists():
            logger.debug("未找到协议配置文件，跳过 YAML 顺序映射: %s", config_path)
            return

        try:
            from src.yaml_cmdformat import YamlCmdFormat

            protocol_config = YamlCmdFormat(config_path)
            self._data_manager.set_protocol_config(protocol_config)
        except Exception as e:
            logger.warning("加载协议配置失败，回放字段顺序将使用报文顺序: %s", e)

    def _setup_after_load(self) -> None:
        """数据加载后的初始化"""
        # 设置时间范围
        time_range = self._data_manager.time_range
        if time_range:
            start, end = time_range
            self._view_start = start
            self._view_end = end
            self._view.set_time_range_limits(
                start.timestamp(), end.timestamp()
            )

        # 获取所有字段配置，并全部设为不启用（用户手动选择）
        configs = self._data_manager.get_all_field_configs()
        for config in configs:
            config.enabled = False
            self._data_manager.update_field_enabled(config.field_path, False)

        # 刷新字段树（默认不展开、不勾选）
        self._view.refresh_field_tree(configs, expand_all=False)

        # 为每个可绘图字段添加到图表（但不显示数据，等待用户选择）
        for config in configs:
            self._view.add_chart_field(config)

        # 启用导出
        self._view.set_export_enabled(self._data_manager.data_count > 0)

    def on_clear_data(self) -> None:
        """清空所有数据（供 View 委托调用）"""
        self._data_manager.reset()
        self._view.clear_chart()
        self._view.refresh_field_tree([])
        self._view.update_data_count(0)
        self._view.set_export_enabled(False)
        self._view.update_status("数据已清空")
        self._data_source = ""

    # ============== 时间范围操作 ==============

    def on_time_range_changed(
        self,
        start_epoch: float,
        end_epoch: float,
    ) -> None:
        """
        时间范围变更

        Args:
            start_epoch: 起始时间（epoch秒数）
            end_epoch: 结束时间（epoch秒数）
        """
        self._view_start = datetime.fromtimestamp(start_epoch)
        self._view_end = datetime.fromtimestamp(end_epoch)

        # 刷新图表（仅显示选定范围内的数据）
        configs = self._data_manager.get_enabled_field_configs()
        field_paths = [c.field_path for c in configs]
        range_points = self._data_manager.get_data_in_range(self._view_start, self._view_end)
        plot_data = self._data_manager.get_plot_data_batch_from_points(field_paths, range_points)

        self._view.update_all_chart_data(plot_data)
        self._view.update_data_count(len(range_points))

    # ============== 数据导出 ==============

    def on_export_json(self, file_path: str) -> None:
        """
        导出为 JSON 格式

        Args:
            file_path: 输出文件路径
        """
        try:
            count = self._data_manager.export_to_json(file_path)
            self._view.show_export_result(True, file_path)
            self._view.update_status(f"已导出 {count} 个数据点到 JSON")
        except Exception as e:
            logger.error("JSON 导出失败: %s", e)
            self._view.show_export_result(False, str(e))

    def on_export_csv(self, file_path: str) -> None:
        """
        导出为 CSV 格式

        Args:
            file_path: 输出文件路径
        """
        try:
            count = self._data_manager.export_to_csv(file_path)
            self._view.show_export_result(True, file_path)
            self._view.update_status(f"已导出 {count} 个数据点到 CSV")
        except Exception as e:
            logger.error("CSV 导出失败: %s", e)
            self._view.show_export_result(False, str(e))
