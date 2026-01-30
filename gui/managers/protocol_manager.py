"""
文件名称: protocol_manager.py
内容摘要: 协议管理器 - 负责协议的发现、加载和统计
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gui.models import ProtocolInfo, ProtocolStats


class ProtocolManager:
    """协议管理器

    负责协议的发现、加载、验证和统计信息获取。
    完全独立于 GUI 框架，可在单元测试中直接使用。
    """

    def __init__(self, configs_dir: Path):
        """初始化协议管理器

        Args:
            configs_dir: 协议配置目录
        """
        self._configs_dir = Path(configs_dir)
        self._protocols: Dict[str, ProtocolInfo] = {}
        self._ensure_src_path()

    def _ensure_src_path(self):
        """确保 src 目录在 Python 路径中"""
        src_path = self._configs_dir.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

    def discover_protocols(self) -> List[ProtocolInfo]:
        """发现所有可用协议

        扫描配置目录，发现所有包含 protocol.yaml 的协议。

        Returns:
            协议信息列表
        """
        self._protocols.clear()

        if not self._configs_dir.exists():
            return []

        for protocol_dir in sorted(self._configs_dir.iterdir()):
            if not protocol_dir.is_dir():
                continue

            yaml_config = protocol_dir / "protocol.yaml"
            if not yaml_config.exists():
                continue

            protocol_name = protocol_dir.name

            # 创建协议信息
            protocol_info = ProtocolInfo(
                name=protocol_name,
                config_path=yaml_config,
                log_path=None,  # 日志文件由用户选择
                log_exists=False,
                log_size=0,
                config_valid=True,  # 初始假设有效
            )

            self._protocols[protocol_name] = protocol_info

        return list(self._protocols.values())

    def get_protocol_info(self, protocol_name: str) -> Optional[ProtocolInfo]:
        """获取协议信息

        Args:
            protocol_name: 协议名称

        Returns:
            协议信息，如果不存在则返回 None
        """
        return self._protocols.get(protocol_name)

    def get_all_protocols(self) -> List[ProtocolInfo]:
        """获取所有协议信息

        Returns:
            协议信息列表
        """
        return list(self._protocols.values())

    def load_protocol_config(self, protocol_name: str):
        """加载协议配置

        Args:
            protocol_name: 协议名称

        Returns:
            协议配置对象，如果加载失败则返回 None

        Raises:
            ValueError: 如果协议不存在
        """
        from yaml_config import YamlConfigLoader

        protocol_info = self.get_protocol_info(protocol_name)
        if not protocol_info:
            raise ValueError(f"Protocol not found: {protocol_name}")

        loader = YamlConfigLoader()
        try:
            config = loader.load_protocol_config(protocol_info.config_path)
            return config
        except Exception as e:
            # 更新协议状态为无效
            protocol_info.config_valid = False
            raise

    def get_protocol_stats(self, protocol_name: str) -> Optional[ProtocolStats]:
        """获取协议统计信息

        Args:
            protocol_name: 协议名称

        Returns:
            协议统计信息，如果获取失败则返回 None
        """
        try:
            config = self.load_protocol_config(protocol_name)
            if not config:
                return None

            # 统计信息
            cmd_count = len(config.cmds) if config.cmds else 0
            enum_count = len(config.enums) if config.enums else 0
            type_count = len(config.types) if config.types else 0

            # 构建命令列表
            commands: List[Tuple[str, str]] = []
            if config.cmds:
                for cmd_id in config.cmds.keys():
                    commands.append((str(cmd_id), str(cmd_id)))

            stats = ProtocolStats(
                cmd_count=cmd_count,
                enum_count=enum_count,
                type_count=type_count,
                commands=commands,
            )

            # 更新协议信息
            protocol_info = self.get_protocol_info(protocol_name)
            if protocol_info:
                protocol_info.stats = stats

            return stats

        except Exception:
            return None

    def update_protocol_log_path(
        self,
        protocol_name: str,
        log_path: Path
    ) -> bool:
        """更新协议的日志文件路径

        Args:
            protocol_name: 协议名称
            log_path: 日志文件路径

        Returns:
            是否更新成功
        """
        protocol_info = self.get_protocol_info(protocol_name)
        if not protocol_info:
            return False

        log_file = Path(log_path)
        log_exists = log_file.exists()
        log_size = log_file.stat().st_size if log_exists else 0

        protocol_info.log_path = log_file
        protocol_info.log_exists = log_exists
        protocol_info.log_size = log_size

        return True

    def validate_protocol(self, protocol_name: str) -> bool:
        """验证协议配置

        Args:
            protocol_name: 协议名称

        Returns:
            是否验证通过
        """
        from validate_configs import ConfigValidator

        protocol_info = self.get_protocol_info(protocol_name)
        if not protocol_info:
            return False

        validator = ConfigValidator()
        is_valid = validator.validate_protocol_config(protocol_info.config_path)

        # 更新协议状态
        protocol_info.config_valid = is_valid

        return is_valid

    def refresh_protocols(self) -> List[ProtocolInfo]:
        """刷新协议列表

        重新扫描配置目录，更新协议信息。

        Returns:
            更新后的协议信息列表
        """
        return self.discover_protocols()

    def has_protocol(self, protocol_name: str) -> bool:
        """检查协议是否存在

        Args:
            protocol_name: 协议名称

        Returns:
            协议是否存在
        """
        return protocol_name in self._protocols

    def get_protocol_count(self) -> int:
        """获取协议数量

        Returns:
            协议总数
        """
        return len(self._protocols)
