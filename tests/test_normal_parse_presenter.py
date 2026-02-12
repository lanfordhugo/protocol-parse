"""
文件名称: test_normal_parse_presenter.py
内容摘要: NormalParsePresenter 单元测试（使用 Mock View）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from gui.models.protocol_model import ProtocolModel, ProtocolInfo, ProtocolDetail, ValidationResult
from gui.models.parse_model import ParseModel
from gui.presenters.normal_parse_presenter import NormalParsePresenter


def _create_mock_view():
    """创建 Mock View 实例"""
    view = MagicMock()
    view.get_selected_protocol_name.return_value = None
    view.get_filter_settings.return_value = {}
    return view


@pytest.mark.unit
class TestNormalParsePresenterInit:
    """NormalParsePresenter 初始化测试"""

    def test_initialize_loads_protocols(self, configs_dir: Path):
        """测试初始化时加载协议列表"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.initialize()

        # 应该调用了 display_protocols 和 select_protocol_by_name
        view.display_protocols.assert_called_once()
        protocols = view.display_protocols.call_args[0][0]
        assert len(protocols) > 0
        view.select_protocol_by_name.assert_called_once_with("sinexcel")

    def test_initialize_empty_dir(self, tmp_path: Path):
        """测试空目录初始化"""
        view = _create_mock_view()
        model = ProtocolModel(tmp_path)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.initialize()

        view.display_protocols.assert_called_once_with([])


@pytest.mark.unit
class TestNormalParsePresenterProtocol:
    """NormalParsePresenter 协议相关测试"""

    def test_on_protocol_selected(self, configs_dir: Path):
        """测试协议选择事件"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        model.discover_protocols()
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_protocol_selected("sinexcel")

        # 应该更新了协议详情和状态
        view.display_protocol_detail.assert_called()
        view.emit_status_changed.assert_called()
        # 状态消息应该包含协议名称
        status_msg = view.emit_status_changed.call_args[0][0]
        assert "sinexcel" in status_msg

    def test_on_protocol_selected_nonexistent(self, configs_dir: Path):
        """测试选择不存在的协议"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        model.discover_protocols()
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_protocol_selected("nonexistent")

        # 不应该更新详情
        view.display_protocol_detail.assert_not_called()


@pytest.mark.unit
class TestNormalParsePresenterParse:
    """NormalParsePresenter 解析相关测试"""

    def test_on_parse_clicked_no_selection(self, configs_dir: Path):
        """测试无选中协议时点击解析"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = None
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_parse_clicked()

        view.show_warning.assert_called_once()

    def test_on_parse_clicked_no_log(self, configs_dir: Path):
        """测试无日志文件时点击解析"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = "sinexcel"
        model = ProtocolModel(configs_dir)
        model.discover_protocols()
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_parse_clicked()

        # 应该提示日志文件不存在
        view.show_warning.assert_called_once()

    def test_on_stop_clicked_no_worker(self, configs_dir: Path):
        """测试无工作线程时点击停止"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        # 不应该抛出异常
        presenter.on_stop_clicked()

    def test_on_validate_clicked_no_selection(self, configs_dir: Path):
        """测试无选中协议时点击验证"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = None
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_validate_clicked()

        view.show_warning.assert_called_once()

    def test_on_validate_clicked_valid_protocol(self, configs_dir: Path):
        """测试验证有效协议"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = "sinexcel"
        model = ProtocolModel(configs_dir)
        model.discover_protocols()
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_validate_clicked()

        # 应该有验证结果日志
        view.log_info.assert_called()
        # 应该更新列表项
        view.update_protocol_list_item.assert_called()


@pytest.mark.unit
class TestNormalParsePresenterLogFile:
    """NormalParsePresenter 日志文件相关测试"""

    def test_on_select_log_no_selection(self, configs_dir: Path):
        """测试无选中协议时选择日志"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = None
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_select_log_clicked()

        view.show_warning.assert_called_once()

    def test_on_select_log_user_cancels(self, configs_dir: Path):
        """测试用户取消选择日志"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = "sinexcel"
        view.show_file_dialog.return_value = None  # 用户取消
        model = ProtocolModel(configs_dir)
        model.discover_protocols()
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_select_log_clicked()

        # 不应该有日志信息
        view.log_info.assert_not_called()

    def test_on_log_file_dropped_no_selection(self, configs_dir: Path):
        """测试无选中协议时拖拽文件"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = None
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        presenter.on_log_file_dropped("/path/to/file.log")

        view.show_warning.assert_called_once()

    def test_on_log_file_dropped_with_selection(self, configs_dir: Path, tmp_path: Path):
        """测试有选中协议时拖拽文件"""
        view = _create_mock_view()
        view.get_selected_protocol_name.return_value = "sinexcel"
        model = ProtocolModel(configs_dir)
        model.discover_protocols()
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        log_file = tmp_path / "test.log"
        log_file.write_text("测试内容")
        presenter.on_log_file_dropped(str(log_file))

        view.log_info.assert_called()
        assert "拖拽" in view.log_info.call_args[0][0]


@pytest.mark.unit
class TestNormalParsePresenterWaveReplay:
    """NormalParsePresenter 波形回放跳转测试"""

    def test_open_wave_replay_calls_view_interface(self, configs_dir: Path):
        """波形回放跳转应通过 View 接口的 request_wave_replay 方法"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        # 模拟已保存的波形条目数据
        presenter._last_wave_entries = [
            ("2024-08-29 09:00:00:000", {"电压": 220.0}, 4, "Recv"),
            ("2024-08-29 09:00:01:000", {"电压": 221.0}, 4, "Recv"),
        ]

        presenter._open_wave_replay_with_parsed_data("sinexcel")

        # 应该通过 View 接口调用 request_wave_replay
        view.request_wave_replay.assert_called_once()
        entries_arg, source_arg = view.request_wave_replay.call_args[0]
        assert len(entries_arg) == 2
        assert "sinexcel" in source_arg

    def test_open_wave_replay_no_entries_warns(self, configs_dir: Path):
        """无波形数据时应显示警告而不是调用跳转"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        # 空数据
        presenter._last_wave_entries = []

        presenter._open_wave_replay_with_parsed_data("sinexcel")

        view.log_warning.assert_called()
        view.request_wave_replay.assert_not_called()

    def test_open_wave_replay_no_attr_warns(self, configs_dir: Path):
        """_last_wave_entries 不存在时应显示警告"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        # 不设置 _last_wave_entries
        presenter._open_wave_replay_with_parsed_data("sinexcel")

        view.log_warning.assert_called()
        view.request_wave_replay.assert_not_called()


@pytest.mark.unit
class TestNormalParsePresenterCleanup:
    """NormalParsePresenter 资源清理测试"""

    def test_cleanup_no_threads(self, configs_dir: Path):
        """测试无线程时清理"""
        view = _create_mock_view()
        model = ProtocolModel(configs_dir)
        presenter = NormalParsePresenter(view=view, protocol_model=model, parse_model=ParseModel())

        # 不应该抛出异常
        presenter.cleanup()
