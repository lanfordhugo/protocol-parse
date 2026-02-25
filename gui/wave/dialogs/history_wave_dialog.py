"""
文件名称: history_wave_dialog.py
内容摘要: 历史波形分析窗口，分析已解析的静态数据，支持时间范围选择和数据导出
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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


class HistoryWaveDialog(WaveViewMixin, QDialog):
    """
    历史波形分析窗口

    实现 IHistoryWaveView 接口。

    UI布局：
    ┌─────────────────────────────────────┐
    │ 导出数据 | 导入数据 | 数据: N条     │
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
            presenter: HistoryWavePresenter 实例
        """
        self._presenter = presenter
        self._connect_signals()

    def _setup_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("历史波形分析")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setWindowFlags(
            Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # === 工具栏 ===
        toolbar = QHBoxLayout()

        # 导出按钮（带下拉菜单）
        self._export_btn = QPushButton("导出数据")
        self._export_btn.setFixedWidth(90)
        export_menu = QMenu(self)
        export_menu.addAction("导出为 JSON", self._on_export_json)
        export_menu.addAction("导出为 CSV", self._on_export_csv)
        self._export_btn.setMenu(export_menu)
        self._export_btn.setEnabled(False)
        toolbar.addWidget(self._export_btn)

        # 导入JSON按钮
        self._import_btn = QPushButton("导入JSON")
        self._import_btn.setFixedWidth(90)
        self._import_btn.clicked.connect(self._on_import_json)
        toolbar.addWidget(self._import_btn)

        # 加载日志文件按钮
        self._load_log_btn = QPushButton("加载日志")
        self._load_log_btn.setFixedWidth(90)
        self._load_log_btn.setToolTip("加载 .log 文件进行波形回放")
        self._load_log_btn.clicked.connect(self._on_load_log_file)
        toolbar.addWidget(self._load_log_btn)

        # 自动缩放按钮
        self._auto_range_btn = QPushButton("自动缩放")
        self._auto_range_btn.setFixedWidth(80)
        self._auto_range_btn.clicked.connect(self._on_auto_range)
        toolbar.addWidget(self._auto_range_btn)

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
        self._status_bar.showMessage("就绪 - 点击“加载日志”或“导入JSON”加载数据")
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

    # ============== UI事件 ==============

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

    def _on_import_json(self) -> None:
        """导入JSON数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入波形数据",
            "",
            "JSON 文件 (*.json)",
        )
        if file_path and self._presenter:
            self._presenter.import_from_json(file_path)

    def _on_auto_range(self) -> None:
        """自动缩放"""
        self._chart.auto_range()

    def _on_load_log_file(self) -> None:
        """加载.log文件进行波形回放"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载日志文件",
            "",
            "日志文件 (*.log);;所有文件 (*)",
        )
        if file_path and self._presenter:
            self._presenter.load_from_log_file(file_path)

    # ============== IHistoryWaveView 接口实现（由 WaveViewMixin 提供） ==============

    # ============== 窗口事件 ==============

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        self.closed.emit()
        super().closeEvent(event)
