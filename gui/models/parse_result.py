"""
文件名称: parse_result.py
内容摘要: 解析结果数据类
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class ParseStatus(Enum):
    """解析状态枚举"""

    PENDING = "pending"  # 等待解析
    RUNNING = "running"  # 解析中
    SUCCESS = "success"  # 解析成功
    FAILED = "failed"  # 解析失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class ParseFilter:
    """解析过滤器设置"""

    # 时间范围
    start_time: Optional[datetime] = None  # 开始时间
    end_time: Optional[datetime] = None  # 结束时间

    # 命令过滤
    include_cmds: Optional[List[str]] = None  # 包含的命令ID列表
    exclude_cmds: Optional[List[str]] = None  # 排除的命令ID列表

    # 高级选项
    skip_invalid: bool = False  # 跳过无效数据
    strict_mode: bool = False  # 严格模式

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'include_cmds': self.include_cmds,
            'exclude_cmds': self.exclude_cmds,
            'skip_invalid': self.skip_invalid,
            'strict_mode': self.strict_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ParseFilter':
        """从字典创建实例"""
        return cls(
            start_time=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None,
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            include_cmds=data.get('include_cmds'),
            exclude_cmds=data.get('exclude_cmds'),
            skip_invalid=data.get('skip_invalid', False),
            strict_mode=data.get('strict_mode', False),
        )


@dataclass
class ParseResult:
    """解析结果数据类

    包含解析任务的所有信息，包括状态、进度、结果文件等。
    完全独立于 GUI 框架，可在单元测试中直接使用。
    """

    # 基本信息
    protocol_name: str  # 协议名称
    config_path: Path  # 配置文件路径
    log_path: Path  # 日志文件路径

    # 状态信息
    status: ParseStatus = ParseStatus.PENDING  # 解析状态
    progress: int = 0  # 进度百分比 (0-100)
    current_step: str = ""  # 当前步骤描述

    # 结果信息
    success: bool = False  # 是否成功
    message: str = ""  # 结果消息
    output_path: Optional[Path] = None  # 输出文件路径

    # 统计信息
    total_lines: int = 0  # 总行数
    parsed_lines: int = 0  # 已解析行数
    error_count: int = 0  # 错误数量

    # 时间信息
    start_time: Optional[datetime] = None  # 开始时间
    end_time: Optional[datetime] = None  # 结束时间

    # 错误信息
    errors: List[str] = field(default_factory=list)  # 错误列表

    def __post_init__(self):
        """初始化后处理"""
        # 确保 config_path 是 Path 对象
        if isinstance(self.config_path, str):
            object.__setattr__(self, 'config_path', Path(self.config_path))

        # 确保 log_path 是 Path 对象
        if isinstance(self.log_path, str):
            object.__setattr__(self, 'log_path', Path(self.log_path))

        # 确保 output_path 是 Path 对象
        if self.output_path and isinstance(self.output_path, str):
            object.__setattr__(self, 'output_path', Path(self.output_path))

        # 自动计算进度
        if self.total_lines > 0:
            object.__setattr__(self, 'progress', int((self.parsed_lines / self.total_lines) * 100))
        else:
            object.__setattr__(self, 'progress', 0)

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == ParseStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in [ParseStatus.SUCCESS, ParseStatus.FAILED, ParseStatus.CANCELLED]

    @property
    def duration_seconds(self) -> Optional[float]:
        """解析耗时（秒）"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """成功率 (parsed_lines / total_lines * 100)"""
        if self.total_lines == 0:
            return 0.0
        return (self.parsed_lines / self.total_lines) * 100

    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            'protocol_name': self.protocol_name,
            'config_path': str(self.config_path),
            'log_path': str(self.log_path),
            'status': self.status.value,
            'progress': self.progress,
            'current_step': self.current_step,
            'success': self.success,
            'message': self.message,
            'output_path': str(self.output_path) if self.output_path else None,
            'total_lines': self.total_lines,
            'parsed_lines': self.parsed_lines,
            'error_count': self.error_count,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'errors': self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ParseResult':
        """从字典创建实例（用于反序列化）"""
        return cls(
            protocol_name=data['protocol_name'],
            config_path=Path(data['config_path']),
            log_path=Path(data['log_path']),
            status=ParseStatus(data.get('status', ParseStatus.PENDING.value)),
            progress=data.get('progress', 0),
            current_step=data.get('current_step', ""),
            success=data.get('success', False),
            message=data.get('message', ""),
            output_path=Path(data['output_path']) if data.get('output_path') else None,
            total_lines=data.get('total_lines', 0),
            parsed_lines=data.get('parsed_lines', 0),
            error_count=data.get('error_count', 0),
            start_time=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None,
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            errors=data.get('errors', []),
        )
