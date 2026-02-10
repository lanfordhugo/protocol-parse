"""
文件名称: i_tcp_server_view.py
内容摘要: TcpServerPage 的 View 接口定义（MVP 模式中的 V 接口）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from tcp_log.models.tcp_server_model import EntryData, StatsData, CmdStatsItem


@runtime_checkable
class ITcpServerPageView(Protocol):
    """
    TCP 服务端页面的 View 接口（Protocol 协议类）

    使用 Protocol 而非 ABC，避免与 QWidget Shiboken 元类冲突。
    """

    # ============== 服务器状态 ==============

    def update_server_state(self, state_text: str) -> None:
        """更新服务器状态显示"""
        ...

    def get_server_config(self) -> Dict[str, Any]:
        """
        获取服务器配置

        Returns:
            包含 host, port 的字典
        """
        ...

    # ============== 协议管理 ==============

    def set_protocol_list(self, names: List[str]) -> None:
        """设置协议下拉列表"""
        ...

    # ============== 解析结果表格 ==============

    def add_result_row(
        self,
        entry_data: EntryData,
        summary: str,
    ) -> None:
        """添加一行解析结果"""
        ...

    def remove_oldest_rows(self, count: int) -> None:
        """移除最旧的 N 行"""
        ...

    def clear_result_table(self) -> None:
        """清空结果表格"""
        ...

    def refresh_result_table(
        self,
        entries: List[EntryData],
        summaries: List[str],
    ) -> None:
        """刷新整个结果表格"""
        ...

    # ============== 详情面板 ==============

    def show_entry_detail(self, detail_text: str) -> None:
        """显示条目详情"""
        ...

    # ============== 统计 ==============

    def update_stats_summary(self, stats: StatsData) -> None:
        """更新统计摘要"""
        ...

    def update_stats_detail(self, items: List[CmdStatsItem]) -> None:
        """更新统计详情表格"""
        ...

    def update_cache_label(self, current: int, max_count: int) -> None:
        """更新缓存条数标签"""
        ...

    # ============== 过滤 ==============

    def add_filter_option(self, cmd_text: str) -> None:
        """添加过滤选项"""
        ...

    def get_filter_cmd(self) -> Optional[int]:
        """获取当前过滤的命令 ID"""
        ...

    def is_success_only(self) -> bool:
        """是否仅显示成功"""
        ...

    def is_auto_scroll(self) -> bool:
        """是否自动滚动"""
        ...

    def reset_filter(self) -> None:
        """重置过滤器"""
        ...

    # ============== 保存选项 ==============

    def is_save_log_enabled(self) -> bool:
        """是否启用日志保存"""
        ...

    def is_save_result_enabled(self) -> bool:
        """是否启用结果保存"""
        ...

    # ============== 对话框/通知 ==============

    def show_warning(self, title: str, message: str) -> None:
        """显示警告对话框"""
        ...

    def emit_status_changed(self, message: str) -> None:
        """发送状态变化信号"""
        ...

    # ============== 波形数据转发 ==============

    def emit_entry_parsed(
        self,
        timestamp_str: str,
        parsed_content: Optional[dict],
        cmd_id: Optional[int],
        direction: Optional[str],
        success: bool,
    ) -> None:
        """
        转发已解析的数据条目（供波形窗口使用）

        Args:
            timestamp_str: 时间戳字符串
            parsed_content: 解析后的内容字典
            cmd_id: 命令ID
            direction: 数据方向
            success: 是否解析成功
        """
        ...
