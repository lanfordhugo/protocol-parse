"""
文件名称: protocol_info.py
内容摘要: 协议信息数据类
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ProtocolStats:
    """协议统计信息"""

    cmd_count: int = 0  # 命令数量
    enum_count: int = 0  # 枚举数量
    type_count: int = 0  # 类型数量
    commands: List[Tuple[str, str]] = field(default_factory=list)  # 命令列表 (id, name)


@dataclass
class ProtocolInfo:
    """协议信息数据类

    包含协议的配置信息、日志文件信息和状态信息。
    完全独立于 GUI 框架，可在单元测试中直接使用。
    """

    # 基本信息
    name: str  # 协议名称
    config_path: Path  # 配置文件路径

    # 日志文件信息
    log_path: Optional[Path] = None  # 日志文件路径
    log_exists: bool = False  # 日志文件是否存在
    log_size: int = 0  # 日志文件大小（字节）

    # 配置状态
    config_valid: bool = True  # 配置是否有效

    # 协议统计信息（延迟加载）
    stats: Optional[ProtocolStats] = None

    def __post_init__(self):
        """初始化后处理"""
        # 确保 config_path 是 Path 对象
        if isinstance(self.config_path, str):
            object.__setattr__(self, 'config_path', Path(self.config_path))

        # 确保 log_path 是 Path 对象
        if isinstance(self.log_path, str):
            object.__setattr__(self, 'log_path', Path(self.log_path))

    @property
    def has_log(self) -> bool:
        """是否有可用的日志文件"""
        return self.log_exists and self.log_size > 0

    @property
    def log_size_human(self) -> str:
        """人类可读的日志文件大小"""
        return self._format_size(self.log_size)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            'name': self.name,
            'config_path': str(self.config_path),
            'log_path': str(self.log_path) if self.log_path else None,
            'log_exists': self.log_exists,
            'log_size': self.log_size,
            'config_valid': self.config_valid,
            'stats': {
                'cmd_count': self.stats.cmd_count if self.stats else 0,
                'enum_count': self.stats.enum_count if self.stats else 0,
                'type_count': self.stats.type_count if self.stats else 0,
                'commands': self.stats.commands if self.stats else [],
            } if self.stats else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProtocolInfo':
        """从字典创建实例（用于反序列化）"""
        stats = None
        if data.get('stats'):
            stats_data = data['stats']
            stats = ProtocolStats(
                cmd_count=stats_data.get('cmd_count', 0),
                enum_count=stats_data.get('enum_count', 0),
                type_count=stats_data.get('type_count', 0),
                commands=stats_data.get('commands', []),
            )

        return cls(
            name=data['name'],
            config_path=Path(data['config_path']),
            log_path=Path(data['log_path']) if data.get('log_path') else None,
            log_exists=data.get('log_exists', False),
            log_size=data.get('log_size', 0),
            config_valid=data.get('config_valid', True),
            stats=stats,
        )
