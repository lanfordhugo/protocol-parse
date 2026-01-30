"""
GUI 数据模型模块

本模块包含 GUI 应用使用的所有数据类，用于表示业务数据。
这些数据类完全独立于 GUI 框架，可在单元测试中直接使用。
"""

from .protocol_info import ProtocolInfo, ProtocolStats
from .parse_result import ParseResult, ParseFilter, ParseStatus
from .validation_result import ValidationResult, ValidationStatus

__all__ = [
    'ProtocolInfo',
    'ProtocolStats',
    'ParseResult',
    'ParseFilter',
    'ParseStatus',
    'ValidationResult',
    'ValidationStatus',
]
