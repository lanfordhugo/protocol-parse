"""
文件名称: test_protocol_manager.py
内容摘要: ProtocolManager 单元测试
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-30
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from gui.managers.protocol_manager import ProtocolManager
from gui.models import ProtocolInfo, ProtocolStats


class TestProtocolManagerInit:
    """测试 ProtocolManager 初始化"""

    def test_init_with_valid_dir(self, tmp_path):
        """测试使用有效目录初始化"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        manager = ProtocolManager(configs_dir)

        assert manager._configs_dir == configs_dir
        assert manager._protocols == {}

    def test_init_with_path_string(self, tmp_path):
        """测试使用字符串路径初始化"""
        configs_dir = str(tmp_path / "configs")
        Path(configs_dir).mkdir()

        manager = ProtocolManager(configs_dir)

        assert isinstance(manager._configs_dir, Path)
        assert manager._configs_dir == Path(configs_dir)


class TestDiscoverProtocols:
    """测试协议发现功能"""

    def test_discover_empty_directory(self, tmp_path):
        """测试空目录"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        manager = ProtocolManager(configs_dir)
        protocols = manager.discover_protocols()

        assert protocols == []
        assert manager.get_protocol_count() == 0

    def test_discover_single_protocol(self, tmp_path):
        """测试发现单个协议"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)

        yaml_file = v8_dir / "protocol.yaml"
        yaml_file.write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)
        protocols = manager.discover_protocols()

        assert len(protocols) == 1
        assert protocols[0].name == "v8"
        assert protocols[0].config_path == yaml_file
        assert protocols[0].config_valid is True
        assert protocols[0].log_exists is False

    def test_discover_multiple_protocols(self, tmp_path):
        """测试发现多个协议"""
        configs_dir = tmp_path / "configs"

        # 创建 3 个协议
        for name in ["v8", "sinexcel", "yunwei"]:
            protocol_dir = configs_dir / name
            protocol_dir.mkdir(parents=True)
            (protocol_dir / "protocol.yaml").write_text(f"meta: {{protocol: {name}}}")

        manager = ProtocolManager(configs_dir)
        protocols = manager.discover_protocols()

        assert len(protocols) == 3
        protocol_names = [p.name for p in protocols]
        assert "v8" in protocol_names
        assert "sinexcel" in protocol_names
        assert "yunwei" in protocol_names

    def test_discover_ignores_non_yaml_dirs(self, tmp_path):
        """测试忽略没有 protocol.yaml 的目录"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)

        # 不创建 protocol.yaml

        manager = ProtocolManager(configs_dir)
        protocols = manager.discover_protocols()

        assert len(protocols) == 0

    def test_discover_ignores_files(self, tmp_path):
        """测试忽略文件（只处理目录）"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        # 创建一个文件而不是目录
        (configs_dir / "not_a_dir.txt").write_text("test")

        manager = ProtocolManager(configs_dir)
        protocols = manager.discover_protocols()

        assert len(protocols) == 0

    def test_discover_nonexistent_directory(self, tmp_path):
        """测试不存在的目录"""
        configs_dir = tmp_path / "nonexistent"

        manager = ProtocolManager(configs_dir)
        protocols = manager.discover_protocols()

        assert protocols == []

    def test_discover_clears_previous_cache(self, tmp_path):
        """测试重新发现时清除旧缓存"""
        configs_dir = tmp_path / "configs"

        # 第一次发现
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)
        protocols1 = manager.discover_protocols()
        assert len(protocols1) == 1

        # 添加新协议
        sinexcel_dir = configs_dir / "sinexcel"
        sinexcel_dir.mkdir(parents=True)
        (sinexcel_dir / "protocol.yaml").write_text("meta: {protocol: sinexcel}")

        # 重新发现
        protocols2 = manager.discover_protocols()
        assert len(protocols2) == 2


class TestGetProtocolInfo:
    """测试获取协议信息"""

    def test_get_existing_protocol(self, tmp_path):
        """测试获取存在的协议"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        protocol_info = manager.get_protocol_info("v8")

        assert protocol_info is not None
        assert protocol_info.name == "v8"

    def test_get_nonexistent_protocol(self, tmp_path):
        """测试获取不存在的协议"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        manager = ProtocolManager(configs_dir)

        protocol_info = manager.get_protocol_info("nonexistent")

        assert protocol_info is None

    def test_get_protocol_before_discover(self, tmp_path):
        """测试在 discover 之前获取协议"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)

        # 不调用 discover_protocols
        protocol_info = manager.get_protocol_info("v8")

        assert protocol_info is None


class TestGetAllProtocols:
    """测试获取所有协议"""

    def test_get_all_protocols_empty(self, tmp_path):
        """测试空列表"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        manager = ProtocolManager(configs_dir)
        protocols = manager.get_all_protocols()

        assert protocols == []

    def test_get_all_protocols_after_discover(self, tmp_path):
        """测试发现后获取所有协议"""
        configs_dir = tmp_path / "configs"

        for name in ["v8", "sinexcel"]:
            protocol_dir = configs_dir / name
            protocol_dir.mkdir(parents=True)
            (protocol_dir / "protocol.yaml").write_text(f"meta: {{protocol: {name}}}")

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        protocols = manager.get_all_protocols()

        assert len(protocols) == 2


class TestUpdateProtocolLogPath:
    """测试更新协议日志路径"""

    def test_update_log_path_existing_file(self, tmp_path):
        """测试更新为存在的日志文件"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        # 创建日志文件
        log_file = tmp_path / "v8.log"
        log_file.write_text("test log content\n" * 10)

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        manager.update_protocol_log_path("v8", log_file)

        protocol_info = manager.get_protocol_info("v8")
        assert protocol_info.log_path == log_file
        assert protocol_info.log_exists is True
        assert protocol_info.log_size > 0

    def test_update_log_path_nonexistent_file(self, tmp_path):
        """测试更新为不存在的日志文件"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        log_file = tmp_path / "nonexistent.log"
        manager.update_protocol_log_path("v8", log_file)

        protocol_info = manager.get_protocol_info("v8")
        assert protocol_info.log_path == log_file
        assert protocol_info.log_exists is False
        assert protocol_info.log_size == 0


class TestRefreshProtocols:
    """测试刷新协议列表"""

    def test_refresh_protocols(self, tmp_path):
        """测试刷新功能"""
        configs_dir = tmp_path / "configs"

        # 初始状态
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)
        protocols1 = manager.discover_protocols()
        assert len(protocols1) == 1

        # 添加新协议
        sinexcel_dir = configs_dir / "sinexcel"
        sinexcel_dir.mkdir(parents=True)
        (sinexcel_dir / "protocol.yaml").write_text("meta: {protocol: sinexcel}")

        # 刷新
        protocols2 = manager.refresh_protocols()

        assert len(protocols2) == 2


class TestHasProtocol:
    """测试协议存在性检查"""

    def test_has_protocol_existing(self, tmp_path):
        """测试检查存在的协议"""
        configs_dir = tmp_path / "configs"
        v8_dir = configs_dir / "v8"
        v8_dir.mkdir(parents=True)
        (v8_dir / "protocol.yaml").write_text("meta: {protocol: v8}")

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        assert manager.has_protocol("v8") is True

    def test_has_protocol_nonexistent(self, tmp_path):
        """测试检查不存在的协议"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        assert manager.has_protocol("nonexistent") is False


class TestGetProtocolCount:
    """测试获取协议数量"""

    def test_get_protocol_count_empty(self, tmp_path):
        """测试空目录"""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        assert manager.get_protocol_count() == 0

    def test_get_protocol_count_multiple(self, tmp_path):
        """测试多个协议"""
        configs_dir = tmp_path / "configs"

        for name in ["v8", "sinexcel", "yunwei"]:
            protocol_dir = configs_dir / name
            protocol_dir.mkdir(parents=True)
            (protocol_dir / "protocol.yaml").write_text(f"meta: {{protocol: {name}}}")

        manager = ProtocolManager(configs_dir)
        manager.discover_protocols()

        assert manager.get_protocol_count() == 3
