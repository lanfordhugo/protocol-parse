"""
文件名称: detail_panel_presenter.py
内容摘要: 详情面板 Presenter - 协调详情面板 View 和 Model
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from gui.managers import ProtocolManager, ParseManager, ValidationManager
from gui.models import ProtocolInfo, ParseFilter
from gui.views import IDetailPanelView


class DetailPanelPresenter:
    """详情面板 Presenter

    职责：
    - 响应详情面板的用户事件
    - 协调解析流程
    - 管理过滤设置
    - 显示解析进度
    """

    def __init__(
        self,
        view: IDetailPanelView,
        protocol_manager: ProtocolManager,
        parse_manager: ParseManager,
        validation_manager: ValidationManager,
    ):
        """初始化 Presenter

        Args:
            view: 详情面板 View 接口
            protocol_manager: 协议管理器
            parse_manager: 解析管理器
            validation_manager: 验证管理器
        """
        self._view = view
        self._protocol_manager = protocol_manager
        self._parse_manager = parse_manager
        self._validation_manager = validation_manager

        self._current_protocol: Optional[str] = None
        self._parse_filter = ParseFilter()

        # 连接 View 信号
        self._view.parse_clicked.connect(self._on_parse_clicked)
        self._view.stop_clicked.connect(self._on_stop_clicked)
        self._view.validate_clicked.connect(self._on_validate_clicked)
        self._view.open_output_dir_clicked.connect(self._on_open_output_dir)
        self._view.select_log_clicked.connect(self._on_select_log)
        self._view.time_range_changed.connect(self._on_time_range_changed)
        self._view.command_filter_changed.connect(self._on_command_filter_changed)

    def update_protocol_info(self, protocol_name: str) -> None:
        """更新协议详情显示

        Args:
            protocol_name: 协议名称
        """
        try:
            self._current_protocol = protocol_name

            # 获取协议信息
            protocol_info = self._protocol_manager.get_protocol_info(protocol_name)
            if not protocol_info:
                self._view.show_error(f"协议不存在: {protocol_name}")
                return

            # 获取协议统计信息
            stats = self._protocol_manager.get_protocol_stats(protocol_name)

            # 更新 View
            self._view.update_protocol_info(protocol_info, stats)

            # 更新日志文件显示
            if protocol_info.log_path and protocol_info.log_exists:
                self._view.update_log_file(protocol_info.log_path)

        except Exception as e:
            self._view.show_error(f"更新协议信息失败: {e}")

    def _on_parse_clicked(self) -> None:
        """处理解析按钮点击"""
        try:
            if not self._current_protocol:
                self._view.show_error("请先选择协议")
                return

            # 获取协议信息
            protocol_info = self._protocol_manager.get_protocol_info(
                self._current_protocol
            )
            if not protocol_info:
                self._view.show_error(f"协议不存在: {self._current_protocol}")
                return

            # 检查日志文件
            if not protocol_info.log_path or not protocol_info.log_exists:
                self._view.show_error("请先选择日志文件")
                return

            # 验证配置
            is_valid, error_msg = self._parse_manager.validate_parse_config(
                protocol_name=self._current_protocol,
                config_path=protocol_info.config_path,
                log_path=protocol_info.log_path,
            )
            if not is_valid:
                self._view.show_error(f"配置验证失败: {error_msg}")
                return

            # 发射解析请求信号
            self._view.parse_requested.emit(
                self._current_protocol,
                self._parse_filter,
            )

        except Exception as e:
            self._view.show_error(f"启动解析失败: {e}")

    def _on_stop_clicked(self) -> None:
        """处理停止按钮点击"""
        try:
            # 发射停止请求信号
            self._view.stop_requested.emit()
        except Exception as e:
            self._view.show_error(f"停止解析失败: {e}")

    def _on_validate_clicked(self) -> None:
        """处理验证按钮点击"""
        try:
            if not self._current_protocol:
                self._view.show_error("请先选择协议")
                return

            # 获取协议信息
            protocol_info = self._protocol_manager.get_protocol_info(
                self._current_protocol
            )
            if not protocol_info:
                self._view.show_error(f"协议不存在: {self._current_protocol}")
                return

            # 执行验证
            result = self._validation_manager.validate_protocol_config(
                protocol_name=self._current_protocol,
                config_path=protocol_info.config_path,
            )

            # 显示验证结果
            self._view.show_validation_result(result)

        except Exception as e:
            self._view.show_error(f"验证配置失败: {e}")

    def _on_open_output_dir(self) -> None:
        """处理打开输出目录"""
        try:
            output_dir = self._parse_manager.get_output_dir()
            if not output_dir.exists():
                output_dir = self._parse_manager.ensure_output_dir()

            # 根据操作系统打开文件管理器
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # Linux/Mac
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', output_dir])
                else:  # Linux
                    subprocess.run(['xdg-open', output_dir])
        except Exception as e:
            self._view.show_error(f"打开输出目录失败: {e}")

    def _on_select_log(self) -> None:
        """处理选择日志文件"""
        try:
            if not self._current_protocol:
                self._view.show_error("请先选择协议")
                return

            # 打开文件选择对话框
            log_path, _ = self._view.show_file_dialog(
                title="选择日志文件",
                file_filter="日志文件 (*.log);;所有文件 (*.*)",
            )

            if not log_path:
                return

            log_file = Path(log_path)

            # 验证日志文件
            if not log_file.exists():
                self._view.show_error(f"日志文件不存在: {log_file}")
                return

            if log_file.stat().st_size == 0:
                self._view.show_error(f"日志文件为空: {log_file}")
                return

            # 更新协议的日志文件
            success = self._protocol_manager.update_protocol_log_path(
                self._current_protocol, log_file
            )

            if success:
                # 更新 View
                self._view.update_log_file(log_file)
                self._view.show_info(f"已选择日志文件: {log_file.name}")
            else:
                self._view.show_error("更新日志文件失败")

        except Exception as e:
            self._view.show_error(f"选择日志文件失败: {e}")

    def _on_time_range_changed(self, start, end) -> None:
        """处理时间范围变化

        Args:
            start: 开始时间
            end: 结束时间
        """
        try:
            # 更新过滤器
            self._parse_filter.start_time = start
            self._parse_filter.end_time = end
        except Exception as e:
            self._view.show_error(f"更新时间范围失败: {e}")

    def _on_command_filter_changed(self, filter_data) -> None:
        """处理命令过滤变化

        Args:
            filter_data: 过滤数据 (include_cmds, exclude_cmds)
        """
        try:
            include_cmds = filter_data.get('include_cmds', [])
            exclude_cmds = filter_data.get('exclude_cmds', [])

            # 验证命令ID有效性
            if self._current_protocol:
                stats = self._protocol_manager.get_protocol_stats(self._current_protocol)
                if stats:
                    available_cmds = {cmd_id for cmd_id, _ in stats.commands}

                    # 检查 include_cmds
                    for cmd_id in include_cmds:
                        if cmd_id not in available_cmds:
                            self._view.show_warning(
                                f"包含命令ID可能无效: {cmd_id}"
                            )

                    # 检查 exclude_cmds
                    for cmd_id in exclude_cmds:
                        if cmd_id not in available_cmds:
                            self._view.show_warning(
                                f"排除命令ID可能无效: {cmd_id}"
                            )

            # 更新过滤器
            self._parse_filter.include_cmds = include_cmds
            self._parse_filter.exclude_cmds = exclude_cmds

        except Exception as e:
            self._view.show_error(f"更新命令过滤失败: {e}")

    def get_parse_filter(self) -> ParseFilter:
        """获取当前解析过滤器

        Returns:
            解析过滤器
        """
        return self._parse_filter

    def reset_parse_filter(self) -> None:
        """重置解析过滤器"""
        self._parse_filter = ParseFilter()
        self._view.reset_filter_display()
