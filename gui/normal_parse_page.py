"""
文件名称: normal_parse_page.py
内容摘要: 普通解析页面组件（MVP 模式中的 View 实现）
当前版本: v2.0.0
作者: lanford
创建日期: 2025-01-10
修改日期: 2025-02-08
修改说明: 重构为 MVP 模式，实现 INormalParsePageView 接口，
          业务逻辑委托给 NormalParsePresenter
"""

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from .protocol_panel import ProtocolPanel
from .detail_panel import DetailPanel
from .log_panel import LogPanel
from .widgets.searchable_list import ProtocolItem
from gui.models.protocol_model import ProtocolDetail, ProtocolInfo


class NormalParsePage(QWidget):
    """
    普通解析页面 - MVP 模式中的 View 实现

    职责：
    - UI 组件的创建和布局
    - 将用户交互事件转发给 Presenter
    - 实现 INormalParsePageView 接口供 Presenter 更新 UI
    """

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presenter = None  # 由外部注入

        self._setup_ui()

        # 启用拖拽支持
        self.setAcceptDrops(True)

    def set_presenter(self, presenter) -> None:
        """
        注入 Presenter（MVP 组装时调用）

        Args:
            presenter: NormalParsePresenter 实例
        """
        self._presenter = presenter
        self._connect_signals()
        # Presenter 初始化（加载协议列表、选择默认协议）
        self._presenter.initialize()

    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 使用 Splitter 布局
        main_splitter = QSplitter(Qt.Vertical)

        # 上部分：左右分栏
        top_splitter = QSplitter(Qt.Horizontal)

        # 左侧：协议列表
        self.protocol_panel = ProtocolPanel()
        self.protocol_panel.setMinimumWidth(250)
        self.protocol_panel.setMaximumWidth(350)
        top_splitter.addWidget(self.protocol_panel)

        # 右侧：详情面板
        self.detail_panel = DetailPanel()
        top_splitter.addWidget(self.detail_panel)

        top_splitter.setStretchFactor(0, 0)
        top_splitter.setStretchFactor(1, 1)

        # 底部：日志面板
        self.log_panel = LogPanel()
        self.log_panel.setMinimumHeight(150)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.log_panel)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)

        layout.addWidget(main_splitter)

    def _connect_signals(self):
        """连接 UI 信号到 Presenter 方法"""
        self.protocol_panel.protocol_selected.connect(
            self._presenter.on_protocol_selected
        )
        self.detail_panel.parse_clicked.connect(
            self._presenter.on_parse_clicked
        )
        self.detail_panel.stop_clicked.connect(
            self._presenter.on_stop_clicked
        )
        self.detail_panel.validate_clicked.connect(
            self._presenter.on_validate_clicked
        )
        self.detail_panel.open_output_dir_clicked.connect(
            self._presenter.on_open_output_dir
        )
        self.detail_panel.select_log_clicked.connect(
            self._presenter.on_select_log_clicked
        )

    # ============== INormalParsePageView 接口实现 ==============

    def display_protocols(self, protocols: List[ProtocolInfo]) -> None:
        """显示协议列表"""
        protocol_items = [
            ProtocolItem(
                name=p.name,
                config_valid=p.config_valid,
                log_exists=p.log_exists,
                log_size=p.log_size,
            )
            for p in protocols
        ]
        self.protocol_panel.protocol_list.set_protocols(protocol_items)

    def update_protocol_list_item(self, info: ProtocolInfo) -> None:
        """更新单个协议列表项的显示状态"""
        item = ProtocolItem(
            name=info.name,
            config_valid=info.config_valid,
            log_exists=info.log_exists,
            log_size=info.log_size,
        )
        self.protocol_panel.protocol_list.refresh_item(item)

    def select_protocol_by_name(self, name: str) -> None:
        """在列表中选中指定协议"""
        list_widget = self.protocol_panel.protocol_list.list_widget
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.UserRole) == name:
                list_widget.setCurrentRow(i)
                return
        # 如果没找到指定协议，选中第一个
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)

    def get_selected_protocol_name(self) -> Optional[str]:
        """获取当前选中的协议名称"""
        return self.protocol_panel.get_selected_protocol()

    def display_protocol_detail(self, detail: ProtocolDetail) -> None:
        """显示协议详细信息"""
        self.detail_panel.update_protocol_info(
            name=detail.name,
            config_path=detail.config_path,
            config_valid=detail.config_valid,
            log_path=detail.log_path,
            log_exists=detail.log_exists,
            log_size=detail.log_size,
            cmd_count=detail.cmd_count,
            enum_count=detail.enum_count,
            type_count=detail.type_count,
            commands=detail.commands,
        )

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前的过滤设置"""
        return self.detail_panel.get_filter_settings()

    def set_parsing_state(self, is_parsing: bool) -> None:
        """设置解析状态"""
        self.detail_panel.set_parsing(is_parsing)

    @Slot(str)
    def log_info(self, message: str) -> None:
        """显示信息日志"""
        self.log_panel.log_info(message)

    @Slot(str)
    def log_success(self, message: str) -> None:
        """显示成功日志"""
        self.log_panel.log_success(message)

    @Slot(str)
    def log_warning(self, message: str) -> None:
        """显示警告日志"""
        self.log_panel.log_warning(message)

    @Slot(str)
    def log_error(self, message: str) -> None:
        """显示错误日志"""
        self.log_panel.log_error(message)

    def reset_progress(self) -> None:
        """重置进度条"""
        self.log_panel.reset_progress()

    @Slot(int, int)
    def set_progress(self, current: int, total: int) -> None:
        """设置进度"""
        self.log_panel.set_progress(current, total)

    def show_warning(self, title: str, message: str) -> None:
        """显示警告对话框"""
        QMessageBox.warning(self, title, message)

    def show_parse_complete_dialog(self, output_path: str) -> bool:
        """显示解析完成确认对话框"""
        reply = QMessageBox.question(
            self,
            "解析完成",
            f"解析结果已保存到:\n{output_path}\n\n是否立即打开查看？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        return reply == QMessageBox.Yes

    def show_file_dialog(
        self,
        title: str,
        directory: str,
        file_filter: str,
    ) -> Optional[str]:
        """显示文件选择对话框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, directory, file_filter
        )
        return file_path if file_path else None

    def emit_status_changed(self, message: str) -> None:
        """发送状态变化信号"""
        self.status_changed.emit(message)

    # ============== Qt 事件处理（仅转发给 Presenter） ==============

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith(('.log', '.txt')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件 - 委托给 Presenter"""
        if not self._presenter:
            return

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.log', '.txt')):
                self._presenter.on_log_file_dropped(file_path)
                break

    def cleanup(self) -> None:
        """清理资源"""
        # 委托给 Presenter 清理工作线程
        if self._presenter:
            self._presenter.cleanup()

        # 清理详情面板的扫描线程
        self.detail_panel.cleanup()
