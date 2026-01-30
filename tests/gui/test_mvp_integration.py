"""
文件名称: test_mvp_integration.py
内容摘要: MVP 架构集成测试 - 验证 Model 层和 Manager 层的基本功能
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

import pytest
from pathlib import Path
from datetime import datetime

from gui.models import (
    ProtocolInfo, ProtocolStats,
    ParseResult, ParseFilter, ParseStatus,
    ValidationResult, ValidationStatus
)


class TestProtocolInfo:
    """测试 ProtocolInfo 数据类"""

    def test_create_protocol_info(self):
        """测试创建协议信息"""
        info = ProtocolInfo(
            name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
        )

        assert info.name == "test_protocol"
        assert info.config_path == Path("/configs/test/protocol.yaml")
        assert info.log_path is None
        assert info.log_exists is False
        assert info.log_size == 0
        assert info.config_valid is True

    def test_protocol_info_with_log(self):
        """测试带日志文件的协议信息"""
        info = ProtocolInfo(
            name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            log_path=Path("/logs/test.log"),
            log_exists=True,
            log_size=1024 * 1024,  # 1MB
        )

        assert info.has_log is True
        assert info.log_size_human == "1.0 MB"

    def test_protocol_info_serialization(self):
        """测试协议信息序列化"""
        info = ProtocolInfo(
            name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            log_path=Path("/logs/test.log"),
            log_exists=True,
            log_size=1024,
        )

        # 转换为字典
        data = info.to_dict()
        assert data['name'] == "test_protocol"
        assert data['log_size'] == 1024

        # 从字典恢复
        restored = ProtocolInfo.from_dict(data)
        assert restored.name == info.name
        assert restored.log_size == info.log_size


class TestParseResult:
    """测试 ParseResult 数据类"""

    def test_create_parse_result(self):
        """测试创建解析结果"""
        result = ParseResult(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            log_path=Path("/logs/test.log"),
        )

        assert result.protocol_name == "test_protocol"
        assert result.status == ParseStatus.PENDING
        assert result.progress == 0
        assert result.is_running is False
        assert result.is_completed is False

    def test_parse_result_progress(self):
        """测试解析进度"""
        result = ParseResult(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            log_path=Path("/logs/test.log"),
            status=ParseStatus.RUNNING,
            total_lines=1000,
            parsed_lines=500,
        )

        assert result.progress == 50
        assert result.is_running is True
        assert result.success_rate == 50.0

    def test_parse_result_completed(self):
        """测试解析完成"""
        result = ParseResult(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            log_path=Path("/logs/test.log"),
            status=ParseStatus.SUCCESS,
            success=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        assert result.is_completed is True
        assert result.duration_seconds is not None


class TestParseFilter:
    """测试 ParseFilter 数据类"""

    def test_create_empty_filter(self):
        """测试创建空过滤器"""
        filter_settings = ParseFilter()

        assert filter_settings.start_time is None
        assert filter_settings.end_time is None
        assert filter_settings.include_cmds is None
        assert filter_settings.exclude_cmds is None

    def test_filter_with_commands(self):
        """测试带命令过滤的过滤器"""
        filter_settings = ParseFilter(
            include_cmds=["cmd1", "cmd2"],
            exclude_cmds=["cmd3"],
        )

        assert len(filter_settings.include_cmds) == 2
        assert len(filter_settings.exclude_cmds) == 1

    def test_filter_serialization(self):
        """测试过滤器序列化"""
        filter_settings = ParseFilter(
            skip_invalid=True,
            strict_mode=False,
        )

        data = filter_settings.to_dict()
        assert data['skip_invalid'] is True
        assert data['strict_mode'] is False

        restored = ParseFilter.from_dict(data)
        assert restored.skip_invalid == filter_settings.skip_invalid


class TestValidationResult:
    """测试 ValidationResult 数据类"""

    def test_create_valid_result(self):
        """测试创建验证通过的结果"""
        result = ValidationResult.create_valid(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
        )

        assert result.is_valid is True
        assert result.has_warnings is False
        assert result.status == ValidationStatus.VALID
        assert "✅" in result.summary

    def test_create_warning_result(self):
        """测试创建有警告的验证结果"""
        warnings = ["警告1", "警告2"]
        result = ValidationResult.create_warning(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            warnings=warnings,
        )

        assert result.is_valid is True
        assert result.has_warnings is True
        assert result.warning_count == 2
        assert "⚠️" in result.summary

    def test_create_invalid_result(self):
        """测试创建验证失败的结果"""
        errors = ["错误1", "错误2", "错误3"]
        result = ValidationResult.create_invalid(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
            errors=errors,
        )

        assert result.is_valid is False
        assert result.error_count == 3
        assert "❌" in result.summary

    def test_validation_result_serialization(self):
        """测试验证结果序列化"""
        result = ValidationResult.create_valid(
            protocol_name="test_protocol",
            config_path=Path("/configs/test/protocol.yaml"),
        )

        data = result.to_dict()
        assert data['protocol_name'] == "test_protocol"
        assert data['is_valid'] is True

        restored = ValidationResult.from_dict(data)
        assert restored.protocol_name == result.protocol_name
        assert restored.is_valid == result.is_valid


class TestProtocolStats:
    """测试 ProtocolStats 数据类"""

    def test_create_stats(self):
        """测试创建统计信息"""
        stats = ProtocolStats(
            cmd_count=10,
            enum_count=5,
            type_count=3,
            commands=[("cmd1", "Command 1"), ("cmd2", "Command 2")],
        )

        assert stats.cmd_count == 10
        assert stats.enum_count == 5
        assert stats.type_count == 3
        assert len(stats.commands) == 2
