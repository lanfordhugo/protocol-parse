# gui/widgets/multi_select_combo.py
"""
文件名称: multi_select_combo.py
内容摘要: 可搜索的多选下拉框组件，支持模糊匹配和多项选择
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QPushButton, QFrame, QCheckBox,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QFocusEvent


class MultiSelectPopup(QFrame):
    """多选弹出框"""
    
    selection_changed = Signal(list)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._items: List[Tuple[str, str]] = []  # [(value, display_text), ...]
        self._selected: set = set()
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 输入搜索...")
        self.search_input.textChanged.connect(self._filter_items)
        layout.addWidget(self.search_input)
        
        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(150)
        self.list_widget.setMaximumHeight(250)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.list_widget.itemClicked.connect(self._on_item_clicked)  # 点击整行切换选中
        layout.addWidget(self.list_widget)
        
        # 底部操作
        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all)
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def set_items(self, items: List[Tuple[str, str]]):
        """设置选项列表 [(value, display_text), ...]"""
        self._items = items
        self._refresh_list()
    
    def _refresh_list(self):
        """刷新列表显示"""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        filter_text = self.search_input.text().lower().strip()
        
        for value, display_text in self._items:
            # 模糊匹配
            if filter_text and filter_text not in display_text.lower():
                continue
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if value in self._selected else Qt.Unchecked
            )
            self.list_widget.addItem(item)
        
        self.list_widget.blockSignals(False)
    
    def _filter_items(self, text: str):
        """过滤选项"""
        self._refresh_list()
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """点击整行切换选中状态"""
        # 切换选中状态
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
    
    def _on_item_changed(self, item: QListWidgetItem):
        """选项状态变化"""
        value = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            self._selected.add(value)
        else:
            self._selected.discard(value)
        self.selection_changed.emit(list(self._selected))
    
    def _select_all(self):
        """全选当前可见项"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked)
    
    def _clear_all(self):
        """清除所有选择"""
        self._selected.clear()
        self._refresh_list()
        self.selection_changed.emit([])
    
    def get_selected(self) -> List[str]:
        """获取已选择的值列表"""
        return list(self._selected)
    
    def set_selected(self, values: List[str]):
        """设置已选择的值"""
        self._selected = set(values)
        self._refresh_list()


class MultiSelectComboBox(QWidget):
    """可搜索的多选下拉框"""
    
    selection_changed = Signal(list)
    
    def __init__(
        self,
        placeholder: str = "点击选择...",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._placeholder = placeholder
        self._items: List[Tuple[str, str]] = []
        self._popup: Optional[MultiSelectPopup] = None
        self._display_map: Dict[str, str] = {}  # value -> display_text
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 显示框
        self.display_edit = QLineEdit()
        self.display_edit.setReadOnly(True)
        self.display_edit.setPlaceholderText(self._placeholder)
        self.display_edit.setCursor(Qt.PointingHandCursor)
        self.display_edit.mousePressEvent = self._on_display_clicked
        layout.addWidget(self.display_edit)
    
    def _on_display_clicked(self, event):
        """点击显示框时打开弹窗"""
        self._toggle_popup()
    
    def _toggle_popup(self):
        """切换弹窗显示"""
        if self._popup and self._popup.isVisible():
            self._popup.hide()
            return
        
        if not self._popup:
            self._popup = MultiSelectPopup()
            self._popup.selection_changed.connect(self._on_selection_changed)
        
        self._popup.set_items(self._items)
        
        # 定位弹窗
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.setMinimumWidth(self.width())
        self._popup.move(global_pos)
        self._popup.show()
        self._popup.search_input.setFocus()
    
    def _on_selection_changed(self, selected: List[str]):
        """选择变化时更新显示"""
        self._update_display(selected)
        self.selection_changed.emit(selected)
    
    def _update_display(self, selected: List[str]):
        """更新显示文本"""
        if not selected:
            self.display_edit.clear()
            self.display_edit.setPlaceholderText(self._placeholder)
        else:
            # 显示已选项目（限制长度）
            display_texts = [
                self._display_map.get(v, v) for v in selected[:3]
            ]
            text = ", ".join(display_texts)
            if len(selected) > 3:
                text += f" (+{len(selected) - 3})"
            self.display_edit.setText(text)
    
    def set_items(self, items: List[Tuple[str, str]]):
        """设置选项列表 [(value, display_text), ...]"""
        self._items = items
        self._display_map = {v: d for v, d in items}
        if self._popup:
            self._popup.set_items(items)
    
    def get_selected(self) -> List[str]:
        """获取已选择的值列表"""
        if self._popup:
            return self._popup.get_selected()
        return []
    
    def set_selected(self, values: List[str]):
        """设置已选择的值"""
        if not self._popup:
            self._popup = MultiSelectPopup()
            self._popup.set_items(self._items)
            self._popup.selection_changed.connect(self._on_selection_changed)
        self._popup.set_selected(values)
        self._update_display(values)
    
    def clear_selection(self):
        """清除选择"""
        if self._popup:
            self._popup._clear_all()
        self.display_edit.clear()
    
    def setEnabled(self, enabled: bool):
        """设置启用状态"""
        super().setEnabled(enabled)
        self.display_edit.setEnabled(enabled)
