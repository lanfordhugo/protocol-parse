"""
文件名称: protocol_panel_presenter.py
内容摘要: 协议面板 Presenter - 协调协议面板 View 和 Model
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import Optional

from gui.managers import ProtocolManager
from gui.models import ProtocolInfo
from gui.views import IProtocolPanelView


class ProtocolPanelPresenter:
    """协议面板 Presenter

    职责：
    - 响应协议面板的用户事件
    - 协调协议列表加载
    - 管理协议选择状态
    - 协调其他 Presenter 更新
    """

    def __init__(self, view: IProtocolPanelView, protocol_manager: ProtocolManager):
        """初始化 Presenter

        Args:
            view: 协议面板 View 接口
            protocol_manager: 协议管理器
        """
        self._view = view
        self._protocol_manager = protocol_manager
        self._current_protocol: Optional[str] = None

        # 连接 View 信号
        self._view.protocol_selected.connect(self._on_protocol_selected)

    def load_protocols(self) -> None:
        """加载协议列表"""
        try:
            protocols = self._protocol_manager.discover_protocols()
            self._view.load_protocols(protocols)
        except Exception as e:
            self._view.show_error(f"加载协议失败: {e}")

    def select_protocol(self, name: str) -> None:
        """选择协议

        Args:
            name: 协议名称
        """
        try:
            # 验证协议是否存在
            if not self._protocol_manager.has_protocol(name):
                self._view.show_error(f"协议不存在: {name}")
                return

            # 验证协议配置
            is_valid = self._protocol_manager.validate_protocol(name)
            if not is_valid:
                self._view.show_warning(f"协议配置可能存在错误: {name}")

            # 更新当前协议
            self._current_protocol = name

            # 发射信号（由 View 处理）
            self._view.protocol_selected.emit(name)

        except Exception as e:
            self._view.show_error(f"选择协议失败: {e}")

    def refresh_protocols(self) -> None:
        """刷新协议列表"""
        try:
            protocols = self._protocol_manager.refresh_protocols()
            self._view.load_protocols(protocols)
        except Exception as e:
            self._view.show_error(f"刷新协议列表失败: {e}")

    def get_current_protocol(self) -> Optional[str]:
        """获取当前选择的协议

        Returns:
            当前协议名称，如果未选择则返回 None
        """
        return self._current_protocol

    def get_protocol_info(self, name: str) -> Optional[ProtocolInfo]:
        """获取协议信息

        Args:
            name: 协议名称

        Returns:
            协议信息，如果不存在则返回 None
        """
        try:
            return self._protocol_manager.get_protocol_info(name)
        except Exception as e:
            self._view.show_error(f"获取协议信息失败: {e}")
            return None

    def _on_protocol_selected(self, protocol_name: str) -> None:
        """处理协议选择事件

        Args:
            protocol_name: 协议名称
        """
        # 更新当前协议
        self._current_protocol = protocol_name
