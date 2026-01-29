"""
基于YAML配置的统一协议实现（重构版）
完全基于YAML配置驱动的协议解析器，无需依赖任何旧模块
"""

import logging
from collections import defaultdict
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional

from src.logger_instance import log
from src.protocol_data_extractor import ProtocolDataExtractor
from src.protocol_output_formatter import ProtocolOutputFormatter
from src.protocol_parser import ProtocolParser
from src.yaml_cmdformat import YamlCmdFormat
from src.yaml_field_parser import YamlFieldParser

logger = logging.getLogger(__name__)


class YamlUnifiedProtocol:
    """基于YAML配置的统一协议类（协调器）"""

    def __init__(self, log_file_name: str, protocol_yaml_path: str):
        """初始化协议解析器

        Args:
            log_file_name: 日志文件路径
            protocol_yaml_path: YAML协议配置文件路径
        """
        # 保存文件路径
        self.log_file_name = log_file_name
        self.protocol_yaml_path = protocol_yaml_path

        # 加载YAML配置
        self.yaml_format = YamlCmdFormat(protocol_yaml_path)
        self.yaml_config = self.yaml_format.config

        # 创建字段解析器（保留用于向后兼容）
        self.field_parser = YamlFieldParser(self.yaml_format.config)

        # 创建三个核心组件
        self.extractor = ProtocolDataExtractor(self.yaml_config.frame_head)
        self.parser = ProtocolParser(self.yaml_format)
        self.formatter = ProtocolOutputFormatter(self.yaml_format)

        logger.info(f"初始化YAML协议: {self.yaml_config.meta.protocol}")

        # 性能统计
        self._reset_perf_stats()

        # 进度回调和停止标志（用于GUI）
        self._progress_callback = None
        self._should_stop = False

    def set_progress_callback(self, callback):
        """设置进度回调函数

        Args:
            callback: 回调函数，签名为 callback(current: int, total: int)
        """
        self._progress_callback = callback

    def set_should_stop(self, value: bool = True):
        """设置停止标志

        Args:
            value: 是否停止，默认为 True
        """
        self._should_stop = value

    def _emit_progress(self, current: int, total: int):
        """发送进度更新"""
        if self._progress_callback:
            try:
                self._progress_callback(current, total)
            except Exception:
                pass  # 忽略回调异常

    def _check_should_stop(self) -> bool:
        """检查是否应该停止

        Returns:
            是否应该停止
        """
        return self._should_stop

    def set_include_cmds(self, cmd_list: List[int]):
        """设置包含的命令ID列表

        Args:
            cmd_list: 要包含的命令ID列表，只解析这些命令
        """
        self.parser.set_filters(include_cmds=cmd_list)

    def set_exclude_cmds(self, cmd_list: List[int]):
        """设置排除的命令ID列表

        Args:
            cmd_list: 要排除的命令ID列表，不解析这些命令
        """
        self.parser.set_filters(exclude_cmds=cmd_list)

    def set_time_range(self, start_time: datetime, end_time: datetime):
        """设置时间过滤范围

        Args:
            start_time: 起始时间
            end_time: 结束时间
        """
        self.parser.set_filters(time_range=(start_time, end_time))

    def _reset_perf_stats(self):
        """重置性能统计数据"""
        self.perf_stats = {
            "extract": [],
            "parse": [],
            "screen": [],
            "total": [],
            "cmd_counts": defaultdict(int),
            "errors": 0,
        }

    def _record_phase(self, phase: str, duration: float) -> None:
        """记录阶段耗时"""
        if phase in self.perf_stats:
            self.perf_stats[phase].append(duration)

    def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用YAML配置解析数据内容（向后兼容接口）

        Args:
            data_groups: 数据组列表

        Returns:
            解析后的数据组列表
        """
        return self.parser.parse_data_groups(
            data_groups,
            progress_callback=self._progress_callback,
            should_stop_callback=self._check_should_stop,
        )

    def screen_parse_data(self, parse_data: List[Dict[str, Any]]) -> Optional[str]:
        """筛选并打印解析结果，同时输出到特定的解析文件（向后兼容接口）

        Args:
            parse_data: 解析后的数据列表

        Returns:
            输出文件的绝对路径，如果没有数据则返回 None
        """
        return self.formatter.format_and_save(parse_data, self.perf_stats)

    def extract_data_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """从文件中提取数据（向后兼容接口）

        Args:
            file_path: 文件路径

        Returns:
            提取的数据列表
        """
        return self.extractor.extract_from_file(file_path)

    def run(self) -> Optional[str]:
        """运行协议解析

        Returns:
            解析结果文件的绝对路径，如果解析失败或无数据则返回 None
        """
        try:
            self._reset_perf_stats()
            total_start = perf_counter()

            # 提取数据
            extract_start = perf_counter()
            self._emit_progress(5, 100)  # 开始提取
            data_groups = self.extract_data_from_file(self.log_file_name)
            extract_duration = perf_counter() - extract_start
            self._record_phase("extract", extract_duration)

            if not data_groups:
                self._record_phase("total", perf_counter() - total_start)
                return None

            self._emit_progress(10, 100)  # 提取完成

            # 解析数据
            parse_start = perf_counter()
            parsed_data = self.parse_data_content(data_groups)
            parse_duration = perf_counter() - parse_start
            self._record_phase("parse", parse_duration)

            # 更新性能统计（从解析器获取）
            self.perf_stats["cmd_counts"] = self.parser.perf_stats["cmd_counts"]
            self.perf_stats["errors"] = self.parser.perf_stats["errors"]

            # 检查是否被停止
            if self._check_should_stop():
                return None

            # 筛选并打印结果
            screen_start = perf_counter()
            self._emit_progress(85, 100)  # 开始输出
            output_path = self.screen_parse_data(parsed_data)
            screen_duration = perf_counter() - screen_start
            self._record_phase("screen", screen_duration)
            self._record_phase("total", perf_counter() - total_start)

            self._emit_progress(100, 100)  # 完成
            return output_path

        except Exception as e:
            log.e_print(f"协议解析失败: {e}")
            raise
