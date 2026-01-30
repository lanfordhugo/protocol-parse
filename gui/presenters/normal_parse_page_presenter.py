"""
文件名称: normal_parse_page_presenter.py
内容摘要: 普通解析页面 Presenter - 协调整个解析页面
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from typing import Dict, Any, Optional
from pathlib import Path

from gui.managers import ParseManager
from gui.models import ParseResult, ParseFilter, ParseStatus
from gui.views import (
    INormalParsePageView,
    IProtocolPanelView,
    IDetailPanelView,
    ILogPanelView,
)


class NormalParsePagePresenter:
    """普通解析页面 Presenter

    职责：
    - 协调三个子 Presenter（协议、详情、日志）
    - 管理页面级状态（解析中/空闲）
    - 协调解析流程
    - 处理页面级事件
    """

    def __init__(self, view: INormalParsePageView, parse_manager: ParseManager):
        """初始化 Presenter

        Args:
            view: 普通解析页面 View 接口
            parse_manager: 解析管理器
        """
        self._view = view
        self._parse_manager = parse_manager
        self._protocol_presenter = None
        self._detail_presenter = None
        self._log_presenter = None
        self._is_parsing = False
        self._current_result: Optional[ParseResult] = None

        # 连接 View 信号
        self._view.protocol_selected.connect(self._on_protocol_selected)
        self._view.parse_requested.connect(self._on_parse_requested)
        self._view.stop_requested.connect(self._on_stop_requested)
        self._view.validate_requested.connect(self._on_validate_requested)

    def set_protocol_presenter(self, presenter) -> None:
        """设置协议面板 Presenter

        Args:
            presenter: ProtocolPanelPresenter 实例
        """
        self._protocol_presenter = presenter

    def set_detail_presenter(self, presenter) -> None:
        """设置详情面板 Presenter

        Args:
            presenter: DetailPanelPresenter 实例
        """
        self._detail_presenter = presenter

    def set_log_presenter(self, presenter) -> None:
        """设置日志面板 Presenter

        Args:
            presenter: LogPanelPresenter 实例
        """
        self._log_presenter = presenter

    def initialize(self) -> None:
        """初始化页面"""
        try:
            # 加载协议列表
            if self._protocol_presenter:
                self._protocol_presenter.load_protocols()

            # 重置进度
            if self._log_presenter:
                self._log_presenter.reset_progress()

        except Exception as e:
            if self._log_presenter:
                self._log_presenter.log_error(f"初始化页面失败: {e}")

    def _on_protocol_selected(self, protocol_name: str) -> None:
        """处理协议选择事件

        Args:
            protocol_name: 协议名称
        """
        try:
            # 通知详情面板更新
            if self._detail_presenter:
                self._detail_presenter.update_protocol_info(protocol_name)

            # 记录日志
            if self._log_presenter:
                self._log_presenter.log_info(f"已选择协议: {protocol_name}")

        except Exception as e:
            if self._log_presenter:
                self._log_presenter.log_error(f"处理协议选择失败: {e}")

    def _on_parse_requested(
        self,
        protocol_name: str,
        filter_settings: ParseFilter
    ) -> None:
        """处理解析请求

        Args:
            protocol_name: 协议名称
            filter_settings: 过滤设置
        """
        try:
            # 更新状态
            self._is_parsing = True
            self._view.set_parse_state(True)

            # 记录日志
            if self._log_presenter:
                self._log_presenter.log_info(f"开始解析协议: {protocol_name}")
                self._log_presenter.reset_progress()

            # 获取协议信息（从 protocol_presenter）
            protocol_info = None
            if self._protocol_presenter:
                protocol_info = self._protocol_presenter.get_protocol_info(
                    protocol_name
                )

            if not protocol_info:
                raise ValueError(f"协议不存在: {protocol_name}")

            # 执行解析（同步版本，后续可改为异步）
            def progress_callback(current: int, total: int, message: str = ""):
                """进度回调"""
                if self._log_presenter:
                    self._log_presenter.update_progress(current, total)
                    if message:
                        self._log_presenter.log_info(message)

            result = self._parse_manager.execute_parse(
                protocol_name=protocol_name,
                config_path=protocol_info.config_path,
                log_path=protocol_info.log_path,
                filter_settings=filter_settings,
                progress_callback=progress_callback,
            )

            # 更新结果
            self._current_result = result

            # 处理解析结果
            if result.success:
                if self._log_presenter:
                    self._log_presenter.log_success(
                        f"解析完成: {result.message}"
                    )
                    self._log_presenter.log_info(
                        f"输出文件: {result.output_path}"
                    )

                # 询问是否打开输出目录
                self._view.show_parse_complete(result)
            else:
                if self._log_presenter:
                    self._log_presenter.log_error(
                        f"解析失败: {result.message}"
                    )
                    for error in result.errors:
                        self._log_presenter.log_error(f"  - {error}")

            # 恢复状态
            self._is_parsing = False
            self._view.set_parse_state(False)

        except Exception as e:
            if self._log_presenter:
                self._log_presenter.log_error(f"解析过程异常: {e}")

            self._is_parsing = False
            self._view.set_parse_state(False)

    def _on_stop_requested(self) -> None:
        """处理停止请求"""
        try:
            # 当前版本不支持中断，只记录日志
            if self._log_presenter:
                self._log_presenter.log_warning("停止请求已接收（当前版本不支持中断）")

            # 更新状态
            self._is_parsing = False
            self._view.set_parse_state(False)

        except Exception as e:
            if self._log_presenter:
                self._log_presenter.log_error(f"处理停止请求失败: {e}")

    def _on_validate_requested(self, protocol_name: str) -> None:
        """处理验证请求

        Args:
            protocol_name: 协议名称
        """
        try:
            # 验证由 detail_presenter 处理，这里只记录日志
            if self._log_presenter:
                self._log_presenter.log_info(f"开始验证协议配置: {protocol_name}")

        except Exception as e:
            if self._log_presenter:
                self._log_presenter.log_error(f"处理验证请求失败: {e}")

    def get_parse_result(self) -> Optional[ParseResult]:
        """获取最近的解析结果

        Returns:
            解析结果，如果未解析则返回 None
        """
        return self._current_result

    def is_parsing(self) -> bool:
        """检查是否正在解析

        Returns:
            是否正在解析
        """
        return self._is_parsing

    def open_output_directory(self) -> None:
        """打开输出目录"""
        try:
            output_dir = self._parse_manager.get_output_dir()
            if not output_dir.exists():
                output_dir = self._parse_manager.ensure_output_dir()

            # 由 View 处理打开操作
            self._view.open_directory_requested.emit(str(output_dir))

            if self._log_presenter:
                self._log_presenter.log_info(f"已打开输出目录: {output_dir}")

        except Exception as e:
            if self._log_presenter:
                self._log_presenter.log_error(f"打开输出目录失败: {e}")
