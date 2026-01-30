"""
文件名称: test_parse_manager.py
内容摘要: ParseManager 单元测试
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-30
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from gui.managers.parse_manager import ParseManager
from gui.models import ParseResult, ParseFilter, ParseStatus


class TestParseManagerInit:
    """测试 ParseManager 初始化"""

    def test_init_with_valid_dir(self, tmp_path):
        """测试使用有效目录初始化"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        manager = ParseManager(output_dir)

        assert manager._output_dir == output_dir



class TestValidateParseConfig:
    """测试解析配置验证"""

    def test_validate_valid_config(self, tmp_path):
        """测试验证有效配置"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        config_file = tmp_path / "configs" / "v8" / "protocol.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("meta: {protocol: v8}")

        log_file = tmp_path / "v8.log"
        log_file.write_text("test")

        manager = ParseManager(output_dir)

        is_valid, message = manager.validate_parse_config("v8", config_file, log_file)

        assert is_valid is True

    def test_validate_missing_log_path(self, tmp_path):
        """测试缺少日志路径"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        config_file = tmp_path / "configs" / "v8" / "protocol.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("meta: {protocol: v8}")

        log_file = tmp_path / "nonexistent.log"

        manager = ParseManager(output_dir)

        is_valid, message = manager.validate_parse_config("v8", config_file, log_file)

        assert is_valid is False


class TestEstimateParseTime:
    """测试估算解析时间"""

    def test_estimate_time_existing_file(self, tmp_path):
        """测试估算已存在文件的解析时间"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        # 创建测试日志文件（100 行）
        log_file = tmp_path / "v8.log"
        log_file.write_text("\n".join([f"line {i}" for i in range(100)]))

        manager = ParseManager(output_dir)
        time_estimate = manager.estimate_parse_time(log_file)

        assert time_estimate is not None
        assert time_estimate > 0


class TestGetOutputDir:
    """测试获取输出目录"""

    def test_get_output_dir(self, tmp_path):
        """测试获取输出目录路径"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        manager = ParseManager(output_dir)

        assert manager.get_output_dir() == output_dir


class TestEnsureOutputDir:
    """测试确保输出目录存在"""

    def test_ensure_output_dir_existing(self, tmp_path):
        """测试目录已存在"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        manager = ParseManager(output_dir)
        result = manager.ensure_output_dir()

        assert result == output_dir
        assert result.exists()

    def test_ensure_output_dir_nonexistent(self, tmp_path):
        """测试目录不存在时创建"""
        output_dir = tmp_path / "new_parsed_log"

        manager = ParseManager(output_dir)
        result = manager.ensure_output_dir()

        assert result == output_dir
        assert result.exists()


class TestCountLogLines:
    """测试统计日志行数"""

    def test_count_lines_empty_file(self, tmp_path):
        """测试空文件"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        manager = ParseManager(output_dir)
        line_count = manager._count_log_lines(log_file)

        assert line_count == 0

    def test_count_lines_multiple_lines(self, tmp_path):
        """测试多行文件"""
        output_dir = tmp_path / "parsed_log"
        output_dir.mkdir()

        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join([f"line {i}" for i in range(10)]))

        manager = ParseManager(output_dir)
        line_count = manager._count_log_lines(log_file)

        assert line_count == 10
