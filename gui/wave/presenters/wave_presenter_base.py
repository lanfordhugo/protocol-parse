"""
文件名称: wave_presenter_base.py
内容摘要: 波形 Presenter 基类，封装实时和历史模式共享的业务逻辑
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from typing import Any, Dict, List, Optional

from gui.wave.models.wave_data_manager import (
    FieldConfig,
    WaveDataManager,
)
from gui.wave.utils.field_type_detector import FieldType, FieldTypeDetector
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper

logger = logging.getLogger(__name__)


class WavePresenterBase:
    """
    波形 Presenter 基类

    职责：
    - 管理 WaveDataManager 和 View 的交互
    - 字段添加/删除/配置变更的业务逻辑
    - 图表数据刷新

    子类需实现：
    - _get_view(): 返回具体的 View 接口实例
    """

    def __init__(self, data_manager: Optional[WaveDataManager] = None, **kwargs):
        """
        初始化基类

        支持协作式多重继承（与 QObject 兼容）。
        data_manager 设为可选参数以适配 Python MRO。

        Args:
            data_manager: 波形数据管理器
            **kwargs: 传递给 super().__init__() 的额外参数
        """
        super().__init__(**kwargs)
        self._data_manager = data_manager
        self._type_detector = FieldTypeDetector()

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
    ) -> Optional[FieldConfig]:
        """
        添加字段到监控

        Args:
            field_path: 字段路径
            sample_value: 样本值（用于类型检测）
            cmd_id: 命令ID
            display_name: 自定义显示名称

        Returns:
            创建的字段配置，失败返回 None
        """
        # 检查是否已存在
        existing = self._data_manager.get_field_config(field_path)
        if existing:
            logger.info("字段 %s 已在监控中", field_path)
            return existing

        # 检测类型
        field_type = self._type_detector.detect(sample_value)
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
            self._refresh_field_data(field_path)
        else:
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

    def refresh_all_charts(self) -> None:
        """刷新所有启用字段的图表数据"""
        view = self._get_view()
        if not view:
            return

        configs = self._data_manager.get_enabled_field_configs()
        plot_data = {}

        for config in configs:
            timestamps, values = self._data_manager.get_plot_data(config.field_path)
            plot_data[config.field_path] = (timestamps, values)

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

    # ============== 子类需实现 ==============

    def _get_view(self):
        """
        返回 View 接口实例

        子类必须实现此方法。

        Returns:
            IWaveViewBase 实例
        """
        raise NotImplementedError("子类必须实现 _get_view()")
