"""
文件名称: i_wave_view.py
内容摘要: 波形窗口 View 接口定义（MVP 模式中的 V 接口）
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable

from gui.wave.models.wave_data_manager import FieldConfig


@runtime_checkable
class IWaveViewBase(Protocol):
    """
    波形窗口基础 View 接口

    定义实时和历史波形窗口共享的 View 操作。
    使用 Protocol 而非 ABC，避免与 QWidget Shiboken 元类冲突。
    """

    # ============== 图表操作 ==============

    def add_chart_field(self, config: FieldConfig) -> None:
        """添加字段到图表"""
        ...

    def remove_chart_field(self, field_path: str) -> None:
        """从图表移除字段"""
        ...

    def update_chart_data(
        self,
        field_path: str,
        timestamps: List[float],
        values: List[Optional[float]],
    ) -> None:
        """更新指定字段的图表数据"""
        ...

    def update_all_chart_data(
        self,
        plot_data: Dict[str, Tuple[List[float], List[Optional[float]]]],
    ) -> None:
        """批量更新所有字段的图表数据"""
        ...

    def clear_chart(self) -> None:
        """清空图表"""
        ...

    # ============== 字段树操作 ==============

    def add_field_to_tree(self, config: FieldConfig) -> None:
        """添加字段到字段树"""
        ...

    def remove_field_from_tree(self, field_path: str) -> None:
        """从字段树移除字段"""
        ...

    def update_field_in_tree(self, config: FieldConfig) -> None:
        """更新字段树中的字段配置"""
        ...

    def refresh_field_tree(self, configs: List[FieldConfig]) -> None:
        """刷新整个字段树"""
        ...

    # ============== 状态显示 ==============

    def update_status(self, message: str) -> None:
        """更新状态栏消息"""
        ...

    def update_data_count(self, count: int) -> None:
        """更新数据点计数显示"""
        ...


@runtime_checkable
class IRealTimeWaveView(IWaveViewBase, Protocol):
    """
    实时波形窗口 View 接口

    在基础接口上增加实时模式特有的操作。
    """

    def set_paused(self, paused: bool) -> None:
        """设置暂停/继续状态"""
        ...

    def set_time_window(self, seconds: float) -> None:
        """设置显示时间窗口"""
        ...

    def scroll_to_latest(self) -> None:
        """滚动到最新数据"""
        ...

    def set_x_range(self, x_min: float, x_max: float) -> None:
        """设置X轴显示范围（时间窗口控制）"""
        ...


@runtime_checkable
class IHistoryWaveView(IWaveViewBase, Protocol):
    """
    历史波形窗口 View 接口

    在基础接口上增加历史模式特有的操作。
    """

    def set_time_range_limits(
        self,
        start: float,
        end: float,
    ) -> None:
        """设置时间范围选择器的范围限制"""
        ...

    def set_export_enabled(self, enabled: bool) -> None:
        """设置导出按钮的启用状态"""
        ...

    def show_export_result(self, success: bool, file_path: str) -> None:
        """显示导出结果提示"""
        ...
