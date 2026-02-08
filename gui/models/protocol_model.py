"""
文件名称: protocol_model.py
内容摘要: 协议数据模型 - 封装协议发现、加载、验证的业务逻辑（纯 Python，不依赖 Qt）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ProtocolInfo:
    """协议基础信息（用于列表展示）"""

    name: str
    config_path: str
    log_path: str = ""
    log_exists: bool = False
    log_size: int = 0
    config_valid: bool = True


@dataclass
class ProtocolDetail:
    """协议详细信息（用于详情面板展示）"""

    name: str
    config_path: str
    config_valid: bool
    log_path: str
    log_exists: bool
    log_size: int
    cmd_count: int = 0
    enum_count: int = 0
    type_count: int = 0
    commands: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class ValidationResult:
    """协议验证结果"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ProtocolModel:
    """
    协议数据模型

    职责：
    - 协议自动发现（扫描 configs/ 目录）
    - 协议配置加载和统计信息提取
    - 协议验证
    - 协议日志路径管理

    注意：本类为纯 Python 实现，不依赖 PySide6
    """

    def __init__(self, configs_dir: Path):
        """
        初始化协议模型

        Args:
            configs_dir: 协议配置目录路径
        """
        self._configs_dir = configs_dir
        self._protocols: Dict[str, ProtocolInfo] = {}

    @property
    def configs_dir(self) -> Path:
        """获取配置目录路径"""
        return self._configs_dir

    def discover_protocols(self) -> List[ProtocolInfo]:
        """
        自动发现所有可用协议

        扫描 configs/ 目录下的子目录，查找包含 protocol.yaml 的目录。

        Returns:
            协议信息列表
        """
        self._protocols.clear()

        if not self._configs_dir.exists():
            logger.warning(f"协议配置目录不存在: {self._configs_dir}")
            return []

        for protocol_dir in sorted(self._configs_dir.iterdir()):
            if not protocol_dir.is_dir():
                continue

            yaml_config = protocol_dir / "protocol.yaml"
            if not yaml_config.exists():
                continue

            protocol_name = protocol_dir.name
            self._protocols[protocol_name] = ProtocolInfo(
                name=protocol_name,
                config_path=str(yaml_config),
                log_path="",
                log_exists=False,
                log_size=0,
                config_valid=True,
            )

        return list(self._protocols.values())

    def get_protocol_info(self, name: str) -> Optional[ProtocolInfo]:
        """
        获取协议基础信息

        Args:
            name: 协议名称

        Returns:
            协议信息，不存在时返回 None
        """
        return self._protocols.get(name)

    def get_protocol_detail(self, name: str) -> Optional[ProtocolDetail]:
        """
        获取协议详细信息（包含统计数据）

        加载协议配置文件，提取 cmd/enum/type 数量和命令列表。

        Args:
            name: 协议名称

        Returns:
            协议详细信息，失败时返回 None
        """
        info = self._protocols.get(name)
        if not info:
            return None

        cmd_count = 0
        enum_count = 0
        type_count = 0
        commands: List[Tuple[str, str]] = []

        try:
            config = self._load_config(info.config_path)
            if config:
                cmd_count = len(config.cmds) if config.cmds else 0
                enum_count = len(config.enums) if config.enums else 0
                type_count = len(config.types) if config.types else 0

                if config.cmds:
                    for cmd_id in config.cmds.keys():
                        commands.append((str(cmd_id), str(cmd_id)))
        except Exception as e:
            logger.warning(f"加载配置统计失败: {e}")

        return ProtocolDetail(
            name=name,
            config_path=info.config_path,
            config_valid=info.config_valid,
            log_path=info.log_path,
            log_exists=info.log_exists,
            log_size=info.log_size,
            cmd_count=cmd_count,
            enum_count=enum_count,
            type_count=type_count,
            commands=commands,
        )

    def validate_protocol(self, name: str) -> ValidationResult:
        """
        验证协议配置

        Args:
            name: 协议名称

        Returns:
            验证结果
        """
        info = self._protocols.get(name)
        if not info:
            return ValidationResult(
                is_valid=False,
                errors=[f"协议 {name} 不存在"],
            )

        try:
            config = self._load_config(info.config_path)
            if config:
                # 使用 YamlConfigLoader 内置验证
                info.config_valid = True
                return ValidationResult(is_valid=True)
            else:
                info.config_valid = False
                return ValidationResult(
                    is_valid=False,
                    errors=[f"协议 {name} 配置加载失败"],
                )
        except Exception as e:
            info.config_valid = False
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
            )

    def validate_protocol_detailed(self, name: str) -> ValidationResult:
        """
        使用 ConfigValidator 进行详细验证

        Args:
            name: 协议名称

        Returns:
            包含详细 errors/warnings 的验证结果
        """
        info = self._protocols.get(name)
        if not info:
            return ValidationResult(
                is_valid=False,
                errors=[f"协议 {name} 不存在"],
            )

        try:
            # 确保 src 目录在路径中
            self._ensure_src_path()

            from validate_configs import ConfigValidator
            validator = ConfigValidator()
            is_valid = validator.validate_protocol_config(Path(info.config_path))

            info.config_valid = is_valid

            return ValidationResult(
                is_valid=is_valid,
                errors=list(validator.errors),
                warnings=list(validator.warnings),
            )
        except Exception as e:
            logger.warning(f"详细验证失败: {e}")
            return ValidationResult(
                is_valid=True,
                warnings=[str(e)],
            )

    def set_log_path(self, name: str, log_path: str) -> Optional[ProtocolInfo]:
        """
        设置协议的日志文件路径

        Args:
            name: 协议名称
            log_path: 日志文件路径

        Returns:
            更新后的协议信息，协议不存在时返回 None
        """
        info = self._protocols.get(name)
        if not info:
            return None

        log_file = Path(log_path)
        info.log_path = log_path
        info.log_exists = log_file.exists()
        info.log_size = log_file.stat().st_size if info.log_exists else 0

        return info

    def update_protocol_status(
        self,
        name: str,
        config_valid: Optional[bool] = None,
        log_exists: Optional[bool] = None,
        log_size: Optional[int] = None,
    ) -> None:
        """
        更新协议状态

        Args:
            name: 协议名称
            config_valid: 配置是否有效
            log_exists: 日志是否存在
            log_size: 日志大小
        """
        info = self._protocols.get(name)
        if not info:
            return

        if config_valid is not None:
            info.config_valid = config_valid
        if log_exists is not None:
            info.log_exists = log_exists
        if log_size is not None:
            info.log_size = log_size

    def can_parse(self, name: str) -> Tuple[bool, str]:
        """
        检查协议是否满足解析条件

        Args:
            name: 协议名称

        Returns:
            (是否可解析, 原因说明)
        """
        info = self._protocols.get(name)
        if not info:
            return False, "请先选择要解析的协议"

        if not info.log_exists or info.log_size == 0:
            return False, (
                f"日志文件不存在或为空:\n{info.log_path}\n\n"
                "请先将日志内容拷贝到该文件。"
            )

        return True, ""

    def _load_config(self, config_path: str) -> Any:
        """
        加载协议配置（内部方法）

        Args:
            config_path: 配置文件路径

        Returns:
            ProtocolConfig 对象
        """
        from src.yaml_config import YamlConfigLoader
        loader = YamlConfigLoader()
        return loader.load_protocol_config(config_path)

    def _ensure_src_path(self) -> None:
        """确保 src 目录在 sys.path 中"""
        from gui.config import PROJECT_ROOT
        src_path = str(PROJECT_ROOT / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
