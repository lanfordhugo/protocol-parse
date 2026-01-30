"""
文件名称: i_detail_panel_view.py
内容摘要: 详情面板 View 接口
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import List, Tuple, Dict, Any
from datetime import datetime
from PySide6.QtCore import Signal, QObject


class IDetailPanelView:
    """详情面板接口（抽象基类）

    职责：
    - 显示协议详情信息
    - 显示过滤设置控件
    - 捕获用户操作事件
    - 显示解析进度

    注意：
    - 这是一个抽象接口，不继承 QObject 或 QWidget
    - 实现类需要继承 QWidget 和此类（多重继承）
    - 信号需要在实现类中定义
    """

    # === 信号定义（需要在实现类中重新定义） ===
    # 以下是信号类型的文档说明，实际定义在实现类中
    # parse_clicked = Signal()  # 点击解析按钮
    # stop_clicked = Signal()  # 点击停止按钮
    # validate_clicked = Signal()  # 点击验证按钮
    # open_output_dir_clicked = Signal()  # 点击打开输出目录
    # select_log_clicked = Signal()  # 点击选择日志文件
    # time_range_changed = Signal(object, object)  # 时间范围变化 (start, end)
    # command_filter_changed = Signal(list)  # 命令过滤变化 (include_cmds, exclude_cmds)
    # terminal_filter_changed = Signal(str)  # 终端ID过滤变化

    # === Presenter 调用的方法（更新 UI） ===

    def update_protocol_info(
        self,
        name: str,
        config_path: str,
        config_valid: bool,
        log_path: str,
        log_exists: bool,
        log_size: int,
        cmd_count: int,
        enum_count: int,
        type_count: int,
        commands: List[Tuple[str, str]]
    ) -> None:
        """更新协议详情显示

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
        raise NotImplementedError

    def set_parse_button_enabled(self, enabled: bool) -> None:
        """启用/禁用解析按钮

        Args:
            enabled: 是否启用
        """
        raise NotImplementedError

    def set_stop_button_enabled(self, enabled: bool) -> None:
        """启用/禁用停止按钮

        Args:
            enabled: 是否启用
        """
        raise NotImplementedError

    def set_progress(self, current: int, total: int) -> None:
        """设置解析进度

        Args:
            current: 当前进度
            total: 总进度
        """
        raise NotImplementedError

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前过滤设置

        Returns:
            过滤设置字典，包含：
            - time_range: (start, end) 或 None
            - include_cmds: List[str] 或 None
            - exclude_cmds: List[str] 或 None
            - terminal_id: str 或 None
        """
        raise NotImplementedError

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径

        Args:
            path: 日志文件路径
        """
        raise NotImplementedError

    def set_commands(self, commands: List[Tuple[str, str]]) -> None:
        """设置命令列表（用于过滤控件）

        Args:
            commands: 命令列表 [(id, name), ...]
        """
        raise NotImplementedError

    def reset_progress(self) -> None:
        """重置进度条"""
        raise NotImplementedError
