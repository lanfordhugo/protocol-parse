"""
协议解析器
解析协议数据内容，包括头部解析、命令过滤、数据内容解析
"""

import logging
import struct
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.logger_instance import log
from src.yaml_cmdformat import YamlCmdFormat

logger = logging.getLogger(__name__)


class ProtocolParser:
    """协议解析器类

    负责解析协议数据，包括头部信息、命令内容和数据字段
    """

    def __init__(self, yaml_format: YamlCmdFormat):
        """初始化协议解析器

        Args:
            yaml_format: YAML命令格式管理器实例
        """
        self.yaml_format = yaml_format
        self.yaml_config = yaml_format.config

        # 性能统计
        self.perf_stats = {
            "cmd_counts": defaultdict(int),
            "errors": 0,
        }

    def reset_stats(self) -> None:
        """重置性能统计数据"""
        self.perf_stats = {
            "cmd_counts": defaultdict(int),
            "errors": 0,
        }

    def set_filters(
        self,
        include_cmds: Optional[List[int]] = None,
        exclude_cmds: Optional[List[int]] = None,
        time_range: Optional[tuple[datetime, datetime]] = None,
    ) -> None:
        """设置解析过滤条件

        Args:
            include_cmds: 包含的命令ID列表，只解析这些命令
            exclude_cmds: 排除的命令ID列表，不解析这些命令
            time_range: 时间范围 (start_time, end_time)
        """
        self._include_cmds = include_cmds
        self._exclude_cmds = exclude_cmds
        self._time_range = time_range

    def parse_data_groups(
        self,
        data_groups: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
        should_stop_callback: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """解析数据组列表

        Args:
            data_groups: 数据组列表
            progress_callback: 进度回调函数，签名为 callback(current: int, total: int)
            should_stop_callback: 停止检查回调函数，返回 True 表示停止

        Returns:
            解析后的数据组列表
        """
        parsed_data_groups = []
        total_count = len(data_groups)

        for index, group in enumerate(data_groups):
            # 检查停止标志
            if should_stop_callback and should_stop_callback():
                break

            # 发送进度更新（10-80%用于数据解析阶段）
            if progress_callback:
                progress = 10 + int((index / total_count) * 70)
                try:
                    progress_callback(progress, 100)
                except Exception:
                    pass  # 忽略回调异常

            try:
                # 解析数据字节
                data_bytes = group["data"].strip().split()
                if len(data_bytes) < self.yaml_config.head_len:
                    continue

                # 转换为字节数组（性能优化：使用 fromhex 替代列表推导）
                byte_data = bytes.fromhex("".join(data_bytes))

                # 解析头部字段
                header_info = self._parse_header(byte_data[: self.yaml_config.head_len])
                if not header_info:
                    continue

                cmd_id = header_info.get("cmd")
                if cmd_id is None:
                    continue

                # 应用命令过滤
                if not self._check_cmd_filter(cmd_id):
                    continue

                # 检查是否支持该命令
                if not self.yaml_format.has_cmd(cmd_id):
                    continue

                # 应用时间过滤
                timestamp_str = group.get("time", "")
                if not self._check_time_filter(timestamp_str):
                    continue

                # 解析数据内容（跳过头部和尾部）
                tail_len = self.yaml_config.tail_len
                content_data = byte_data[
                    self.yaml_config.head_len : -tail_len if tail_len > 0 else None
                ]

                try:
                    parsed_content = self.yaml_format.parse_cmd_data(cmd_id, content_data)

                    # 构建结果
                    self.perf_stats["cmd_counts"][cmd_id] += 1
                    result = {
                        "timestamp": group.get("time", ""),
                        "direction": group.get("direction", ""),
                        "terminal_id": group.get("terminal_id"),
                        "raw_data": group.get("data", ""),
                        "header": header_info,
                        "cmd": cmd_id,
                        "content": parsed_content,
                    }

                    parsed_data_groups.append(result)

                except Exception as e:
                    self.perf_stats["errors"] += 1
                    self.perf_stats["cmd_counts"][cmd_id] += 1
                    # 添加原始数据作为备用
                    result = {
                        "timestamp": group.get("time", ""),
                        "direction": group.get("direction", ""),
                        "terminal_id": group.get("terminal_id"),
                        "raw_data": group.get("data", ""),
                        "header": header_info,
                        "cmd": cmd_id,
                        "content": {"raw": content_data.hex().upper()},
                        "parse_error": str(e),
                    }
                    parsed_data_groups.append(result)

            except Exception as e:
                log.e_print(f"处理数据组失败: {e}")
                continue

        return parsed_data_groups

    def _parse_header(self, header_data: bytes) -> Optional[Dict[str, Any]]:
        """解析数据包头部

        Args:
            header_data: 头部字节数据

        Returns:
            解析后的头部信息字典，失败返回 None
        """
        try:
            header_fields = self.yaml_format.get_head_fields()
            header_info = {}

            for field_config in header_fields:
                name = field_config["name"]
                offset = field_config["offset"]
                length = field_config["length"]
                endian = field_config["endian"]
                field_type = field_config["type"]

                if offset + length > len(header_data):
                    continue

                field_data = header_data[offset : offset + length]

                # 解析字段值
                if field_type == "uint":
                    value = self._parse_uint_field(field_data, endian)
                elif field_type == "const":
                    value = self._parse_uint_field(field_data, endian)
                    # 检查常量值
                    expected = field_config.get("const_value")
                    if expected is not None and value != expected:
                        if field_config.get("required", True):
                            return None
                elif field_type == "hex":
                    value = field_data.hex().upper()
                elif field_type == "ascii":
                    value = field_data.decode("ascii", errors="ignore").rstrip("\x00")
                else:
                    value = field_data.hex().upper()

                header_info[name] = value

            return header_info

        except Exception as e:
            logger.debug(f"解析头部失败: {e}")
            return None

    def _parse_uint_field(self, data: bytes, endian: str) -> int:
        """解析无符号整数字段

        Args:
            data: 字节数据
            endian: 字节序（'little' 或 'big'）

        Returns:
            解析后的整数值

        Raises:
            ValueError: 不支持的数据长度
        """
        fmt = "<" if endian == "little" else ">"

        if len(data) == 1:
            return struct.unpack("B", data)[0]
        elif len(data) == 2:
            return struct.unpack(fmt + "H", data)[0]
        elif len(data) == 4:
            return struct.unpack(fmt + "L", data)[0]
        elif len(data) == 8:
            return struct.unpack(fmt + "Q", data)[0]
        else:
            raise ValueError(f"不支持的 uint 大小: {len(data)}")

    def _check_cmd_filter(self, cmd_id: int) -> bool:
        """检查命令ID是否通过过滤条件

        Args:
            cmd_id: 命令ID

        Returns:
            True 表示通过（应该解析），False 表示不通过（应该跳过）
        """
        # 如果设置了包含列表，只解析列表中的命令
        if hasattr(self, "_include_cmds") and self._include_cmds is not None:
            return cmd_id in self._include_cmds

        # 如果设置了排除列表，跳过列表中的命令
        if hasattr(self, "_exclude_cmds") and self._exclude_cmds is not None:
            return cmd_id not in self._exclude_cmds

        # 都没有设置，解析所有命令
        return True

    def _check_time_filter(self, timestamp_str: str) -> bool:
        """检查时间是否在过滤范围内

        Args:
            timestamp_str: 时间戳字符串（格式：YYYY-MM-DD HH:MM:SS.mmm）

        Returns:
            True 表示通过（在范围内），False 表示不通过（不在范围内）
        """
        if not hasattr(self, "_time_range") or self._time_range is None:
            return True  # 没有设置时间过滤，全部通过

        try:
            # 解析时间戳
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
            start_time, end_time = self._time_range
            return start_time <= timestamp <= end_time
        except (ValueError, TypeError):
            # 时间格式错误，默认通过
            return True
