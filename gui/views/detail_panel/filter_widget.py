"""
文件名称: filter_widget.py
内容摘要: 过滤设置组件
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from datetime import datetime
from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QGridLayout, QLabel, QCheckBox,
    QDialog, QMessageBox
)
from PySide6.QtCore import Signal

from gui.widgets.datetime_picker import DateTimePickerWidget
from gui.widgets.multi_select_combo import MultiSelectComboBox
from gui.widgets.log_time_scanner import LogTimeScanner, TimeScanResult
from gui.shared.time_utils import format_time_range_smart


class FilterWidget(QGroupBox):
    """过滤设置组件

    职责：
    - 提供时间过滤设置
    - 提供命令过滤设置（包含/排除）
    - 后台扫描日志时间范围
    - 可视化时间选择对话框

    信号：
    - time_range_changed: 时间范围变化 (start, end)
    - command_filter_changed: 命令过滤变化 (include_cmds, exclude_cmds)
    """

    # 信号：通知过滤器变化
    time_range_changed = Signal(object, object)  # (start, end)
    command_filter_changed = Signal(object, object)  # (include_cmds, exclude_cmds)

    def __init__(self, parent: Optional['QWidget'] = None):
        super().__init__("过滤设置（可选）", parent)

        # 日志时间扫描器（后台线程）
        self._scanner: Optional[LogTimeScanner] = None
        self._scan_result: Optional[TimeScanResult] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 复选框统一样式
        checkbox_style = """
            QCheckBox {
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox:unchecked {
                background-color: #34495e;
                color: #ecf0f1;
            }
            QCheckBox:checked {
                background-color: #3498db;
                color: white;
            }
            QCheckBox:hover {
                background-color: #2980b9;
            }
        """

        # 时间过滤
        self.time_filter_check = QCheckBox("启用时间过滤")
        self.time_filter_check.setStyleSheet(checkbox_style)
        layout.addWidget(self.time_filter_check)

        time_layout = QGridLayout()
        time_layout.setContentsMargins(20, 0, 0, 0)

        # 日志时间范围显示
        time_layout.addWidget(QLabel("📅 日志范围:"), 0, 0)
        self.log_range_label = QLabel("未加载")
        self.log_range_label.setStyleSheet("color: #888; font-size: 11px;")
        time_layout.addWidget(self.log_range_label, 0, 1)

        # 当前选择显示
        time_layout.addWidget(QLabel("🕒 当前选择:"), 1, 0)
        self.current_range_label = QLabel("未选择")
        self.current_range_label.setStyleSheet("color: #569cd6; font-size: 11px;")
        time_layout.addWidget(self.current_range_label, 1, 1)

        # 可视化选择按钮
        self.open_visual_picker_btn = QPushButton("📊 可视化选择时间范围...")
        self.open_visual_picker_btn.setEnabled(False)
        self.open_visual_picker_btn.clicked.connect(self._open_visual_time_picker)
        time_layout.addWidget(self.open_visual_picker_btn, 2, 0, 1, 2)

        layout.addLayout(time_layout)

        # 保留原有的 DateTimePickerWidget（用于内部存储，设为不可见）
        self.start_time_picker = DateTimePickerWidget()
        self.start_time_picker.setVisible(False)
        self.end_time_picker = DateTimePickerWidget()
        self.end_time_picker.setVisible(False)

        # 命令过滤
        self.cmd_filter_check = QCheckBox("启用命令过滤")
        self.cmd_filter_check.setStyleSheet(checkbox_style)
        layout.addWidget(self.cmd_filter_check)

        cmd_layout = QGridLayout()
        cmd_layout.setContentsMargins(20, 0, 0, 0)

        cmd_layout.addWidget(QLabel("包含:"), 0, 0)
        self.include_cmd_combo = MultiSelectComboBox("选择要包含的命令...")
        self.include_cmd_combo.setEnabled(False)
        cmd_layout.addWidget(self.include_cmd_combo, 0, 1)

        cmd_layout.addWidget(QLabel("排除:"), 1, 0)
        self.exclude_cmd_combo = MultiSelectComboBox("选择要排除的命令...")
        self.exclude_cmd_combo.setEnabled(False)
        cmd_layout.addWidget(self.exclude_cmd_combo, 1, 1)

        layout.addLayout(cmd_layout)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.time_filter_check.toggled.connect(self._on_time_filter_toggled)
        self.cmd_filter_check.toggled.connect(self._on_cmd_filter_toggled)

    def _on_time_filter_toggled(self, checked: bool) -> None:
        """时间过滤启用状态变化

        Args:
            checked: 是否启用
        """
        # 启用/禁用可视化选择按钮
        # 只有当扫描完成后才启用按钮
        if checked and self._scan_result and self._scan_result.has_valid_range:
            self.open_visual_picker_btn.setEnabled(True)
        else:
            self.open_visual_picker_btn.setEnabled(False)

        # 发射信号（禁用时传递 None）
        if not checked:
            self.time_range_changed.emit(None, None)

    def _on_cmd_filter_toggled(self, checked: bool) -> None:
        """命令过滤启用状态变化

        Args:
            checked: 是否启用
        """
        self.include_cmd_combo.setEnabled(checked)
        self.exclude_cmd_combo.setEnabled(checked)

        # 发射信号（禁用时传递 None）
        if not checked:
            self.command_filter_changed.emit(None, None)

    def set_commands(self, commands: List[Tuple[str, str]]) -> None:
        """设置可用的命令列表

        Args:
            commands: 命令列表 [(cmd_id, display_text), ...]
        """
        self.include_cmd_combo.set_items(commands)
        self.exclude_cmd_combo.set_items(commands)

        # 连接选择变化信号
        self.include_cmd_combo.selection_changed.connect(
            lambda: self._emit_command_filter_changed()
        )
        self.exclude_cmd_combo.selection_changed.connect(
            lambda: self._emit_command_filter_changed()
        )

    def _emit_command_filter_changed(self) -> None:
        """发射命令过滤变化信号"""
        if self.cmd_filter_check.isChecked():
            include = self.get_include_cmds()
            exclude = self.get_exclude_cmds()
            self.command_filter_changed.emit(include, exclude)

    def get_time_filter(self) -> Optional[Tuple[datetime, datetime]]:
        """获取时间过滤条件

        Returns:
            (start_time, end_time) 或 None
        """
        if not self.time_filter_check.isChecked():
            return None
        start = self.start_time_picker.get_datetime()
        end = self.end_time_picker.get_datetime()
        if start and end:
            return (start, end)
        return None

    def get_include_cmds(self) -> Optional[List[str]]:
        """获取包含的命令列表

        Returns:
            包含的命令ID列表或None
        """
        if not self.cmd_filter_check.isChecked():
            return None
        selected = self.include_cmd_combo.get_selected()
        return selected if selected else None

    def get_exclude_cmds(self) -> Optional[List[str]]:
        """获取排除的命令列表

        Returns:
            排除的命令ID列表或None
        """
        if not self.cmd_filter_check.isChecked():
            return None
        selected = self.exclude_cmd_combo.get_selected()
        return selected if selected else None

    def clear(self) -> None:
        """清空过滤设置"""
        self.time_filter_check.setChecked(False)
        self.cmd_filter_check.setChecked(False)
        self.start_time_picker.set_datetime(None)
        self.end_time_picker.set_datetime(None)
        self.include_cmd_combo.clear_selection()
        self.exclude_cmd_combo.clear_selection()

        # 清空显示标签
        self.log_range_label.setText("未加载")
        self.log_range_label.setStyleSheet("color: #888; font-size: 11px;")
        self.current_range_label.setText("未选择")

        # 清理扫描状态
        self._scan_result = None
        if hasattr(self, '_last_scanned_path'):
            delattr(self, '_last_scanned_path')

    def cleanup(self) -> None:
        """清理资源（停止扫描线程）"""
        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()
            self._scanner.wait()

    def set_log_path(self, log_path: Optional[str]) -> None:
        """设置日志文件路径（用于加载时间范围）

        Args:
            log_path: 日志文件路径
        """
        self._log_path = log_path

        # 如果路径有效，自动触发后台扫描
        if log_path:
            self._start_background_scan()

    def _start_background_scan(self) -> None:
        """启动后台日志时间扫描"""
        if not hasattr(self, '_log_path') or not self._log_path:
            return

        # 如果已有扫描结果且路径未变，不重复扫描
        if self._scan_result and hasattr(self, '_last_scanned_path'):
            if self._last_scanned_path == self._log_path:
                return

        # 更新 UI 状态：正在扫描
        self.log_range_label.setText("🔄 正在扫描日志时间范围...")
        self.log_range_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        self.open_visual_picker_btn.setEnabled(False)  # 扫描期间禁用按钮

        # 启动后台扫描线程
        self._scanner = LogTimeScanner(self._log_path, self)
        self._scanner.progress.connect(self._on_scan_progress)
        self._scanner.finished.connect(self._on_scan_finished)
        self._scanner.error.connect(self._on_scan_error)
        self._scanner.start()

    def _on_scan_progress(self, current: int, total: int) -> None:
        """扫描进度更新（可选显示，避免频繁刷新）

        Args:
            current: 当前进度
            total: 总进度
        """
        # 每 10% 更新一次显示
        if total > 0 and current % (total // 10) == 0:
            progress = int(current * 100 / total)
            self.log_range_label.setText(f"🔄 正在扫描... {progress}%")

    def _on_scan_finished(self, result: TimeScanResult) -> None:
        """扫描完成

        Args:
            result: 扫描结果
        """
        self._scan_result = result
        self._last_scanned_path = self._log_path

        if result.has_valid_range:
            # 显示日志时间范围（智能格式化 + 时间跨度）
            range_str = format_time_range_smart(result.min_time, result.max_time)
            span_str = result.time_span_human
            self.log_range_label.setText(f"{range_str} (跨度: {span_str})")
            self.log_range_label.setStyleSheet("color: #27ae60; font-size: 11px;")

            # 如果时间过滤已启用，则启用可视化选择按钮
            if self.time_filter_check.isChecked():
                self.open_visual_picker_btn.setEnabled(True)
        else:
            # 没有找到有效时间戳
            self.log_range_label.setText("⚠️ 未找到有效时间戳")
            self.log_range_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def _on_scan_error(self, error_msg: str) -> None:
        """扫描错误

        Args:
            error_msg: 错误信息
        """
        self.log_range_label.setText(f"❌ 扫描失败")
        self.log_range_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def _open_visual_time_picker(self) -> None:
        """打开可视化时间选择对话框"""
        if not hasattr(self, '_log_path') or not self._log_path:
            QMessageBox.warning(self, "提示", "请先选择日志文件")
            return

        # 获取当前选择
        current_range = self.get_time_filter()

        # 导入并打开对话框
        try:
            from gui.widgets.visual_time_picker_dialog import VisualTimePickerDialog

            dialog = VisualTimePickerDialog(
                self._log_path,
                current_range,
                self
            )

            if dialog.exec() == QDialog.Accepted:
                range_result = dialog.get_time_range()
                if range_result:
                    start, end = range_result
                    self.start_time_picker.set_datetime(start)
                    self.end_time_picker.set_datetime(end)
                    self._update_display_labels()

        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"打开可视化时间选择器失败:\n{str(e)}"
            )

    def _update_display_labels(self) -> None:
        """更新显示标签"""
        start = self.start_time_picker.get_datetime()
        end = self.end_time_picker.get_datetime()

        if start and end:
            # 显示当前选择（智能格式化）
            range_str = format_time_range_smart(start, end)
            self.current_range_label.setText(range_str)
            # 发射信号
            self.time_range_changed.emit(start, end)
        else:
            self.current_range_label.setText("未选择")
