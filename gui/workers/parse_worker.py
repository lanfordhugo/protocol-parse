"""
文件名称: parse_worker.py
内容摘要: 后台解析工作线程
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-24
"""

from typing import Dict, Any, Optional

from PySide6.QtCore import QObject, Signal, Slot


class ParseWorker(QObject):
    """解析工作线程"""

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
        protocol_name: str,
        config_path: str,
        log_path: str,
        filter_settings: Dict[str, Any]
    ) -> None:
        """
        初始化解析工作线程

        Args:
            protocol_name: 协议名称
            config_path: 配置文件路径
            log_path: 日志文件路径
            filter_settings: 过滤设置字典
        """
        super().__init__()
        self.protocol_name = protocol_name
        self.config_path = config_path
        self.log_path = log_path
        self.filter_settings = filter_settings
        self._should_stop = False
        self._protocol: Optional[Any] = None  # 保存协议引用以便停止

    def stop(self) -> None:
        """请求停止"""
        self._should_stop = True
        # 如果协议已创建，立即设置其停止标志
        if self._protocol:
            self._protocol.set_should_stop(True)

    @Slot()
    def run(self) -> None:
        """执行解析任务"""
        protocol = None
        try:
            self.started.emit()
            self.log_info.emit(f"协议 {self.protocol_name} 配置加载完成")

            # 检查过滤条件
            time_range = self.filter_settings.get('time_range')
            include_cmds = self.filter_settings.get('include_cmds')
            exclude_cmds = self.filter_settings.get('exclude_cmds')

            if time_range:
                start, end = time_range
                self.log_info.emit(
                    f"应用过滤条件: 时间 {start.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"~ {end.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            if include_cmds:
                self.log_info.emit(f"应用过滤条件: 包含命令 {include_cmds}")

            if exclude_cmds:
                self.log_info.emit(f"应用过滤条件: 排除命令 {exclude_cmds}")

            self.log_info.emit(f"开始解析日志文件 {self.log_path} ...")

            # 导入解析器并执行
            from src.yaml_unified_protocol import YamlUnifiedProtocol

            protocol = YamlUnifiedProtocol(
                self.log_path,
                self.config_path
            )

            # 保存协议引用以便停止
            self._protocol = protocol

            # 设置进度回调
            protocol.set_progress_callback(
                lambda current, total: self.progress.emit(current, total)
            )

            # 如果已经请求停止，立即设置协议停止标志
            if self._should_stop:
                protocol.set_should_stop(True)

            # 设置过滤条件
            if include_cmds:
                protocol.set_include_cmds([int(c) for c in include_cmds])
            if exclude_cmds:
                protocol.set_exclude_cmds([int(c) for c in exclude_cmds])
            if time_range:
                protocol.set_time_range(time_range[0], time_range[1])

            self.progress.emit(10, 100)
            self.log_info.emit("正在提取数据...")

            # 执行解析
            output_path = protocol.run()

            # 检查是否被停止
            if self._should_stop:
                self.log_warning.emit("解析已被用户停止")
                self.finished.emit(False, "解析已停止", "")
                return

            self.progress.emit(90, 100)

            if output_path:
                self.log_success.emit(f"解析完成，结果已保存到: {output_path}")
                self.progress.emit(100, 100)
                self.finished.emit(True, "解析完成", output_path)
            else:
                self.log_warning.emit("解析完成，但没有生成输出文件（可能没有匹配的数据）")
                self.progress.emit(100, 100)
                self.finished.emit(True, "解析完成（无数据）", "")

        except Exception as e:
            # 检查是否是停止导致的异常
            if self._should_stop:
                self.log_warning.emit("解析已被用户停止")
                self.finished.emit(False, "解析已停止", "")
            else:
                # 友好化错误信息
                error_msg = self._friendly_error_message(str(e))
                self.log_error.emit(f"解析失败: {error_msg}")
                self.finished.emit(False, error_msg, "")
        finally:
            # 确保停止协议（如果存在）
            if protocol and self._should_stop:
                protocol.set_should_stop(True)

    def _friendly_error_message(self, error: str) -> str:
        """
        将技术错误信息转换为友好的中文提示

        Args:
            error: 原始错误信息

        Returns:
            str: 友好的中文错误提示
        """
        error_lower = error.lower()

        # 文件相关错误
        if "no such file" in error_lower or "找不到" in error_lower:
            return "日志文件不存在，请检查文件路径是否正确"
        if "permission denied" in error_lower or "拒绝访问" in error_lower:
            return "无法访问文件，请检查文件权限或关闭占用该文件的程序"
        if "encoding" in error_lower or "codec" in error_lower:
            return "文件编码错误，请确保日志文件为 UTF-8 或 GBK 编码"

        # 协议相关错误
        if "protocol" in error_lower and "not found" in error_lower:
            return "协议配置未找到，请检查 configs 目录下是否存在对应的 protocol.yaml"
        if "yaml" in error_lower:
            return "协议配置文件格式错误，请检查 YAML 语法是否正确"
        if "head" in error_lower or "header" in error_lower:
            return "日志格式不匹配，请确认选择了正确的协议"

        # 数据相关错误
        if "no data" in error_lower or "没有数据" in error_lower:
            return "日志文件中没有找到有效的报文数据"
        if "parse" in error_lower or "解析" in error_lower:
            return f"报文解析错误: {error}。请检查日志格式是否与协议匹配"

        # 默认返回原始错误
        return error
