"""
文件名称: server_panel.py
内容摘要: TCP 服务端页面组件（MVP 模式中的 View 实现）
当前版本: v2.1.0
作者: lanford
创建日期: 2025-01-10
修改日期: 2026-02-09
修改说明: 添加波形监控窗口集成
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QSplitter, QHeaderView, QMessageBox, QAbstractItemView, QCompleter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject, QStringListModel
from PySide6.QtGui import QFont, QColor

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tcp_log.tcp_server import TcpLogServer
from tcp_log.models.tcp_server_model import TcpServerModel, EntryData, StatsData, CmdStatsItem


class SignalBridge(QObject):
    """信号桥接，用于线程间通信"""
    state_changed = Signal(str)
    client_connected = Signal(object)
    client_disconnected = Signal()
    entry_received = Signal(object)
    log_message = Signal(str)
    error_message = Signal(str)


class TcpServerPage(QWidget):
    """
    TCP 服务端页面 - MVP 模式中的 View 实现

    职责：
    - UI 组件的创建和布局
    - 将用户交互事件转发给 Presenter
    - 实现 ITcpServerPageView 接口供 Presenter 更新 UI
    """

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)
    # 信号：已解析数据转发（供波形窗口使用）
    entry_parsed = Signal(str, object, object, object, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presenter = None  # 由外部注入

        # 创建基础设施（服务器 + 信号桥接）
        self._server = TcpLogServer()
        self._signal_bridge = SignalBridge()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 设置等宽字体
        mono_font = QFont("Consolas", 9)

        # === 服务器配置组 ===
        server_group = QGroupBox("服务器配置")
        server_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        server_layout = QHBoxLayout(server_group)

        server_layout.addWidget(QLabel("监听地址:"))
        self._host_input = QLineEdit("0.0.0.0")
        self._host_input.setFixedWidth(120)
        server_layout.addWidget(self._host_input)

        server_layout.addWidget(QLabel("端口:"))
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(9999)
        self._port_input.setFixedWidth(80)
        server_layout.addWidget(self._port_input)

        server_layout.addWidget(QLabel("协议:"))
        self._protocol_combo = QComboBox()
        self._protocol_combo.setEditable(True)
        self._protocol_combo.setInsertPolicy(QComboBox.NoInsert)
        self._protocol_combo.setMinimumWidth(150)

        self._protocol_completer = QCompleter()
        self._protocol_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._protocol_completer.setFilterMode(Qt.MatchContains)
        self._protocol_combo.setCompleter(self._protocol_completer)

        server_layout.addWidget(self._protocol_combo)

        self._start_btn = QPushButton("启动服务")
        self._start_btn.setFixedWidth(80)
        server_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("停止服务")
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        server_layout.addWidget(self._stop_btn)

        # 波形监控按钮
        self._wave_btn = QPushButton("波形")
        self._wave_btn.setFixedWidth(60)
        self._wave_btn.setToolTip("打开实时波形监控窗口")
        self._wave_btn.clicked.connect(self._open_wave_window)
        server_layout.addWidget(self._wave_btn)

        # 历史波形按钮
        self._history_wave_btn = QPushButton("历史")
        self._history_wave_btn.setFixedWidth(60)
        self._history_wave_btn.setToolTip("打开历史波形分析窗口")
        self._history_wave_btn.clicked.connect(self._open_history_wave_window)
        server_layout.addWidget(self._history_wave_btn)

        server_layout.addStretch()

        self._status_label = QLabel("状态: ● 已停止")
        self._status_label.setStyleSheet("color: gray;")
        server_layout.addWidget(self._status_label)

        layout.addWidget(server_group)

        # === 主分割器（左右布局）===
        main_splitter = QSplitter(Qt.Horizontal)

        # === 左侧：实时解析组 ===
        parse_group = QGroupBox("实时解析")
        parse_layout = QVBoxLayout(parse_group)

        # 过滤选项
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("过滤:"))
        self._filter_combo = QComboBox()
        self._filter_combo.setEditable(True)
        self._filter_combo.setInsertPolicy(QComboBox.NoInsert)
        self._filter_combo.addItem("全部命令")
        self._filter_combo.setMinimumWidth(120)

        self._filter_completer = QCompleter()
        self._filter_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._filter_completer.setFilterMode(Qt.MatchContains)
        self._filter_combo.setCompleter(self._filter_completer)

        filter_layout.addWidget(self._filter_combo)

        self._success_only_check = QCheckBox("仅成功")
        filter_layout.addWidget(self._success_only_check)

        self._auto_scroll_check = QCheckBox("自动滚动")
        self._auto_scroll_check.setChecked(True)
        filter_layout.addWidget(self._auto_scroll_check)

        filter_layout.addStretch()

        self._clear_table_btn = QPushButton("清空")
        self._clear_table_btn.setMinimumWidth(60)
        filter_layout.addWidget(self._clear_table_btn)

        parse_layout.addLayout(filter_layout)

        # 解析结果表格
        self._result_table = QTableWidget()
        self._result_table.setColumnCount(5)
        self._result_table.setHorizontalHeaderLabels(["时间", "方向", "CMD", "终端ID", "摘要"])
        self._result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._result_table.setColumnWidth(0, 90)
        self._result_table.setColumnWidth(1, 50)
        self._result_table.setColumnWidth(2, 60)
        self._result_table.setColumnWidth(3, 60)
        self._result_table.verticalHeader().setDefaultSectionSize(26)
        self._result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.setFont(mono_font)
        parse_layout.addWidget(self._result_table)

        main_splitter.addWidget(parse_group)

        # === 右侧：详情组 ===
        detail_group = QGroupBox("详情")
        detail_layout = QVBoxLayout(detail_group)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setFont(mono_font)
        self._detail_text.setMinimumWidth(250)
        detail_layout.addWidget(self._detail_text)

        detail_btn_layout = QHBoxLayout()
        detail_btn_layout.addStretch()
        self._copy_detail_btn = QPushButton("复制")
        self._copy_detail_btn.setMinimumWidth(60)
        self._copy_detail_btn.clicked.connect(self._copy_detail)
        detail_btn_layout.addWidget(self._copy_detail_btn)
        detail_layout.addLayout(detail_btn_layout)

        main_splitter.addWidget(detail_group)

        main_splitter.setSizes([450, 300])
        layout.addWidget(main_splitter)

        # === 统计组 ===
        stats_group = QGroupBox("统计")
        stats_main_layout = QVBoxLayout(stats_group)

        stats_summary_layout = QHBoxLayout()

        self._stats_label = QLabel("总计: 0 条  |  成功: 0  |  失败: 0")
        stats_summary_layout.addWidget(self._stats_label)

        self._cache_label = QLabel("缓存: 0/10000")
        self._cache_label.setStyleSheet("color: #888;")
        stats_summary_layout.addWidget(self._cache_label)

        stats_summary_layout.addWidget(QLabel("缓存上限:"))
        self._cache_size_spin = QSpinBox()
        self._cache_size_spin.setRange(1000, 100000)
        self._cache_size_spin.setSingleStep(1000)
        self._cache_size_spin.setValue(TcpServerModel.DEFAULT_MAX_CACHE)
        self._cache_size_spin.setSuffix(" 条")
        self._cache_size_spin.setFixedWidth(120)
        self._cache_size_spin.setToolTip("TCP报文缓存上限（调整后立即生效）")
        stats_summary_layout.addWidget(self._cache_size_spin)

        stats_summary_layout.addStretch()

        self._toggle_stats_btn = QPushButton("展开详情 ▼")
        self._toggle_stats_btn.setMinimumWidth(100)
        self._toggle_stats_btn.setCheckable(True)
        stats_summary_layout.addWidget(self._toggle_stats_btn)

        self._reset_stats_btn = QPushButton("重置统计")
        self._reset_stats_btn.setMinimumWidth(90)
        stats_summary_layout.addWidget(self._reset_stats_btn)

        stats_main_layout.addLayout(stats_summary_layout)

        self._stats_detail_table = QTableWidget()
        self._stats_detail_table.setColumnCount(4)
        self._stats_detail_table.setHorizontalHeaderLabels(["CMD", "命令名称", "接收次数", "成功率"])
        self._stats_detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._stats_detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._stats_detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._stats_detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._stats_detail_table.setColumnWidth(0, 60)
        self._stats_detail_table.setColumnWidth(2, 80)
        self._stats_detail_table.setColumnWidth(3, 80)
        self._stats_detail_table.verticalHeader().setDefaultSectionSize(26)
        self._stats_detail_table.setMinimumHeight(120)
        self._stats_detail_table.setMaximumHeight(180)
        self._stats_detail_table.setFont(mono_font)
        self._stats_detail_table.setVisible(False)
        stats_main_layout.addWidget(self._stats_detail_table)

        stats_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout.addWidget(stats_group)

        # === 日志保存选项 ===
        save_widget = QWidget()
        save_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        save_layout = QHBoxLayout(save_widget)
        save_layout.setContentsMargins(5, 5, 5, 5)

        self._save_log_check = QCheckBox("保存日志")
        save_layout.addWidget(self._save_log_check)

        self._save_result_check = QCheckBox("保存解析结果")
        save_layout.addWidget(self._save_result_check)

        self._save_path_label = QLabel(f"保存位置: {project_root / 'tcp_output'}")
        self._save_path_label.setStyleSheet("color: #888; font-size: 11px;")
        save_layout.addWidget(self._save_path_label)

        save_layout.addStretch()
        layout.addWidget(save_widget)

    def set_presenter(self, presenter) -> None:
        """
        注入 Presenter（MVP 组装时调用）

        Args:
            presenter: TcpServerPresenter 实例
        """
        self._presenter = presenter
        self._setup_connections()
        self._presenter.initialize()

    def _setup_connections(self):
        """连接 UI 信号到 Presenter 方法"""
        self._start_btn.clicked.connect(self._presenter.on_start_clicked)
        self._stop_btn.clicked.connect(self._presenter.on_stop_clicked)
        self._clear_table_btn.clicked.connect(self._presenter.on_clear_results)
        self._reset_stats_btn.clicked.connect(self._presenter.on_reset_stats)
        self._cache_size_spin.valueChanged.connect(
            self._presenter.on_cache_size_changed
        )

        self._result_table.itemSelectionChanged.connect(self._on_selection_changed)
        self._protocol_combo.currentTextChanged.connect(
            self._presenter.on_protocol_changed
        )
        self._filter_combo.currentTextChanged.connect(
            lambda _: self._presenter.on_filter_changed()
        )
        self._toggle_stats_btn.clicked.connect(self._on_toggle_stats)
        self._copy_detail_btn.clicked.connect(self._copy_detail)

        # 信号桥接 → Presenter
        self._signal_bridge.state_changed.connect(
            self._presenter.on_server_state_changed
        )
        self._signal_bridge.client_connected.connect(
            self._presenter.on_client_connected
        )
        self._signal_bridge.client_disconnected.connect(
            self._presenter.on_client_disconnected
        )
        self._signal_bridge.entry_received.connect(
            self._presenter.on_entry_received
        )
        self._signal_bridge.log_message.connect(
            self._presenter.on_log_message
        )
        self._signal_bridge.error_message.connect(
            self._presenter.on_error_message
        )

        # 设置服务器回调 → 信号桥接
        self._server.set_callbacks(
            on_state_changed=lambda s: self._signal_bridge.state_changed.emit(s.value),
            on_client_connected=lambda c: self._signal_bridge.client_connected.emit(c),
            on_client_disconnected=lambda: self._signal_bridge.client_disconnected.emit(),
            on_entry_received=lambda e: self._signal_bridge.entry_received.emit(e),
            on_log=lambda m: self._signal_bridge.log_message.emit(m),
            on_error=lambda m: self._signal_bridge.error_message.emit(m),
        )

    # ============== 内部 UI 事件（转发给 Presenter） ==============

    def _on_selection_changed(self):
        """表格选择改变 - 通知 Presenter"""
        rows = self._result_table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        item = self._result_table.item(row, 0)
        if item:
            entry_index = item.data(Qt.UserRole)
            if entry_index is not None:
                self._presenter.on_selection_changed(entry_index)

    def _on_toggle_stats(self):
        """切换统计详情 - 通知 Presenter"""
        is_visible = self._stats_detail_table.isVisible()
        self._stats_detail_table.setVisible(not is_visible)
        if not is_visible:
            self._toggle_stats_btn.setText("收起详情 ▲")
            self._presenter.on_toggle_stats_detail(True)
        else:
            self._toggle_stats_btn.setText("展开详情 ▼")

    def _copy_detail(self):
        """复制详情内容"""
        text = self._detail_text.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.status_changed.emit("已复制到剪贴板")

    # ============== ITcpServerPageView 接口实现 ==============

    def update_server_state(self, state_text: str) -> None:
        """更新服务器状态显示"""
        state_colors = {
            "已停止": ("#888888", False),
            "启动中": ("#FFA500", False),
            "监听中": ("#4CAF50", True),
            "已连接": ("#00CED1", True),
            "错误": ("#F44336", False),
        }
        color, running = state_colors.get(state_text, ("gray", False))
        self._status_label.setText(f"状态: ● {state_text}")
        self._status_label.setStyleSheet(f"color: {color};")
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._protocol_combo.setEnabled(not running)

    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return {
            "host": self._host_input.text().strip(),
            "port": self._port_input.value(),
        }

    def set_protocol_list(self, names: List[str]) -> None:
        """设置协议下拉列表"""
        # 暂时阻断信号，避免 addItems 时多次触发 on_protocol_changed
        self._protocol_combo.blockSignals(True)
        self._protocol_combo.clear()
        self._protocol_combo.addItems(names)
        model = QStringListModel(names)
        self._protocol_completer.setModel(model)
        self._protocol_combo.blockSignals(False)
        if names:
            # 恢复信号后再设置选中项，只触发一次
            self._protocol_combo.setCurrentIndex(0)

    def add_result_row(self, entry_data: EntryData, summary: str) -> None:
        """添加一行解析结果"""
        entry = entry_data.entry
        row = self._result_table.rowCount()
        self._result_table.insertRow(row)

        time_text = entry.timestamp.split()[-1] if ' ' in entry.timestamp else entry.timestamp
        time_item = QTableWidgetItem(time_text)
        self._result_table.setItem(row, 0, time_item)

        dir_item = QTableWidgetItem(entry.direction)
        dir_item.setTextAlignment(Qt.AlignCenter)
        self._result_table.setItem(row, 1, dir_item)

        cmd_item = QTableWidgetItem(str(entry.cmd_id))
        cmd_item.setTextAlignment(Qt.AlignCenter)
        self._result_table.setItem(row, 2, cmd_item)

        terminal_text = str(entry.terminal_id) if entry.terminal_id is not None else ""
        terminal_item = QTableWidgetItem(terminal_text)
        terminal_item.setTextAlignment(Qt.AlignCenter)
        self._result_table.setItem(row, 3, terminal_item)

        summary_item = QTableWidgetItem(summary)
        if not entry_data.success:
            summary_item.setForeground(QColor("red"))
        self._result_table.setItem(row, 4, summary_item)

        # 存储条目在 all_entries 中的索引，用于 Presenter 查询详情
        if self._presenter:
            entries = self._presenter._model.all_entries
            time_item.setData(Qt.UserRole, len(entries) - 1)

        if self._auto_scroll_check.isChecked():
            self._result_table.scrollToBottom()

    def remove_oldest_rows(self, count: int) -> None:
        """移除最旧的 N 行"""
        for _ in range(count):
            if self._result_table.rowCount() > 0:
                self._result_table.removeRow(0)

    def clear_result_table(self) -> None:
        """清空结果表格"""
        self._result_table.setRowCount(0)
        self._detail_text.clear()

    def refresh_result_table(
        self, entries: List[EntryData], summaries: List[str]
    ) -> None:
        """刷新整个结果表格"""
        self._result_table.setRowCount(0)
        for entry_data, summary in zip(entries, summaries):
            self.add_result_row(entry_data, summary)

    def show_entry_detail(self, detail_text: str) -> None:
        """显示条目详情"""
        self._detail_text.setText(detail_text)

    def update_stats_summary(self, stats: StatsData) -> None:
        """更新统计摘要"""
        self._stats_label.setText(
            f"📊 总计: {stats.entry_count} 条  |  "
            f"✅ 成功: {stats.success_count} ({stats.success_rate:.1f}%)  |  "
            f"❌ 失败: {stats.fail_count}  |  "
            f"📋 命令种类: {stats.cmd_count}"
        )
        if self._stats_detail_table.isVisible() and self._presenter:
            items = self._presenter._model.get_cmd_stats_detail()
            self.update_stats_detail(items)

    def update_stats_detail(self, items: List[CmdStatsItem]) -> None:
        """更新统计详情表格"""
        self._stats_detail_table.setRowCount(0)
        for item in items:
            row = self._stats_detail_table.rowCount()
            self._stats_detail_table.insertRow(row)

            cmd_item = QTableWidgetItem(f"cmd{item.cmd_id}")
            cmd_item.setTextAlignment(Qt.AlignCenter)
            self._stats_detail_table.setItem(row, 0, cmd_item)

            name_item = QTableWidgetItem(item.cmd_name)
            self._stats_detail_table.setItem(row, 1, name_item)

            count_item = QTableWidgetItem(str(item.total_count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self._stats_detail_table.setItem(row, 2, count_item)

            rate = item.success_rate
            rate_item = QTableWidgetItem(f"{rate:.1f}%")
            rate_item.setTextAlignment(Qt.AlignCenter)
            if rate >= 90:
                rate_item.setForeground(QColor("#4CAF50"))
            elif rate >= 50:
                rate_item.setForeground(QColor("#FF9800"))
            else:
                rate_item.setForeground(QColor("#F44336"))
            self._stats_detail_table.setItem(row, 3, rate_item)

    def update_cache_label(self, current: int, max_count: int) -> None:
        """更新缓存条数标签"""
        self._cache_label.setText(f"缓存: {current}/{max_count}")
        if current > max_count * 0.8:
            self._cache_label.setStyleSheet("color: #FFA500;")
        else:
            self._cache_label.setStyleSheet("color: #888;")

    def add_filter_option(self, cmd_text: str) -> None:
        """添加过滤选项（去重）"""
        for i in range(self._filter_combo.count()):
            if self._filter_combo.itemText(i) == cmd_text:
                return
        self._filter_combo.addItem(cmd_text)
        items = [self._filter_combo.itemText(i) for i in range(self._filter_combo.count())]
        model = QStringListModel(items)
        self._filter_completer.setModel(model)

    def get_filter_cmd(self) -> Optional[int]:
        """获取当前过滤的命令 ID"""
        text = self._filter_combo.currentText()
        if text == "全部命令" or not text:
            return None
        if text.startswith("cmd"):
            try:
                return int(text[3:])
            except ValueError:
                return None
        try:
            return int(text)
        except ValueError:
            return None

    def is_success_only(self) -> bool:
        """是否仅显示成功"""
        return self._success_only_check.isChecked()

    def is_auto_scroll(self) -> bool:
        """是否自动滚动"""
        return self._auto_scroll_check.isChecked()

    def reset_filter(self) -> None:
        """重置过滤器"""
        self._filter_combo.clear()
        self._filter_combo.addItem("全部命令")

    def is_save_log_enabled(self) -> bool:
        """是否启用日志保存"""
        return self._save_log_check.isChecked()

    def is_save_result_enabled(self) -> bool:
        """是否启用结果保存"""
        return self._save_result_check.isChecked()

    def show_warning(self, title: str, message: str) -> None:
        """显示警告对话框"""
        QMessageBox.warning(self, title, message)

    def emit_status_changed(self, message: str) -> None:
        """发送状态变化信号"""
        self.status_changed.emit(message)

    def emit_entry_parsed(
        self,
        timestamp_str: str,
        parsed_content: Optional[dict],
        cmd_id: Optional[int],
        direction: Optional[str],
        success: bool,
    ) -> None:
        """转发已解析的数据条目（供波形窗口使用）"""
        self.entry_parsed.emit(timestamp_str, parsed_content, cmd_id, direction, success)

    # ============== 波形窗口管理 ==============

    def _open_wave_window(self) -> None:
        """打开实时波形监控窗口"""
        if hasattr(self, '_wave_dialog') and self._wave_dialog and self._wave_dialog.isVisible():
            self._wave_dialog.raise_()
            self._wave_dialog.activateWindow()
            return

        from gui.wave.dialogs.real_time_wave_dialog import RealTimeWaveDialog
        from gui.wave.presenters.real_time_presenter import RealTimeWavePresenter
        from gui.wave.models.wave_data_manager import WaveDataManager

        protocol_config = None
        if self._presenter and hasattr(self._presenter, '_model'):
            protocol_config = self._presenter._model.current_protocol

        data_manager = WaveDataManager(protocol_config=protocol_config)
        self._wave_dialog = RealTimeWaveDialog(self)
        wave_presenter = RealTimeWavePresenter(
            view=self._wave_dialog,
            data_manager=data_manager,
        )
        self._wave_dialog.set_presenter(wave_presenter)

        # 连接已解析数据信号到波形 Presenter
        self._wave_connection = lambda ts, content, cmd, direction, success: (
            wave_presenter.on_entry_parsed(ts, content, cmd, direction)
            if success and content else None
        )
        self.entry_parsed.connect(self._wave_connection)
        self._wave_dialog.closed.connect(self._on_wave_dialog_closed)
        self._wave_dialog.show()

    def _on_wave_dialog_closed(self) -> None:
        """波形窗口关闭回调"""
        # 断开信号连接，避免内存泄漏
        if hasattr(self, '_wave_connection') and self._wave_connection:
            try:
                self.entry_parsed.disconnect(self._wave_connection)
            except RuntimeError:
                pass
            self._wave_connection = None
        self._wave_dialog = None

    def _open_history_wave_window(self) -> None:
        """打开历史波形分析窗口（纯文件加载模式，支持.log和JSON回放）"""
        if hasattr(self, '_history_wave_dialog') and self._history_wave_dialog and self._history_wave_dialog.isVisible():
            self._history_wave_dialog.raise_()
            self._history_wave_dialog.activateWindow()
            return

        from gui.wave.dialogs.history_wave_dialog import HistoryWaveDialog
        from gui.wave.presenters.history_presenter import HistoryWavePresenter
        from gui.wave.models.wave_data_manager import WaveDataManager

        # 获取当前协议配置（用于解析.log文件）
        protocol_config = None
        if self._presenter and hasattr(self._presenter, '_model'):
            protocol_config = self._presenter._model.current_protocol

        data_manager = WaveDataManager(protocol_config=protocol_config)
        self._history_wave_dialog = HistoryWaveDialog(self)
        history_presenter = HistoryWavePresenter(
            view=self._history_wave_dialog,
            data_manager=data_manager,
            protocol_config=protocol_config,
        )
        self._history_wave_dialog.set_presenter(history_presenter)

        self._history_wave_dialog.closed.connect(self._on_history_wave_dialog_closed)
        self._history_wave_dialog.show()

    def _on_history_wave_dialog_closed(self) -> None:
        """历史波形窗口关闭回调"""
        self._history_wave_dialog = None

    def cleanup(self) -> None:
        """清理资源（停止服务器线程）"""
        # 关闭波形窗口
        if hasattr(self, '_wave_dialog') and self._wave_dialog:
            self._wave_dialog.close()
        if hasattr(self, '_history_wave_dialog') and self._history_wave_dialog:
            self._history_wave_dialog.close()

        if self._server and self._server.is_running:
            self._server.stop()
