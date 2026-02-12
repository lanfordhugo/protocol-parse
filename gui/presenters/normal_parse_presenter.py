"""
文件名称: normal_parse_presenter.py
内容摘要: 普通解析页面的 Presenter（MVP 模式中的 P）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QSettings, QThread, Qt

from gui.config import (
    CONFIGS_DIR,
    DEFAULT_PROTOCOL,
    LOG_FILE_FILTER,
    PARSED_LOG_DIR,
)
from gui.models.protocol_model import ProtocolModel
from gui.models.parse_model import ParseModel
from gui.views.i_normal_parse_view import INormalParsePageView
from gui.workers import ParseWorker
from gui.shared import get_app_dir, open_directory, open_file

logger = logging.getLogger(__name__)


class NormalParsePresenter(QObject):
    """
    普通解析页面 Presenter

    职责：
    - 响应 View 的用户交互事件
    - 调用 Model 层获取/处理数据
    - 通过 View 接口更新 UI 展示
    - 管理解析工作线程的生命周期

    依赖：
    - INormalParsePageView: View 接口
    - ProtocolModel: 协议业务模型
    - ParseModel: 解析业务模型
    """

    def __init__(
        self,
        view: INormalParsePageView,
        protocol_model: ProtocolModel,
        parse_model: ParseModel,
        settings: Optional[QSettings] = None,
    ):
        """
        初始化 Presenter

        Args:
            view: View 接口实例
            protocol_model: 协议模型
            parse_model: 解析模型
            settings: QSettings 实例（用于持久化用户偏好）
        """
        super().__init__()
        self._view = view
        self._protocol_model = protocol_model
        self._parse_model = parse_model
        self._settings = settings

        # 解析线程管理
        self._parse_thread: Optional[QThread] = None
        self._parse_worker: Optional[ParseWorker] = None

        # 输出目录
        self._output_dir = PARSED_LOG_DIR

    def initialize(self) -> None:
        """
        初始化 Presenter（加载协议列表、选择默认协议）

        应在 View 的 UI 初始化完成后调用。
        """
        self._load_protocols()
        self._select_default_protocol(DEFAULT_PROTOCOL)

    def _load_protocols(self) -> None:
        """加载协议列表到 View"""
        protocols = self._protocol_model.discover_protocols()
        self._view.display_protocols(protocols)

    def _select_default_protocol(self, protocol_name: str) -> None:
        """选择默认协议"""
        self._view.select_protocol_by_name(protocol_name)

    # ============== 用户交互事件处理 ==============

    def on_protocol_selected(self, protocol_name: str) -> None:
        """
        用户选择了一个协议

        Args:
            protocol_name: 协议名称
        """
        info = self._protocol_model.get_protocol_info(protocol_name)
        if not info:
            return

        # 尝试恢复上次使用的日志文件路径
        if not info.log_path and self._settings:
            last_log = self._settings.value(f"last_log/{protocol_name}", "")
            if last_log and Path(last_log).exists():
                self._protocol_model.set_log_path(protocol_name, last_log)
                self._view.log_info(f"已恢复上次使用的日志文件: {last_log}")

        # 详细验证协议配置
        validation = self._protocol_model.validate_protocol_detailed(protocol_name)
        if validation.is_valid:
            if validation.warnings:
                self._view.log_warning(
                    f"协议 {protocol_name} 校验通过（{len(validation.warnings)} 个警告）"
                )
                for warning in validation.warnings:
                    self._view.log_warning(f"  ↳ {warning}")
            else:
                self._view.log_success(f"协议 {protocol_name} 校验通过")
        else:
            self._view.log_error(
                f"协议 {protocol_name} 校验失败（{len(validation.errors)} 个错误）"
            )
            for error in validation.errors:
                self._view.log_error(f"  ↳ {error}")

        # 获取详细信息并更新 View
        detail = self._protocol_model.get_protocol_detail(protocol_name)
        if detail:
            self._view.display_protocol_detail(detail)

        self._view.emit_status_changed(f"选中协议: {protocol_name}")

    def on_parse_clicked(self) -> None:
        """用户点击了「开始解析」"""
        protocol_name = self._view.get_selected_protocol_name()
        if not protocol_name:
            self._view.show_warning("提示", "请先选择要解析的协议")
            return

        info = self._protocol_model.get_protocol_info(protocol_name)
        if not info:
            return

        # 检查是否满足解析条件
        can_parse, reason = self._protocol_model.can_parse(protocol_name)
        if not can_parse:
            self._view.show_warning("提示", reason)
            return

        filter_settings = self._view.get_filter_settings()

        # 创建工作线程
        self._parse_thread = QThread()
        self._parse_worker = ParseWorker(
            protocol_name,
            info.config_path,
            info.log_path,
            filter_settings,
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
        self._view.emit_status_changed(f"正在解析: {protocol_name}")

        # 启动线程
        self._parse_thread.start()

    def on_stop_clicked(self) -> None:
        """用户点击了「停止解析」"""
        if self._parse_worker:
            self._parse_worker.stop()
            self._view.log_warning("正在停止解析...")
            self._view.emit_status_changed("正在停止解析...")

    def on_validate_clicked(self) -> None:
        """用户点击了「验证配置」"""
        protocol_name = self._view.get_selected_protocol_name()
        if not protocol_name:
            self._view.show_warning("提示", "请先选择要验证的协议")
            return

        self._view.log_info(f"开始验证协议 {protocol_name} 的配置...")

        validation = self._protocol_model.validate_protocol(protocol_name)
        info = self._protocol_model.get_protocol_info(protocol_name)

        if validation.is_valid:
            self._view.log_success(f"协议 {protocol_name} 配置验证通过")
            if info:
                self._view.update_protocol_list_item(info)
            # 重新触发协议选择以刷新详情
            self.on_protocol_selected(protocol_name)
        else:
            self._view.log_error(f"协议 {protocol_name} 配置加载失败")
            if info:
                self._view.update_protocol_list_item(info)

    def on_select_log_clicked(self) -> None:
        """用户点击了「选择日志文件」"""
        protocol_name = self._view.get_selected_protocol_name()
        if not protocol_name:
            self._view.show_warning("提示", "请先选择协议")
            return

        # 确定初始目录
        if self._settings:
            last_dir = self._settings.value("last_log_dir", str(Path.home()))
        else:
            last_dir = str(Path.home())

        # 打开文件选择对话框
        file_path = self._view.show_file_dialog(
            title=f"选择 {protocol_name} 协议的日志文件",
            directory=last_dir,
            file_filter=LOG_FILE_FILTER,
        )

        if file_path:
            # 保存目录和日志路径
            if self._settings:
                self._settings.setValue("last_log_dir", str(Path(file_path).parent))
                self._settings.setValue(f"last_log/{protocol_name}", file_path)

            self._protocol_model.set_log_path(protocol_name, file_path)
            self.on_protocol_selected(protocol_name)
            self._view.log_info(f"已选择日志文件: {file_path}")

    def on_open_output_dir(self) -> None:
        """用户点击了「打开输出目录」"""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        open_directory(self._output_dir)

    def on_log_file_dropped(self, file_path: str) -> None:
        """
        用户拖拽了日志文件

        Args:
            file_path: 日志文件路径
        """
        protocol_name = self._view.get_selected_protocol_name()
        if not protocol_name:
            self._view.show_warning("提示", "请先选择一个协议，再拖入日志文件")
            return

        self._protocol_model.set_log_path(protocol_name, file_path)
        if self._settings:
            self._settings.setValue(f"last_log/{protocol_name}", file_path)
        self.on_protocol_selected(protocol_name)
        self._view.log_info(f"已通过拖拽加载日志文件: {file_path}")

    # ============== 内部回调 ==============

    def _on_parse_finished(self, success: bool, message: str, output_path: str) -> None:
        """
        解析完成回调

        注意：通过 QueuedConnection，确保此回调在主线程事件循环执行，
        因此可以安全调用 _parse_thread.wait()。

        Args:
            success: 是否成功
            message: 消息
            output_path: 输出文件路径
        """
        self._view.set_parsing_state(False)

        # 在销毁 worker 之前，保存波形条目数据
        self._last_wave_entries = []
        if self._parse_worker and hasattr(self._parse_worker, '_wave_entries'):
            self._last_wave_entries = self._parse_worker._wave_entries

        # 清理线程（QueuedConnection 确保此处在主线程执行，wait() 安全）
        if self._parse_thread:
            self._parse_thread.quit()
            self._parse_thread.wait()
            self._parse_thread.deleteLater()
            self._parse_thread = None
            self._parse_worker = None

        protocol_name = self._view.get_selected_protocol_name() or ""
        if success:
            self._view.emit_status_changed(
                f"✅ 解析完成 | {protocol_name} | "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            if output_path:
                action = self._view.show_parse_complete_dialog(output_path)
                if action == "open_file":
                    open_file(output_path)
                elif action == "open_wave":
                    self._open_wave_replay_with_parsed_data(protocol_name)
        else:
            self._view.emit_status_changed(f"❌ 解析失败 | {protocol_name}")

    def _open_wave_replay_with_parsed_data(self, protocol_name: str) -> None:
        """
        将解析结果传递给数据回放页面

        通过 View 接口的 request_wave_replay() 发起跳转请求，
        由主窗口在组装层连接信号完成实际跳转。
        """
        # 从已完成的 worker 中获取波形条目
        if not hasattr(self, '_last_wave_entries') or not self._last_wave_entries:
            self._view.log_warning("无可用的解析数据用于波形展示")
            return

        source_name = f"普通解析 - {protocol_name}"
        self._view.request_wave_replay(self._last_wave_entries, source_name)
        self._view.log_info(
            f"已将 {len(self._last_wave_entries)} 个数据点发送到波形回放页面"
        )

    # ============== 资源管理 ==============

    def cleanup(self) -> None:
        """清理资源（停止工作线程）

        关闭窗口时调用，确保解析线程安全退出：
        1. 请求工作线程停止
        2. 通知线程事件循环退出
        3. 等待线程自然结束（最多5秒）
        4. 超时则强制终止（避免 QThread: Destroyed while running）
        """
        if self._parse_worker:
            self._parse_worker.stop()
        if self._parse_thread and self._parse_thread.isRunning():
            self._parse_thread.quit()
            if not self._parse_thread.wait(5000):
                # 5秒内未结束，强制终止
                self._parse_thread.terminate()
                self._parse_thread.wait(2000)
