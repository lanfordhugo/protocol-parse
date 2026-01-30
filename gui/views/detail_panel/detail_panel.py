"""
文件名称: detail_panel.py
内容摘要: 详情面板主组件（MVP 架构 View 层）
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import List, Tuple, Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame
from PySide6.QtCore import Signal

from gui.views import IDetailPanelView
from .protocol_detail_widget import ProtocolDetailWidget
from .filter_widget import FilterWidget
from .action_widget import ActionWidget


class DetailPanel(QWidget, IDetailPanelView):
    """右侧详情面板（MVP 架构 View 层）

    职责：
    - 组合三个子组件（协议详情、过滤设置、操作按钮）
    - 实现 IDetailPanelView 接口
    - 转发子组件信号到 Presenter

    多重继承：
    - QWidget: 提供 Qt 组件功能
    - IDetailPanelView: 定义接口契约

    信号：
    - parse_clicked: 点击解析按钮
    - stop_clicked: 点击停止按钮
    - validate_clicked: 点击验证按钮
    - open_output_dir_clicked: 点击打开输出目录
    - select_log_clicked: 点击选择日志文件
    - time_range_changed: 时间范围变化 (start, end)
    - command_filter_changed: 命令过滤变化 (filter_data)
    - terminal_filter_changed: 终端ID过滤变化
    """

    # 信号：由 IDetailPanelView 接口定义
    parse_clicked = Signal()
    stop_clicked = Signal()
    validate_clicked = Signal()
    open_output_dir_clicked = Signal()
    select_log_clicked = Signal()
    time_range_changed = Signal(object, object)  # (start, end)
    command_filter_changed = Signal(dict)  # (filter_data)
    terminal_filter_changed = Signal(str)  # terminal_id

    def __init__(self, parent: Optional[QWidget] = None):
        # 多重继承：先初始化 QWidget，再初始化 IDetailPanelView
        QWidget.__init__(self, parent)
        IDetailPanelView.__init__(self)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """初始化UI"""
        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # 协议详情
        self.detail_widget: ProtocolDetailWidget = ProtocolDetailWidget()
        layout.addWidget(self.detail_widget)

        # 过滤设置
        self.filter_widget: FilterWidget = FilterWidget()
        layout.addWidget(self.filter_widget)

        # 操作按钮
        self.action_widget: ActionWidget = ActionWidget()
        layout.addWidget(self.action_widget)

        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        """连接信号"""
        # ActionWidget 信号
        self.action_widget.parse_clicked.connect(self.parse_clicked.emit)
        self.action_widget.stop_clicked.connect(self.stop_clicked.emit)
        self.action_widget.validate_clicked.connect(self.validate_clicked.emit)
        self.action_widget.open_output_dir_clicked.connect(
            self.open_output_dir_clicked.emit
        )

        # ProtocolDetailWidget 信号
        self.detail_widget.select_log_btn.clicked.connect(
            self.select_log_clicked.emit
        )

        # FilterWidget 信号
        self.filter_widget.time_range_changed.connect(self.time_range_changed.emit)
        self.filter_widget.command_filter_changed.connect(
            self._on_command_filter_changed
        )

    # === IDetailPanelView 接口方法实现 ===

    def update_protocol_info(
        self,
        name: str,
        config_path: str,
        config_valid: bool,
        log_path: str,
        log_exists: bool,
        log_size: int,
        cmd_count: int = 0,
        enum_count: int = 0,
        type_count: int = 0,
        commands: Optional[List[Tuple[str, str]]] = None
    ) -> None:
        """更新协议详情显示（接口方法）

        Args:
            name: 协议名称
            config_path: 配置文件路径
            config_valid: 配置是否有效
            log_path: 日志文件路径
            log_exists: 日志是否存在
            log_size: 日志文件大小
            cmd_count: 命令数量
            enum_count: 枚举数量
            type_count: 类型数量
            commands: 命令列表 [(id, name), ...]
        """
        self.detail_widget.update_info(
            name, config_path, config_valid,
            log_path, log_exists, log_size,
            cmd_count, enum_count, type_count
        )

        # 更新命令过滤选项
        if commands:
            self.filter_widget.set_commands(commands)

        # 传递日志路径到 FilterWidget，触发自动扫描
        if log_path and log_exists:
            self.filter_widget.set_log_path(log_path)

    def set_parse_button_enabled(self, enabled: bool) -> None:
        """启用/禁用解析按钮（接口方法）

        Args:
            enabled: 是否启用
        """
        self.action_widget.parse_btn.setEnabled(enabled)

    def set_stop_button_enabled(self, enabled: bool) -> None:
        """启用/禁用停止按钮（接口方法）

        Args:
            enabled: 是否启用
        """
        self.action_widget.stop_btn.setEnabled(enabled)

    def set_progress(self, current: int, total: int) -> None:
        """设置解析进度（接口方法）

        Args:
            current: 当前进度
            total: 总进度

        TODO: Phase 2 实现进度显示
        当前实现：暂无进度条组件
        """
        # TODO: Phase 2 添加进度条组件
        pass

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前过滤设置（接口方法）

        Returns:
            过滤设置字典，包含：
            - time_range: (start, end) 或 None
            - include_cmds: List[str] 或 None
            - exclude_cmds: List[str] 或 None
        """
        return {
            'time_range': self.filter_widget.get_time_filter(),
            'include_cmds': self.filter_widget.get_include_cmds(),
            'exclude_cmds': self.filter_widget.get_exclude_cmds(),
        }

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径（接口方法）

        Args:
            path: 日志文件路径
        """
        self.filter_widget.set_log_path(path)

    def set_commands(self, commands: List[Tuple[str, str]]) -> None:
        """设置命令列表（接口方法）

        Args:
            commands: 命令列表 [(id, name), ...]
        """
        self.filter_widget.set_commands(commands)

    def reset_progress(self) -> None:
        """重置进度条（接口方法）

        TODO: Phase 2 实现进度显示
        """
        # TODO: Phase 2 添加进度条组件
        pass

    # === 私有方法 ===

    def _on_command_filter_changed(
        self,
        include: Optional[List[str]],
        exclude: Optional[List[str]]
    ) -> None:
        """处理命令过滤变化信号

        Args:
            include: 包含的命令列表
            exclude: 排除的命令列表

        将 FilterWidget 的双参数信号转换为接口要求的单参数信号
        """
        filter_data = {
            'include_cmds': include,
            'exclude_cmds': exclude
        }
        self.command_filter_changed.emit(filter_data)

    # === 遗留方法（保留向后兼容） ===

    def set_parsing(self, parsing: bool) -> None:
        """设置解析状态（遗留方法，保留向后兼容）

        Args:
            parsing: 是否正在解析
        """
        self.action_widget.set_parsing(parsing)

    def clear(self) -> None:
        """清空面板（遗留方法，保留向后兼容）"""
        self.detail_widget.clear()
        self.filter_widget.clear()

    def cleanup(self) -> None:
        """清理资源（遗留方法，保留向后兼容）"""
        self.filter_widget.cleanup()
