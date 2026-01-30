# gui/protocol_panel.py
"""
文件名称: protocol_panel.py
内容摘要: 左侧协议列表面板，包含可搜索的协议列表
当前版本: v1.1.0 (MVP 重构)
作者: lanford
创建日期: 2024-12-24
重构日期: 2026-01-29
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox
from PySide6.QtCore import Signal

from .widgets.searchable_list import SearchableListWidget, ProtocolItem
from .views import IProtocolPanelView


class ProtocolPanel(QWidget, IProtocolPanelView):
    """左侧协议列表面板（MVP 架构 - View 层）

    职责：
    - 显示协议列表
    - 捕获用户选择事件
    - 更新协议状态显示

    MVP 重构说明：
    - 实现 IProtocolPanelView 接口
    - 移除业务逻辑到 Presenter（Phase 2）
    - 保留向后兼容的旧接口
    """

    # === 信号：用户事件（由 IProtocolPanelView 接口定义） ===
    protocol_selected = Signal(str)  # 用户选择协议

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._protocols: Dict[str, Dict[str, Any]] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 协议选择分组
        group = QGroupBox("协议选择")
        group_layout = QVBoxLayout(group)

        # 可搜索列表
        self.protocol_list = SearchableListWidget()
        self.protocol_list.protocol_selected.connect(self._on_protocol_selected)
        group_layout.addWidget(self.protocol_list)

        layout.addWidget(group)

    # ==================== View 接口实现 ====================

    def load_protocols(self, protocols: List[ProtocolItem]) -> None:
        """加载协议列表（MVP 接口）

        Args:
            protocols: 协议项列表
        """
        self.protocol_list.set_protocols(protocols)

    def set_selected_protocol(self, protocol_name: str) -> None:
        """设置选中的协议（MVP 接口）

        Args:
            protocol_name: 协议名称
        """
        self.protocol_list.set_selected_protocol(protocol_name)

    def update_protocol_status(
        self,
        protocol_name: str,
        config_valid: bool,
        log_exists: bool,
        log_size: int
    ) -> None:
        """更新协议状态显示（MVP 接口）

        Args:
            protocol_name: 协议名称
            config_valid: 配置是否有效
            log_exists: 日志文件是否存在
            log_size: 日志文件大小（字节）
        """
        if protocol_name not in self._protocols:
            return

        info = self._protocols[protocol_name]
        info['config_valid'] = config_valid
        info['log_exists'] = log_exists
        info['log_size'] = log_size

        # 更新列表显示
        item = ProtocolItem(
            name=protocol_name,
            config_valid=config_valid,
            log_exists=log_exists,
            log_size=log_size
        )
        self.protocol_list.refresh_item(item)

    def get_selected_protocol(self) -> Optional[str]:
        """获取当前选中的协议名称（MVP 接口）

        Returns:
            协议名称，未选中时返回 None
        """
        return self.protocol_list.get_selected_protocol()

    # ==================== 事件处理 ====================

    def _on_protocol_selected(self, protocol_name: str) -> None:
        """协议选择变化时转发信号"""
        self.protocol_selected.emit(protocol_name)

    # ==================== 向后兼容接口（Phase 2 后移除） ====================

    def load_protocols_from_dir(self, configs_dir: Path) -> None:
        """加载协议列表（旧接口 - 保持向后兼容）

        TODO: Phase 2 后移除，使用 Presenter.load_protocols() 代替

        Args:
            configs_dir: 配置目录路径
        """
        # ❌ 业务逻辑：扫描目录、验证配置
        # TODO: Phase 2 移除到 Presenter
        self._protocols.clear()
        protocol_items: List[ProtocolItem] = []

        if not configs_dir.exists():
            return

        for protocol_dir in sorted(configs_dir.iterdir()):
            if not protocol_dir.is_dir():
                continue

            yaml_config = protocol_dir / "protocol.yaml"
            if not yaml_config.exists():
                continue

            protocol_name = protocol_dir.name

            # 存储协议信息（日志路径由用户选择）
            self._protocols[protocol_name] = {
                'config_path': str(yaml_config),
                'log_path': '',  # 用户选择
                'log_exists': False,
                'log_size': 0,
                'config_valid': True,  # 初始假设有效，后续验证更新
            }

            # 创建列表项（日志状态显示为待选择）
            item = ProtocolItem(
                name=protocol_name,
                config_valid=True,
                log_exists=False,
                log_size=0
            )
            protocol_items.append(item)

        # 调用 MVP 接口
        self.load_protocols(protocol_items)

    def get_protocol_info(self, protocol_name: str) -> Optional[Dict[str, Any]]:
        """获取协议信息（旧接口 - 保持向后兼容）

        TODO: Phase 2 后移除，由 Model 层提供

        Args:
            protocol_name: 协议名称

        Returns:
            协议信息字典
        """
        # TODO: Phase 2 移除，由 Model 层提供
        return self._protocols.get(protocol_name)

    def refresh(self, configs_dir: Path) -> None:
        """刷新协议列表（旧接口 - 保持向后兼容）

        TODO: Phase 2 后移除

        Args:
            configs_dir: 配置目录路径
        """
        self.load_protocols_from_dir(configs_dir)

    def set_log_path(self, protocol_name: str, log_path: str) -> None:
        """设置协议的日志路径（旧接口 - 保持向后兼容）

        TODO: Phase 2 后移除

        Args:
            protocol_name: 协议名称
            log_path: 日志文件路径
        """
        if protocol_name not in self._protocols:
            return

        info = self._protocols[protocol_name]
        log_file = Path(log_path)
        log_exists = log_file.exists()
        log_size = log_file.stat().st_size if log_exists else 0

        info['log_path'] = log_path
        info['log_exists'] = log_exists
        info['log_size'] = log_size

        # 调用 MVP 接口更新显示
        self.update_protocol_status(
            protocol_name,
            info['config_valid'],
            log_exists,
            log_size
        )
