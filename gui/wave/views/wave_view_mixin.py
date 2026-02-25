"""
文件名称: wave_view_mixin.py
内容摘要: 波形 View 公共实现混入类，封装三个 View 实现中重复的 IWaveViewBase 接口委托
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-25
"""

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMessageBox

from gui.wave.models.wave_data_manager import FieldConfig


class WaveViewMixin:
    """
    波形 View 公共实现混入类

    封装 IWaveViewBase 接口中所有 View 实现完全一致的委托方法。
    要求宿主类具有以下属性：
    - self._chart: WaveChartWidget 实例
    - self._field_tree: FieldTreeWidget 实例
    - self._status_bar: QStatusBar 实例
    - self._data_count_label: QLabel 实例
    """

    # ============== 图表操作 ==============

    def add_chart_field(self, config: FieldConfig) -> None:
        """添加字段到图表"""
        self._chart.add_field(config)

    def remove_chart_field(self, field_path: str) -> None:
        """从图表移除字段"""
        self._chart.remove_field(field_path)

    def update_chart_data(
        self,
        field_path: str,
        timestamps: List[float],
        values: List[Optional[float]],
    ) -> None:
        """更新指定字段的图表数据"""
        self._chart.update_data(field_path, timestamps, values)

    def update_all_chart_data(
        self,
        plot_data: Dict[str, Tuple[List[float], List[Optional[float]]]],
    ) -> None:
        """批量更新所有字段的图表数据"""
        self._chart.update_all_data(plot_data)

    def clear_chart(self) -> None:
        """清空图表"""
        self._chart.clear()

    # ============== 字段树操作 ==============

    def add_field_to_tree(self, config: FieldConfig) -> None:
        """添加字段到字段树"""
        self._field_tree.add_field(config)

    def remove_field_from_tree(self, field_path: str) -> None:
        """从字段树移除字段"""
        self._field_tree.remove_field(field_path)

    def update_field_in_tree(self, config: FieldConfig) -> None:
        """更新字段树中的字段配置"""
        self._field_tree.update_field(config)

    def refresh_field_tree(self, configs: List[FieldConfig], expand_all: bool = True) -> None:
        """刷新整个字段树"""
        self._field_tree.refresh(configs, expand_all)

    # ============== 状态显示 ==============

    @Slot(str)
    def update_status(self, message: str) -> None:
        """更新状态栏"""
        self._status_bar.showMessage(message)

    @Slot(int)
    def update_data_count(self, count: int) -> None:
        """更新数据点计数"""
        self._data_count_label.setText(f"数据: {count} 条")

    # ============== 导出相关 ==============

    def set_export_enabled(self, enabled: bool) -> None:
        """设置导出按钮启用状态"""
        self._export_btn.setEnabled(enabled)

    def show_export_result(self, success: bool, file_path: str) -> None:
        """显示导出结果"""
        if success:
            QMessageBox.information(
                self,
                "导出成功",
                f"数据已导出到:\n{file_path}",
            )
        else:
            QMessageBox.warning(
                self,
                "导出失败",
                f"导出失败: {file_path}",
            )

    def set_time_range_limits(self, start: float, end: float) -> None:
        """设置时间范围选择器的范围限制"""
        self._chart.set_x_range(start, end)
