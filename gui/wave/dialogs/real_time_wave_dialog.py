"""
文件名称: real_time_wave_dialog.py
内容摘要: 实时波形监控窗口，从TCP服务端持续接收数据并动态更新波形
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig
from gui.wave.widgets.field_tree_widget import FieldTreeWidget
from gui.wave.widgets.wave_chart_widget import WaveChartWidget

logger = logging.getLogger(__name__)

# 时间窗口选项
_TIME_WINDOW_OPTIONS = [
    ("30秒", 30.0),
    ("1分钟", 60.0),
    ("2分钟", 120.0),
    ("5分钟", 300.0),
    ("10分钟", 600.0),
    ("全部", 0.0),  # 0 表示显示全部数据
]


class RealTimeWaveDialog(QDialog):
    """
    实时波形监控窗口

    实现 IRealTimeWaveView 接口。

    UI布局：
    ┌─────────────────────────────────────┐
    │ 暂停 | 时间窗口: 1分钟 | 数据: N条  │
    ├──────────────┬──────────────────────┤
    │ 字段树       │ 波形图               │
    │ ├ CMD 4      │ [多字段波形叠加]     │
    │ │ ├ 电压     │                      │
    │ │ └ 电流     │                      │
    │ └ CMD 5      │                      │
    │   └ 功率     │                      │
    ├──────────────┴──────────────────────┤
    │ 状态栏                              │
    └─────────────────────────────────────┘
    """

    # 信号：窗口关闭
    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._presenter = None

        self._setup_ui()

    def set_presenter(self, presenter) -> None:
        """
        注入 Presenter

        Args:
            presenter: RealTimeWavePresenter 实例
        """
        self._presenter = presenter
        self._connect_signals()
        self._presenter.start()

    def _setup_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("实时波形监控")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        # 允许独立窗口
        self.setWindowFlags(
            Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # === 工具栏 ===
        toolbar = QHBoxLayout()

        # 暂停/继续按钮
        self._pause_btn = QPushButton("⏸ 暂停")
        self._pause_btn.setFixedWidth(80)
        self._pause_btn.setCheckable(True)
        toolbar.addWidget(self._pause_btn)

        toolbar.addWidget(QLabel("时间窗口:"))

        # 时间窗口选择
        self._time_window_combo = QComboBox()
        self._time_window_combo.setFixedWidth(100)
        for label, _ in _TIME_WINDOW_OPTIONS:
            self._time_window_combo.addItem(label)
        # 默认选择 "1分钟"
        self._time_window_combo.setCurrentIndex(1)
        toolbar.addWidget(self._time_window_combo)

        toolbar.addStretch()

        # 数据计数
        self._data_count_label = QLabel("数据: 0 条")
        self._data_count_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self._data_count_label)

        layout.addLayout(toolbar)

        # === 主内容区（左右分栏）===
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：字段树
        self._field_tree = FieldTreeWidget()
        self._field_tree.setMinimumWidth(180)
        self._field_tree.setMaximumWidth(280)
        splitter.addWidget(self._field_tree)

        # 右侧：波形图
        self._chart = WaveChartWidget()
        splitter.addWidget(self._chart)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 700])

        layout.addWidget(splitter, 1)

        # === 状态栏 ===
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("就绪")
        layout.addWidget(self._status_bar)

    def _connect_signals(self) -> None:
        """连接 UI 信号到 Presenter"""
        self._pause_btn.toggled.connect(self._on_pause_toggled)
        self._time_window_combo.currentIndexChanged.connect(
            self._on_time_window_changed
        )

        # 字段树信号
        self._field_tree.field_enabled_changed.connect(
            self._presenter.on_field_enabled_changed
        )
        self._field_tree.field_color_changed.connect(
            self._presenter.on_field_color_changed
        )
        self._field_tree.field_removed.connect(
            self._presenter.on_remove_field
        )
        self._field_tree.field_renamed.connect(
            self._presenter.on_field_renamed
        )

    # ============== UI事件 ==============

    def _on_pause_toggled(self, checked: bool) -> None:
        """暂停/继续切换"""
        if self._presenter:
            self._presenter.on_pause_toggled(checked)

    def _on_time_window_changed(self, index: int) -> None:
        """时间窗口变更"""
        if self._presenter and 0 <= index < len(_TIME_WINDOW_OPTIONS):
            _, seconds = _TIME_WINDOW_OPTIONS[index]
            if seconds <= 0:
                # "全部" 选项：设置一个很大的时间窗口
                seconds = 86400.0  # 24小时
            self._presenter.on_time_window_changed(seconds)

    # ============== IRealTimeWaveView 接口实现 ==============

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

    def add_field_to_tree(self, config: FieldConfig) -> None:
        """添加字段到字段树"""
        self._field_tree.add_field(config)

    def remove_field_from_tree(self, field_path: str) -> None:
        """从字段树移除字段"""
        self._field_tree.remove_field(field_path)

    def update_field_in_tree(self, config: FieldConfig) -> None:
        """更新字段树中的字段配置"""
        self._field_tree.update_field(config)

    def refresh_field_tree(self, configs: List[FieldConfig]) -> None:
        """刷新整个字段树"""
        self._field_tree.refresh(configs)

    @Slot(str)
    def update_status(self, message: str) -> None:
        """更新状态栏"""
        self._status_bar.showMessage(message)

    @Slot(int)
    def update_data_count(self, count: int) -> None:
        """更新数据点计数"""
        self._data_count_label.setText(f"数据: {count} 条")

    def set_paused(self, paused: bool) -> None:
        """设置暂停状态"""
        self._pause_btn.blockSignals(True)
        self._pause_btn.setChecked(paused)
        self._pause_btn.setText("▶ 继续" if paused else "⏸ 暂停")
        self._pause_btn.blockSignals(False)

    def set_time_window(self, seconds: float) -> None:
        """设置显示时间窗口"""
        # 不需要额外操作，UI已通过combo更新
        pass

    def scroll_to_latest(self) -> None:
        """滚动到最新数据"""
        self._chart.scroll_to_latest()

    def set_x_range(self, x_min: float, x_max: float) -> None:
        """设置X轴显示范围（时间窗口控制）"""
        self._chart.set_x_range(x_min, x_max)

    # ============== 窗口事件 ==============

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        if self._presenter:
            self._presenter.cleanup()
        self.closed.emit()
        super().closeEvent(event)
