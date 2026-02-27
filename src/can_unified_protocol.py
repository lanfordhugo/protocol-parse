"""
文件名称: can_unified_protocol.py
内容摘要: CAN协议统一协调器 - 编排CAN数据提取、解析、格式化输出的完整流程
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
"""

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional

from src.can_data_extractor import CanDataExtractor
from src.can_protocol_parser import CanProtocolParser
from src.logger_instance import log
from src.yaml_cmdformat import YamlCmdFormat

logger = logging.getLogger(__name__)

# 默认CAN协议YAML配置路径
DEFAULT_CAN_CONFIG = "configs/v6_can/protocol.yaml"


class CanUnifiedProtocol:
    """CAN协议统一协调器

    编排CAN数据的提取→解析→输出完整流程，
    对外接口与 YamlUnifiedProtocol 保持风格一致。
    """

    def __init__(
        self,
        log_file_path: str,
        config_path: str = DEFAULT_CAN_CONFIG,
    ) -> None:
        """初始化CAN协议协调器

        Args:
            log_file_path: CAN日志文件路径
            config_path: YAML协议配置文件路径
        """
        self.log_file_path = log_file_path
        self.config_path = config_path

        # 加载YAML配置
        self.yaml_format = YamlCmdFormat(config_path)

        # 创建核心组件
        self.extractor = CanDataExtractor()
        self.parser = CanProtocolParser(self.yaml_format)

        logger.info(
            f"初始化CAN协议: {self.yaml_format.config.meta.protocol}"
        )

        # 性能统计
        self._reset_perf_stats()

        # 进度回调和停止标志
        self._progress_callback: Optional[Callable[[int, int], None]] = None
        self._should_stop = False

    def set_progress_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        """设置进度回调"""
        self._progress_callback = callback

    def set_should_stop(self, value: bool = True) -> None:
        """设置停止标志"""
        self._should_stop = value
        self.parser.set_should_stop(value)

    def set_include_cmds(self, cmd_list: List[int]) -> None:
        """设置包含的PF码列表"""
        self.parser.set_include_pfs(cmd_list)

    def set_exclude_cmds(self, cmd_list: List[int]) -> None:
        """设置排除的PF码列表"""
        self.parser.set_exclude_pfs(cmd_list)

    def set_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> None:
        """设置时间过滤范围"""
        self.parser.set_time_range(start_time, end_time)

    def _emit_progress(self, current: int, total: int) -> None:
        """发送进度更新"""
        if self._progress_callback:
            try:
                self._progress_callback(current, total)
            except Exception:
                pass

    def _reset_perf_stats(self) -> None:
        """重置性能统计"""
        self.perf_stats: Dict[str, Any] = {
            "extract": [],
            "parse": [],
            "screen": [],
            "total": [],
            "cmd_counts": defaultdict(int),
            "errors": 0,
        }

    def run(self) -> Optional[str]:
        """运行CAN协议解析

        Returns:
            解析结果文件路径，无数据时返回None
        """
        try:
            self._reset_perf_stats()
            total_start = perf_counter()

            # 1. 提取阶段
            extract_start = perf_counter()
            self._emit_progress(5, 100)

            is_csv = self.extractor.detect_file_format(self.log_file_path)
            self.extractor.set_progress_callback(
                lambda cur, tot: self._emit_progress(
                    5 + int((cur / max(tot, 1)) * 25), 100
                )
            )
            data_groups = self.extractor.extract(
                self.log_file_path, is_csv=is_csv
            )

            extract_duration = perf_counter() - extract_start
            self.perf_stats["extract"].append(extract_duration)

            if not data_groups:
                log.printf("未提取到有效CAN数据")
                self.perf_stats["total"].append(
                    perf_counter() - total_start
                )
                return None

            self._emit_progress(30, 100)

            # 2. 解析阶段
            parse_start = perf_counter()
            self.parser.set_progress_callback(
                lambda cur, tot: self._emit_progress(
                    30 + int((cur / max(tot, 1)) * 40), 100
                )
            )
            parsed_data = self.parser.parse(data_groups)

            parse_duration = perf_counter() - parse_start
            self.perf_stats["parse"].append(parse_duration)
            self.perf_stats["cmd_counts"] = self.parser.perf_stats[
                "cmd_counts"
            ]
            self.perf_stats["errors"] = self.parser.perf_stats["errors"]

            if self._should_stop:
                return None

            self._emit_progress(70, 100)

            # 3. 输出阶段
            screen_start = perf_counter()
            output_path = self._format_and_save(parsed_data)
            screen_duration = perf_counter() - screen_start
            self.perf_stats["screen"].append(screen_duration)
            self.perf_stats["total"].append(perf_counter() - total_start)

            self._emit_progress(100, 100)
            return output_path

        except Exception as e:
            log.e_print(f"CAN协议解析失败: {e}")
            raise

    def _format_and_save(
        self,
        parsed_data: List[Dict[str, Any]],
        output_dir: str = "parsed_log",
    ) -> Optional[str]:
        """格式化CAN解析结果并保存到文件"""
        if not parsed_data:
            log.printf("没有解析到有效CAN数据")
            return None

        protocol_name = self.yaml_format.config.meta.protocol
        timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        output_filename = f"parsed_{protocol_name}_log_{timestamp}.txt"
        output_path = Path(output_dir) / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = self._build_output_lines(parsed_data)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
            return str(output_path.resolve())
        except Exception as e:
            log.e_print(f"保存CAN解析结果失败: {e}")
            return None

    def _build_output_lines(
        self, parsed_data: List[Dict[str, Any]]
    ) -> List[str]:
        """构建输出行列表"""
        lines: List[str] = []

        # 头部信息
        protocol_info = self.yaml_format.get_protocol_info()
        lines.append(f"成功解析 {len(parsed_data)} 条CAN数据")
        lines.append(
            f"协议: {protocol_info['protocol']} v{protocol_info['version']}"
        )

        # PF码统计
        pf_stats: Dict[str, int] = {}
        for item in parsed_data:
            cmd = item.get("cmd", 0)
            pf_name = item.get("cmd_name", "")
            key = f"PF 0x{cmd:02X}"
            if pf_name and pf_name != key:
                key = f"{key}({pf_name})"
            pf_stats[key] = pf_stats.get(key, 0) + 1

        lines.append("\nPF码统计:")
        for pf_key, count in sorted(pf_stats.items()):
            lines.append(f"  {pf_key}: {count} 条")

        # 详细数据
        total = len(parsed_data)
        for i, item in enumerate(parsed_data):
            if self._progress_callback and total > 0 and i % max(1, total // 50) == 0:
                progress = 70 + int((i / total) * 28)
                try:
                    self._progress_callback(progress, 100)
                except Exception:
                    pass

            cmd = item.get("cmd", 0)
            cmd_name = item.get("cmd_name", f"PF 0x{cmd:02X}")
            lines.append(f"\n=== 数据项 {i + 1} ===")
            lines.append(f"时间: {item.get('timestamp', 'N/A')}")
            lines.append(f"方向: {item.get('direction', 'N/A')}")
            lines.append(f"帧ID: {item.get('frame_id', 'N/A')}")
            lines.append(
                f"源板: {item.get('tx_board', 'N/A')} → "
                f"目标板: {item.get('rx_board', 'N/A')}"
            )
            lines.append(f"PF码: 0x{cmd:02X} ({cmd_name})")

            content = item.get("content", {})
            if content:
                lines.append("解析内容:")
                self._collect_content_lines(content, lines, indent=2)

        # 性能统计
        lines.extend(self._build_perf_lines())
        return lines

    def _collect_content_lines(
        self,
        content: Any,
        lines: List[str],
        indent: int = 0,
    ) -> None:
        """递归收集内容行"""
        prefix = "  " * indent

        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, dict):
                    if "value" in value and "name" in value:
                        lines.append(
                            f"{prefix}{key}: {value['value']} ({value['name']})"
                        )
                    else:
                        lines.append(f"{prefix}{key}:")
                        self._collect_content_lines(value, lines, indent + 1)
                elif isinstance(value, list):
                    if all(isinstance(v, str) for v in value):
                        lines.append(f"{prefix}{key}: {', '.join(value)}")
                    else:
                        lines.append(f"{prefix}{key}: [{len(value)} 项]")
                        for j, v in enumerate(value):
                            if isinstance(v, dict):
                                lines.append(f"{prefix}  [{j}]:")
                                self._collect_content_lines(v, lines, indent + 2)
                            else:
                                lines.append(f"{prefix}  [{j}]: {v}")
                else:
                    lines.append(f"{prefix}{key}: {value}")

    def _build_perf_lines(self) -> List[str]:
        """构建性能统计行"""
        lines: List[str] = []
        lines.append("\n=== 性能统计摘要 ===")

        def _fmt(values: List[float]) -> str:
            if not values:
                return "N/A"
            return (
                f"平均 {sum(values)/len(values)*1000:.2f} ms | "
                f"最大 {max(values)*1000:.2f} ms"
            )

        lines.append(f"总耗时: {_fmt(self.perf_stats.get('total', []))}")
        lines.append(f"提取:   {_fmt(self.perf_stats.get('extract', []))}")
        lines.append(f"解析:   {_fmt(self.perf_stats.get('parse', []))}")
        lines.append(f"输出:   {_fmt(self.perf_stats.get('screen', []))}")

        if self.perf_stats.get("cmd_counts"):
            lines.append("PF码处理统计:")
            for pf_key, count in sorted(
                self.perf_stats["cmd_counts"].items()
            ):
                lines.append(f"  {pf_key}: {count} 条")

        if self.perf_stats.get("errors"):
            lines.append(f"解析失败: {self.perf_stats['errors']} 次")

        lines.append("====================\n")
        return lines
