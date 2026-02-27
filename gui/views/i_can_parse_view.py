"""
文件名称: i_can_parse_view.py
内容摘要: CAN解析页面的 View 接口定义（MVP 模式中的 V 接口）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class ICanParsePageView(Protocol):
    """
    CAN解析页面的 View 接口（Protocol 协议类）

    与 NormalParsePage 不同，CAN解析页面不需要协议列表，
    固定使用 v6_can 协议配置。
    """

    # ============== 文件操作 ==============

    def get_selected_log_path(self) -> Optional[str]:
        """获取当前选中的日志文件路径"""
        ...

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径显示"""
        ...

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前的过滤设置"""
        ...

    def set_parsing_state(self, is_parsing: bool) -> None:
        """设置解析状态（控制按钮的启用/禁用）"""
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
        """设置进度"""
        ...

    # ============== 对话框操作 ==============

    def show_warning(self, title: str, message: str) -> None:
        """显示警告对话框"""
        ...

    def show_parse_complete_dialog(self, output_path: str) -> str:
        """显示解析完成对话框，返回用户动作"""
        ...

    def show_file_dialog(
        self,
        title: str,
        directory: str,
        file_filter: str,
    ) -> Optional[str]:
        """显示文件选择对话框"""
        ...

    # ============== 状态通知 ==============

    def emit_status_changed(self, message: str) -> None:
        """发送状态变化信号"""
        ...
