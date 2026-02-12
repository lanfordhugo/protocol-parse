"""
文件名称: i_normal_parse_view.py
内容摘要: NormalParsePage 的 View 接口定义（MVP 模式中的 V 接口）
当前版本: v1.0.1
作者: lanford
创建日期: 2025-02-08
修改说明: 使用 Protocol 替代 ABC 以避免与 QWidget 的元类冲突
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from gui.models.protocol_model import ProtocolDetail, ProtocolInfo


@runtime_checkable
class INormalParsePageView(Protocol):
    """
    普通解析页面的 View 接口（Protocol 协议类）

    定义 Presenter 可以调用的 View 操作方法。
    NormalParsePage 实现此接口，Presenter 通过此接口更新 View。

    使用 Protocol 而非 ABC，因为 QWidget 的 Shiboken 元类与 ABCMeta 不兼容。
    Protocol 使用结构化子类型（structural subtyping），无需显式继承。
    """

    # ============== 协议列表操作 ==============

    def display_protocols(self, protocols: List[ProtocolInfo]) -> None:
        """
        显示协议列表

        Args:
            protocols: 协议信息列表
        """
        ...

    def update_protocol_list_item(self, info: ProtocolInfo) -> None:
        """
        更新单个协议列表项的显示状态

        Args:
            info: 协议信息
        """
        ...

    def select_protocol_by_name(self, name: str) -> None:
        """
        在列表中选中指定协议

        Args:
            name: 协议名称
        """
        ...

    def get_selected_protocol_name(self) -> Optional[str]:
        """
        获取当前选中的协议名称

        Returns:
            协议名称，未选中时返回 None
        """
        ...

    # ============== 详情面板操作 ==============

    def display_protocol_detail(self, detail: ProtocolDetail) -> None:
        """
        显示协议详细信息

        Args:
            detail: 协议详细信息
        """
        ...

    def get_filter_settings(self) -> Dict[str, Any]:
        """
        获取当前的过滤设置

        Returns:
            过滤设置字典
        """
        ...

    def set_parsing_state(self, is_parsing: bool) -> None:
        """
        设置解析状态（控制按钮的启用/禁用）

        Args:
            is_parsing: 是否正在解析
        """
        ...

    # ============== 日志面板操作 ==============

    def log_info(self, message: str) -> None:
        """显示信息日志"""
        ...

    def log_success(self, message: str) -> None:
        """显示成功日志"""
        ...

    def log_warning(self, message: str) -> None:
        """显示警告日志"""
        ...

    def log_error(self, message: str) -> None:
        """显示错误日志"""
        ...

    def reset_progress(self) -> None:
        """重置进度条"""
        ...

    def set_progress(self, current: int, total: int) -> None:
        """
        设置进度

        Args:
            current: 当前进度
            total: 总进度
        """
        ...

    # ============== 对话框操作 ==============

    def show_warning(self, title: str, message: str) -> None:
        """
        显示警告对话框

        Args:
            title: 标题
            message: 消息内容
        """
        ...

    def show_parse_complete_dialog(self, output_path: str) -> str:
        """
        显示解析完成确认对话框

        Args:
            output_path: 输出文件路径

        Returns:
            用户选择的动作: 'open_file' / 'open_wave' / 'close'
        """
        ...

    def show_file_dialog(
        self,
        title: str,
        directory: str,
        file_filter: str,
    ) -> Optional[str]:
        """
        显示文件选择对话框

        Args:
            title: 对话框标题
            directory: 初始目录
            file_filter: 文件过滤器

        Returns:
            选中的文件路径，取消时返回 None
        """
        ...

    # ============== 页面跳转请求 ==============

    def request_wave_replay(self, entries: list, source_name: str) -> None:
        """
        请求跳转到波形回放页面并加载数据

        由 Presenter 调用，View 通过信号通知主窗口完成实际跳转。

        Args:
            entries: 解析条目列表 [(timestamp_str, content, cmd_id, direction), ...]
            source_name: 数据源名称
        """
        ...

    # ============== 状态通知 ==============

    def emit_status_changed(self, message: str) -> None:
        """
        发送状态变化信号（通知主窗口更新状态栏）

        Args:
            message: 状态消息
        """
        ...
