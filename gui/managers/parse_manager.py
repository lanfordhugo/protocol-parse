"""
文件名称: parse_manager.py
内容摘要: 解析管理器 - 负责解析流程的管理和执行
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from gui.models import ParseResult, ParseFilter, ParseStatus


class ParseManager:
    """解析管理器

    负责解析流程的配置验证、过滤器构建和解析执行。
    完全独立于 GUI 框架，可在单元测试中直接使用。
    """

    def __init__(self, output_dir: Path):
        """初始化解析管理器

        Args:
            output_dir: 输出目录
        """
        self._output_dir = Path(output_dir)
        self._ensure_src_path()

    def _ensure_src_path(self):
        """确保 src 目录在 Python 路径中"""
        src_path = self._output_dir.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

    def validate_parse_config(
        self,
        protocol_name: str,
        config_path: Path,
        log_path: Path
    ) -> tuple[bool, str]:
        """验证解析配置

        Args:
            protocol_name: 协议名称
            config_path: 配置文件路径
            log_path: 日志文件路径

        Returns:
            (是否有效, 错误消息)
        """
        # 检查配置文件是否存在
        if not Path(config_path).exists():
            return False, f"配置文件不存在: {config_path}"

        # 检查日志文件是否存在
        log_file = Path(log_path)
        if not log_file.exists():
            return False, f"日志文件不存在: {log_path}"

        # 检查日志文件是否为空
        if log_file.stat().st_size == 0:
            return False, f"日志文件为空: {log_path}"

        # 尝试加载协议配置
        try:
            from yaml_config import YamlConfigLoader
            loader = YamlConfigLoader()
            config = loader.load_protocol_config(config_path)
            if not config:
                return False, f"无法加载协议配置: {config_path}"
        except Exception as e:
            return False, f"配置加载失败: {e}"

        return True, ""

    def build_parse_filters(
        self,
        filter_settings: ParseFilter
    ) -> dict:
        """构建解析过滤器

        Args:
            filter_settings: 过滤器设置

        Returns:
            解析器使用的过滤器字典
        """
        filters = {}

        # 时间范围过滤
        if filter_settings.start_time or filter_settings.end_time:
            filters['time_range'] = {}
            if filter_settings.start_time:
                filters['time_range']['start'] = filter_settings.start_time
            if filter_settings.end_time:
                filters['time_range']['end'] = filter_settings.end_time

        # 命令过滤
        if filter_settings.include_cmds:
            filters['include_cmds'] = filter_settings.include_cmds
        if filter_settings.exclude_cmds:
            filters['exclude_cmds'] = filter_settings.exclude_cmds

        # 高级选项
        if filter_settings.skip_invalid:
            filters['skip_invalid'] = True
        if filter_settings.strict_mode:
            filters['strict_mode'] = True

        return filters

    def execute_parse(
        self,
        protocol_name: str,
        config_path: Path,
        log_path: Path,
        filter_settings: Optional[ParseFilter] = None,
        progress_callback=None
    ) -> ParseResult:
        """执行解析（同步版本）

        Args:
            protocol_name: 协议名称
            config_path: 配置文件路径
            log_path: 日志文件路径
            filter_settings: 过滤器设置
            progress_callback: 进度回调函数 (current, total, message)

        Returns:
            解析结果
        """
        # 创建解析结果对象
        result = ParseResult(
            protocol_name=protocol_name,
            config_path=Path(config_path),
            log_path=Path(log_path),
            status=ParseStatus.RUNNING,
            start_time=datetime.now(),
        )

        try:
            # 验证配置
            is_valid, error_msg = self.validate_parse_config(
                protocol_name, config_path, log_path
            )
            if not is_valid:
                result.status = ParseStatus.FAILED
                result.message = error_msg
                result.errors.append(error_msg)
                result.end_time = datetime.now()
                return result

            # 构建过滤器
            filters = {}
            if filter_settings:
                filters = self.build_parse_filters(filter_settings)

            # 执行解析
            from yaml_unified_protocol import YamlUnifiedProtocol

            protocol = YamlUnifiedProtocol(str(config_path))

            # 统计日志文件行数
            result.total_lines = self._count_log_lines(log_path)

            # 自定义进度回调
            def _progress_callback(current: int, total: int, message: str = ""):
                result.parsed_lines = current
                result.total_lines = total
                result.progress = int((current / total * 100)) if total > 0 else 0
                result.current_step = message

                if progress_callback:
                    progress_callback(current, total, message)

            # 解析日志
            output_file = protocol.parse_log_file(
                str(log_path),
                output_dir=str(self._output_dir),
                filters=filters if filters else None,
                progress_callback=_progress_callback,
            )

            # 更新结果
            result.status = ParseStatus.SUCCESS
            result.success = True
            result.message = f"解析完成: {protocol_name}"
            result.output_path = Path(output_file)
            result.progress = 100
            result.end_time = datetime.now()

        except Exception as e:
            result.status = ParseStatus.FAILED
            result.success = False
            result.message = f"解析失败: {e}"
            result.errors.append(str(e))
            result.error_count += 1
            result.end_time = datetime.now()

        return result

    def _count_log_lines(self, log_path: Path) -> int:
        """统计日志文件行数

        Args:
            log_path: 日志文件路径

        Returns:
            日志文件行数
        """
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def create_parse_filter(self) -> ParseFilter:
        """创建默认的解析过滤器

        Returns:
            默认的解析过滤器
        """
        return ParseFilter()

    def estimate_parse_time(self, log_path: Path) -> Optional[float]:
        """估算解析时间（秒）

        基于文件大小的简单估算，假设每秒处理 1000 行。

        Args:
            log_path: 日志文件路径

        Returns:
            预估解析时间（秒），如果无法估算则返回 None
        """
        try:
            line_count = self._count_log_lines(log_path)
            # 假设每秒处理 1000 行
            return line_count / 1000.0
        except Exception:
            return None

    def get_output_dir(self) -> Path:
        """获取输出目录

        Returns:
            输出目录路径
        """
        return self._output_dir

    def ensure_output_dir(self) -> Path:
        """确保输出目录存在

        Returns:
            输出目录路径
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir
