"""
文件名称: log_entry_parser.py
内容摘要: spdlog日志条目解析器，负责从TCP流中分离完整的日志条目
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class LogEntry:
    """日志条目数据结构"""
    timestamp: str          # 时间戳
    level: str              # 日志级别 (I/W/E/D/T/C)
    direction: str          # 方向 (Recv/Send/TX/RX)
    byte_count: int         # 字节数
    cmd_id: int             # 命令ID
    source_info: str        # 源信息 (文件:行号 pid:xxx tid:xxx)
    hex_data: str           # 十六进制数据
    raw_text: str           # 原始文本
    terminal_id: Optional[int] = None  # 终端ID，如 [1] 中的 1，部分报文可能没有


class LogEntryParser:
    """
    spdlog日志条目解析器
    
    支持两种日志格式:
    1. [I 2024-08-29 09:26:16:261] [5] yy com: Recv 109 Bytes(cmd=7[0X7]) [file:line pid:xxx tid:xxx]:
    2. [2025-06-30 08:51:52.804] [10] ccucom: Recv 30 Bytes(cmd=3[0X0003]) [file:line tid:xxx]
    """
    
    # 日志头正则模式 - 匹配两种格式
    # 格式1: [I 2024-08-29 09:26:16:261] (带日志级别)
    # 格式2: [2025-06-30 08:51:52.804] (无日志级别)
    LOG_HEAD_PATTERN = re.compile(
        r'^\[(?:(?P<level>[IWEDTC])\s+)?'
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.:]\d{2,3})\]',
        re.MULTILINE
    )
    
    # 日志信息行正则
    LOG_INFO_PATTERN = re.compile(
        r'\[(?P<id>\d+)\]\s+'
        r'(?P<channel>\w+\s*\w*):\s+'
        r'(?P<direction>Recv|Send|TX|RX)\s+'
        r'(?P<bytes>\d+)\s+Bytes'
        r'\(cmd=(?P<cmd>\d+)\[0[Xx](?P<cmd_hex>[0-9A-Fa-f]+)\]\)\s+'
        r'\[(?P<source>[^\]]+)\]'
    )
    
    def __init__(self):
        self._buffer = ""
        self._entries: List[LogEntry] = []
    
    def feed(self, data: str) -> List[LogEntry]:
        """
        向解析器输入数据，返回解析出的完整日志条目列表
        
        :param data: 接收到的数据
        :return: 解析出的完整日志条目列表
        """
        self._buffer += data
        return self._extract_entries()
    
    def _extract_entries(self) -> List[LogEntry]:
        """从缓冲区提取完整的日志条目"""
        entries = []
        
        # 查找所有日志头的位置
        positions = []
        for match in self.LOG_HEAD_PATTERN.finditer(self._buffer):
            positions.append(match.start())
        
        if len(positions) < 2:
            # 不足两个日志头，无法确定第一条日志是否完整
            return entries
        
        # 提取完整的日志条目（除了最后一个，因为可能不完整）
        for i in range(len(positions) - 1):
            start = positions[i]
            end = positions[i + 1]
            raw_text = self._buffer[start:end]
            
            entry = self._parse_entry(raw_text)
            if entry:
                entries.append(entry)
        
        # 保留最后一个日志头之后的内容（可能不完整）
        self._buffer = self._buffer[positions[-1]:]
        
        return entries
    
    def _parse_entry(self, raw_text: str) -> Optional[LogEntry]:
        """解析单条日志条目"""
        lines = raw_text.strip().split('\n')
        if not lines:
            return None
        
        # 解析第一行（日志头）
        first_line = lines[0]
        head_match = self.LOG_HEAD_PATTERN.match(first_line)
        if not head_match:
            return None
        
        level = head_match.group('level') or 'I'
        timestamp = head_match.group('timestamp')
        
        # 解析日志信息
        info_match = self.LOG_INFO_PATTERN.search(first_line)
        if not info_match:
            return None
        
        direction = info_match.group('direction')
        byte_count = int(info_match.group('bytes'))
        cmd_id = int(info_match.group('cmd'))
        source_info = info_match.group('source')
        
        # 提取终端ID（可选字段）
        terminal_id_str = info_match.group('id')
        terminal_id = int(terminal_id_str) if terminal_id_str else None
        
        # 提取十六进制数据（第二行及之后）
        hex_lines = []
        for line in lines[1:]:
            line = line.strip()
            if line and self._is_hex_line(line):
                hex_lines.append(line)
        
        hex_data = ' '.join(hex_lines)
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            direction=direction,
            byte_count=byte_count,
            cmd_id=cmd_id,
            source_info=source_info,
            hex_data=hex_data,
            raw_text=raw_text,
            terminal_id=terminal_id
        )
    
    def _is_hex_line(self, line: str) -> bool:
        """判断是否是十六进制数据行"""
        # 移除空格后，检查是否都是十六进制字符
        clean = line.replace(' ', '').replace('\t', '')
        if not clean:
            return False
        return all(c in '0123456789ABCDEFabcdef' for c in clean)
    
    def flush(self) -> List[LogEntry]:
        """
        刷新缓冲区，尝试解析剩余内容
        用于连接断开时处理最后一条日志
        """
        if not self._buffer.strip():
            return []
        
        entry = self._parse_entry(self._buffer)
        self._buffer = ""
        
        return [entry] if entry else []
    
    def reset(self):
        """重置解析器状态"""
        self._buffer = ""
        self._entries.clear()
    
    @classmethod
    def parse_file(cls, file_path: str) -> List[LogEntry]:
        """
        解析整个日志文件
        
        :param file_path: 日志文件路径
        :return: 日志条目列表
        """
        parser = cls()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        entries = parser.feed(content)
        entries.extend(parser.flush())
        
        return entries
    
    @classmethod
    def count_entries(cls, file_path: str) -> int:
        """
        快速统计日志文件中的条目数量
        
        :param file_path: 日志文件路径
        :return: 条目数量
        """
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if cls.LOG_HEAD_PATTERN.match(line):
                    count += 1
        return count
