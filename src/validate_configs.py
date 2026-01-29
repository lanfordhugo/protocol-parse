#!/usr/bin/env python3
"""
配置校验器
用于验证YAML协议配置的完整性和正确性
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from yaml_config import ProtocolConfig, yaml_loader

# 当前文件已在src目录中，无需添加路径



class ConfigValidator:
    """配置校验器"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_protocol_config(self, config_path: Path) -> bool:
        """验证单个协议配置"""
        self.errors.clear()
        self.warnings.clear()

        try:
            config = yaml_loader.load_protocol_config(config_path)

            # 基础验证
            basic_errors = yaml_loader.validate_config(config)
            self.errors.extend(basic_errors)

            # 扩展验证
            self._validate_protocol_specific(config)
            self._validate_consistency(config)
            self._validate_completeness(config)

            return len(self.errors) == 0

        except Exception as e:
            self.errors.append(f"Failed to load config: {e}")
            return False

    def _validate_protocol_specific(self, config: ProtocolConfig):
        """协议特定验证"""
        # 验证端序设置
        if config.meta.default_endian not in ["LE", "BE"]:
            self.errors.append(f"Invalid default_endian: {config.meta.default_endian}")

        # 验证命令ID范围
        for cmd_id in config.cmds.keys():
            if not (1 <= cmd_id <= 65535):
                self.warnings.append(f"Command ID {cmd_id} outside typical range [1-65535]")

    def _validate_consistency(self, config: ProtocolConfig):
        """一致性验证"""
        # 验证类型与字段长度的一致性
        for cmd_id, fields in config.cmds.items():
            self._validate_field_type_consistency(fields, config, f"cmd{cmd_id}")

    def _validate_field_type_consistency(self, fields, config: ProtocolConfig, context: str):
        """验证字段类型一致性"""
        from yaml_config import Field, Group

        for field_item in fields:
            if isinstance(field_item, Field):
                if field_item.type in config.types:
                    type_def = config.types[field_item.type]

                    # 检查长度一致性
                    if type_def.bytes and field_item.len != type_def.bytes:
                        self.errors.append(
                            f"{context}: Field '{field_item.name}' length {field_item.len} "
                            f"doesn't match type '{field_item.type}' expected length {type_def.bytes}"
                        )

                    # 检查缩放因子合理性
                    if field_item.scale is not None:
                        if type_def.base not in ["uint", "int"]:
                            self.warnings.append(
                                f"{context}: Scale factor on non-numeric field '{field_item.name}'"
                            )

            elif isinstance(field_item, Group):
                self._validate_field_type_consistency(field_item.fields, config, f"{context}.group")

    def _validate_completeness(self, config: ProtocolConfig):
        """完整性验证"""
        # 检查是否有未使用的类型定义
        used_types = set()
        for fields in config.cmds.values():
            self._collect_used_types(fields, used_types)

        unused_types = set(config.types.keys()) - used_types
        if unused_types:
            self.warnings.append(f"Unused type definitions: {', '.join(unused_types)}")

        # 检查是否有未使用的枚举定义
        used_enums = set()
        for fields in config.cmds.values():
            self._collect_used_enums(fields, used_enums)

        unused_enums = set(config.enums.keys()) - used_enums
        if unused_enums:
            self.warnings.append(f"Unused enum definitions: {', '.join(unused_enums)}")

    def _collect_used_types(self, fields, used_types: set):
        """收集使用的类型"""
        from yaml_config import Field, Group

        for field_item in fields:
            if isinstance(field_item, Field):
                used_types.add(field_item.type)
            elif isinstance(field_item, Group):
                self._collect_used_types(field_item.fields, used_types)

    def _collect_used_enums(self, fields, used_enums: set):
        """收集使用的枚举"""
        from yaml_config import Field, Group

        for field_item in fields:
            if isinstance(field_item, Field):
                if field_item.enum:
                    used_enums.add(field_item.enum)
            elif isinstance(field_item, Group):
                self._collect_used_enums(field_item.fields, used_enums)

    def print_results(self, config_path: Path):
        """打印验证结果"""
        print(f"\n=== Validation Results for {config_path.name} ===")

        if self.errors:
            print(f"\n[ERROR] Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n[WARNING] Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.errors and not self.warnings:
            print("\n[OK] Configuration is valid!")
        elif not self.errors:
            print(f"\n[OK] Configuration is valid (with {len(self.warnings)} warnings)")
        else:
            print(f"\n[ERROR] Configuration has {len(self.errors)} errors")


def validate_all_configs(configs_dir: Path) -> bool:
    """验证所有协议配置"""
    validator = ConfigValidator()
    all_valid = True

    # 查找所有protocol.yaml文件
    yaml_files = list(configs_dir.glob("*/protocol.yaml"))

    if not yaml_files:
        print(f"No protocol.yaml files found in {configs_dir}")
        return False

    print(f"Found {len(yaml_files)} protocol configuration files")

    for config_file in yaml_files:
        print(f"\n{'='*60}")
        print(f"Validating: {config_file}")
        print("=" * 60)

        is_valid = validator.validate_protocol_config(config_file)
        validator.print_results(config_file)

        if not is_valid:
            all_valid = False

    print(f"\n{'='*60}")
    if all_valid:
        print("[OK] All configurations are valid!")
    else:
        print("[ERROR] Some configurations have errors!")
    print("=" * 60)

    return all_valid


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Validate protocol configurations")
    parser.add_argument(
        "config_path", nargs="?", help="Path to protocol.yaml file or configs directory"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all protocol configurations in configs/ directory",
    )

    args = parser.parse_args()

    # 确定配置路径
    if args.all or not args.config_path:
        # 验证所有配置
        configs_dir = Path(__file__).parent.parent / "configs"
        if not configs_dir.exists():
            print(f"Configs directory not found: {configs_dir}")
            sys.exit(1)

        success = validate_all_configs(configs_dir)
        sys.exit(0 if success else 1)

    else:
        # 验证单个配置
        config_path = Path(args.config_path)
        if not config_path.exists():
            print(f"Config file not found: {config_path}")
            sys.exit(1)

        validator = ConfigValidator()
        is_valid = validator.validate_protocol_config(config_path)
        validator.print_results(config_path)

        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
