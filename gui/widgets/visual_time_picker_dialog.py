# gui/widgets/visual_time_picker_dialog.py
"""
文件名称: visual_time_picker_dialog.py
内容摘要: 可视化时间范围选择对话框，整合滑块和精确输入
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-23
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QDialogButtonBox, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt

from .datetime_picker import DateTimePickerWidget
from .time_range_slider import TimeRangeSlider
from .log_time_scanner import LogTimeScanner, TimeScanResult
from .time_formatter import format_time_range_smart


class VisualTimePickerDialog(QDialog):
    """
    可视化时间范围选择对话框

    职责：
    - 弹窗对话框，整合所有可视化组件
    - 加载并显示日志时间范围
    - 时间轴滑块 + 精确输入框
    - 双向绑定（滑块 ↔ 输入框）
    - 快捷选择按钮（全部、前半、后半等）
    """

    def __init__(
        self,
        log_path: str,
        current_range: Optional[Tuple[datetime, datetime]] = None,
        parent=None
    ):
        """
        初始化对话框

        Args:
            log_path: 日志文件路径
            current_range: 当前选择的时间范围 (start, end)
            parent: 父窗口
        """
        super().__init__(parent)

        self._log_path = log_path
        self._current_range = current_range
        self._scanner: Optional[LogTimeScanner] = None
        self._scan_result: Optional[TimeScanResult] = None

        # 缓存（避免重复扫描）
        self._cache: Dict[str, TimeScanResult] = {}

        self._setup_ui()
        self._connect_signals()

        # 加载日志时间范围
        self._load_log_time_range()

    def _setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("可视化时间范围选择")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # 1. 日志时间范围信息
        info_group = QGroupBox("日志时间范围")
        info_layout = QVBoxLayout(info_group)

        self.log_range_label = QLabel("正在扫描...")
        self.log_range_label.setStyleSheet("color: #888; font-size: 12px;")
        info_layout.addWidget(self.log_range_label)

        self.scan_info_label = QLabel("")
        self.scan_info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.scan_info_label)

        layout.addWidget(info_group)

        # 2. 时间轴滑块
        slider_group = QGroupBox("时间轴")
        slider_layout = QVBoxLayout(slider_group)

        self.time_slider = TimeRangeSlider()
        self.time_slider.setEnabled(False)  # 扫描完成后启用
        slider_layout.addWidget(self.time_slider)

        layout.addWidget(slider_group)

        # 3. 精确输入区域
        input_group = QGroupBox("精确输入")
        input_layout = QVBoxLayout(input_group)

        # 起始时间
        start_row = QHBoxLayout()
        start_row.addWidget(QLabel("起始时间:"))
        self.start_picker = DateTimePickerWidget()
        self.start_picker.setEnabled(False)
        start_row.addWidget(self.start_picker)
        input_layout.addLayout(start_row)

        # 结束时间
        end_row = QHBoxLayout()
        end_row.addWidget(QLabel("结束时间:"))
        self.end_picker = DateTimePickerWidget()
        self.end_picker.setEnabled(False)
        end_row.addWidget(self.end_picker)
        input_layout.addLayout(end_row)

        # 选择范围摘要
        self.range_summary_label = QLabel("未选择")
        self.range_summary_label.setStyleSheet("color: #569cd6; font-weight: bold; padding: 5px;")
        self.range_summary_label.setAlignment(Qt.AlignCenter)
        input_layout.addWidget(self.range_summary_label)

        layout.addWidget(input_group)

        # 4. 快捷选择按钮
        quick_group = QGroupBox("快捷选择")
        quick_layout = QHBoxLayout(quick_group)

        self.btn_all = QPushButton("全部")
        self.btn_all.clicked.connect(self._select_all)
        quick_layout.addWidget(self.btn_all)

        self.btn_first_half = QPushButton("前半段")
        self.btn_first_half.clicked.connect(self._select_first_half)
        quick_layout.addWidget(self.btn_first_half)

        self.btn_second_half = QPushButton("后半段")
        self.btn_second_half.clicked.connect(self._select_second_half)
        quick_layout.addWidget(self.btn_second_half)

        self.btn_first_hour = QPushButton("前1小时")
        self.btn_first_hour.clicked.connect(self._select_first_hour)
        quick_layout.addWidget(self.btn_first_hour)

        self.btn_last_hour = QPushButton("最近1小时")
        self.btn_last_hour.clicked.connect(self._select_last_hour)
        quick_layout.addWidget(self.btn_last_hour)

        layout.addWidget(quick_group)

        # 5. 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 6. 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("扫描中... %p%")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def _connect_signals(self):
        """连接信号"""
        self.time_slider.range_changed.connect(self._on_slider_changed)
        self.start_picker.datetime_changed.connect(self._on_picker_changed)
        self.end_picker.datetime_changed.connect(self._on_picker_changed)

    def _load_log_time_range(self):
        """加载日志时间范围"""
        # 检查缓存
        if self._log_path in self._cache:
            self._on_scan_finished(self._cache[self._log_path])
            return

        # 启动后台扫描
        self._scanner = LogTimeScanner(self._log_path, self)
        self._scanner.progress.connect(self._on_scan_progress)
        self._scanner.finished.connect(self._on_scan_finished)
        self._scanner.error.connect(self._on_scan_error)

        self.progress_bar.setVisible(True)
        self.log_range_label.setText("正在扫描日志文件...")
        self._scanner.start()

    def _on_scan_progress(self, current: int, total: int):
        """扫描进度更新"""
        if total > 0:
            progress = int(current * 100 / total)
            self.progress_bar.setValue(progress)

    def _on_scan_finished(self, result: TimeScanResult):
        """扫描完成"""
        self.progress_bar.setVisible(False)
        self._scan_result = result

        # 缓存结果
        if self._log_path:
            self._cache[self._log_path] = result

        # 更新UI
        if result.has_valid_range:
            # 显示日志时间范围
            min_str = result.min_time.strftime("%Y-%m-%d %H:%M:%S")
            max_str = result.max_time.strftime("%Y-%m-%d %H:%M:%S")
            self.log_range_label.setText(f"{min_str} ~ {max_str}")

            # 显示扫描信息
            scan_info = f"扫描耗时: {result.scan_duration:.2f}s | "
            scan_info += f"记录数: {result.total_lines} | "
            scan_info += f"时间跨度: {result.time_span_human}"
            self.scan_info_label.setText(scan_info)

            # 设置滑块范围
            self.time_slider.set_time_range(result.min_time, result.max_time)
            self.time_slider.setEnabled(True)

            # 设置输入框范围
            self.start_picker.setEnabled(True)
            self.end_picker.setEnabled(True)

            # 如果有当前选择，应用之；否则选择全部
            if self._current_range:
                start, end = self._current_range
                # 限制在范围内
                start = max(result.min_time, min(start, result.max_time))
                end = max(result.min_time, min(end, result.max_time))
                self.time_slider.set_selection(start, end)
                self.start_picker.set_datetime(start)
                self.end_picker.set_datetime(end)
            else:
                # 默认选择全部
                self.time_slider.set_selection(result.min_time, result.max_time)
                self.start_picker.set_datetime(result.min_time)
                self.end_picker.set_datetime(result.max_time)

            # 启用快捷按钮
            self._enable_quick_buttons(True)

        else:
            # 没有找到有效时间戳
            self.log_range_label.setText("❌ 未找到有效时间戳")
            self.scan_info_label.setText("请检查日志文件格式")
            self.time_slider.setEnabled(False)
            self.start_picker.setEnabled(False)
            self.end_picker.setEnabled(False)
            self._enable_quick_buttons(False)

    def _on_scan_error(self, error_msg: str):
        """扫描错误"""
        self.progress_bar.setVisible(False)
        self.log_range_label.setText(f"❌ 扫描失败")
        self.scan_info_label.setText(error_msg)
        self.time_slider.setEnabled(False)
        self.start_picker.setEnabled(False)
        self.end_picker.setEnabled(False)
        self._enable_quick_buttons(False)

    def _on_slider_changed(self, start: datetime, end: datetime):
        """滑块范围变化"""
        # 更新输入框（阻止信号循环）
        self.start_picker.blockSignals(True)
        self.end_picker.blockSignals(True)
        self.start_picker.set_datetime(start)
        self.end_picker.set_datetime(end)
        self.start_picker.blockSignals(False)
        self.end_picker.blockSignals(False)

        # 更新摘要
        self._update_range_summary(start, end)

    def _on_picker_changed(self, dt: datetime):
        """输入框变化"""
        start = self.start_picker.get_datetime()
        end = self.end_picker.get_datetime()

        if start and end:
            # 更新滑块（阻止信号循环）
            self.time_slider.blockSignals(True)
            self.time_slider.set_selection(start, end)
            self.time_slider.blockSignals(False)

            # 更新摘要
            self._update_range_summary(start, end)

    def _update_range_summary(self, start: datetime, end: datetime):
        """更新范围摘要"""
        span_seconds = (end - start).total_seconds()

        if span_seconds < 60:
            span_str = f"{span_seconds:.0f}秒"
        elif span_seconds < 3600:
            minutes = span_seconds / 60
            span_str = f"{minutes:.1f}分钟"
        elif span_seconds < 86400:
            hours = span_seconds / 3600
            span_str = f"{hours:.1f}小时"
        else:
            days = span_seconds / 86400
            span_str = f"{days:.1f}天"

        # 使用智能格式化时间范围
        range_str = format_time_range_smart(start, end)
        self.range_summary_label.setText(f"{range_str} ({span_str})")

    def _enable_quick_buttons(self, enabled: bool):
        """启用/禁用快捷按钮"""
        self.btn_all.setEnabled(enabled)
        self.btn_first_half.setEnabled(enabled)
        self.btn_second_half.setEnabled(enabled)
        self.btn_first_hour.setEnabled(enabled)
        self.btn_last_hour.setEnabled(enabled)

    def _select_all(self):
        """选择全部范围"""
        if self._scan_result and self._scan_result.has_valid_range:
            self.time_slider.set_selection(self._scan_result.min_time, self._scan_result.max_time)

    def _select_first_half(self):
        """选择前半段"""
        if self._scan_result and self._scan_result.has_valid_range:
            min_time = self._scan_result.min_time
            max_time = self._scan_result.max_time
            mid_time = min_time + (max_time - min_time) / 2
            self.time_slider.set_selection(min_time, mid_time)

    def _select_second_half(self):
        """选择后半段"""
        if self._scan_result and self._scan_result.has_valid_range:
            min_time = self._scan_result.min_time
            max_time = self._scan_result.max_time
            mid_time = min_time + (max_time - min_time) / 2
            self.time_slider.set_selection(mid_time, max_time)

    def _select_first_hour(self):
        """选择前1小时"""
        if self._scan_result and self._scan_result.has_valid_range:
            min_time = self._scan_result.min_time
            max_time = self._scan_result.max_time
            one_hour_later = min_time + timedelta(hours=1)

            # 限制不超过最大时间
            if one_hour_later > max_time:
                one_hour_later = max_time

            self.time_slider.set_selection(min_time, one_hour_later)

    def _select_last_hour(self):
        """选择最近1小时"""
        if self._scan_result and self._scan_result.has_valid_range:
            min_time = self._scan_result.min_time
            max_time = self._scan_result.max_time
            one_hour_before = max_time - timedelta(hours=1)

            # 限制不小于最小时间
            if one_hour_before < min_time:
                one_hour_before = min_time

            self.time_slider.set_selection(one_hour_before, max_time)

    def get_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """
        获取选择的时间范围

        Returns:
            Optional[Tuple[起始时间, 结束时间]]: 如果未选择返回 None
        """
        start = self.start_picker.get_datetime()
        end = self.end_picker.get_datetime()

        if start and end:
            return (start, end)

        return None

    def closeEvent(self, event):
        """关闭事件（清理资源）"""
        # 停止扫描线程
        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()
            self._scanner.wait()

        # 清理缓存
        self._cache.clear()

        super().closeEvent(event)
