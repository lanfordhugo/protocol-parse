"""
文件名称: test_replay_presenter.py
内容摘要: ReplayPresenter 单元测试（on_clear_data、重复加载、数据隔离）
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-12
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, call

import pytest

from gui.wave.models.wave_data_manager import WaveDataManager
from gui.wave.presenters.replay_presenter import ReplayPresenter


def _create_mock_view():
    """创建符合 IHistoryWaveView 接口的 Mock View"""
    view = MagicMock()
    return view


def _make_entries(field_names, count=5, cmd_id=4, base_hour=9):
    """
    构造测试条目列表

    Args:
        field_names: 字段名列表
        count: 条目数
        cmd_id: 命令ID
        base_hour: 起始小时

    Returns:
        entries 列表 [(timestamp_str, content_dict, cmd_id, direction), ...]
    """
    entries = []
    for i in range(count):
        ts = f"2024-08-29 {base_hour:02d}:{i:02d}:00:000"
        content = {name: float(i + idx) for idx, name in enumerate(field_names)}
        entries.append((ts, content, cmd_id, "Recv"))
    return entries


@pytest.mark.unit
class TestReplayPresenterOnClearData:
    """ReplayPresenter.on_clear_data 测试"""

    def setup_method(self):
        self.view = _create_mock_view()
        self.data_manager = WaveDataManager()
        self.presenter = ReplayPresenter(
            view=self.view,
            data_manager=self.data_manager,
        )

    def test_clear_data_resets_data_manager(self):
        """on_clear_data 调用 reset() 清空数据管理器"""
        entries = _make_entries(["电压", "电流"], count=3)
        self.presenter.load_from_entries(entries, "测试数据")
        assert self.data_manager.data_count == 3
        assert len(self.data_manager.get_all_field_configs()) == 2

        self.presenter.on_clear_data()

        assert self.data_manager.data_count == 0
        assert len(self.data_manager.get_all_field_configs()) == 0

    def test_clear_data_updates_view(self):
        """on_clear_data 正确更新 View 状态"""
        entries = _make_entries(["电压"], count=2)
        self.presenter.load_from_entries(entries, "测试数据")
        self.view.reset_mock()

        self.presenter.on_clear_data()

        self.view.clear_chart.assert_called_once()
        self.view.refresh_field_tree.assert_called_once_with([])
        self.view.update_data_count.assert_called_with(0)
        self.view.set_export_enabled.assert_called_with(False)
        self.view.update_status.assert_called_with("数据已清空")

    def test_clear_data_on_empty_manager(self):
        """空状态下调用 on_clear_data 不应异常"""
        self.presenter.on_clear_data()

        assert self.data_manager.data_count == 0
        self.view.clear_chart.assert_called_once()


@pytest.mark.unit
class TestReplayPresenterRepeatedLoad:
    """ReplayPresenter 重复加载测试 — 验证不会累积旧字段"""

    def setup_method(self):
        self.view = _create_mock_view()
        self.data_manager = WaveDataManager()
        self.presenter = ReplayPresenter(
            view=self.view,
            data_manager=self.data_manager,
        )

    def test_reload_different_fields_no_stale(self):
        """第二次加载不同字段时，旧字段不应残留"""
        # 第一次加载：电压、电流
        entries_a = _make_entries(["电压", "电流"], count=3)
        self.presenter.load_from_entries(entries_a, "数据A")
        configs_a = self.data_manager.get_all_field_configs()
        assert {c.field_path for c in configs_a} == {"电压", "电流"}

        # 第二次加载：功率、温度（不同字段）
        entries_b = _make_entries(["功率", "温度"], count=5, cmd_id=5, base_hour=10)
        self.presenter.load_from_entries(entries_b, "数据B")

        configs_b = self.data_manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs_b}
        assert field_paths == {"功率", "温度"}
        assert "电压" not in field_paths
        assert "电流" not in field_paths
        assert self.data_manager.data_count == 5

    def test_reload_same_fields_fresh_data(self):
        """重新加载相同字段时，数据应完全刷新"""
        entries_1 = _make_entries(["电压"], count=3)
        self.presenter.load_from_entries(entries_1, "数据1")
        assert self.data_manager.data_count == 3

        entries_2 = _make_entries(["电压"], count=10, base_hour=11)
        self.presenter.load_from_entries(entries_2, "数据2")
        assert self.data_manager.data_count == 10

    def test_load_after_clear_no_stale(self):
        """清空后再加载，不应残留旧字段"""
        entries_a = _make_entries(["电压", "电流"], count=3)
        self.presenter.load_from_entries(entries_a, "数据A")

        self.presenter.on_clear_data()

        entries_b = _make_entries(["SOC", "温度"], count=5, cmd_id=6, base_hour=12)
        self.presenter.load_from_entries(entries_b, "数据B")

        configs = self.data_manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}
        assert field_paths == {"SOC", "温度"}
        assert self.data_manager.data_count == 5


@pytest.mark.unit
class TestReplayPresenterLoadFromEntries:
    """ReplayPresenter.load_from_entries 基础测试"""

    def setup_method(self):
        self.view = _create_mock_view()
        self.data_manager = WaveDataManager()
        self.presenter = ReplayPresenter(
            view=self.view,
            data_manager=self.data_manager,
        )

    def test_load_returns_count(self):
        """load_from_entries 返回加载的数据点数"""
        entries = _make_entries(["电压", "电流"], count=5)
        count = self.presenter.load_from_entries(entries, "测试")
        assert count == 5

    def test_load_empty_entries(self):
        """加载空列表返回0"""
        count = self.presenter.load_from_entries([], "空数据")
        assert count == 0
        self.view.update_status.assert_called()

    def test_load_enables_export(self):
        """加载数据后导出按钮应启用"""
        entries = _make_entries(["电压"], count=3)
        self.presenter.load_from_entries(entries, "测试")
        self.view.set_export_enabled.assert_called_with(True)

    def test_load_refreshes_field_tree(self):
        """加载数据后字段树应刷新"""
        entries = _make_entries(["电压", "电流"], count=3)
        self.presenter.load_from_entries(entries, "测试")
        self.view.refresh_field_tree.assert_called()
        # 应该传入2个字段配置
        configs = self.view.refresh_field_tree.call_args[0][0]
        assert len(configs) == 2


@pytest.mark.unit
class TestReplayPresenterImportJson:
    """ReplayPresenter.import_from_json 测试"""

    def setup_method(self):
        self.view = _create_mock_view()
        self.data_manager = WaveDataManager()
        self.presenter = ReplayPresenter(
            view=self.view,
            data_manager=self.data_manager,
        )

    def test_import_json_resets_old_data(self):
        """import_from_json 应先重置旧数据再导入"""
        # 先加载一些数据
        entries = _make_entries(["电压"], count=3)
        self.presenter.load_from_entries(entries, "旧数据")
        assert self.data_manager.data_count == 3

        # 准备JSON文件
        json_data = {
            "field_configs": [
                {
                    "field_path": "功率",
                    "display_name": "功率",
                    "field_type": "NUMERIC",
                    "chart_type": "LINE",
                    "color": "#FF0000",
                    "enabled": True,
                    "cmd_id": 5,
                }
            ],
            "data_points": [
                {
                    "timestamp": "2024-08-29T10:00:00",
                    "values": {"功率": 100.0},
                    "cmd_id": 5,
                    "direction": "Recv",
                },
                {
                    "timestamp": "2024-08-29T10:01:00",
                    "values": {"功率": 200.0},
                    "cmd_id": 5,
                    "direction": "Recv",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            json.dump(json_data, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            count = self.presenter.import_from_json(tmp_path)
            assert count == 2

            # 旧字段"电压"不应残留
            configs = self.data_manager.get_all_field_configs()
            field_paths = {c.field_path for c in configs}
            assert "电压" not in field_paths
            assert "功率" in field_paths
        finally:
            os.unlink(tmp_path)

    def test_import_invalid_json_returns_zero(self):
        """导入无效JSON文件应返回0且不崩溃"""
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write("这不是有效的JSON")
            tmp_path = f.name

        try:
            count = self.presenter.import_from_json(tmp_path)
            assert count == 0
            # 应显示错误状态
            self.view.update_status.assert_called()
        finally:
            os.unlink(tmp_path)
