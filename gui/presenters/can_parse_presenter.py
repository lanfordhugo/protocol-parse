"""
文件名称: can_parse_presenter.py
内容摘要: CAN解析页面的 Presenter（MVP 模式中的 P）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QSettings, QThread, Qt

from gui.config import PARSED_LOG_DIR
from gui.views.i_can_parse_view import ICanParsePageView
from gui.workers.can_parse_worker import CanParseWorker
from gui.shared import open_directory, open_file

logger = logging.getLogger(__name__)

# CAN日志文件过滤器
CAN_LOG_FILE_FILTER = "CAN日志文件 (*.log *.csv *.txt);;所有文件 (*)"

# 默认CAN配置路径
DEFAULT_CAN_CONFIG = "configs/v6_can/protocol.yaml"


class CanParsePresenter(QObject):
    """
    CAN解析页面 Presenter

    职责：
    - 响应 View 的用户交互事件
    - 管理CAN解析工作线程的生命周期
    - 通过 View 接口更新 UI 展示
    """

    def __init__(
        self,
        view: ICanParsePageView,
        settings: Optional[QSettings] = None,
    ):
        super().__init__()
        self._view = view
        self._settings = settings

        # 解析线程管理
        self._parse_thread: Optional[QThread] = None
        self._parse_worker: Optional[CanParseWorker] = None

        # 输出目录
        self._output_dir = PARSED_LOG_DIR

    def initialize(self) -> None:
        """初始化 Presenter"""
        # 恢复上次使用的日志文件
        if self._settings:
            last_log = self._settings.value("can_parse/last_log", "")
            if last_log and Path(last_log).exists():
                self._view.set_log_path(last_log)
                self._view.log_info(f"已恢复上次使用的CAN日志: {last_log}")

        self._view.log_info("V6 CAN协议解析就绪")
        self._view.emit_status_changed("V6 CAN解析 | 就绪")

    # ============== 用户交互事件处理 ==============

    def on_select_log_clicked(self) -> None:
        """用户点击了「选择日志文件」"""
        if self._settings:
            last_dir = self._settings.value(
                "can_parse/last_dir", str(Path.home())
            )
        else:
            last_dir = str(Path.home())

        file_path = self._view.show_file_dialog(
            title="选择CAN日志文件",
            directory=last_dir,
            file_filter=CAN_LOG_FILE_FILTER,
        )

        if file_path:
            if self._settings:
                self._settings.setValue(
                    "can_parse/last_dir", str(Path(file_path).parent)
                )
                self._settings.setValue("can_parse/last_log", file_path)

            self._view.set_log_path(file_path)
            self._view.log_info(f"已选择CAN日志: {file_path}")

    def on_parse_clicked(self) -> None:
        """用户点击了「开始解析」"""
        log_path = self._view.get_selected_log_path()
        if not log_path:
            self._view.show_warning("提示", "请先选择CAN日志文件")
            return

        if not Path(log_path).exists():
            self._view.show_warning("提示", f"日志文件不存在: {log_path}")
            return

        config_path = DEFAULT_CAN_CONFIG
        if not Path(config_path).exists():
            self._view.show_warning(
                "提示", f"CAN协议配置不存在: {config_path}"
            )
            return

        filter_settings = self._view.get_filter_settings()

        # 创建工作线程
        self._parse_thread = QThread()
        self._parse_worker = CanParseWorker(
            config_path, log_path, filter_settings
        )
        self._parse_worker.moveToThread(self._parse_thread)

        # 连接信号
        self._parse_thread.started.connect(self._parse_worker.run)
        self._parse_worker.log_info.connect(self._view.log_info)
        self._parse_worker.log_success.connect(self._view.log_success)
        self._parse_worker.log_warning.connect(self._view.log_warning)
        self._parse_worker.log_error.connect(self._view.log_error)
        self._parse_worker.progress.connect(self._view.set_progress)
        self._parse_worker.finished.connect(
            self._on_parse_finished,
            Qt.ConnectionType.QueuedConnection,
        )

        # 更新 UI 状态
        self._view.set_parsing_state(True)
        self._view.reset_progress()
        self._view.emit_status_changed("正在解析CAN日志...")

        # 启动线程
        self._parse_thread.start()

    def on_stop_clicked(self) -> None:
        """用户点击了「停止解析」"""
        if self._parse_worker:
            self._parse_worker.stop()
            self._view.log_warning("正在停止解析...")
            self._view.emit_status_changed("正在停止CAN解析...")

    def on_open_output_dir(self) -> None:
        """用户点击了「打开输出目录」"""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        open_directory(self._output_dir)

    def on_log_file_dropped(self, file_path: str) -> None:
        """用户拖拽了日志文件"""
        if self._settings:
            self._settings.setValue("can_parse/last_log", file_path)
        self._view.set_log_path(file_path)
        self._view.log_info(f"已通过拖拽加载CAN日志: {file_path}")

    # ============== 内部回调 ==============

    def _on_parse_finished(
        self, success: bool, message: str, output_path: str
    ) -> None:
        """解析完成回调（主线程执行）"""
        self._view.set_parsing_state(False)

        # 清理线程
        if self._parse_thread:
            self._parse_thread.quit()
            self._parse_thread.wait()
            self._parse_thread.deleteLater()
            self._parse_thread = None
            self._parse_worker = None

        if success:
            self._view.emit_status_changed(
                f"✅ CAN解析完成 | "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            if output_path:
                action = self._view.show_parse_complete_dialog(output_path)
                if action == "open_file":
                    open_file(output_path)
        else:
            self._view.emit_status_changed("❌ CAN解析失败")

    # ============== 资源管理 ==============

    def cleanup(self) -> None:
        """清理资源"""
        if self._parse_worker:
            self._parse_worker.stop()
        if self._parse_thread and self._parse_thread.isRunning():
            self._parse_thread.quit()
            if not self._parse_thread.wait(5000):
                self._parse_thread.terminate()
                self._parse_thread.wait(2000)
