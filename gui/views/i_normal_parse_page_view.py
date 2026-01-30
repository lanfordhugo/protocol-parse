"""
文件名称: i_normal_parse_page_view.py
内容摘要: 普通解析页面 View 接口
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import Dict, Any


class INormalParsePageView:
    """普通解析页面接口

    职责：
    - 协调协议面板、详情面板、日志面板
    - 捕获页面级用户事件
    - 显示页面级状态

    注意：Signal 在实现类中定义，不在接口中定义
    """

    # === Presenter 调用的方法（更新 UI） ===

    def set_parse_state(self, is_parsing: bool) -> None:
        """设置解析状态

        Args:
            is_parsing: 是否正在解析
        """
        raise NotImplementedError

    def show_error_message(self, title: str, message: str) -> None:
        """显示错误消息对话框

        Args:
            title: 标题
            message: 消息内容
        """
        raise NotImplementedError

    def show_info_message(self, title: str, message: str) -> None:
        """显示信息消息对话框

        Args:
            title: 标题
            message: 消息内容
        """
        raise NotImplementedError

    def show_warning_message(self, title: str, message: str) -> None:
        """显示警告消息对话框

        Args:
            title: 标题
            message: 消息内容
        """
        raise NotImplementedError

    def get_protocol_panel_view(self):
        """获取协议面板 View 接口

        Returns:
            IProtocolPanelView 实例
        """
        raise NotImplementedError

    def get_detail_panel_view(self):
        """获取详情面板 View 接口

        Returns:
            IDetailPanelView 实例
        """
        raise NotImplementedError

    def get_log_panel_view(self):
        """获取日志面板 View 接口

        Returns:
            ILogPanelView 实例
        """
        raise NotImplementedError
