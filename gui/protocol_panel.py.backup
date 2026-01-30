# gui/protocol_panel.py
"""
文件名称: protocol_panel.py
内容摘要: 左侧协议列表面板，包含可搜索的协议列表
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox
from PySide6.QtCore import Signal

from .widgets.searchable_list import SearchableListWidget, ProtocolItem


class ProtocolPanel(QWidget):
    """左侧协议列表面板"""
    
    # 信号：协议选择变化
    protocol_selected = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._protocols: Dict[str, Dict[str, Any]] = {}
        self._setup_ui()
    
    def _setup_ui(self):
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
    
    def _on_protocol_selected(self, protocol_name: str):
        """协议选择变化时转发信号"""
        self.protocol_selected.emit(protocol_name)
    
    def load_protocols(self, configs_dir: Path):
        """加载协议列表（只扫描配置，日志由用户选择）"""
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
        
        self.protocol_list.set_protocols(protocol_items)
    
    def get_protocol_info(self, protocol_name: str) -> Optional[Dict[str, Any]]:
        """获取协议信息"""
        return self._protocols.get(protocol_name)
    
    def get_selected_protocol(self) -> Optional[str]:
        """获取当前选中的协议"""
        return self.protocol_list.get_selected_protocol()
    
    def update_protocol_status(
        self,
        protocol_name: str,
        config_valid: bool,
        log_exists: Optional[bool] = None,
        log_size: Optional[int] = None
    ):
        """更新协议状态"""
        if protocol_name not in self._protocols:
            return
        
        info = self._protocols[protocol_name]
        info['config_valid'] = config_valid
        
        if log_exists is not None:
            info['log_exists'] = log_exists
        if log_size is not None:
            info['log_size'] = log_size
        
        # 更新列表显示
        item = ProtocolItem(
            name=protocol_name,
            config_valid=info['config_valid'],
            log_exists=info['log_exists'],
            log_size=info['log_size']
        )
        self.protocol_list.refresh_item(item)
    
    def refresh(self, configs_dir: Path):
        """刷新协议列表"""
        self.load_protocols(configs_dir)
    
    def set_log_path(self, protocol_name: str, log_path: str):
        """设置协议的日志路径"""
        if protocol_name not in self._protocols:
            return
        
        info = self._protocols[protocol_name]
        log_file = Path(log_path)
        log_exists = log_file.exists()
        log_size = log_file.stat().st_size if log_exists else 0
        
        info['log_path'] = log_path
        info['log_exists'] = log_exists
        info['log_size'] = log_size
        
        # 更新列表显示
        item = ProtocolItem(
            name=protocol_name,
            config_valid=info['config_valid'],
            log_exists=log_exists,
            log_size=log_size
        )
        self.protocol_list.refresh_item(item)
