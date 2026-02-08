"""
文件名称: test_protocol_model.py
内容摘要: ProtocolModel 单元测试
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gui.models.protocol_model import ProtocolModel, ProtocolInfo, ProtocolDetail, ValidationResult


@pytest.mark.unit
class TestProtocolModel:
    """ProtocolModel 单元测试"""

    def test_discover_protocols_with_valid_dir(self, configs_dir: Path):
        """测试在有效配置目录中发现协议"""
        model = ProtocolModel(configs_dir)
        protocols = model.discover_protocols()

        # 应该发现多个协议
        assert len(protocols) > 0
        # 每个协议应该有名称
        for p in protocols:
            assert isinstance(p, ProtocolInfo)
            assert p.name
            assert p.config_path

    def test_discover_protocols_with_nonexistent_dir(self, tmp_path: Path):
        """测试在不存在的目录中发现协议"""
        model = ProtocolModel(tmp_path / "nonexistent")
        protocols = model.discover_protocols()
        assert protocols == []

    def test_discover_protocols_with_empty_dir(self, tmp_path: Path):
        """测试在空目录中发现协议"""
        model = ProtocolModel(tmp_path)
        protocols = model.discover_protocols()
        assert protocols == []

    def test_get_protocol_info_existing(self, configs_dir: Path):
        """测试获取已存在协议的信息"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        # 获取 sinexcel 协议信息
        info = model.get_protocol_info("sinexcel")
        assert info is not None
        assert info.name == "sinexcel"
        assert info.config_path
        assert info.config_valid is True

    def test_get_protocol_info_nonexistent(self, configs_dir: Path):
        """测试获取不存在协议的信息"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        info = model.get_protocol_info("nonexistent_protocol")
        assert info is None

    def test_set_log_path(self, configs_dir: Path, tmp_path: Path):
        """测试设置日志路径"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        # 创建一个临时日志文件
        log_file = tmp_path / "test.log"
        log_file.write_text("测试日志内容")

        model.set_log_path("sinexcel", str(log_file))
        info = model.get_protocol_info("sinexcel")

        assert info is not None
        assert info.log_path == str(log_file)
        assert info.log_exists is True
        assert info.log_size > 0

    def test_set_log_path_nonexistent_file(self, configs_dir: Path):
        """测试设置不存在的日志路径"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        model.set_log_path("sinexcel", "/nonexistent/path.log")
        info = model.get_protocol_info("sinexcel")

        assert info is not None
        assert info.log_exists is False
        assert info.log_size == 0

    def test_can_parse_without_log(self, configs_dir: Path):
        """测试没有日志文件时不能解析"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        can, reason = model.can_parse("sinexcel")
        assert can is False
        assert "日志" in reason

    def test_can_parse_with_log(self, configs_dir: Path, tmp_path: Path):
        """测试有日志文件时可以解析"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        log_file = tmp_path / "test.log"
        log_file.write_text("测试日志内容")
        model.set_log_path("sinexcel", str(log_file))

        can, reason = model.can_parse("sinexcel")
        assert can is True

    def test_can_parse_nonexistent_protocol(self, configs_dir: Path):
        """测试不存在的协议"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        can, reason = model.can_parse("nonexistent")
        assert can is False

    def test_get_protocol_detail(self, configs_dir: Path):
        """测试获取协议详细信息"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        detail = model.get_protocol_detail("sinexcel")
        assert detail is not None
        assert isinstance(detail, ProtocolDetail)
        assert detail.name == "sinexcel"
        assert detail.cmd_count >= 0
        assert detail.enum_count >= 0
        assert detail.type_count >= 0

    def test_get_protocol_detail_nonexistent(self, configs_dir: Path):
        """测试获取不存在协议的详细信息"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        detail = model.get_protocol_detail("nonexistent")
        assert detail is None

    def test_validate_protocol(self, configs_dir: Path):
        """测试协议验证"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        result = model.validate_protocol("sinexcel")
        assert isinstance(result, ValidationResult)
        # sinexcel 配置应该是有效的
        assert result.is_valid is True

    def test_validate_protocol_updates_status(self, configs_dir: Path):
        """测试验证后更新协议状态"""
        model = ProtocolModel(configs_dir)
        model.discover_protocols()

        model.validate_protocol("sinexcel")
        info = model.get_protocol_info("sinexcel")
        assert info is not None
        assert info.config_valid is True


@pytest.mark.unit
class TestProtocolInfo:
    """ProtocolInfo 数据类测试"""

    def test_default_values(self):
        """测试默认值"""
        info = ProtocolInfo(name="test", config_path="/path/to/config.yaml")
        assert info.name == "test"
        assert info.config_path == "/path/to/config.yaml"
        assert info.config_valid is True
        assert info.log_path == ""
        assert info.log_exists is False
        assert info.log_size == 0


@pytest.mark.unit
class TestValidationResult:
    """ValidationResult 数据类测试"""

    def test_valid_result(self):
        """测试有效结果"""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self):
        """测试无效结果"""
        result = ValidationResult(
            is_valid=False,
            errors=["错误1", "错误2"],
            warnings=["警告1"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
