# gui/widgets/searchable_list.py
"""
文件名称: searchable_list.py
内容摘要: 可搜索列表组件，支持模糊匹配过滤
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from typing import List, Dict, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QColor


class ProtocolItem:
    """协议项数据类"""
    
    def __init__(
        self,
        name: str,
        config_valid: bool = True,
        log_exists: bool = True,
        log_size: int = 0
    ):
        self.name = name
        self.config_valid = config_valid
        self.log_exists = log_exists
        self.log_size = log_size


class SearchableListWidget(QWidget):
    """可搜索的协议列表组件"""
    
    # 信号：选中协议变化
    protocol_selected = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items: Dict[str, ProtocolItem] = {}
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 输入协议名搜索...")
        self.search_input.setClearButtonEnabled(True)
        layout.addWidget(self.search_input)
        
        # 列表（简洁样式，带分隔线）
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #2a2a2a;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # 底部统计
        self.count_label = QLabel("已发现 0 个协议配置")
        self.count_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.count_label)
    
    def _connect_signals(self):
        """连接信号"""
        self.search_input.textChanged.connect(self._on_search_changed)
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
    
    def _on_search_changed(self, text: str):
        """搜索文本变化时过滤列表"""
        text = text.lower().strip()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            protocol_name = item.data(Qt.UserRole)
            # 模糊匹配
            visible = text in protocol_name.lower() if text else True
            item.setHidden(not visible)
    
    def _on_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """选中项变化时发出信号"""
        if current:
            protocol_name = current.data(Qt.UserRole)
            self.protocol_selected.emit(protocol_name)
    
    def set_protocols(self, protocols: List[ProtocolItem]):
        """设置协议列表"""
        self._items.clear()
        self.list_widget.clear()
        
        for protocol in protocols:
            self._items[protocol.name] = protocol
            item = QListWidgetItem()
            item.setText(protocol.name)
            item.setData(Qt.UserRole, protocol.name)
            self.list_widget.addItem(item)
        
        self.count_label.setText(f"已发现 {len(protocols)} 个协议配置")
        
        # 不默认选中，由主窗口控制
        pass
    
    def get_selected_protocol(self) -> Optional[str]:
        """获取当前选中的协议名称"""
        current = self.list_widget.currentItem()
        if current:
            return current.data(Qt.UserRole)
        return None
    
    def get_protocol_item(self, name: str) -> Optional[ProtocolItem]:
        """获取协议项信息"""
        return self._items.get(name)
    
    def refresh_item(self, protocol: ProtocolItem):
        """刷新单个协议项的显示"""
        self._items[protocol.name] = protocol
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == protocol.name:
                item.setText(protocol.name)
                break
