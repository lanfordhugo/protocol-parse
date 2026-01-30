"""
文件名称: i_protocol_panel_view.py
内容摘要: 协议列表面板 View 接口
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import List, Optional

from gui.widgets.searchable_list import ProtocolItem


class IProtocolPanelView:
    """协议列表面板接口

    职责：
    - 显示协议列表
    - 捕获用户选择事件
    - 更新协议状态显示

    注意：Signal 在实现类中定义，不在接口中定义
    """

    # === Presenter 调用的方法（更新 UI） ===

    def load_protocols(self, protocols: List[ProtocolItem]) -> None:
        """加载协议列表

        Args:
            protocols: 协议项列表
        """
        raise NotImplementedError

    def set_selected_protocol(self, protocol_name: str) -> None:
        """设置选中的协议

        Args:
            protocol_name: 协议名称
        """
        raise NotImplementedError

    def update_protocol_status(
        self,
        protocol_name: str,
        config_valid: bool,
        log_exists: bool,
        log_size: int
    ) -> None:
        """更新协议状态显示

        Args:
            protocol_name: 协议名称
            config_valid: 配置是否有效
            log_exists: 日志文件是否存在
            log_size: 日志文件大小（字节）
        """
        raise NotImplementedError

    def get_selected_protocol(self) -> Optional[str]:
        """获取当前选中的协议名称

        Returns:
            协议名称，未选中时返回 None
        """
        raise NotImplementedError
