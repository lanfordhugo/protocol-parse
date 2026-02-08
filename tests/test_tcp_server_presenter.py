"""
文件名称: test_tcp_server_presenter.py
内容摘要: TcpServerPresenter 单元测试（使用 Mock View 和 Mock Server）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock

from tcp_log.models.tcp_server_model import TcpServerModel, EntryData, StatsData
from tcp_log.presenters.tcp_server_presenter import TcpServerPresenter


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


@dataclass
class MockClientInfo:
    """模拟 ClientInfo 对象"""
    address: str = "127.0.0.1"
    port: int = 12345


def _create_mock_view():
    """创建 Mock View"""
    view = MagicMock()
    view.get_server_config.return_value = {"host": "0.0.0.0", "port": 9999}
    view.get_filter_cmd.return_value = None
    view.is_success_only.return_value = False
    view.is_auto_scroll.return_value = True
    view.is_save_log_enabled.return_value = False
    view.is_save_result_enabled.return_value = False
    return view


def _create_mock_server():
    """创建 Mock Server"""
    server = MagicMock()
    return server


@pytest.mark.unit
class TestTcpServerPresenterInit:
    """TcpServerPresenter 初始化测试"""

    def test_initialize_loads_protocols(self, configs_dir: Path, tmp_path: Path):
        """测试初始化加载协议列表"""
        view = _create_mock_view()
        model = TcpServerModel(configs_dir, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.initialize()

        view.set_protocol_list.assert_called_once()
        names = view.set_protocol_list.call_args[0][0]
        assert len(names) > 0

    def test_initialize_empty_dir(self, tmp_path: Path):
        """测试空目录初始化"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path / "empty", tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.initialize()

        view.set_protocol_list.assert_called_once_with([])


@pytest.mark.unit
class TestTcpServerPresenterControl:
    """TcpServerPresenter 服务器控制测试"""

    def test_on_start_no_protocol(self, tmp_path: Path):
        """测试无协议时启动"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_start_clicked()

        view.show_warning.assert_called_once()
        server.start.assert_not_called()

    def test_on_stop(self, tmp_path: Path):
        """测试停止服务"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_stop_clicked()

        server.stop.assert_called_once()

    def test_on_protocol_changed(self, tmp_path: Path):
        """测试协议切换（未知协议）"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_protocol_changed("unknown")

        view.emit_status_changed.assert_called_once()


@pytest.mark.unit
class TestTcpServerPresenterServerEvents:
    """TcpServerPresenter 服务器事件测试"""

    def test_on_server_state_changed(self, tmp_path: Path):
        """测试服务器状态变化"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_server_state_changed("监听中")

        view.update_server_state.assert_called_once_with("监听中")

    def test_on_client_connected(self, tmp_path: Path):
        """测试客户端连接"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        client = MockClientInfo()
        presenter.on_client_connected(client)

        view.emit_status_changed.assert_called_once()
        assert "127.0.0.1" in view.emit_status_changed.call_args[0][0]

    def test_on_client_disconnected(self, tmp_path: Path):
        """测试客户端断开"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_client_disconnected()

        view.emit_status_changed.assert_called_once()
        assert "断开" in view.emit_status_changed.call_args[0][0]

    def test_on_log_message(self, tmp_path: Path):
        """测试日志消息"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_log_message("测试日志")

        view.emit_status_changed.assert_called_once_with("测试日志")

    def test_on_error_message(self, tmp_path: Path):
        """测试错误消息"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_error_message("连接失败")

        msg = view.emit_status_changed.call_args[0][0]
        assert "错误" in msg
        assert "连接失败" in msg


@pytest.mark.unit
class TestTcpServerPresenterEntry:
    """TcpServerPresenter 条目处理测试"""

    def test_on_entry_received_basic(self, tmp_path: Path):
        """测试接收条目基本流程"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        entry = MockLogEntry()
        presenter.on_entry_received(entry)

        # 应该更新缓存标签和统计
        view.update_cache_label.assert_called()
        view.update_stats_summary.assert_called()
        # 应该添加过滤选项
        view.add_filter_option.assert_called_with("cmd1")
        # 应该添加结果行（默认无过滤）
        view.add_result_row.assert_called_once()

    def test_on_entry_received_filtered_out(self, tmp_path: Path):
        """测试条目被过滤掉"""
        view = _create_mock_view()
        view.get_filter_cmd.return_value = 99  # 过滤只看 cmd99
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        entry = MockLogEntry(cmd_id=1)  # cmd1 不匹配过滤
        presenter.on_entry_received(entry)

        # 不应该添加结果行
        view.add_result_row.assert_not_called()
        # 但统计仍然更新
        view.update_stats_summary.assert_called()

    def test_on_entry_received_with_save_log(self, tmp_path: Path):
        """测试启用日志保存"""
        view = _create_mock_view()
        view.is_save_log_enabled.return_value = True
        save_dir = tmp_path / "output"
        model = TcpServerModel(tmp_path, save_dir)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        entry = MockLogEntry()
        presenter.on_entry_received(entry)

        # 应该保存了日志文件
        assert save_dir.exists()
        log_files = list(save_dir.glob("tcp_log_*.log"))
        assert len(log_files) == 1


@pytest.mark.unit
class TestTcpServerPresenterActions:
    """TcpServerPresenter 用户操作测试"""

    def test_on_clear_results(self, tmp_path: Path):
        """测试清空结果"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        # 先添加条目
        model.parse_entry(MockLogEntry())

        presenter.on_clear_results()

        assert model.cache_count == 0
        view.clear_result_table.assert_called_once()
        view.reset_filter.assert_called_once()

    def test_on_reset_stats(self, tmp_path: Path):
        """测试重置统计"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        model.parse_entry(MockLogEntry())
        presenter.on_reset_stats()

        stats = model.get_stats()
        assert stats.entry_count == 0
        server.reset_stats.assert_called_once()
        view.update_stats_summary.assert_called()

    def test_on_toggle_stats_detail_show(self, tmp_path: Path):
        """测试展开统计详情"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        model.parse_entry(MockLogEntry(cmd_id=1))
        model.parse_entry(MockLogEntry(cmd_id=2))

        presenter.on_toggle_stats_detail(show=True)

        view.update_stats_detail.assert_called_once()
        items = view.update_stats_detail.call_args[0][0]
        assert len(items) == 2

    def test_on_toggle_stats_detail_hide(self, tmp_path: Path):
        """测试收起统计详情"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_toggle_stats_detail(show=False)

        # 隐藏时不应该更新统计详情
        view.update_stats_detail.assert_not_called()

    def test_on_selection_changed_valid(self, tmp_path: Path):
        """测试有效行选中"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        model.parse_entry(MockLogEntry())

        presenter.on_selection_changed(0)

        view.show_entry_detail.assert_called_once()
        detail = view.show_entry_detail.call_args[0][0]
        assert "数据项" in detail

    def test_on_selection_changed_invalid_index(self, tmp_path: Path):
        """测试无效索引选中"""
        view = _create_mock_view()
        model = TcpServerModel(tmp_path, tmp_path)
        server = _create_mock_server()
        presenter = TcpServerPresenter(view=view, model=model, server=server)

        presenter.on_selection_changed(999)

        view.show_entry_detail.assert_not_called()
