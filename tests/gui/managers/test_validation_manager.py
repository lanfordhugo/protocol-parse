"""
文件名称: test_validation_manager.py
内容摘要: ValidationManager 单元测试
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-30
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from gui.managers.validation_manager import ValidationManager
from gui.models import ValidationResult, ValidationStatus


class TestValidationManagerInit:
    """测试 ValidationManager 初始化"""

    def test_init(self):
        """测试初始化"""
        manager = ValidationManager()

        assert manager is not None


class TestGetValidationSummary:
    """测试获取验证摘要"""

    def test_get_summary_all_valid(self, tmp_path):
        """测试全部有效的摘要"""
        manager = ValidationManager()

        results = [
            ValidationResult.create_valid("v8", Path("configs/v8/protocol.yaml")),
            ValidationResult.create_valid("sinexcel", Path("configs/sinexcel/protocol.yaml")),
        ]

        summary = manager.get_validation_summary(results)

        assert summary['total'] == 2
        assert summary['valid'] == 2
        assert summary['warnings'] == 0
        assert summary['invalid'] == 0
        assert summary['success_rate'] == 100.0

    def test_get_summary_mixed_results(self, tmp_path):
        """测试混合结果的摘要"""
        manager = ValidationManager()

        results = [
            ValidationResult.create_valid("v8", Path("configs/v8/protocol.yaml")),
            ValidationResult.create_warning(
                "sinexcel",
                Path("configs/sinexcel/protocol.yaml"),
                warnings=["建议添加描述"]
            ),
            ValidationResult.create_invalid(
                "yunwei",
                Path("configs/yunwei/protocol.yaml"),
                errors=["语法错误"]
            ),
        ]

        summary = manager.get_validation_summary(results)

        assert summary['total'] == 3
        assert summary['valid'] == 1
        assert summary['warnings'] == 1
        assert summary['invalid'] == 1
        assert summary['success_rate'] == pytest.approx(66.67, rel=0.1)

    def test_get_summary_empty_results(self, tmp_path):
        """测试空结果的摘要"""
        manager = ValidationManager()

        summary = manager.get_validation_summary([])

        assert summary['total'] == 0
        assert summary['valid'] == 0
        assert summary['warnings'] == 0
        assert summary['invalid'] == 0
        assert summary['success_rate'] == 0


class TestGetCommonErrors:
    """测试获取常见错误"""

    def test_get_common_errors(self, tmp_path):
        """测试获取常见错误统计"""
        manager = ValidationManager()

        results = [
            ValidationResult.create_invalid(
                "v8",
                Path("configs/v8/protocol.yaml"),
                errors=["缺少 meta 字段", "版本号缺失"]
            ),
            ValidationResult.create_invalid(
                "sinexcel",
                Path("configs/sinexcel/protocol.yaml"),
                errors=["缺少 meta 字段", "枚举定义错误"]
            ),
            ValidationResult.create_invalid(
                "yunwei",
                Path("configs/yunwei/protocol.yaml"),
                errors=["缺少 meta 字段"]
            ),
        ]

        common_errors = manager.get_common_errors(results)

        # "缺少 meta 字段" 出现了 3 次，应该排在第一位
        assert len(common_errors) == 3
        assert common_errors[0] == ("缺少 meta 字段", 3)
        assert common_errors[1][1] == 1  # 其他错误只出现 1 次

    def test_get_common_errors_no_errors(self, tmp_path):
        """测试没有错误的情况"""
        manager = ValidationManager()

        results = [
            ValidationResult.create_valid("v8", Path("configs/v8/protocol.yaml")),
        ]

        common_errors = manager.get_common_errors(results)

        assert common_errors == []


class TestGetCommonWarnings:
    """测试获取常见警告"""

    def test_get_common_warnings(self, tmp_path):
        """测试获取常见警告统计"""
        manager = ValidationManager()

        results = [
            ValidationResult.create_warning(
                "v8",
                Path("configs/v8/protocol.yaml"),
                warnings=["建议添加描述", "建议添加版本"]
            ),
            ValidationResult.create_warning(
                "sinexcel",
                Path("configs/sinexcel/protocol.yaml"),
                warnings=["建议添加描述", "建议添加示例"]
            ),
        ]

        common_warnings = manager.get_common_warnings(results)

        # "建议添加描述" 出现了 2 次
        assert len(common_warnings) == 3
        assert common_warnings[0] == ("建议添加描述", 2)
        assert common_warnings[1][1] == 1

    def test_get_common_warnings_no_warnings(self, tmp_path):
        """测试没有警告的情况"""
        manager = ValidationManager()

        results = [
            ValidationResult.create_valid("v8", Path("configs/v8/protocol.yaml")),
        ]

        common_warnings = manager.get_common_warnings(results)

        assert common_warnings == []
