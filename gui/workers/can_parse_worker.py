"""
文件名称: can_parse_worker.py
内容摘要: CAN协议后台解析工作线程
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
"""

from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal, Slot


class CanParseWorker(QObject):
    """CAN解析工作线程"""

    # 信号定义
    started = Signal()
    progress = Signal(int, int)  # current, total
    log_info = Signal(str)
    log_success = Signal(str)
    log_warning = Signal(str)
    log_error = Signal(str)
    finished = Signal(bool, str, str)  # success, message, output_path

    def __init__(
        self,
        config_path: str,
        log_path: str,
        filter_settings: Dict[str, Any],
    ) -> None:
        """初始化CAN解析工作线程

        Args:
            config_path: YAML配置文件路径
            log_path: CAN日志文件路径
            filter_settings: 过滤设置字典
        """
        super().__init__()
        self.config_path = config_path
        self.log_path = log_path
        self.filter_settings = filter_settings
        self._should_stop = False
        self._protocol: Optional[Any] = None

    def stop(self) -> None:
        """请求停止"""
        self._should_stop = True
        if self._protocol:
            self._protocol.set_should_stop(True)

    @Slot()
    def run(self) -> None:
        """执行CAN解析任务"""
        protocol = None
        try:
            self.started.emit()
            self.log_info.emit("CAN协议配置加载中...")

            # 应用过滤条件日志
            include_cmds = self.filter_settings.get("include_cmds")
            exclude_cmds = self.filter_settings.get("exclude_cmds")
            time_range = self.filter_settings.get("time_range")

            if time_range:
                start, end = time_range
                self.log_info.emit(
                    f"时间过滤: {start.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"~ {end.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            if include_cmds:
                self.log_info.emit(f"包含PF码: {include_cmds}")
            if exclude_cmds:
                self.log_info.emit(f"排除PF码: {exclude_cmds}")

            self.log_info.emit(f"开始解析CAN日志: {self.log_path}")

            # 导入并创建CAN协议协调器
            from src.can_unified_protocol import CanUnifiedProtocol

            protocol = CanUnifiedProtocol(
                self.log_path, self.config_path
            )
            self._protocol = protocol

            # 设置进度回调
            protocol.set_progress_callback(
                lambda current, total: self.progress.emit(current, total)
            )

            # 检查停止标志
            if self._should_stop:
                protocol.set_should_stop(True)

            # 设置过滤条件
            if include_cmds:
                protocol.set_include_cmds([int(c) for c in include_cmds])
            if exclude_cmds:
                protocol.set_exclude_cmds([int(c) for c in exclude_cmds])
            if time_range:
                protocol.set_time_range(time_range[0], time_range[1])

            self.log_info.emit("正在提取CAN帧数据...")

            # 执行解析
            output_path = protocol.run()

            if self._should_stop:
                self.log_warning.emit("解析已被用户停止")
                self.finished.emit(False, "解析已停止", "")
                return

            if output_path:
                self.log_success.emit(
                    f"CAN解析完成，结果已保存到: {output_path}"
                )
                self.finished.emit(True, "解析完成", output_path)
            else:
                self.log_warning.emit(
                    "解析完成，但没有生成输出文件（可能没有匹配的数据）"
                )
                self.finished.emit(True, "解析完成（无数据）", "")

        except Exception as e:
            if self._should_stop:
                self.log_warning.emit("解析已被用户停止")
                self.finished.emit(False, "解析已停止", "")
            else:
                error_msg = self._friendly_error(str(e))
                self.log_error.emit(f"解析失败: {error_msg}")
                self.finished.emit(False, error_msg, "")
        finally:
            if protocol and self._should_stop:
                protocol.set_should_stop(True)

    @staticmethod
    def _friendly_error(error: str) -> str:
        """将技术错误转换为友好的中文提示"""
        err = error.lower()
        if "no such file" in err or "找不到" in err:
            return "日志文件不存在，请检查文件路径"
        if "permission denied" in err:
            return "无法访问文件，请检查权限"
        if "encoding" in err or "codec" in err:
            return "文件编码错误，请确保为 UTF-8 或 GBK 编码"
        if "yaml" in err:
            return "协议配置文件格式错误"
        return error
