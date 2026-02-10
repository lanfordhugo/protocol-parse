"""
文件名称: tcp_server_presenter.py
内容摘要: TCP 服务端页面的 Presenter（MVP 模式中的 P）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import logging
from typing import Optional

from tcp_log.models.tcp_server_model import TcpServerModel
from tcp_log.tcp_server import TcpLogServer, ClientInfo
from tcp_log.log_entry_parser import LogEntry

logger = logging.getLogger(__name__)


class TcpServerPresenter:
    """
    TCP 服务端页面 Presenter

    职责：
    - 响应 View 的用户交互事件
    - 调用 Model 层处理业务逻辑
    - 通过 View 接口更新 UI 展示
    - 管理 TcpLogServer 和 SignalBridge 的连接
    """

    def __init__(self, view, model: TcpServerModel, server: TcpLogServer):
        """
        初始化 Presenter

        Args:
            view: ITcpServerPageView 接口实例
            model: TCP 服务端业务模型
            server: TCP 日志服务器实例
        """
        self._view = view
        self._model = model
        self._server = server

    def initialize(self) -> None:
        """初始化：扫描协议列表"""
        protocol_names = self._model.scan_protocols()
        self._view.set_protocol_list(protocol_names)

    # ============== 用户交互事件 ==============

    def on_protocol_changed(self, protocol_name: str) -> None:
        """
        用户切换协议

        Args:
            protocol_name: 协议名称
        """
        success, message = self._model.load_protocol(protocol_name)
        self._view.emit_status_changed(message)

    def on_start_clicked(self) -> None:
        """用户点击「启动服务」"""
        if not self._model.has_protocol:
            self._view.show_warning("警告", "请先选择协议")
            return

        config = self._view.get_server_config()
        self._server.start(config["host"], config["port"])

    def on_stop_clicked(self) -> None:
        """用户点击「停止服务」"""
        self._server.stop()

    def on_clear_results(self) -> None:
        """用户点击「清空」"""
        self._model.clear_entries()
        self._view.clear_result_table()
        self._view.reset_filter()

    def on_reset_stats(self) -> None:
        """用户点击「重置统计」"""
        self._model.reset_stats()
        self._server.reset_stats()
        stats = self._model.get_stats()
        self._view.update_stats_summary(stats)

    def on_selection_changed(self, entry_index: int) -> None:
        """
        用户选中表格某行

        Args:
            entry_index: 对应 all_entries 中的索引（存储在 UserRole 中）
        """
        entries = self._model.all_entries
        if 0 <= entry_index < len(entries):
            ed = entries[entry_index]
            detail_text = TcpServerModel.format_detail(
                ed.entry, ed.parsed, ed.success
            )
            self._view.show_entry_detail(detail_text)

    def on_filter_changed(self) -> None:
        """用户切换过滤条件"""
        self._refresh_table()

    def on_toggle_stats_detail(self, show: bool) -> None:
        """
        用户展开/收起统计详情

        Args:
            show: 是否显示详情
        """
        if show:
            items = self._model.get_cmd_stats_detail()
            self._view.update_stats_detail(items)

    # ============== 服务器事件回调（由 SignalBridge 转发） ==============

    def on_server_state_changed(self, state_text: str) -> None:
        """服务器状态变化"""
        self._view.update_server_state(state_text)

    def on_client_connected(self, client_info: ClientInfo) -> None:
        """客户端连接"""
        self._view.emit_status_changed(
            f"客户端已连接: {client_info.address}:{client_info.port}"
        )

    def on_client_disconnected(self) -> None:
        """客户端断开"""
        self._view.emit_status_changed("客户端已断开")

    def on_entry_received(self, entry: LogEntry) -> None:
        """
        收到日志条目（核心事件处理）

        Args:
            entry: 日志条目
        """
        # 1. Model 解析条目并更新统计
        entry_data = self._model.parse_entry(entry)

        # 2. 缓存管理
        removed = self._model.trim_cache_if_needed()
        if removed > 0:
            self._view.remove_oldest_rows(removed)

        # 3. 更新缓存标签
        self._view.update_cache_label(self._model.cache_count, self._model.max_cache)

        # 4. 保存（如果启用）
        if self._view.is_save_log_enabled():
            error = self._model.save_log_entry(entry)
            if error:
                self._view.emit_status_changed(error)

        if self._view.is_save_result_enabled():
            error = self._model.save_parsed_result(
                entry, entry_data.parsed, entry_data.success
            )
            if error:
                self._view.emit_status_changed(error)

        # 5. 转发已解析数据（供波形窗口使用）
        self._view.emit_entry_parsed(
            timestamp_str=entry.timestamp,
            parsed_content=entry_data.parsed if entry_data.success else None,
            cmd_id=entry.cmd_id,
            direction=entry.direction,
            success=entry_data.success,
        )

        # 6. 过滤判断并显示
        filter_cmd = self._view.get_filter_cmd()
        success_only = self._view.is_success_only()
        should_show = TcpServerModel.should_show_entry(
            entry.cmd_id, entry_data.success, filter_cmd, success_only
        )

        if should_show:
            summary = TcpServerModel.generate_summary(entry_data.parsed)
            if not entry_data.success and not entry_data.parsed:
                summary = f"[原始] {entry.hex_data[:50]}..."
            self._view.add_result_row(entry_data, summary)

        # 6. 更新过滤下拉框（新命令）
        cmd_text = f"cmd{entry.cmd_id}"
        self._view.add_filter_option(cmd_text)

        # 7. 更新统计
        stats = self._model.get_stats()
        self._view.update_stats_summary(stats)

    def on_log_message(self, message: str) -> None:
        """服务器日志消息"""
        self._view.emit_status_changed(message)

    def on_error_message(self, message: str) -> None:
        """服务器错误消息"""
        self._view.emit_status_changed(f"错误: {message}")

    # ============== 内部方法 ==============

    def _refresh_table(self) -> None:
        """根据当前过滤条件刷新表格"""
        filter_cmd = self._view.get_filter_cmd()
        success_only = self._view.is_success_only()

        entries = []
        summaries = []
        for ed in self._model.all_entries:
            if TcpServerModel.should_show_entry(
                ed.entry.cmd_id, ed.success, filter_cmd, success_only
            ):
                entries.append(ed)
                summary = TcpServerModel.generate_summary(ed.parsed)
                if not ed.success and not ed.parsed:
                    summary = f"[原始] {ed.entry.hex_data[:50]}..."
                summaries.append(summary)

        self._view.refresh_result_table(entries, summaries)
