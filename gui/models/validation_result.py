"""
文件名称: validation_result.py
内容摘要: 验证结果数据类
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ValidationStatus(Enum):
    """验证状态枚举"""

    PENDING = "pending"  # 等待验证
    RUNNING = "running"  # 验证中
    VALID = "valid"  # 验证通过
    INVALID = "invalid"  # 验证失败
    WARNING = "warning"  # 有警告
    ERROR = "error"  # 验证出错


@dataclass
class ValidationResult:
    """验证结果数据类

    包含协议配置验证的所有信息，包括状态、错误、警告等。
    完全独立于 GUI 框架，可在单元测试中直接使用。
    """

    # 基本信息
    protocol_name: str  # 协议名称
    config_path: Path  # 配置文件路径

    # 状态信息
    status: ValidationStatus = ValidationStatus.PENDING  # 验证状态
    message: str = ""  # 结果消息

    # 验证结果
    is_valid: bool = False  # 是否有效
    has_warnings: bool = False  # 是否有警告

    # 错误和警告
    errors: List[str] = field(default_factory=list)  # 错误列表
    warnings: List[str] = field(default_factory=list)  # 警告列表

    # 详细信息
    details: dict = field(default_factory=dict)  # 详细验证信息

    # 时间信息
    validation_time: Optional[datetime] = None  # 验证时间

    def __post_init__(self):
        """初始化后处理"""
        # 确保 config_path 是 Path 对象
        if isinstance(self.config_path, str):
            object.__setattr__(self, 'config_path', Path(self.config_path))

        # 设置验证时间
        if not self.validation_time:
            object.__setattr__(self, 'validation_time', datetime.now())

    @property
    def error_count(self) -> int:
        """错误数量"""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """警告数量"""
        return len(self.warnings)

    @property
    def is_valid_with_warnings(self) -> bool:
        """是否有效但有警告"""
        return self.is_valid and self.has_warnings

    @property
    def summary(self) -> str:
        """验证摘要"""
        if self.status == ValidationStatus.VALID:
            return f"✅ 配置验证通过 ({self.protocol_name})"
        elif self.status == ValidationStatus.WARNING:
            return f"⚠️  配置验证通过但有警告 ({self.warning_count} 个) ({self.protocol_name})"
        elif self.status == ValidationStatus.INVALID:
            return f"❌ 配置验证失败 ({self.error_count} 个错误) ({self.protocol_name})"
        elif self.status == ValidationStatus.ERROR:
            return f"💥 验证过程出错: {self.message} ({self.protocol_name})"
        else:
            return f"⏳ 等待验证... ({self.protocol_name})"

    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            'protocol_name': self.protocol_name,
            'config_path': str(self.config_path),
            'status': self.status.value,
            'message': self.message,
            'is_valid': self.is_valid,
            'has_warnings': self.has_warnings,
            'errors': self.errors,
            'warnings': self.warnings,
            'details': self.details,
            'validation_time': self.validation_time.isoformat() if self.validation_time else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ValidationResult':
        """从字典创建实例（用于反序列化）"""
        return cls(
            protocol_name=data['protocol_name'],
            config_path=Path(data['config_path']),
            status=ValidationStatus(data.get('status', ValidationStatus.PENDING.value)),
            message=data.get('message', ""),
            is_valid=data.get('is_valid', False),
            has_warnings=data.get('has_warnings', False),
            errors=data.get('errors', []),
            warnings=data.get('warnings', []),
            details=data.get('details', {}),
            validation_time=datetime.fromisoformat(data['validation_time']) if data.get('validation_time') else None,
        )

    @classmethod
    def create_valid(cls, protocol_name: str, config_path: Path) -> 'ValidationResult':
        """创建验证通过的结果"""
        return cls(
            protocol_name=protocol_name,
            config_path=config_path,
            status=ValidationStatus.VALID,
            is_valid=True,
            has_warnings=False,
            message=f"协议 {protocol_name} 配置验证通过",
        )

    @classmethod
    def create_warning(
        cls,
        protocol_name: str,
        config_path: Path,
        warnings: List[str]
    ) -> 'ValidationResult':
        """创建有警告的验证结果"""
        return cls(
            protocol_name=protocol_name,
            config_path=config_path,
            status=ValidationStatus.WARNING,
            is_valid=True,
            has_warnings=True,
            warnings=warnings,
            message=f"协议 {protocol_name} 配置验证通过（{len(warnings)} 个警告）",
        )

    @classmethod
    def create_invalid(
        cls,
        protocol_name: str,
        config_path: Path,
        errors: List[str],
        warnings: List[str] = None
    ) -> 'ValidationResult':
        """创建验证失败的结果"""
        return cls(
            protocol_name=protocol_name,
            config_path=config_path,
            status=ValidationStatus.INVALID,
            is_valid=False,
            has_warnings=bool(warnings),
            errors=errors,
            warnings=warnings or [],
            message=f"协议 {protocol_name} 配置验证失败（{len(errors)} 个错误）",
        )

    @classmethod
    def create_error(
        cls,
        protocol_name: str,
        config_path: Path,
        error_message: str
    ) -> 'ValidationResult':
        """创建验证出错的结果"""
        return cls(
            protocol_name=protocol_name,
            config_path=config_path,
            status=ValidationStatus.ERROR,
            is_valid=False,
            message=error_message,
            errors=[error_message],
        )
