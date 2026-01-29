"""
协议数据提取器
从日志文件中提取数据组，支持方向信息和终端ID提取
"""

import logging
import re
from typing import Any, Dict, List

from src.logger_instance import log

logger = logging.getLogger(__name__)


class ProtocolDataExtractor:
    """协议数据提取器类

    负责从日志文件中提取数据组，包括时间戳、方向、终端ID和原始数据
    """

    def __init__(self, frame_head_pattern: str):
        """初始化数据提取器

        Args:
            frame_head_pattern: 协议帧头正则表达式模式
        """
        self.frame_head_pattern = frame_head_pattern

        # 预编译正则表达式（性能优化：避免重复编译）
        self._info_line_re = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{2,3}")
        self._byte_sequence_re = re.compile(frame_head_pattern)
        self._direction_re = re.compile(r"(Send|Recv|TX|RX)", re.IGNORECASE)
        self._terminal_id_re = re.compile(r"\[(\d+)\]\s+\w+.*?:")  # 匹配 [数字] 终端ID

    def extract_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """从文件中提取数据组

        Args:
            file_path: 日志文件路径

        Returns:
            提取的数据组列表，每个数据组包含 time, direction, terminal_id, data 字段

        Raises:
            IOError: 文件读取失败
        """
        # 使用预编译的正则表达式（性能优化）
        info_line_re = self._info_line_re
        byte_sequence_re = self._byte_sequence_re
        direction_re = self._direction_re
        terminal_id_re = self._terminal_id_re

        data_groups = []
        current_group = None
        is_collecting_data = False

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line == "":
                        continue

                    # 跳过注释行（以 // 开头）
                    if line.startswith("//"):
                        continue

                    info_line_match = info_line_re.search(line)
                    if info_line_match:
                        # 保存上一个数据组
                        if current_group:
                            data_groups.append(current_group)
                            is_collecting_data = False

                        # 提取时间戳
                        time_str = info_line_match.group()

                        # 提取方向信息
                        direction_match = direction_re.search(line)
                        direction = direction_match.group() if direction_match else ""

                        # 提取终端ID
                        terminal_id_match = terminal_id_re.search(line)
                        terminal_id = int(terminal_id_match.group(1)) if terminal_id_match else None

                        # 创建新的数据组
                        current_group = {
                            "time": time_str,
                            "direction": direction,
                            "terminal_id": terminal_id,
                            "data_parts": [],  # 性能优化：使用列表收集，避免频繁字符串拼接
                        }
                        continue

                    # 检查行中是否包含帧头字节序列
                    byte_sequence_match = byte_sequence_re.search(line)
                    if byte_sequence_match:
                        is_collecting_data = True
                        # 从匹配的字节序列开始收集数据
                        line = line[byte_sequence_match.start() :]

                    # 收集数据行
                    if is_collecting_data and current_group is not None:
                        current_group["data_parts"].append(line)

                # 处理最后一个数据组
                if current_group:
                    data_groups.append(current_group)

                # 合并 data_parts 为 data 字符串
                for group in data_groups:
                    if "data_parts" in group:
                        group["data"] = " ".join(group["data_parts"])
                        del group["data_parts"]

                # 过滤空数据组
                data_groups = [g for g in data_groups if g.get("data")]

            return data_groups

        except IOError as e:
            error_msg = f"无法打开文件 {file_path}: {str(e)}"
            log.e_print(error_msg)
            raise IOError(error_msg) from e

    def set_frame_head_pattern(self, pattern: str) -> None:
        """更新帧头匹配模式

        Args:
            pattern: 新的帧头正则表达式模式
        """
        self.frame_head_pattern = pattern
        self._byte_sequence_re = re.compile(pattern)
