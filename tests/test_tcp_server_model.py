"""
文件名称: test_tcp_server_model.py
内容摘要: TcpServerModel 单元测试
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import json
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from tcp_log.models.tcp_server_model import (
    TcpServerModel, EntryData, StatsData, CmdStatsItem,
)


@dataclass
class MockLogEntry:
    """模拟 LogEntry 对象"""
    timestamp: str = "2025-02-08 12:00:00"
    direction: str = "RX"
    cmd_id: int = 1
    byte_count: int = 10
    terminal_id: Optional[int] = None
    source_info: str = "test"
    hex_data: str = "AA F5 00 01 00 01 01 01 01 02 03 04"
    raw_text: str = "[2025-02-08 12:00:00] RX cmd1 AA F5 00 01\n"


@pytest.mark.unit
class TestTcpServerModel:
    """TcpServerModel 单元测试"""

    def test_scan_protocols(self, configs_dir: Path, tmp_path: Path):
        """测试扫描协议"""
        model = TcpServerModel(configs_dir, tmp_path)
        names = model.scan_protocols()
        assert len(names) > 0
        assert names == sorted(names)  # 应该已排序

    def test_scan_protocols_empty_dir(self, tmp_path: Path):
        """测试扫描空目录"""
        model = TcpServerModel(tmp_path / "empty", tmp_path)
        names = model.scan_protocols()
        assert names == []

    def test_has_protocol_initially_false(self, tmp_path: Path):
        """测试初始无协议"""
        model = TcpServerModel(tmp_path, tmp_path)
        assert model.has_protocol is False

    def test_load_protocol_nonexistent(self, tmp_path: Path):
        """测试加载不存在的协议"""
        model = TcpServerModel(tmp_path, tmp_path)
        success, msg = model.load_protocol("nonexistent")
        assert success is False
        assert "未知协议" in msg

    def test_parse_entry_without_protocol(self, tmp_path: Path):
        """测试无协议时解析条目"""
        model = TcpServerModel(tmp_path, tmp_path)
        entry = MockLogEntry()
        result = model.parse_entry(entry)

        assert isinstance(result, EntryData)
        assert result.success is False
        assert result.entry is entry

    def test_parse_entry_updates_stats(self, tmp_path: Path):
        """测试解析条目更新统计"""
        model = TcpServerModel(tmp_path, tmp_path)

        entry1 = MockLogEntry(cmd_id=1)
        entry2 = MockLogEntry(cmd_id=2)
        entry3 = MockLogEntry(cmd_id=1)

        model.parse_entry(entry1)
        model.parse_entry(entry2)
        model.parse_entry(entry3)

        stats = model.get_stats()
        assert stats.entry_count == 3
        assert stats.cmd_count == 2  # cmd1 和 cmd2

    def test_get_stats_initial(self, tmp_path: Path):
        """测试初始统计"""
        model = TcpServerModel(tmp_path, tmp_path)
        stats = model.get_stats()
        assert stats.entry_count == 0
        assert stats.success_count == 0
        assert stats.fail_count == 0
        assert stats.cmd_count == 0

    def test_reset_stats(self, tmp_path: Path):
        """测试重置统计"""
        model = TcpServerModel(tmp_path, tmp_path)
        model.parse_entry(MockLogEntry())
        model.parse_entry(MockLogEntry())

        model.reset_stats()
        stats = model.get_stats()
        assert stats.entry_count == 0
        assert stats.success_count == 0

    def test_trim_cache_not_needed(self, tmp_path: Path):
        """测试缓存未满时不清理"""
        model = TcpServerModel(tmp_path, tmp_path, max_cache=100)
        model.parse_entry(MockLogEntry())
        removed = model.trim_cache_if_needed()
        assert removed == 0

    def test_trim_cache_when_full(self, tmp_path: Path):
        """测试缓存满时清理"""
        model = TcpServerModel(tmp_path, tmp_path, max_cache=5)
        for i in range(6):
            model.parse_entry(MockLogEntry(cmd_id=i))

        removed = model.trim_cache_if_needed()
        assert removed > 0
        assert model.cache_count <= model.max_cache

    def test_clear_entries(self, tmp_path: Path):
        """测试清空条目"""
        model = TcpServerModel(tmp_path, tmp_path)
        model.parse_entry(MockLogEntry())
        model.parse_entry(MockLogEntry())

        model.clear_entries()
        assert model.cache_count == 0

    def test_get_cmd_stats_detail(self, tmp_path: Path):
        """测试获取命令统计详情"""
        model = TcpServerModel(tmp_path, tmp_path)
        model.parse_entry(MockLogEntry(cmd_id=1))
        model.parse_entry(MockLogEntry(cmd_id=1))
        model.parse_entry(MockLogEntry(cmd_id=2))

        details = model.get_cmd_stats_detail()
        assert len(details) == 2
        assert all(isinstance(d, CmdStatsItem) for d in details)
        # 按接收次数降序
        assert details[0].total_count >= details[1].total_count

    def test_save_log_entry(self, tmp_path: Path):
        """测试保存日志条目"""
        save_dir = tmp_path / "output"
        model = TcpServerModel(tmp_path, save_dir)
        entry = MockLogEntry()

        error = model.save_log_entry(entry)
        assert error is None
        assert save_dir.exists()

        # 检查文件是否存在
        log_files = list(save_dir.glob("tcp_log_*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert entry.raw_text.strip() in content

    def test_save_parsed_result(self, tmp_path: Path):
        """测试保存解析结果"""
        save_dir = tmp_path / "output"
        model = TcpServerModel(tmp_path, save_dir)
        entry = MockLogEntry()

        error = model.save_parsed_result(entry, {"field1": "value1"}, True)
        assert error is None

        json_files = list(save_dir.glob("tcp_parsed_*.json"))
        assert len(json_files) == 1
        content = json_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip())
        assert record["cmd_id"] == 1
        assert record["success"] is True
        assert record["parsed"]["field1"] == "value1"


@pytest.mark.unit
class TestTcpServerModelStatic:
    """TcpServerModel 静态方法测试"""

    def test_generate_summary_none(self):
        """测试空解析结果"""
        assert TcpServerModel.generate_summary(None) == ""

    def test_generate_summary_error(self):
        """测试错误解析结果"""
        result = TcpServerModel.generate_summary({"error": "解析失败"})
        assert "[错误]" in result

    def test_generate_summary_normal(self):
        """测试正常解析结果"""
        result = TcpServerModel.generate_summary({
            "field1": 100,
            "field2": {"value": 1, "name": "枚举值"},
            "field3": [1, 2, 3],
        })
        assert "field1=100" in result
        assert "field2=枚举值" in result
        assert "field3=[3项]" in result

    def test_format_detail(self):
        """测试格式化详情"""
        entry = MockLogEntry()
        text = TcpServerModel.format_detail(entry, {"f1": 42}, True)
        assert "数据项" in text
        assert "cmd1" in text
        assert "f1: 42" in text
        assert entry.hex_data in text

    def test_should_show_entry_all(self):
        """测试全部显示"""
        assert TcpServerModel.should_show_entry(1, True, None, False) is True
        assert TcpServerModel.should_show_entry(1, False, None, False) is True

    def test_should_show_entry_success_only(self):
        """测试仅成功过滤"""
        assert TcpServerModel.should_show_entry(1, True, None, True) is True
        assert TcpServerModel.should_show_entry(1, False, None, True) is False

    def test_should_show_entry_cmd_filter(self):
        """测试命令过滤"""
        assert TcpServerModel.should_show_entry(1, True, 1, False) is True
        assert TcpServerModel.should_show_entry(2, True, 1, False) is False


@pytest.mark.unit
class TestStatsData:
    """StatsData 数据类测试"""

    def test_success_rate_zero(self):
        """测试零条目时的成功率"""
        stats = StatsData()
        assert stats.success_rate == 0.0

    def test_success_rate_normal(self):
        """测试正常成功率"""
        stats = StatsData(entry_count=10, success_count=8, fail_count=2)
        assert stats.success_rate == 80.0


@pytest.mark.unit
class TestCmdStatsItem:
    """CmdStatsItem 数据类测试"""

    def test_success_rate(self):
        """测试命令成功率"""
        item = CmdStatsItem(cmd_id=1, cmd_name="cmd1", total_count=10, success_count=7)
        assert item.success_rate == 70.0

    def test_success_rate_zero(self):
        """测试零次数时的成功率"""
        item = CmdStatsItem(cmd_id=1, cmd_name="cmd1", total_count=0, success_count=0)
        assert item.success_rate == 0.0
