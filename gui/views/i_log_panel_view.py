"""
文件名称: i_log_panel_view.py
内容摘要: 日志面板 View 接口
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""


class ILogPanelView:
    """日志面板接口

    职责：
    - 显示日志消息
    - 显示解析进度
    - 捕获清空日志事件

    注意：Signal 在实现类中定义，不在接口中定义
    """

    # === Presenter 调用的方法（更新 UI） ===

    def log_info(self, message: str) -> None:
        """输出信息日志

        Args:
            message: 日志消息
        """
        raise NotImplementedError

    def log_success(self, message: str) -> None:
        """输出成功日志（绿色）

        Args:
            message: 日志消息
        """
        raise NotImplementedError

    def log_warning(self, message: str) -> None:
        """输出警告日志（橙色）

        Args:
            message: 日志消息
        """
        raise NotImplementedError

    def log_error(self, message: str) -> None:
        """输出错误日志（红色）

        Args:
            message: 日志消息
        """
        raise NotImplementedError

    def clear_log(self) -> None:
        """清空日志"""
        raise NotImplementedError

    def set_progress(self, value: int, total: int) -> None:
        """设置进度条

        Args:
            value: 当前进度值
            total: 总进度值
        """
        raise NotImplementedError

    def reset_progress(self) -> None:
        """重置进度条（归零）"""
        raise NotImplementedError

    def set_log_text(self, text: str) -> None:
        """直接设置日志文本

        Args:
            text: 日志文本内容
        """
        raise NotImplementedError
