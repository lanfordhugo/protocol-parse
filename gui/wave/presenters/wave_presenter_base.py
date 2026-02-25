"""
文件名称: wave_presenter_base.py
内容摘要: 波形 Presenter 基类，封装实时和历史模式共享的业务逻辑
当前版本: v1.1.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtCore import QTimer

from gui.wave.models.wave_data_manager import (
    FieldConfig,
    WaveDataManager,
)
from gui.wave.utils.field_type_detector import FieldType
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper

if TYPE_CHECKING:
    from src.yaml_config import Field, TypeDef

logger = logging.getLogger(__name__)


class WavePresenterBase:
    """
    波形 Presenter 基类

    职责：
    - 管理 WaveDataManager 和 View 的交互
    - 字段添加/删除/配置变更的业务逻辑
    - 图表数据刷新

    基类通过 __init__ 的 view 参数接收 View 实例，子类无需覆写 _get_view()。
    """

    def __init__(self, view=None, data_manager: Optional[WaveDataManager] = None, **kwargs):
        """
        初始化基类

        支持协作式多重继承（与 QObject 兼容）。
        view 和 data_manager 设为可选参数以适配 Python MRO。

        Args:
            view: 波形 View 接口实例
            data_manager: 波形数据管理器
            **kwargs: 传递给 super().__init__() 的额外参数
        """
        super().__init__(**kwargs)
        self._view = view
        self._data_manager = data_manager
        self._pending_enable_fields: set[str] = set()
        self._enable_timer_active = False

        # 当前查看的时间范围（子类 _setup_after_load 和 on_time_range_changed 共用）
        self._view_start: Optional[datetime] = None
        self._view_end: Optional[datetime] = None

    @property
    def data_manager(self) -> WaveDataManager:
        """获取数据管理器"""
        return self._data_manager

    # ============== 字段管理 ==============

    def on_add_field(
        self,
        field_path: str,
        sample_value: Any,
        cmd_id: Optional[int] = None,
        display_name: Optional[str] = None,
        type_def: Optional["TypeDef"] = None,
        field: Optional["Field"] = None,
    ) -> Optional[FieldConfig]:
        """
        添加字段到监控

        Args:
            field_path: 字段路径
            sample_value: 样本值（用于类型检测）
            cmd_id: 命令ID
            display_name: 自定义显示名称
            type_def: YAML 类型定义（可选，用于精确类型判断）
            field: YAML 字段定义（可选，用于精确类型判断）

        Returns:
            创建的字段配置，失败返回 None
        """
        # 检查是否已存在
        existing = self._data_manager.get_field_config(field_path)
        if existing:
            logger.info("字段 %s 已在监控中", field_path)
            return existing

        # 检测类型（优先 YAML 配置，回退值类型检测）
        field_type = self._data_manager.detect_field_type(
            sample_value, type_def, field
        )
        chart_type = ChartTypeMapper.get_chart_type(field_type)

        if chart_type is None:
            logger.warning("字段 %s 的类型 %s 不支持绘图", field_path, field_type.name)
            return None

        # 分配颜色
        existing_count = len(self._data_manager.get_all_field_configs())
        color = ChartTypeMapper.get_color(existing_count)

        # 创建配置
        config = FieldConfig(
            field_path=field_path,
            display_name=display_name or field_path.split(".")[-1],
            field_type=field_type,
            chart_type=chart_type,
            color=color,
            enabled=True,
            cmd_id=cmd_id,
        )

        self._data_manager.add_field_config(config)

        # 通知 View
        view = self._get_view()
        if view:
            view.add_chart_field(config)
            view.add_field_to_tree(config)

        logger.info("已添加监控字段: %s (%s/%s)", field_path, field_type.name, chart_type.name)
        return config

    def on_remove_field(self, field_path: str) -> None:
        """
        移除监控字段

        Args:
            field_path: 字段路径
        """
        removed = self._data_manager.remove_field_config(field_path)
        if removed:
            view = self._get_view()
            if view:
                view.remove_chart_field(field_path)
                view.remove_field_from_tree(field_path)
            logger.info("已移除监控字段: %s", field_path)

    def on_field_color_changed(self, field_path: str, color: str) -> None:
        """
        字段颜色变更

        Args:
            field_path: 字段路径
            color: 新颜色
        """
        self._data_manager.update_field_color(field_path, color)
        config = self._data_manager.get_field_config(field_path)
        if config:
            view = self._get_view()
            if view:
                view.update_field_in_tree(config)

    def on_field_enabled_changed(self, field_path: str, enabled: bool) -> None:
        """
        字段启用状态变更

        Args:
            field_path: 字段路径
            enabled: 是否启用
        """
        self._data_manager.update_field_enabled(field_path, enabled)
        if enabled:
            self._queue_enable_field(field_path)
        else:
            self._pending_enable_fields.discard(field_path)
            view = self._get_view()
            if view:
                view.remove_chart_field(field_path)

    def on_field_renamed(self, field_path: str, new_name: str) -> None:
        """
        字段重命名

        Args:
            field_path: 字段路径
            new_name: 新显示名称
        """
        self._data_manager.update_field_display_name(field_path, new_name)
        config = self._data_manager.get_field_config(field_path)
        if config:
            view = self._get_view()
            if view:
                view.update_field_in_tree(config)

    # ============== 数据刷新 ==============

    def _queue_enable_field(self, field_path: str) -> None:
        """批量合并启用字段的刷新，减少重复遍历数据点"""
        self._pending_enable_fields.add(field_path)
        if self._enable_timer_active:
            return
        self._enable_timer_active = True
        QTimer.singleShot(0, self._flush_pending_enables)

    def _flush_pending_enables(self) -> None:
        """处理批量启用的字段刷新"""
        self._enable_timer_active = False
        if not self._pending_enable_fields:
            return

        pending = list(self._pending_enable_fields)
        self._pending_enable_fields.clear()

        view = self._get_view()
        if not view:
            return

        enabled_fields: List[str] = []
        configs: List[FieldConfig] = []
        for field_path in pending:
            config = self._data_manager.get_field_config(field_path)
            if config and config.enabled:
                enabled_fields.append(field_path)
                configs.append(config)

        if not enabled_fields:
            return

        for config in configs:
            view.add_chart_field(config)

        plot_data = self._data_manager.get_plot_data_batch(enabled_fields)
        view.update_all_chart_data(plot_data)

    def refresh_all_charts(self) -> None:
        """刷新所有启用字段的图表数据"""
        view = self._get_view()
        if not view:
            return

        configs = self._data_manager.get_enabled_field_configs()
        field_paths = [c.field_path for c in configs]
        plot_data = self._data_manager.get_plot_data_batch(field_paths)

        view.update_all_chart_data(plot_data)
        view.update_data_count(self._data_manager.data_count)

    def _refresh_field_data(self, field_path: str) -> None:
        """刷新单个字段的图表数据"""
        view = self._get_view()
        if not view:
            return

        config = self._data_manager.get_field_config(field_path)
        if not config or not config.enabled:
            return

        view.add_chart_field(config)
        timestamps, values = self._data_manager.get_plot_data(field_path)
        view.update_chart_data(field_path, timestamps, values)

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

    def _get_view(self):
        """返回 View 接口实例"""
        return self._view
