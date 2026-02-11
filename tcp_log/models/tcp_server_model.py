"""
文件名称: tcp_server_model.py
内容摘要: TCP 服务端业务模型 - 封装协议扫描、报文解析、统计、保存逻辑（纯 Python）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EntryData:
    """解析后的条目数据"""

    entry: Any  # LogEntry 对象
    parsed: Optional[dict] = None
    success: bool = False


@dataclass
class CmdStatsItem:
    """单个命令的统计项"""

    cmd_id: int
    cmd_name: str
    total_count: int
    success_count: int

    @property
    def success_rate(self) -> float:
        """成功率百分比"""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count * 100


@dataclass
class StatsData:
    """汇总统计数据"""

    entry_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    cmd_count: int = 0

    @property
    def success_rate(self) -> float:
        """总成功率百分比"""
        if self.entry_count == 0:
            return 0.0
        return self.success_count / self.entry_count * 100


class TcpServerModel:
    """
    TCP 服务端业务模型

    职责：
    - 协议配置扫描和加载
    - 报文解析（调用 YamlCmdFormat）
    - 统计数据管理
    - 日志/结果保存
    - 条目缓存管理

    注意：本类为纯 Python 实现，不依赖 PySide6
    """

    # 默认缓存大小
    DEFAULT_MAX_CACHE = 10000

    def __init__(self, configs_dir: Path, save_dir: Path, max_cache: int = DEFAULT_MAX_CACHE):
        """
        初始化 TCP 服务端模型

        Args:
            configs_dir: 协议配置目录
            save_dir: 保存输出目录
            max_cache: 最大缓存条目数（默认10000）
        """
        self._configs_dir = configs_dir
        self._save_dir = save_dir
        self._max_cache = max_cache

        # 协议相关
        self._protocols: Dict[str, str] = {}  # name -> yaml_path
        self._current_protocol = None  # YamlCmdFormat 实例

        # 统计数据
        self._entry_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._cmd_stats: Dict[int, int] = {}

        # 条目缓存（deque 逐条淘汰，满时自动丢弃最旧条目）
        self._all_entries: Deque[EntryData] = deque(maxlen=max_cache)

        # 会话 ID（用于文件命名）
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ============== 协议管理 ==============

    def scan_protocols(self) -> List[str]:
        """
        扫描协议配置目录

        Returns:
            已排序的协议名称列表
        """
        self._protocols.clear()

        if not self._configs_dir.exists():
            return []

        for protocol_dir in self._configs_dir.iterdir():
            if protocol_dir.is_dir():
                yaml_config = protocol_dir / "protocol.yaml"
                if yaml_config.exists():
                    self._protocols[protocol_dir.name] = str(yaml_config)

        return sorted(self._protocols.keys())

    def load_protocol(self, protocol_name: str) -> Tuple[bool, str]:
        """
        加载指定协议

        Args:
            protocol_name: 协议名称

        Returns:
            (是否成功, 消息)
        """
        if protocol_name not in self._protocols:
            self._current_protocol = None
            return False, f"未知协议: {protocol_name}"

        try:
            from src.yaml_cmdformat import YamlCmdFormat
            yaml_path = self._protocols[protocol_name]
            self._current_protocol = YamlCmdFormat(yaml_path)
            return True, f"已加载协议: {protocol_name}"
        except Exception as e:
            self._current_protocol = None
            return False, f"加载协议失败: {e}"

    @property
    def current_protocol(self):
        """获取当前协议"""
        return self._current_protocol

    @property
    def has_protocol(self) -> bool:
        """是否已加载协议"""
        return self._current_protocol is not None

    # ============== 报文解析 ==============

    def parse_entry(self, entry: Any) -> EntryData:
        """
        解析一条日志条目

        Args:
            entry: LogEntry 对象

        Returns:
            解析后的条目数据
        """
        parsed_result = None
        parse_success = False

        if self._current_protocol:
            try:
                hex_str = entry.hex_data.replace(' ', '')
                if hex_str:
                    byte_data = bytes.fromhex(hex_str)
                    config = self._current_protocol.config
                    if len(byte_data) > config.head_len:
                        tail = config.tail_len
                        content = byte_data[config.head_len:-tail] if tail > 0 else byte_data[config.head_len:]
                        parsed_result = self._current_protocol.parse_cmd_data(
                            entry.cmd_id, content
                        )
                        parse_success = True
            except Exception as e:
                parsed_result = {"error": str(e)}

        # 更新统计
        self._entry_count += 1
        if parse_success:
            self._success_count += 1
        else:
            self._fail_count += 1
        self._cmd_stats[entry.cmd_id] = self._cmd_stats.get(entry.cmd_id, 0) + 1

        entry_data = EntryData(entry=entry, parsed=parsed_result, success=parse_success)

        # deque 满时 append 自动淘汰最旧1条，记录是否发生淘汰
        was_full = len(self._all_entries) >= self._max_cache
        self._all_entries.append(entry_data)
        entry_data._evicted = 1 if was_full else 0

        return entry_data

    # ============== 缓存管理 ==============

    @property
    def cache_count(self) -> int:
        """当前缓存条目数"""
        return len(self._all_entries)

    @property
    def max_cache(self) -> int:
        """最大缓存条目数"""
        return self._max_cache

    def set_max_cache(self, size: int) -> None:
        """
        运行时调整缓存大小

        如果新大小比当前数据量小，最旧的数据会被自动丢弃。

        Args:
            size: 新的最大缓存条目数（最小100）
        """
        size = max(100, size)
        self._max_cache = size
        # 重建 deque，超出部分自动从左侧（最旧）丢弃
        self._all_entries = deque(self._all_entries, maxlen=size)

    @property
    def all_entries(self) -> Deque[EntryData]:
        """所有缓存条目"""
        return self._all_entries

    # ============== 统计 ==============

    def get_stats(self) -> StatsData:
        """
        获取汇总统计数据

        Returns:
            统计数据
        """
        return StatsData(
            entry_count=self._entry_count,
            success_count=self._success_count,
            fail_count=self._fail_count,
            cmd_count=len(self._cmd_stats),
        )

    def get_cmd_stats_detail(self) -> List[CmdStatsItem]:
        """
        获取按命令分组的详细统计

        Returns:
            按接收次数降序排列的命令统计列表
        """
        # 统计每个命令的成功/总次数
        cmd_success: Dict[int, Dict[str, int]] = {}
        for entry_data in self._all_entries:
            cmd_id = entry_data.entry.cmd_id
            if cmd_id not in cmd_success:
                cmd_success[cmd_id] = {"total": 0, "success": 0}
            cmd_success[cmd_id]["total"] += 1
            if entry_data.success:
                cmd_success[cmd_id]["success"] += 1

        # 按接收次数降序排列
        sorted_cmds = sorted(self._cmd_stats.items(), key=lambda x: x[1], reverse=True)

        result = []
        for cmd_id, count in sorted_cmds:
            stats = cmd_success.get(cmd_id, {"total": 0, "success": 0})
            result.append(CmdStatsItem(
                cmd_id=cmd_id,
                cmd_name=self._get_cmd_name(cmd_id),
                total_count=count,
                success_count=stats["success"],
            ))

        return result

    def reset_stats(self) -> None:
        """重置所有统计数据"""
        self._entry_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._cmd_stats.clear()

    def _get_cmd_name(self, cmd_id: int) -> str:
        """
        获取命令名称

        Args:
            cmd_id: 命令 ID

        Returns:
            命令名称
        """
        if self._current_protocol:
            try:
                config = self._current_protocol.config
                for cmd in config.commands:
                    if cmd.cmd_id == cmd_id:
                        return cmd.name or f"cmd{cmd_id}"
            except Exception:
                pass
        return f"cmd{cmd_id}"

    # ============== 数据格式化 ==============

    @staticmethod
    def generate_summary(parsed: Optional[dict]) -> str:
        """
        生成解析结果摘要

        Args:
            parsed: 解析结果字典

        Returns:
            摘要字符串
        """
        if not parsed:
            return ""
        if "error" in parsed:
            return f"[错误] {parsed['error']}"

        items = []
        for key, value in list(parsed.items())[:4]:
            if isinstance(value, dict):
                if 'value' in value and 'name' in value:
                    items.append(f"{key}={value['name']}")
                else:
                    items.append(f"{key}=...")
            elif isinstance(value, list):
                items.append(f"{key}=[{len(value)}项]")
            else:
                items.append(f"{key}={value}")
        return ", ".join(items)

    @staticmethod
    def format_detail(entry: Any, parsed: Optional[dict], success: bool) -> str:
        """
        格式化条目详情文本

        Args:
            entry: LogEntry 对象
            parsed: 解析结果
            success: 是否成功

        Returns:
            格式化后的详情文本
        """
        lines = []
        lines.append("=== 数据项 ===")
        lines.append(f"时间: {entry.timestamp}")
        lines.append(f"方向: {entry.direction}")
        lines.append(f"命令: cmd{entry.cmd_id}")
        lines.append(f"字节数: {entry.byte_count}")
        if entry.terminal_id is not None:
            lines.append(f"终端ID: {entry.terminal_id}")
        lines.append(f"源信息: {entry.source_info}")
        lines.append("")

        if parsed and success:
            lines.append("解析内容:")
            TcpServerModel._format_parsed_recursive(parsed, lines, indent=2)
        elif parsed and "error" in parsed:
            lines.append(f"解析错误: {parsed['error']}")

        lines.append("")
        lines.append("原始数据:")
        lines.append(entry.hex_data)

        return "\n".join(lines)

    @staticmethod
    def _format_parsed_recursive(data: dict, lines: list, indent: int = 0) -> None:
        """递归格式化解析结果"""
        prefix = " " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                if 'value' in value and 'name' in value:
                    lines.append(f"{prefix}{key}: {value['value']} ({value['name']})")
                else:
                    lines.append(f"{prefix}{key}:")
                    TcpServerModel._format_parsed_recursive(value, lines, indent + 2)
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: [{len(value)} 项]")
                for i, item in enumerate(value[:3]):
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  [{i}]:")
                        TcpServerModel._format_parsed_recursive(item, lines, indent + 4)
                    else:
                        lines.append(f"{prefix}  [{i}]: {item}")
                if len(value) > 3:
                    lines.append(f"{prefix}  ... 还有 {len(value) - 3} 项")
            else:
                lines.append(f"{prefix}{key}: {value}")

    # ============== 数据持久化 ==============

    def save_log_entry(self, entry: Any) -> Optional[str]:
        """
        保存日志条目到文件

        Args:
            entry: LogEntry 对象

        Returns:
            错误消息，成功时返回 None
        """
        try:
            self._save_dir.mkdir(parents=True, exist_ok=True)
            log_file = self._save_dir / f"tcp_log_{self._session_id}.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.raw_text)
                if not entry.raw_text.endswith("\n"):
                    f.write("\n")
            return None
        except Exception as e:
            return f"保存日志失败: {e}"

    def save_parsed_result(
        self, entry: Any, parsed: Optional[dict], success: bool
    ) -> Optional[str]:
        """
        保存解析结果到 JSON 文件

        Args:
            entry: LogEntry 对象
            parsed: 解析结果
            success: 是否成功

        Returns:
            错误消息，成功时返回 None
        """
        try:
            self._save_dir.mkdir(parents=True, exist_ok=True)
            result_file = self._save_dir / f"tcp_parsed_{self._session_id}.json"
            record = {
                "timestamp": entry.timestamp,
                "direction": entry.direction,
                "cmd_id": entry.cmd_id,
                "byte_count": entry.byte_count,
                "terminal_id": entry.terminal_id,
                "success": success,
                "parsed": parsed if parsed else {},
                "hex_data": entry.hex_data,
            }
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return None
        except Exception as e:
            return f"保存解析结果失败: {e}"

    # ============== 过滤 ==============

    @staticmethod
    def should_show_entry(
        cmd_id: int,
        success: bool,
        filter_cmd: Optional[int],
        success_only: bool,
    ) -> bool:
        """
        判断条目是否应该显示

        Args:
            cmd_id: 命令 ID
            success: 是否成功
            filter_cmd: 过滤的命令 ID（None 表示全部）
            success_only: 是否仅显示成功

        Returns:
            是否应该显示
        """
        if success_only and not success:
            return False
        if filter_cmd is not None and cmd_id != filter_cmd:
            return False
        return True

    def clear_entries(self) -> None:
        """清空所有缓存条目"""
        self._all_entries.clear()
