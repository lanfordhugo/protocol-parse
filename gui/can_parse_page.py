"""
文件名称: can_parse_page.py
内容摘要: CAN解析页面组件（MVP 模式中的 View 实现）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
修改说明: V6 CAN协议解析的顶层UI页面，包含文件选择、过滤设置、解析操作和日志面板
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QGridLayout, QSplitter,
    QMessageBox, QFileDialog, QLineEdit,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from .log_panel import LogPanel


class CanParseDetailWidget(QGroupBox):
    """CAN解析详情与操作面板"""

    # 信号
    select_log_clicked = Signal()
    parse_clicked = Signal()
    stop_clicked = Signal()
    open_output_dir_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("V6 CAN 协议解析", parent)
        self._is_parsing = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)

        # === 协议信息 ===
        info_group = QGroupBox("协议信息")
        info_layout = QGridLayout(info_group)
        info_layout.setColumnStretch(1, 1)

        info_layout.addWidget(QLabel("协议名称:"), 0, 0)
        self.protocol_label = QLabel("V6 CAN (MCU/CCU报文)")
        self.protocol_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.protocol_label, 0, 1)

        info_layout.addWidget(QLabel("支持格式:"), 1, 0)
        self.format_label = QLabel("TCU日志(.log) / CSV文件(.csv)")
        info_layout.addWidget(self.format_label, 1, 1)

        layout.addWidget(info_group)

        # === 日志文件选择 ===
        file_group = QGroupBox("日志文件")
        file_layout = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("请选择CAN日志文件或拖拽文件到此处...")
        self.log_path_edit.setReadOnly(True)
        file_row.addWidget(self.log_path_edit)

        self.select_log_btn = QPushButton("选择文件")
        self.select_log_btn.setFixedWidth(90)
        self.select_log_btn.clicked.connect(self.select_log_clicked.emit)
        file_row.addWidget(self.select_log_btn)

        file_layout.addLayout(file_row)

        # 文件状态
        self.file_status_label = QLabel("请选择日志文件")
        self.file_status_label.setStyleSheet("color: #f39c12;")
        file_layout.addWidget(self.file_status_label)

        layout.addWidget(file_group)

        # === 过滤设置 ===
        filter_group = QGroupBox("过滤设置（可选）")
        filter_layout = QGridLayout(filter_group)
        filter_layout.setColumnStretch(1, 1)

        filter_layout.addWidget(QLabel("包含PF码:"), 0, 0)
        self.include_pf_edit = QLineEdit()
        self.include_pf_edit.setPlaceholderText("如: 0x10,0x14,0x16 （留空则不过滤）")
        filter_layout.addWidget(self.include_pf_edit, 0, 1)

        filter_layout.addWidget(QLabel("排除PF码:"), 1, 0)
        self.exclude_pf_edit = QLineEdit()
        self.exclude_pf_edit.setPlaceholderText("如: 0x0F （留空则不排除）")
        filter_layout.addWidget(self.exclude_pf_edit, 1, 1)

        layout.addWidget(filter_group)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.clicked.connect(self.open_output_dir_clicked.emit)
        btn_layout.addWidget(self.open_dir_btn)

        self.parse_btn = QPushButton("开始解析")
        self.parse_btn.setFixedWidth(120)
        self.parse_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2ecc71; }"
            "QPushButton:disabled { background-color: #95a5a6; }"
        )
        self.parse_btn.clicked.connect(self._on_parse_or_stop)
        btn_layout.addWidget(self.parse_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _on_parse_or_stop(self) -> None:
        """解析/停止按钮点击"""
        if self._is_parsing:
            self.stop_clicked.emit()
        else:
            self.parse_clicked.emit()

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径"""
        self.log_path_edit.setText(path)
        p = Path(path)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            if size_kb > 1024:
                size_str = f"{size_kb / 1024:.1f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
            self.file_status_label.setText(f"文件就绪 ({size_str})")
            self.file_status_label.setStyleSheet("color: #27ae60;")
        else:
            self.file_status_label.setText("文件不存在")
            self.file_status_label.setStyleSheet("color: #e74c3c;")

    def get_log_path(self) -> Optional[str]:
        """获取日志文件路径"""
        path = self.log_path_edit.text().strip()
        return path if path else None

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取过滤设置"""
        settings: Dict[str, Any] = {}

        # 解析包含PF码
        include_text = self.include_pf_edit.text().strip()
        if include_text:
            settings["include_cmds"] = self._parse_pf_list(include_text)

        # 解析排除PF码
        exclude_text = self.exclude_pf_edit.text().strip()
        if exclude_text:
            settings["exclude_cmds"] = self._parse_pf_list(exclude_text)

        return settings

    @staticmethod
    def _parse_pf_list(text: str) -> List[int]:
        """解析PF码列表字符串为整数列表"""
        result = []
        for part in text.replace('，', ',').split(','):
            part = part.strip()
            if not part:
                continue
            try:
                if part.startswith('0x') or part.startswith('0X'):
                    result.append(int(part, 16))
                else:
                    result.append(int(part))
            except ValueError:
                pass
        return result

    def set_parsing(self, is_parsing: bool) -> None:
        """设置解析状态"""
        self._is_parsing = is_parsing
        if is_parsing:
            self.parse_btn.setText("停止解析")
            self.parse_btn.setStyleSheet(
                "QPushButton { background-color: #e74c3c; color: white; "
                "font-weight: bold; padding: 8px; border-radius: 4px; }"
                "QPushButton:hover { background-color: #c0392b; }"
            )
            self.select_log_btn.setEnabled(False)
        else:
            self.parse_btn.setText("开始解析")
            self.parse_btn.setStyleSheet(
                "QPushButton { background-color: #27ae60; color: white; "
                "font-weight: bold; padding: 8px; border-radius: 4px; }"
                "QPushButton:hover { background-color: #2ecc71; }"
                "QPushButton:disabled { background-color: #95a5a6; }"
            )
            self.select_log_btn.setEnabled(True)


class CanParsePage(QWidget):
    """
    CAN解析页面 - MVP 模式中的 View 实现

    职责：
    - UI 组件的创建和布局
    - 将用户交互事件转发给 Presenter
    - 实现 ICanParsePageView 接口供 Presenter 更新 UI
    """

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presenter = None
        self._setup_ui()
        self.setAcceptDrops(True)

    def set_presenter(self, presenter) -> None:
        """注入 Presenter"""
        self._presenter = presenter
        self._connect_signals()
        self._presenter.initialize()

    def _setup_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        main_splitter = QSplitter(Qt.Vertical)

        # 上部分：详情面板
        self.detail_panel = CanParseDetailWidget()
        main_splitter.addWidget(self.detail_panel)

        # 底部：日志面板
        self.log_panel = LogPanel()
        self.log_panel.setMinimumHeight(150)
        main_splitter.addWidget(self.log_panel)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)

        layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        """连接 UI 信号到 Presenter 方法"""
        self.detail_panel.select_log_clicked.connect(
            self._presenter.on_select_log_clicked
        )
        self.detail_panel.parse_clicked.connect(
            self._presenter.on_parse_clicked
        )
        self.detail_panel.stop_clicked.connect(
            self._presenter.on_stop_clicked
        )
        self.detail_panel.open_output_dir_clicked.connect(
            self._presenter.on_open_output_dir
        )

    # ============== ICanParsePageView 接口实现 ==============

    def get_selected_log_path(self) -> Optional[str]:
        """获取当前选中的日志文件路径"""
        return self.detail_panel.get_log_path()

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径显示"""
        self.detail_panel.set_log_path(path)

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前的过滤设置"""
        return self.detail_panel.get_filter_settings()

    def set_parsing_state(self, is_parsing: bool) -> None:
        """设置解析状态"""
        self.detail_panel.set_parsing(is_parsing)

    @Slot(str)
    def log_info(self, message: str) -> None:
        self.log_panel.log_info(message)

    @Slot(str)
    def log_success(self, message: str) -> None:
        self.log_panel.log_success(message)

    @Slot(str)
    def log_warning(self, message: str) -> None:
        self.log_panel.log_warning(message)

    @Slot(str)
    def log_error(self, message: str) -> None:
        self.log_panel.log_error(message)

    def reset_progress(self) -> None:
        self.log_panel.reset_progress()

    @Slot(int, int)
    def set_progress(self, current: int, total: int) -> None:
        self.log_panel.set_progress(current, total)

    def show_warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def show_parse_complete_dialog(self, output_path: str) -> str:
        """显示解析完成对话框"""
        msg = QMessageBox(self)
        msg.setWindowTitle("CAN解析完成")
        msg.setText(f"解析结果已保存到:\n{output_path}")

        open_file_btn = msg.addButton("打开文件", QMessageBox.AcceptRole)
        close_btn = msg.addButton("关闭", QMessageBox.RejectRole)
        msg.setDefaultButton(open_file_btn)

        msg.exec()
        if msg.clickedButton() is open_file_btn:
            return "open_file"
        return "close"

    def show_file_dialog(
        self, title: str, directory: str, file_filter: str
    ) -> Optional[str]:
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, directory, file_filter
        )
        return file_path if file_path else None

    def emit_status_changed(self, message: str) -> None:
        self.status_changed.emit(message)

    # ============== Qt 事件处理 ==============

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith(('.log', '.csv', '.txt')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self._presenter:
            return
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.log', '.csv', '.txt')):
                self._presenter.on_log_file_dropped(file_path)
                break

    def cleanup(self) -> None:
        """清理资源"""
        if self._presenter:
            self._presenter.cleanup()
