"""
文件名称: field_tree_widget.py
内容摘要: 字段树管理组件，显示和管理波形监控的字段列表
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QHeaderView,
    QInputDialog,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.wave.models.wave_data_manager import FieldConfig
from gui.wave.utils.chart_type_mapper import ChartType

logger = logging.getLogger(__name__)


def _create_color_icon(color: str, size: int = 12) -> QIcon:
    """
    创建纯色方块图标

    Args:
        color: 颜色字符串（#RRGGBB）
        size: 图标尺寸

    Returns:
        QIcon 对象
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


# 图表类型显示文本
_CHART_TYPE_TEXT = {
    ChartType.LINE: "折线",
    ChartType.STEP: "阶梯",
    ChartType.SCATTER: "散点",
}


class FieldTreeWidget(QWidget):
    """
    字段树管理组件

    功能：
    - 按 CMD 分组显示监控字段
    - 复选框控制字段启用/禁用
    - 右键菜单：删除、重命名、修改颜色
    - 颜色方块指示

    信号：
    - field_enabled_changed(str, bool): 字段启用状态变更
    - field_color_changed(str, str): 字段颜色变更
    - field_removed(str): 字段移除请求
    - field_renamed(str, str): 字段重命名
    """

    # 信号定义
    field_enabled_changed = Signal(str, bool)
    field_color_changed = Signal(str, str)
    field_removed = Signal(str)
    field_renamed = Signal(str, str)
    selection_changed = Signal(int, int)  # (total, selected) 选中状态变化

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # CMD分组节点 {cmd_id: QTreeWidgetItem}
        self._cmd_groups: Dict[Optional[int], QTreeWidgetItem] = {}
        # 字段节点 {field_path: QTreeWidgetItem}
        self._field_items: Dict[str, QTreeWidgetItem] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.setAnimated(True)
        self._tree.setIndentation(12)

        # 信号连接
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self._tree)

    # ============== 字段管理 ==============

    def add_field(self, config: FieldConfig, expand: bool = True) -> None:
        """
        添加字段到树

        Args:
            config: 字段配置
            expand: 是否展开分组（默认 True）
        """
        if config.field_path in self._field_items:
            self.update_field(config)
            return

        # 获取或创建 CMD 分组
        group = self._get_or_create_group(config.cmd_id)

        # 创建字段节点
        item = QTreeWidgetItem(group)
        type_text = _CHART_TYPE_TEXT.get(config.chart_type, "")
        item.setText(0, config.display_name)
        item.setIcon(0, _create_color_icon(config.color))
        item.setCheckState(0, Qt.Checked if config.enabled else Qt.Unchecked)
        item.setData(0, Qt.UserRole, config.field_path)

        # 类型信息合并到 Tooltip
        item.setToolTip(
            0, f"路径: {config.field_path}\n类型: {config.field_type.name}\n图表: {type_text}"
        )

        self._field_items[config.field_path] = item

        # 根据参数决定是否展开分组
        group.setExpanded(expand)

    def remove_field(self, field_path: str) -> None:
        """
        从树中移除字段

        Args:
            field_path: 字段路径
        """
        item = self._field_items.pop(field_path, None)
        if not item:
            return

        parent = item.parent()
        if parent:
            parent.removeChild(item)
            # 如果分组为空，移除分组
            if parent.childCount() == 0:
                cmd_id = parent.data(0, Qt.UserRole)
                self._cmd_groups.pop(cmd_id, None)
                idx = self._tree.indexOfTopLevelItem(parent)
                if idx >= 0:
                    self._tree.takeTopLevelItem(idx)

    def update_field(self, config: FieldConfig) -> None:
        """
        更新字段显示

        Args:
            config: 更新后的字段配置
        """
        item = self._field_items.get(config.field_path)
        if not item:
            return

        # 阻断信号避免触发 itemChanged
        type_text = _CHART_TYPE_TEXT.get(config.chart_type, "")
        self._tree.blockSignals(True)
        item.setText(0, config.display_name)
        item.setIcon(0, _create_color_icon(config.color))
        item.setCheckState(0, Qt.Checked if config.enabled else Qt.Unchecked)
        item.setToolTip(
            0, f"路径: {config.field_path}\n类型: {config.field_type.name}\n图表: {type_text}"
        )
        self._tree.blockSignals(False)

    def refresh(self, configs: List[FieldConfig], expand_all: bool = True) -> None:
        """
        刷新整个字段树

        Args:
            configs: 字段配置列表
            expand_all: 是否展开所有分组（默认 True）
        """
        self._tree.blockSignals(True)
        self._tree.clear()
        self._cmd_groups.clear()
        self._field_items.clear()

        for config in configs:
            self.add_field(config, expand=expand_all)

        self._tree.blockSignals(False)

    def clear(self) -> None:
        """清空字段树"""
        self._tree.clear()
        self._cmd_groups.clear()
        self._field_items.clear()

    # ============== 批量操作 ==============

    def select_all(self) -> None:
        """选中所有字段"""
        if not self._field_items:
            return

        self._tree.blockSignals(True)
        for field_path, item in self._field_items.items():
            item.setCheckState(0, Qt.Checked)
        for cmd_id, group in self._cmd_groups.items():
            group.setCheckState(0, Qt.Checked)
        self._tree.blockSignals(False)

        # 批量发射信号
        for field_path in self._field_items:
            self.field_enabled_changed.emit(field_path, True)
        self._emit_selection_changed()

    def deselect_all(self) -> None:
        """取消选中所有字段"""
        if not self._field_items:
            return

        self._tree.blockSignals(True)
        for field_path, item in self._field_items.items():
            item.setCheckState(0, Qt.Unchecked)
        for cmd_id, group in self._cmd_groups.items():
            group.setCheckState(0, Qt.Unchecked)
        self._tree.blockSignals(False)

        # 批量发射信号
        for field_path in self._field_items:
            self.field_enabled_changed.emit(field_path, False)
        self._emit_selection_changed()

    # ============== 内部方法 ==============

    def _get_or_create_group(self, cmd_id: Optional[int]) -> QTreeWidgetItem:
        """
        获取或创建 CMD 分组节点

        Args:
            cmd_id: 命令ID

        Returns:
            分组节点
        """
        if cmd_id in self._cmd_groups:
            return self._cmd_groups[cmd_id]

        group = QTreeWidgetItem(self._tree)
        if cmd_id is not None:
            group.setText(0, f"CMD {cmd_id}")
        else:
            group.setText(0, "未分组")
        group.setData(0, Qt.UserRole, cmd_id)

        # 分组节点支持三态勾选（全选/部分/全不选）
        group.setFlags(group.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
        group.setCheckState(0, Qt.Unchecked)

        # 加粗分组文字
        font = group.font(0)
        font.setBold(True)
        group.setFont(0, font)

        self._cmd_groups[cmd_id] = group
        return group

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """
        树节点变化回调（复选框切换）

        支持两种场景：
        1. 字段节点勾选变化 → 发射 field_enabled_changed
        2. CMD分组节点勾选变化 → 批量切换所有子字段
        """
        if column != 0:
            return

        field_path = item.data(0, Qt.UserRole)
        if field_path is None:
            return

        # 字段节点
        if field_path in self._field_items:
            enabled = item.checkState(0) == Qt.Checked
            self.field_enabled_changed.emit(field_path, enabled)
            self._emit_selection_changed()
            return

        # CMD 分组节点：批量切换子字段
        if field_path in self._cmd_groups or isinstance(field_path, int) or field_path is None:
            check_state = item.checkState(0)
            # PartiallyChecked 由 Qt 自动设置，不需要我们处理
            if check_state == Qt.PartiallyChecked:
                return
            enabled = check_state == Qt.Checked
            self._tree.blockSignals(True)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, Qt.Checked if enabled else Qt.Unchecked)
            self._tree.blockSignals(False)
            # 批量发射信号
            for i in range(item.childCount()):
                child = item.child(i)
                child_path = child.data(0, Qt.UserRole)
                if child_path and child_path in self._field_items:
                    self.field_enabled_changed.emit(child_path, enabled)
            self._emit_selection_changed()

    def _emit_selection_changed(self) -> None:
        """发射选中状态变化信号"""
        total = len(self._field_items)
        selected = sum(
            1 for item in self._field_items.values()
            if item.checkState(0) == Qt.Checked
        )
        self.selection_changed.emit(total, selected)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        点击行时切换勾选状态

        注意：点击的是字段节点时才切换，CMD分组节点由三态逻辑处理。
        """
        field_path = item.data(0, Qt.UserRole)
        if field_path not in self._field_items:
            return

        # 切换勾选状态
        current_state = item.checkState(0)
        new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
        item.setCheckState(0, new_state)
        # 注意：setCheckState 会触发 itemChanged 信号，进而发射 field_enabled_changed

    def _on_context_menu(self, pos) -> None:
        """右键菜单"""
        item = self._tree.itemAt(pos)
        if not item:
            return

        field_path = item.data(0, Qt.UserRole)
        if field_path is None or field_path not in self._field_items:
            return

        menu = QMenu(self)

        # 修改颜色
        color_action = QAction("修改颜色...", self)
        color_action.triggered.connect(lambda: self._change_color(field_path))
        menu.addAction(color_action)

        # 重命名
        rename_action = QAction("重命名...", self)
        rename_action.triggered.connect(lambda: self._rename_field(field_path))
        menu.addAction(rename_action)

        menu.addSeparator()

        # 删除
        remove_action = QAction("删除", self)
        remove_action.triggered.connect(lambda: self.field_removed.emit(field_path))
        menu.addAction(remove_action)

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

    def _change_color(self, field_path: str) -> None:
        """打开颜色选择对话框"""
        item = self._field_items.get(field_path)
        if not item:
            return

        color = QColorDialog.getColor(parent=self, title="选择字段颜色")
        if color.isValid():
            color_hex = color.name()
            item.setIcon(0, _create_color_icon(color_hex))
            self.field_color_changed.emit(field_path, color_hex)

    def _rename_field(self, field_path: str) -> None:
        """打开重命名对话框"""
        item = self._field_items.get(field_path)
        if not item:
            return

        current_name = item.text(0)
        new_name, ok = QInputDialog.getText(
            self,
            "重命名字段",
            "新名称:",
            text=current_name,
        )
        if ok and new_name and new_name != current_name:
            item.setText(0, new_name)
            self.field_renamed.emit(field_path, new_name)
