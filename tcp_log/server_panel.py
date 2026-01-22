"""
文件名称: server_panel.py
内容摘要: TCP 服务端页面组件（嵌入统一窗口使用）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-10
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QSplitter, QHeaderView, QMessageBox, QAbstractItemView, QCompleter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject, QStringListModel
from PySide6.QtGui import QFont, QColor
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tcp_log.tcp_server import TcpLogServer, ClientInfo
from tcp_log.log_entry_parser import LogEntry
from src.yaml_cmdformat import YamlCmdFormat


class SignalBridge(QObject):
    """信号桥接，用于线程间通信"""
    state_changed = Signal(str)
    client_connected = Signal(object)
    client_disconnected = Signal()
    entry_received = Signal(object)
    log_message = Signal(str)
    error_message = Signal(str)


class TcpServerPage(QWidget):
    """TCP 服务端页面组件"""

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    # 保存目录
    SAVE_DIR = project_root / "tcp_output"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = TcpLogServer()
        self._signal_bridge = SignalBridge()
        self._protocols = {}
        self._current_protocol: Optional[YamlCmdFormat] = None
        self._entry_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._cmd_stats: Dict[int, int] = {}
        self._all_entries = []
        self._current_filter_cmd: Optional[int] = None

        self._log_file = None
        self._result_file = None
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._max_cache_entries = 1000

        self._setup_ui()
        self._setup_connections()
        self._scan_protocols()

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
        self._result_table.setColumnCount(4)
        self._result_table.setHorizontalHeaderLabels(["时间", "方向", "CMD", "摘要"])
        self._result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._result_table.setColumnWidth(0, 90)
        self._result_table.setColumnWidth(1, 50)
        self._result_table.setColumnWidth(2, 60)
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

        self._cache_label = QLabel(f"缓存: 0/{self._max_cache_entries}")
        self._cache_label.setStyleSheet("color: #888;")
        stats_summary_layout.addWidget(self._cache_label)

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

        self._save_path_label = QLabel(f"保存位置: {self.SAVE_DIR}")
        self._save_path_label.setStyleSheet("color: #888; font-size: 11px;")
        save_layout.addWidget(self._save_path_label)

        save_layout.addStretch()
        layout.addWidget(save_widget)

    def _setup_connections(self):
        """设置信号连接"""
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._clear_table_btn.clicked.connect(self._clear_results)
        self._reset_stats_btn.clicked.connect(self._reset_stats)

        self._result_table.itemSelectionChanged.connect(self._on_selection_changed)

        self._protocol_combo.currentTextChanged.connect(self._on_protocol_changed)
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)

        self._save_log_check.stateChanged.connect(self._on_save_option_changed)
        self._save_result_check.stateChanged.connect(self._on_save_option_changed)

        self._toggle_stats_btn.clicked.connect(self._toggle_stats_detail)

        # 信号桥接
        self._signal_bridge.state_changed.connect(self._update_state)
        self._signal_bridge.client_connected.connect(self._on_client_connected)
        self._signal_bridge.client_disconnected.connect(self._on_client_disconnected)
        self._signal_bridge.entry_received.connect(self._on_entry_received)
        self._signal_bridge.log_message.connect(self._show_log)
        self._signal_bridge.error_message.connect(self._show_error)

        # 设置服务器回调
        self._server.set_callbacks(
            on_state_changed=lambda s: self._signal_bridge.state_changed.emit(s.value),
            on_client_connected=lambda c: self._signal_bridge.client_connected.emit(c),
            on_client_disconnected=lambda: self._signal_bridge.client_disconnected.emit(),
            on_entry_received=lambda e: self._signal_bridge.entry_received.emit(e),
            on_log=lambda m: self._signal_bridge.log_message.emit(m),
            on_error=lambda m: self._signal_bridge.error_message.emit(m)
        )

    def _scan_protocols(self):
        """扫描协议配置"""
        configs_dir = project_root / "configs"
        self._protocols.clear()
        self._protocol_combo.clear()

        if not configs_dir.exists():
            return

        for protocol_dir in configs_dir.iterdir():
            if protocol_dir.is_dir():
                yaml_config = protocol_dir / "protocol.yaml"
                if yaml_config.exists():
                    self._protocols[protocol_dir.name] = str(yaml_config)

        protocol_names = sorted(self._protocols.keys())
        self._protocol_combo.addItems(protocol_names)

        model = QStringListModel(protocol_names)
        self._protocol_completer.setModel(model)

        if self._protocols:
            self._protocol_combo.setCurrentIndex(0)

    def _on_protocol_changed(self, protocol_name: str):
        """协议选择改变"""
        if protocol_name in self._protocols:
            try:
                yaml_path = self._protocols[protocol_name]
                self._current_protocol = YamlCmdFormat(yaml_path)
                self.status_changed.emit(f"已加载协议: {protocol_name}")
            except Exception as e:
                self._current_protocol = None
                self.status_changed.emit(f"加载协议失败: {e}")

    def _on_start(self):
        """启动服务"""
        host = self._host_input.text().strip()
        port = self._port_input.value()

        if not self._current_protocol:
            QMessageBox.warning(self, "警告", "请先选择协议")
            return

        self._server.start(host, port)

    def _on_stop(self):
        """停止服务"""
        self._server.stop()

    def _update_state(self, state_text: str):
        """更新状态显示"""
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

    def _on_client_connected(self, client_info: ClientInfo):
        """客户端连接"""
        self.status_changed.emit(f"客户端已连接: {client_info.address}:{client_info.port}")

    def _on_client_disconnected(self):
        """客户端断开"""
        self.status_changed.emit("客户端已断开")

    def _on_entry_received(self, entry: LogEntry):
        """收到日志条目"""
        self._entry_count += 1

        parsed_result = None
        parse_success = False

        if self._current_protocol:
            try:
                hex_str = entry.hex_data.replace(' ', '')
                if hex_str:
                    byte_data = bytes.fromhex(hex_str)
                    config = self._current_protocol.config
                    if len(byte_data) > config.head_len:
                        content_data = byte_data[config.head_len:-config.tail_len] if config.tail_len > 0 else byte_data[config.head_len:]
                        parsed_result = self._current_protocol.parse_cmd_data(entry.cmd_id, content_data)
                        parse_success = True
            except Exception as e:
                parsed_result = {"error": str(e)}

        if parse_success:
            self._success_count += 1
        else:
            self._fail_count += 1

        self._cmd_stats[entry.cmd_id] = self._cmd_stats.get(entry.cmd_id, 0) + 1
        self._update_stats()
        self._update_filter_combo(entry.cmd_id)

        entry_data = {
            "entry": entry,
            "parsed": parsed_result,
            "success": parse_success
        }
        self._all_entries.append(entry_data)

        if len(self._all_entries) > self._max_cache_entries:
            remove_count = max(1, self._max_cache_entries // 10)
            del self._all_entries[:remove_count]
            for _ in range(remove_count):
                if self._result_table.rowCount() > 0:
                    self._result_table.removeRow(0)

        self._update_cache_label()

        if self._save_log_check.isChecked():
            self._save_log_entry(entry)

        if self._save_result_check.isChecked():
            self._save_parsed_result(entry, parsed_result, parse_success)

        if self._should_show_entry(entry.cmd_id, parse_success):
            self._add_result_row(entry, parsed_result, parse_success)

    def _add_result_row(self, entry: LogEntry, parsed_result: Optional[dict], success: bool):
        """添加结果行"""
        row = self._result_table.rowCount()
        self._result_table.insertRow(row)

        time_item = QTableWidgetItem(entry.timestamp.split()[-1] if ' ' in entry.timestamp else entry.timestamp)
        self._result_table.setItem(row, 0, time_item)

        dir_item = QTableWidgetItem(entry.direction)
        dir_item.setTextAlignment(Qt.AlignCenter)
        self._result_table.setItem(row, 1, dir_item)

        cmd_item = QTableWidgetItem(str(entry.cmd_id))
        cmd_item.setTextAlignment(Qt.AlignCenter)
        self._result_table.setItem(row, 2, cmd_item)

        if parsed_result:
            summary = self._generate_summary(parsed_result)
        else:
            summary = f"[原始] {entry.hex_data[:50]}..."

        summary_item = QTableWidgetItem(summary)
        if not success:
            summary_item.setForeground(QColor("red"))
        self._result_table.setItem(row, 3, summary_item)

        time_item.setData(Qt.UserRole, {
            "entry": entry,
            "parsed": parsed_result,
            "success": success
        })

        if self._auto_scroll_check.isChecked():
            self._result_table.scrollToBottom()

        while self._result_table.rowCount() > 1000:
            self._result_table.removeRow(0)

    def _generate_summary(self, parsed: dict) -> str:
        """生成摘要"""
        if not parsed:
            return ""

        if "error" in parsed:
            return f"[错误] {parsed['error']}"

        items = []
        for key, value in list(parsed.items())[:4]:
            if isinstance(value, dict):
                if 'value' in value and 'name' in value:
                    items.append(f"{key}={value['name']}")
                else:
                    items.append(f"{key}=...")
            elif isinstance(value, list):
                items.append(f"{key}=[{len(value)}项]")
            else:
                items.append(f"{key}={value}")

        return ", ".join(items)

    def _on_selection_changed(self):
        """表格选择改变"""
        rows = self._result_table.selectedItems()
        if not rows:
            return

        row = rows[0].row()
        item = self._result_table.item(row, 0)
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        entry = data["entry"]
        parsed = data["parsed"]
        success = data["success"]

        lines = []
        lines.append("=== 数据项 ===")
        lines.append(f"时间: {entry.timestamp}")
        lines.append(f"方向: {entry.direction}")
        lines.append(f"命令: cmd{entry.cmd_id}")
        lines.append(f"字节数: {entry.byte_count}")
        lines.append(f"源信息: {entry.source_info}")
        lines.append("")

        if parsed and success:
            lines.append("解析内容:")
            self._format_parsed(parsed, lines, indent=2)
        elif parsed and "error" in parsed:
            lines.append(f"解析错误: {parsed['error']}")

        lines.append("")
        lines.append("原始数据:")
        lines.append(entry.hex_data)

        self._detail_text.setText("\n".join(lines))

    def _format_parsed(self, data: dict, lines: list, indent: int = 0):
        """格式化解析结果"""
        prefix = " " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                if 'value' in value and 'name' in value:
                    lines.append(f"{prefix}{key}: {value['value']} ({value['name']})")
                else:
                    lines.append(f"{prefix}{key}:")
                    self._format_parsed(value, lines, indent + 2)
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: [{len(value)} 项]")
                for i, item in enumerate(value[:3]):
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  [{i}]:")
                        self._format_parsed(item, lines, indent + 4)
                    else:
                        lines.append(f"{prefix}  [{i}]: {item}")
                if len(value) > 3:
                    lines.append(f"{prefix}  ... 还有 {len(value) - 3} 项")
            else:
                lines.append(f"{prefix}{key}: {value}")

    def _update_stats(self):
        """更新统计信息"""
        success_rate = (self._success_count / self._entry_count * 100) if self._entry_count > 0 else 0

        cmd_count = len(self._cmd_stats)
        self._stats_label.setText(
            f"📊 总计: {self._entry_count} 条  |  "
            f"✅ 成功: {self._success_count} ({success_rate:.1f}%)  |  "
            f"❌ 失败: {self._fail_count}  |  "
            f"📋 命令种类: {cmd_count}"
        )

        if self._stats_detail_table.isVisible():
            self._update_stats_detail_table()

    def _toggle_stats_detail(self):
        """切换统计详情显示"""
        is_visible = self._stats_detail_table.isVisible()
        self._stats_detail_table.setVisible(not is_visible)

        if not is_visible:
            self._toggle_stats_btn.setText("收起详情 ▲")
            self._update_stats_detail_table()
        else:
            self._toggle_stats_btn.setText("展开详情 ▼")

    def _update_stats_detail_table(self):
        """更新统计详情表格"""
        self._stats_detail_table.setRowCount(0)

        cmd_success = {}
        for entry_data in self._all_entries:
            cmd_id = entry_data["entry"].cmd_id
            success = entry_data["success"]
            if cmd_id not in cmd_success:
                cmd_success[cmd_id] = {"total": 0, "success": 0}
            cmd_success[cmd_id]["total"] += 1
            if success:
                cmd_success[cmd_id]["success"] += 1

        sorted_cmds = sorted(self._cmd_stats.items(), key=lambda x: x[1], reverse=True)

        for cmd_id, count in sorted_cmds:
            row = self._stats_detail_table.rowCount()
            self._stats_detail_table.insertRow(row)

            cmd_item = QTableWidgetItem(f"cmd{cmd_id}")
            cmd_item.setTextAlignment(Qt.AlignCenter)
            self._stats_detail_table.setItem(row, 0, cmd_item)

            cmd_name = self._get_cmd_name(cmd_id)
            name_item = QTableWidgetItem(cmd_name)
            self._stats_detail_table.setItem(row, 1, name_item)

            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self._stats_detail_table.setItem(row, 2, count_item)

            if cmd_id in cmd_success:
                stats = cmd_success[cmd_id]
                rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
                rate_text = f"{rate:.1f}%"
                rate_item = QTableWidgetItem(rate_text)
                rate_item.setTextAlignment(Qt.AlignCenter)
                if rate >= 90:
                    rate_item.setForeground(QColor("#4CAF50"))
                elif rate >= 50:
                    rate_item.setForeground(QColor("#FF9800"))
                else:
                    rate_item.setForeground(QColor("#F44336"))
                self._stats_detail_table.setItem(row, 3, rate_item)

    def _get_cmd_name(self, cmd_id: int) -> str:
        """获取命令名称"""
        if self._current_protocol:
            try:
                config = self._current_protocol.config
                for cmd in config.commands:
                    if cmd.cmd_id == cmd_id:
                        return cmd.name or f"cmd{cmd_id}"
            except Exception:
                pass
        return f"cmd{cmd_id}"

    def _should_show_entry(self, cmd_id: int, success: bool) -> bool:
        """判断是否应该显示该条目"""
        if self._success_only_check.isChecked() and not success:
            return False

        if self._current_filter_cmd is not None and cmd_id != self._current_filter_cmd:
            return False

        return True

    def _update_filter_combo(self, cmd_id: int):
        """更新过滤下拉框"""
        cmd_text = f"cmd{cmd_id}"

        for i in range(self._filter_combo.count()):
            if self._filter_combo.itemText(i) == cmd_text:
                return

        self._filter_combo.addItem(cmd_text)

        items = [self._filter_combo.itemText(i) for i in range(self._filter_combo.count())]
        model = QStringListModel(items)
        self._filter_completer.setModel(model)

    def _on_filter_changed(self, text: str):
        """过滤选择改变"""
        if text == "全部命令" or not text:
            self._current_filter_cmd = None
        elif text.startswith("cmd"):
            try:
                self._current_filter_cmd = int(text[3:])
            except ValueError:
                self._current_filter_cmd = None
        else:
            try:
                self._current_filter_cmd = int(text)
            except ValueError:
                self._current_filter_cmd = None

        self._refresh_table()

    def _refresh_table(self):
        """刷新表格显示"""
        self._result_table.setRowCount(0)

        for entry_data in self._all_entries:
            entry = entry_data["entry"]
            parsed = entry_data["parsed"]
            success = entry_data["success"]

            if self._should_show_entry(entry.cmd_id, success):
                self._add_result_row(entry, parsed, success)

    def _on_save_option_changed(self):
        """保存选项改变"""
        if self._save_log_check.isChecked() or self._save_result_check.isChecked():
            self.SAVE_DIR.mkdir(parents=True, exist_ok=True)

    def _save_log_entry(self, entry: LogEntry):
        """保存日志条目"""
        try:
            self.SAVE_DIR.mkdir(parents=True, exist_ok=True)
            log_file = self.SAVE_DIR / f"tcp_log_{self._session_id}.log"

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.raw_text)
                if not entry.raw_text.endswith("\n"):
                    f.write("\n")
        except Exception as e:
            self.status_changed.emit(f"保存日志失败: {e}")

    def _save_parsed_result(self, entry: LogEntry, parsed: Optional[dict], success: bool):
        """保存解析结果"""
        try:
            self.SAVE_DIR.mkdir(parents=True, exist_ok=True)
            result_file = self.SAVE_DIR / f"tcp_parsed_{self._session_id}.json"

            record = {
                "timestamp": entry.timestamp,
                "direction": entry.direction,
                "cmd_id": entry.cmd_id,
                "byte_count": entry.byte_count,
                "success": success,
                "parsed": parsed if parsed else {},
                "hex_data": entry.hex_data
            }

            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            self.status_changed.emit(f"保存解析结果失败: {e}")

    def _clear_results(self):
        """清空结果"""
        self._result_table.setRowCount(0)
        self._detail_text.clear()
        self._all_entries.clear()

        self._filter_combo.clear()
        self._filter_combo.addItem("全部命令")
        self._current_filter_cmd = None

    def _copy_detail(self):
        """复制详情内容"""
        text = self._detail_text.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.status_changed.emit("已复制到剪贴板")

    def _update_cache_label(self):
        """更新缓存条数显示"""
        current = len(self._all_entries)
        self._cache_label.setText(f"缓存: {current}/{self._max_cache_entries}")
        if current > self._max_cache_entries * 0.8:
            self._cache_label.setStyleSheet("color: #FFA500;")
        else:
            self._cache_label.setStyleSheet("color: #888;")

    def _reset_stats(self):
        """重置统计"""
        self._entry_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._cmd_stats.clear()
        self._server.reset_stats()
        self._update_stats()

    def _show_log(self, message: str):
        """显示日志"""
        self.status_changed.emit(message)

    def _show_error(self, message: str):
        """显示错误"""
        self.status_changed.emit(f"错误: {message}")
