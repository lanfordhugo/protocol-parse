"""
文件名称: real_time_wave_dialog.py
内容摘要: 实时波形监控窗口，从TCP服务端持续接收数据并动态更新波形
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig, WaveDataManager
from gui.wave.views.wave_view_mixin import WaveViewMixin
from gui.wave.widgets.field_tree_widget import FieldTreeWidget
from gui.wave.widgets.wave_chart_widget import WaveChartWidget

logger = logging.getLogger(__name__)


class RealTimeWaveDialog(WaveViewMixin, QDialog):
    """
    实时波形监控窗口

    实现 IRealTimeWaveView 接口。

    UI布局：
    ┌──────────────────────────────────────────────────────────┐
    │ 暂停 | 跟踪 | 缓存 | [保存] [☑输出 filename] | N条 │
    ├──────────────┬───────────────────────────────────────────┤
    │ 字段树       │ 波形图（轴感知缩放 + 左键平移）   │
    │ ├ CMD 4      │ 悬浮吸附 Tooltip                   │
    │ │ ├ 电压     │                                  │
    │ │ └ 电流     │                                  │
    │ └ CMD 5      │                                  │
    │   └ 功率     │                                  │
    ├──────────────┴───────────────────────────────────────────┤
    │ 状态栏（显示自动输出文件名等）                      │
    └──────────────────────────────────────────────────────────┘
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

        # === 工具栏第1行：控制区 ===
        toolbar1 = QHBoxLayout()

        # 暂停/继续按钮
        self._pause_btn = QPushButton("⏸ 暂停")
        self._pause_btn.setFixedWidth(80)
        self._pause_btn.setCheckable(True)
        toolbar1.addWidget(self._pause_btn)

        # 跟踪最新按钮
        self._follow_btn = QPushButton("🔴 跟踪")
        self._follow_btn.setFixedWidth(80)
        self._follow_btn.setCheckable(True)
        self._follow_btn.setChecked(True)
        self._follow_btn.setToolTip("自动滚动跟踪最新数据（缩放/平移时自动关闭）")
        toolbar1.addWidget(self._follow_btn)

        toolbar1.addWidget(QLabel("缓存:"))
        self._wave_cache_spin = QSpinBox()
        self._wave_cache_spin.setRange(5000, 200000)
        self._wave_cache_spin.setSingleStep(5000)
        self._wave_cache_spin.setValue(WaveDataManager.DEFAULT_MAX_DATA_POINTS)
        self._wave_cache_spin.setSuffix(" 点")
        self._wave_cache_spin.setFixedWidth(120)
        self._wave_cache_spin.setToolTip("波形数据点缓存上限")
        toolbar1.addWidget(self._wave_cache_spin)

        toolbar1.addStretch()

        # 手动保存按钮
        self._save_btn = QPushButton("💾 保存")
        self._save_btn.setFixedWidth(80)
        self._save_btn.setToolTip("将缓存数据保存为 JSON 文件（弹出文件选择器）")
        toolbar1.addWidget(self._save_btn)

        # 自动输出勾选
        self._auto_output_check = QCheckBox("输出")
        self._auto_output_check.setToolTip("勾选后自动每秒将数据输出到文件")
        toolbar1.addWidget(self._auto_output_check)

        # 自动输出文件名
        self._output_filename = QLineEdit("wave_data")
        self._output_filename.setFixedWidth(140)
        self._output_filename.setPlaceholderText("输出文件名")
        self._output_filename.setToolTip("自动输出文件名（启动时追加日期后缀）")
        toolbar1.addWidget(self._output_filename)

        # 数据计数
        self._data_count_label = QLabel("数据: 0 条")
        self._data_count_label.setStyleSheet("color: #888;")
        toolbar1.addWidget(self._data_count_label)

        layout.addLayout(toolbar1)

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
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._follow_btn.toggled.connect(self._on_follow_toggled)
        self._auto_output_check.toggled.connect(self._on_auto_output_toggled)

        # 图表用户交互（缩放/平移）→ 关闭自动跟踪
        self._chart.user_interacted.connect(self._on_chart_user_interacted)

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

        # 波形缓存大小调整
        self._wave_cache_spin.valueChanged.connect(
            self._presenter.on_wave_cache_size_changed
        )

    # ============== UI事件 ==============

    def _on_pause_toggled(self, checked: bool) -> None:
        """暂停/继续切换"""
        if self._presenter:
            self._presenter.on_pause_toggled(checked)

    def _on_follow_toggled(self, checked: bool) -> None:
        """跟踪最新切换"""
        if self._presenter:
            self._presenter.on_auto_follow_changed(checked)

    def _on_save_clicked(self) -> None:
        """手动保存：弹出文件选择器"""
        if not self._presenter:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存波形数据", "wave_data.json",
            "JSON 文件 (*.json);;CSV 文件 (*.csv);;All Files (*)",
        )
        if file_path:
            self._presenter.on_save_data(file_path)

    def _on_auto_output_toggled(self, checked: bool) -> None:
        """自动输出开关"""
        if not self._presenter:
            return
        filename = self._output_filename.text().strip() or "wave_data"
        self._presenter.on_auto_output_toggled(checked, filename)
        # 勾选时禁止修改文件名
        self._output_filename.setEnabled(not checked)

    def _on_chart_user_interacted(self) -> None:
        """图表用户手动缩放/平移 → 关闭自动跟踪"""
        if self._presenter:
            self._presenter.on_user_interacted()

    # ============== IRealTimeWaveView 接口实现（公共部分由 WaveViewMixin 提供） ==============

    def set_paused(self, paused: bool) -> None:
        """设置暂停状态"""
        self._pause_btn.blockSignals(True)
        self._pause_btn.setChecked(paused)
        self._pause_btn.setText("▶ 继续" if paused else "⏸ 暂停")
        self._pause_btn.blockSignals(False)

    def set_auto_follow(self, follow: bool) -> None:
        """设置跟踪按钮状态"""
        self._follow_btn.blockSignals(True)
        self._follow_btn.setChecked(follow)
        self._follow_btn.setText("🔴 跟踪" if follow else "⚪ 跟踪")
        self._follow_btn.blockSignals(False)

    def show_save_result(self, success: bool, file_path: str, count: int) -> None:
        """显示保存结果"""
        if success:
            self._status_bar.showMessage(f"已保存 {count} 个数据点到 {file_path}")
        else:
            self._status_bar.showMessage(f"保存失败: {file_path}")

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
