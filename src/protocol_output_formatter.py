"""
协议输出格式化器
格式化并输出解析结果到文件
"""

import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.logger_instance import log
from src.yaml_cmdformat import YamlCmdFormat

logger = logging.getLogger(__name__)


class ProtocolOutputFormatter:
    """协议输出格式化器类

    负责格式化解析结果并输出到文件
    """

    def __init__(self, yaml_format: YamlCmdFormat):
        """初始化输出格式化器

        Args:
            yaml_format: YAML命令格式管理器实例
        """
        self.yaml_format = yaml_format
        self.yaml_config = yaml_format.config

    def format_and_save(
        self,
        parse_data: List[Dict[str, Any]],
        perf_stats: Dict[str, Any],
        output_dir: str = "parsed_log",
    ) -> Optional[str]:
        """格式化并保存解析结果

        Args:
            parse_data: 解析后的数据列表
            perf_stats: 性能统计数据
            output_dir: 输出目录

        Returns:
            输出文件的绝对路径，如果没有数据则返回 None
        """
        if not parse_data:
            log.printf("没有解析到有效数据")
            return None

        # 创建输出文件路径
        protocol_info = self.yaml_format.get_protocol_info()
        protocol_name = protocol_info["protocol"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        output_filename = f"parsed_{protocol_name}_log_{timestamp}.txt"
        output_path = os.path.join(output_dir, output_filename)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 准备输出内容
        output_lines = self._build_output_lines(parse_data, protocol_info, perf_stats)

        # 写入文件
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for line in output_lines:
                    f.write(line + "\n")
            return os.path.abspath(output_path)
        except Exception as e:
            log.e_print(f"保存解析结果失败: {e}")
            return None

    def _build_output_lines(
        self,
        parse_data: List[Dict[str, Any]],
        protocol_info: Dict[str, Any],
        perf_stats: Dict[str, Any],
    ) -> List[str]:
        """构建输出行列表

        Args:
            parse_data: 解析后的数据列表
            protocol_info: 协议信息
            perf_stats: 性能统计数据

        Returns:
            输出行列表
        """
        output_lines = []

        # 协议信息
        output_lines.append(f"成功解析 {len(parse_data)} 条数据")
        output_lines.append(f"协议: {protocol_info['protocol']} v{protocol_info['version']}")
        output_lines.append(f"支持命令: {len(protocol_info['supported_cmds'])} 个")

        # 统计命令频次
        cmd_stats = {}
        for item in parse_data:
            cmd = item.get("cmd")
            if cmd:
                cmd_stats[cmd] = cmd_stats.get(cmd, 0) + 1

        output_lines.append("命令统计:")
        for cmd, count in sorted(cmd_stats.items()):
            output_lines.append(f"  cmd{cmd}: {count} 条")

        # 详细输出所有数据
        for i, item in enumerate(parse_data):
            output_lines.append(f"\n=== 数据项 {i+1} ===")
            output_lines.append(f"时间: {item.get('timestamp', 'N/A')}")
            output_lines.append(f"方向: {item.get('direction', 'N/A')}")
            output_lines.append(f"命令: cmd{item.get('cmd', 'N/A')}")

            # 添加终端ID（如果存在）
            terminal_id = item.get("terminal_id")
            if terminal_id is not None:
                output_lines.append(f"终端ID: {terminal_id}")

            # 打印解析内容
            content = item.get("content", {})
            if content:
                output_lines.append("解析内容:")
                self._collect_content_lines(content, output_lines, indent=2)

            if "parse_error" in item:
                output_lines.append(f"解析错误: {item['parse_error']}")

        # 添加性能统计
        output_lines.extend(self._build_perf_stats_lines(perf_stats))

        return output_lines

    def _build_perf_stats_lines(self, perf_stats: Dict[str, Any]) -> List[str]:
        """构建性能统计输出行

        Args:
            perf_stats: 性能统计数据

        Returns:
            性能统计输出行列表
        """
        lines = []
        lines.append("\n=== 性能统计摘要 ===")

        def _format_stats(values: List[float]) -> str:
            """格式化性能统计"""
            if not values:
                return "N/A"
            return (
                f"{len(values)} 次 | 平均 {sum(values)/len(values)*1000:.2f} ms | "
                f"最大 {max(values)*1000:.2f} ms | 最小 {min(values)*1000:.2f} ms"
            )

        lines.append(f"总耗时: {_format_stats(perf_stats.get('total', []))}")
        lines.append(f"提取:   {_format_stats(perf_stats.get('extract', []))}")
        lines.append(f"解析:   {_format_stats(perf_stats.get('parse', []))}")
        lines.append(f"输出:   {_format_stats(perf_stats.get('screen', []))}")

        if perf_stats.get("cmd_counts"):
            lines.append("命令处理统计:")
            for cmd_id, count in sorted(perf_stats["cmd_counts"].items()):
                lines.append(f"  CMD {cmd_id}: {count} 条")

        if perf_stats.get("errors"):
            lines.append(f"解析失败: {perf_stats['errors']} 次")

        lines.append("====================\n")
        return lines

    def _collect_content_lines(
        self, content: Dict[str, Any], output_lines: List[str], indent: int = 0
    ) -> None:
        """递归收集内容行到列表中

        Args:
            content: 内容字典
            output_lines: 输出行列表
            indent: 缩进级别
        """
        prefix = "  " * indent

        for key, value in content.items():
            if isinstance(value, dict):
                if "value" in value and "name" in value:
                    # 枚举值
                    output_lines.append(f"{prefix}{key}: {value['value']} ({value['name']})")
                else:
                    # 嵌套字典
                    output_lines.append(f"{prefix}{key}:")
                    self._collect_content_lines(value, output_lines, indent + 1)
            elif isinstance(value, list):
                output_lines.append(f"{prefix}{key}: [{len(value)} 项]")
                for i, item in enumerate(value):  # 显示所有项
                    if isinstance(item, dict):
                        output_lines.append(f"{prefix}  [{i}]:")
                        self._collect_content_lines(item, output_lines, indent + 2)
                    else:
                        formatted_item = (
                            self._format_float(item) if isinstance(item, float) else item
                        )
                        output_lines.append(f"{prefix}  [{i}]: {formatted_item}")
            else:
                formatted_value = self._format_float(value) if isinstance(value, float) else value
                output_lines.append(f"{prefix}{key}: {formatted_value}")

    def _format_float(self, value: float) -> str:
        """格式化浮点数，避免精度问题

        Args:
            value: 浮点数值

        Returns:
            格式化后的字符串
        """
        if not isinstance(value, float):
            return str(value)

        try:
            # 转换为 Decimal 并格式化为最多5位小数
            decimal_value = Decimal(str(value))
            # 尝试不同的小数位数（最多5位），找到最合适的
            for places in range(5, -1, -1):
                formatted = f"{decimal_value:.{places}f}"
                # 检查格式化后的值是否与原值相等（考虑精度误差）
                if abs(float(formatted) - value) < 1e-10:
                    # 移除末尾的0和小数点
                    return formatted.rstrip("0").rstrip(".")
            # 如果都不匹配，使用5位小数
            return f"{decimal_value:.5f}".rstrip("0").rstrip(".")
        except Exception:
            # 如果 Decimal 转换失败，使用原始方法
            return f"{value:.5f}".rstrip("0").rstrip(".")
