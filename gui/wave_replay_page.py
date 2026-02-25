"""
文件名称: wave_replay_page.py
内容摘要: 数据回放页面 - 独立一级页面，支持多数据源的波形回放（MVP View）
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-11
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig
from gui.wave.views.wave_view_mixin import WaveViewMixin
from gui.wave.widgets.field_tree_widget import FieldTreeWidget
from gui.wave.widgets.wave_chart_widget import WaveChartWidget

logger = logging.getLogger(__name__)


class WaveReplayPage(WaveViewMixin, QWidget):
    """
    数据回放页面 - 独立一级页面

    支持的数据源（均不依赖YAML协议配置）：
    1. 波形JSON文件导入
    2. TCP服务器解析结果
    3. 普通解析结果

    实现 IHistoryWaveView 接口。

    UI布局：
    ┌────────────────────────────────────────────────┐
    │ 数据源: [下拉] | 导入JSON | 导出▼ | 自动缩放  │
    │                              数据: N条         │
    ├──────────────┬─────────────────────────────────┤
    │ 字段树       │ 波形图                          │
    │ ├ CMD 4      │ [多字段波形叠加]                │
    │ │ ├ 电压     │                                 │
    │ │ └ 电流     │                                 │
    │ └ CMD 5      │                                 │
    │   └ 功率     │                                 │
    ├──────────────┴─────────────────────────────────┤
    │ 状态栏                                         │
    └────────────────────────────────────────────────┘
    """

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._presenter = None

        self._setup_ui()

    def set_presenter(self, presenter) -> None:
        """
        注入 Presenter（MVP 组装时调用）

        Args:
            presenter: ReplayPresenter 实例
        """
        self._presenter = presenter
        self._connect_signals()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # === 工具栏 ===
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 0)

        # 数据源标签
        toolbar.addWidget(QLabel("数据源:"))
        self._source_combo = QComboBox()
        self._source_combo.addItems(["波形JSON", "TCP解析结果", "普通解析结果"])
        self._source_combo.setToolTip("选择数据源类型（导入JSON时自动切换）")
        toolbar.addWidget(self._source_combo)

        toolbar.addSpacing(8)

        # 导入JSON按钮
        self._import_btn = QPushButton("导入JSON")
        self._import_btn.clicked.connect(self._on_import_json)
        toolbar.addWidget(self._import_btn)

        # 导出按钮（带下拉菜单）
        self._export_btn = QPushButton("导出数据")
        export_menu = QMenu(self)
        export_menu.addAction("导出为 JSON", self._on_export_json)
        export_menu.addAction("导出为 CSV", self._on_export_csv)
        self._export_btn.setMenu(export_menu)
        self._export_btn.setEnabled(False)
        toolbar.addWidget(self._export_btn)

        toolbar.addSpacing(8)

        # 自动缩放按钮
        self._auto_range_btn = QPushButton("自动缩放")
        self._auto_range_btn.clicked.connect(self._on_auto_range)
        toolbar.addWidget(self._auto_range_btn)

        # 清空数据按钮
        self._clear_btn = QPushButton("清空")
        self._clear_btn.clicked.connect(self._on_clear_data)
        toolbar.addWidget(self._clear_btn)

        toolbar.addStretch()

        # 数据计数
        self._data_count_label = QLabel("数据: 0 条")
        self._data_count_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self._data_count_label)

        layout.addLayout(toolbar)

        # === 主内容区（左右分栏）===
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：字段树区域（包含复选框和树）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        # 字段树工具栏
        tree_toolbar = QHBoxLayout()
        tree_toolbar.setContentsMargins(4, 2, 4, 2)

        # 全选复选框
        self._select_all_checkbox = QCheckBox("全选")
        self._select_all_checkbox.setTristate(True)  # 启用三态
        self._select_all_checkbox.setCheckState(Qt.Unchecked)
        self._select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        self._select_all_checkbox.setToolTip("全选/取消全选所有字段")
        tree_toolbar.addWidget(self._select_all_checkbox)

        tree_toolbar.addStretch()
        left_layout.addLayout(tree_toolbar)

        # 字段树
        self._field_tree = FieldTreeWidget()
        left_layout.addWidget(self._field_tree)

        left_panel.setMinimumWidth(180)
        left_panel.setMaximumWidth(280)
        splitter.addWidget(left_panel)

        # 右侧：波形图
        self._chart = WaveChartWidget()
        splitter.addWidget(self._chart)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 700])

        layout.addWidget(splitter, 1)

        # === 状态栏 ===
        self._status_bar = QStatusBar()
        self._status_bar.showMessage('就绪 - 点击"导入JSON"或从其他页面加载数据')
        layout.addWidget(self._status_bar)

    def _connect_signals(self) -> None:
        """连接 UI 信号到 Presenter"""
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
        # 选中状态变化 → 更新全选复选框
        self._field_tree.selection_changed.connect(self.update_select_all_state)

    # ============== UI事件 ==============

    def _on_import_json(self) -> None:
        """导入JSON数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入波形数据",
            "",
            "JSON 文件 (*.json)",
        )
        if file_path and self._presenter:
            self._source_combo.setCurrentText("波形JSON")
            self._presenter.import_from_json(file_path)

    def _on_export_json(self) -> None:
        """导出为JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 JSON",
            "wave_data.json",
            "JSON 文件 (*.json)",
        )
        if file_path and self._presenter:
            self._presenter.on_export_json(file_path)

    def _on_export_csv(self) -> None:
        """导出为CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 CSV",
            "wave_data.csv",
            "CSV 文件 (*.csv)",
        )
        if file_path and self._presenter:
            self._presenter.on_export_csv(file_path)

    def _on_auto_range(self) -> None:
        """自动缩放：X轴展示全部数据，Y轴适配值范围"""
        self._chart.auto_fit_all()

    def _on_select_all_changed(self, state: int) -> None:
        """
        全选复选框状态变化

        Args:
            state: Qt.CheckState 值（Unchecked=0, PartiallyChecked=1, Checked=2）
        """
        # 阻断信号避免循环
        self._select_all_checkbox.blockSignals(True)

        # 注意：state 是 int 类型，需要与枚举值比较
        if state == Qt.Checked.value:
            # 全选
            self._field_tree.select_all()
            self._select_all_checkbox.setCheckState(Qt.Checked)
        elif state == Qt.Unchecked.value:
            # 取消全选
            self._field_tree.deselect_all()
            self._select_all_checkbox.setCheckState(Qt.Unchecked)
        # PartiallyChecked 时不做操作（由外部更新）

        self._select_all_checkbox.blockSignals(False)

    def update_select_all_state(self, total: int, selected: int) -> None:
        """
        更新全选复选框状态

        Args:
            total: 总字段数
            selected: 已选中字段数
        """
        self._select_all_checkbox.blockSignals(True)
        if selected == 0:
            self._select_all_checkbox.setCheckState(Qt.Unchecked)
        elif selected == total:
            self._select_all_checkbox.setCheckState(Qt.Checked)
        else:
            self._select_all_checkbox.setCheckState(Qt.PartiallyChecked)
        self._select_all_checkbox.blockSignals(False)

    def _on_clear_data(self) -> None:
        """清空数据（委托给 Presenter 执行完整清理）"""
        if self._presenter:
            self._presenter.on_clear_data()

    # ============== 外部数据注入接口 ==============

    def load_entries(
        self,
        entries: List[Tuple[str, Optional[Dict[str, Any]], Optional[int], Optional[str]]],
        source_name: str = "外部数据",
    ) -> int:
        """
        从外部注入解析条目（供主窗口调用）

        Args:
            entries: 列表，每项为 (timestamp_str, parsed_content, cmd_id, direction)
            source_name: 数据源名称

        Returns:
            成功加载的数据点数量
        """
        if not self._presenter:
            return 0

        # 更新数据源下拉框
        if "TCP" in source_name:
            self._source_combo.setCurrentText("TCP解析结果")
        elif "解析" in source_name:
            self._source_combo.setCurrentText("普通解析结果")

        return self._presenter.load_from_entries(entries, source_name)

    # ============== IHistoryWaveView 接口实现（公共部分由 WaveViewMixin 提供） ==============

    def refresh_field_tree(self, configs: List[FieldConfig], expand_all: bool = True) -> None:
        """刷新整个字段树（覆写：额外更新全选复选框状态）"""
        super().refresh_field_tree(configs, expand_all)
        total = len(configs)
        selected = sum(1 for c in configs if c.enabled)
        self.update_select_all_state(total, selected)

    def emit_status_changed(self, message: str) -> None:
        """发送状态变化信号"""
        self.status_changed.emit(message)

    def cleanup(self) -> None:
        """清理资源"""
        pass
