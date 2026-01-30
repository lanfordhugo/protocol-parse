"""
文件名称: log_panel_presenter.py
内容摘要: 日志面板 Presenter - 协调日志面板 View 和 Model
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from gui.views import ILogPanelView


class LogPanelPresenter:
    """日志面板 Presenter

    职责：
    - 响应日志面板的用户事件
    - 管理日志输出
    - 更新解析进度
    - 处理清空日志
    """

    def __init__(self, view: ILogPanelView):
        """初始化 Presenter

        Args:
            view: 日志面板 View 接口
        """
        self._view = view

        # 连接 View 信号
        self._view.clear_clicked.connect(self._on_clear_clicked)

    def log_info(self, message: str) -> None:
        """输出信息日志

        Args:
            message: 日志消息
        """
        self._view.log_info(message)

    def log_success(self, message: str) -> None:
        """输出成功日志

        Args:
            message: 日志消息
        """
        self._view.log_success(message)

    def log_warning(self, message: str) -> None:
        """输出警告日志

        Args:
            message: 日志消息
        """
        self._view.log_warning(message)

    def log_error(self, message: str) -> None:
        """输出错误日志

        Args:
            message: 日志消息
        """
        self._view.log_error(message)

    def update_progress(self, current: int, total: int) -> None:
        """更新解析进度

        Args:
            current: 当前进度
            total: 总进度
        """
        self._view.set_progress(current, total)

    def reset_progress(self) -> None:
        """重置进度条"""
        self._view.reset_progress()

    def _on_clear_clicked(self) -> None:
        """处理清空日志点击

        由 View 处理，无需额外逻辑
        """
        self._view.clear_log()
