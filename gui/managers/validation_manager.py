"""
文件名称: validation_manager.py
内容摘要: 配置验证管理器 - 负责协议配置的验证
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

import sys
from pathlib import Path
from typing import List, Optional

from gui.models import ValidationResult, ValidationStatus


class ValidationManager:
    """配置验证管理器

    负责协议配置的验证，包括语法检查、语义检查和一致性检查。
    完全独立于 GUI 框架，可在单元测试中直接使用。
    """

    def __init__(self):
        """初始化验证管理器"""
        pass

    def validate_protocol_config(
        self,
        protocol_name: str,
        config_path: Path
    ) -> ValidationResult:
        """验证协议配置

        Args:
            protocol_name: 协议名称
            config_path: 配置文件路径

        Returns:
            验证结果
        """
        from validate_configs import ConfigValidator

        try:
            validator = ConfigValidator()
            is_valid = validator.validate_protocol_config(Path(config_path))

            if is_valid:
                # 验证通过
                if validator.warnings:
                    # 有警告
                    return ValidationResult.create_warning(
                        protocol_name=protocol_name,
                        config_path=Path(config_path),
                        warnings=validator.warnings,
                    )
                else:
                    # 完全通过
                    return ValidationResult.create_valid(
                        protocol_name=protocol_name,
                        config_path=Path(config_path),
                    )
            else:
                # 验证失败
                return ValidationResult.create_invalid(
                    protocol_name=protocol_name,
                    config_path=Path(config_path),
                    errors=validator.errors,
                    warnings=validator.warnings,
                )

        except Exception as e:
            # 验证过程出错
            return ValidationResult.create_error(
                protocol_name=protocol_name,
                config_path=Path(config_path),
                error_message=str(e),
            )

    def validate_all_protocols(
        self,
        configs_dir: Path
    ) -> List[ValidationResult]:
        """验证所有协议配置

        Args:
            configs_dir: 配置目录

        Returns:
            所有协议的验证结果列表
        """
        results = []

        if not configs_dir.exists():
            return results

        for protocol_dir in sorted(configs_dir.iterdir()):
            if not protocol_dir.is_dir():
                continue

            yaml_config = protocol_dir / "protocol.yaml"
            if not yaml_config.exists():
                continue

            protocol_name = protocol_dir.name
            result = self.validate_protocol_config(protocol_name, yaml_config)
            results.append(result)

        return results

    def quick_validate(self, config_path: Path) -> bool:
        """快速验证配置文件（只检查语法）

        Args:
            config_path: 配置文件路径

        Returns:
            是否有效
        """
        try:
            from yaml_config import YamlConfigLoader
            loader = YamlConfigLoader()
            config = loader.load_protocol_config(config_path)
            return config is not None
        except Exception:
            return False

    def get_validation_summary(
        self,
        results: List[ValidationResult]
    ) -> dict:
        """获取验证结果摘要

        Args:
            results: 验证结果列表

        Returns:
            摘要信息字典
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid and not r.has_warnings)
        warnings = sum(1 for r in results if r.is_valid and r.has_warnings)
        invalid = sum(1 for r in results if not r.is_valid)

        return {
            'total': total,
            'valid': valid,
            'warnings': warnings,
            'invalid': invalid,
            'success_rate': (valid + warnings) / total * 100 if total > 0 else 0,
        }

    def batch_validate(
        self,
        protocol_names: List[str],
        configs_dir: Path
    ) -> dict[str, ValidationResult]:
        """批量验证多个协议

        Args:
            protocol_names: 协议名称列表
            configs_dir: 配置目录

        Returns:
            协议名称到验证结果的映射
        """
        results = {}

        for protocol_name in protocol_names:
            config_path = configs_dir / protocol_name / "protocol.yaml"
            if config_path.exists():
                results[protocol_name] = self.validate_protocol_config(
                    protocol_name, config_path
                )

        return results

    def get_common_errors(
        self,
        results: List[ValidationResult]
    ) -> List[tuple[str, int]]:
        """获取常见错误

        统计所有验证结果中出现的错误，按频率排序。

        Args:
            results: 验证结果列表

        Returns:
            (错误消息, 出现次数) 列表，按次数降序排列
        """
        error_counts = {}

        for result in results:
            for error in result.errors:
                error_counts[error] = error_counts.get(error, 0) + 1

        # 按次数降序排列
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

    def get_common_warnings(
        self,
        results: List[ValidationResult]
    ) -> List[tuple[str, int]]:
        """获取常见警告

        统计所有验证结果中出现的警告，按频率排序。

        Args:
            results: 验证结果列表

        Returns:
            (警告消息, 出现次数) 列表，按次数降序排列
        """
        warning_counts = {}

        for result in results:
            for warning in result.warnings:
                warning_counts[warning] = warning_counts.get(warning, 0) + 1

        # 按次数降序排列
        return sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)
