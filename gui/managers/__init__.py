"""
GUI 业务管理器模块

本模块包含 GUI 应用的业务逻辑管理器，负责协调数据访问和业务流程。
这些管理器完全独立于 GUI 框架，可在单元测试中直接使用。
"""

from .protocol_manager import ProtocolManager
from .parse_manager import ParseManager
from .validation_manager import ValidationManager

__all__ = [
    'ProtocolManager',
    'ParseManager',
    'ValidationManager',
]
