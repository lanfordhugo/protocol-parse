"""
文件名称: test_wave_data_manager.py
内容摘要: WaveDataManager、FieldTypeDetector、ChartTypeMapper 单元测试
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from gui.wave.models.wave_data_manager import (
    DataPoint,
    FieldConfig,
    WaveDataManager,
    parse_timestamp,
)
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper
from gui.wave.utils.field_type_detector import FieldType, FieldTypeDetector
from gui.wave.utils.downsample import lttb_downsample
from src.yaml_cmdformat import YamlCmdFormat


# ============== FieldTypeDetector 测试 ==============


class TestFieldTypeDetector:
    """字段类型检测器测试"""

    def setup_method(self):
        self.detector = FieldTypeDetector()

    def test_detect_numeric_int(self):
        """检测整数类型"""
        assert self.detector.detect(42) == FieldType.NUMERIC

    def test_detect_numeric_float(self):
        """检测浮点数类型"""
        assert self.detector.detect(3.14) == FieldType.NUMERIC

    def test_detect_boolean_true(self):
        """检测布尔True"""
        assert self.detector.detect(True) == FieldType.BOOLEAN

    def test_detect_boolean_false(self):
        """检测布尔False"""
        assert self.detector.detect(False) == FieldType.BOOLEAN

    def test_detect_enum_dict(self):
        """检测枚举类型（含value和name的字典）"""
        enum_val = {"value": 1, "name": "开启"}
        assert self.detector.detect(enum_val) == FieldType.ENUM

    def test_detect_string(self):
        """检测字符串类型"""
        assert self.detector.detect("hello") == FieldType.STRING

    def test_detect_complex_dict(self):
        """检测复杂字典类型（bitfield等）"""
        complex_val = {"bit0": 1, "bit1": 0}
        assert self.detector.detect(complex_val) == FieldType.STRING

    def test_detect_none(self):
        """检测None值"""
        assert self.detector.detect(None) == FieldType.STRING

    def test_detect_from_samples_numeric(self):
        """从多个样本检测数值类型"""
        values = [1, 2.5, 3, 4.0, 5]
        assert self.detector.detect_from_samples(values) == FieldType.NUMERIC

    def test_detect_from_samples_mixed(self):
        """从混合样本检测类型（取众数）"""
        values = [1, 2, True, 3, 4]
        assert self.detector.detect_from_samples(values) == FieldType.NUMERIC

    def test_detect_from_samples_empty(self):
        """空样本返回STRING"""
        assert self.detector.detect_from_samples([]) == FieldType.STRING

    def test_extract_numeric_value_int(self):
        """提取整数数值"""
        assert self.detector.extract_numeric_value(42, FieldType.NUMERIC) == 42.0

    def test_extract_numeric_value_bool(self):
        """提取布尔数值"""
        assert self.detector.extract_numeric_value(True, FieldType.BOOLEAN) == 1.0
        assert self.detector.extract_numeric_value(False, FieldType.BOOLEAN) == 0.0

    def test_extract_numeric_value_enum(self):
        """提取枚举数值"""
        enum_val = {"value": 3, "name": "模式3"}
        assert self.detector.extract_numeric_value(enum_val, FieldType.ENUM) == 3.0

    def test_extract_numeric_value_none(self):
        """None值返回None"""
        assert self.detector.extract_numeric_value(None, FieldType.NUMERIC) is None


# ============== ChartTypeMapper 测试 ==============


class TestChartTypeMapper:
    """图表类型映射器测试"""

    def test_numeric_maps_to_line(self):
        """数值型映射为折线图"""
        assert ChartTypeMapper.get_chart_type(FieldType.NUMERIC) == ChartType.LINE

    def test_boolean_maps_to_step(self):
        """布尔型映射为阶梯图"""
        assert ChartTypeMapper.get_chart_type(FieldType.BOOLEAN) == ChartType.STEP

    def test_enum_maps_to_scatter(self):
        """枚举型映射为散点图"""
        assert ChartTypeMapper.get_chart_type(FieldType.ENUM) == ChartType.SCATTER

    def test_string_not_chartable(self):
        """字符串类型不可绘图"""
        assert ChartTypeMapper.get_chart_type(FieldType.STRING) is None
        assert ChartTypeMapper.is_chartable(FieldType.STRING) is False

    def test_is_chartable(self):
        """可绘图类型判断"""
        assert ChartTypeMapper.is_chartable(FieldType.NUMERIC) is True
        assert ChartTypeMapper.is_chartable(FieldType.BOOLEAN) is True
        assert ChartTypeMapper.is_chartable(FieldType.ENUM) is True

    def test_get_color_cycling(self):
        """颜色循环分配"""
        color0 = ChartTypeMapper.get_color(0)
        color1 = ChartTypeMapper.get_color(1)
        assert color0 != color1
        # 超过调色板长度时应循环
        color_cycle = ChartTypeMapper.get_color(12)
        assert color_cycle == color0

    def test_get_pyqtgraph_config_line(self):
        """折线图配置"""
        config = ChartTypeMapper.get_pyqtgraph_config(ChartType.LINE)
        assert "antialias" in config

    def test_get_pyqtgraph_config_step(self):
        """阶梯图配置"""
        config = ChartTypeMapper.get_pyqtgraph_config(ChartType.STEP)
        assert "stepMode" in config

    def test_get_pyqtgraph_config_scatter(self):
        """散点图配置"""
        config = ChartTypeMapper.get_pyqtgraph_config(ChartType.SCATTER)
        assert "symbol" in config


# ============== parse_timestamp 测试 ==============


class TestParseTimestamp:
    """时间戳解析测试"""

    def test_parse_colon_format(self):
        """解析冒号分隔毫秒格式"""
        dt = parse_timestamp("2024-08-29 09:26:16:261")
        assert dt.year == 2024
        assert dt.month == 8
        assert dt.hour == 9

    def test_parse_dot_format(self):
        """解析点分隔毫秒格式"""
        dt = parse_timestamp("2025-06-30 08:51:52.804")
        assert dt.year == 2025
        assert dt.minute == 51

    def test_parse_no_ms_format(self):
        """解析无毫秒格式"""
        dt = parse_timestamp("2024-01-01 12:00:00")
        assert dt.second == 0

    def test_parse_invalid_format(self):
        """无效格式抛出异常"""
        with pytest.raises(ValueError):
            parse_timestamp("invalid-timestamp")


# ============== WaveDataManager 测试 ==============


class TestWaveDataManager:
    """波形数据管理器测试"""

    def setup_method(self):
        self.manager = WaveDataManager()
        # 单元测试默认开启全字段录制
        self.manager.set_record_all(True)

    def test_add_entry_basic(self):
        """添加基础数据条目"""
        content = {"电压": 220.5, "电流": 1.2}
        point, new_configs = self.manager.add_entry(
            "2024-08-29 09:26:16:261", content, cmd_id=4
        )
        assert point is not None
        assert self.manager.data_count == 1

    def test_add_entry_with_enum(self):
        """添加含枚举字段的数据"""
        content = {
            "状态": {"value": 1, "name": "运行中"},
            "温度": 25.5,
        }
        point, new_configs = self.manager.add_entry(
            "2024-08-29 09:26:16:261", content, cmd_id=5
        )
        assert point is not None
        assert "状态" in point.values
        assert "温度" in point.values

    def test_add_entry_auto_registers_fields(self):
        """添加数据时自动注册可绘图字段"""
        content = {"电压": 220.5, "开关": True}
        self.manager.add_entry("2024-08-29 09:26:16:261", content, cmd_id=4)

        configs = self.manager.get_all_field_configs()
        assert len(configs) == 2

        voltage_config = self.manager.get_field_config("电压")
        assert voltage_config is not None
        assert voltage_config.field_type == FieldType.NUMERIC
        assert voltage_config.chart_type == ChartType.LINE

        switch_config = self.manager.get_field_config("开关")
        assert switch_config is not None
        assert switch_config.field_type == FieldType.BOOLEAN
        assert switch_config.chart_type == ChartType.STEP

    def test_add_entry_skips_string_fields(self):
        """字符串字段不自动注册"""
        content = {"名称": "设备A", "电压": 220.0}
        self.manager.add_entry("2024-08-29 09:26:16:261", content, cmd_id=4)

        configs = self.manager.get_all_field_configs()
        field_paths = [c.field_path for c in configs]
        assert "名称" not in field_paths
        assert "电压" in field_paths

    def test_add_entry_none_content(self):
        """空内容返回None"""
        point, new_configs = self.manager.add_entry(
            "2024-08-29 09:26:16:261", None, cmd_id=4
        )
        assert point is None
        assert new_configs == []

    def test_add_entry_invalid_timestamp(self):
        """无效时间戳返回None"""
        point, new_configs = self.manager.add_entry(
            "invalid", {"电压": 220.0}, cmd_id=4
        )
        assert point is None
        assert new_configs == []

    def test_get_data_in_range(self):
        """时间范围查询"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:30:00:000", {"v": 2.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 10:00:00:000", {"v": 3.0}, cmd_id=4)

        start = datetime(2024, 8, 29, 9, 15)
        end = datetime(2024, 8, 29, 9, 45)
        result = self.manager.get_data_in_range(start, end)
        assert len(result) == 1
        assert result[0].values["v"] == 2.0

    def test_get_data_in_range_no_limits(self):
        """无限制时返回全部"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 10:00:00:000", {"v": 2.0}, cmd_id=4)

        result = self.manager.get_data_in_range()
        assert len(result) == 2

    def test_get_latest_data(self):
        """获取最近N秒数据"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:30:000", {"v": 2.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:50:000", {"v": 3.0}, cmd_id=4)

        # 最近15秒：只有09:00:50（距最后数据点50秒处起算，50-15=35秒之后的数据）
        result = self.manager.get_latest_data(15)
        assert len(result) == 1
        assert result[0].values["v"] == 3.0

        # 最近25秒：09:00:30和09:00:50（50-25=25秒之后的数据）
        result = self.manager.get_latest_data(25)
        assert len(result) == 2

    def test_get_plot_data(self):
        """获取绘图数据"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:01:000", {"v": 2.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:02:000", {"v": 3.0}, cmd_id=4)

        timestamps, values = self.manager.get_plot_data("v")
        assert len(timestamps) == 3
        assert len(values) == 3
        assert values == [1.0, 2.0, 3.0]

    def test_field_config_management(self):
        """字段配置增删改"""
        config = FieldConfig(
            field_path="test",
            display_name="测试",
            field_type=FieldType.NUMERIC,
            chart_type=ChartType.LINE,
            color="#FF0000",
        )
        self.manager.add_field_config(config)
        assert self.manager.get_field_config("test") is not None

        self.manager.update_field_color("test", "#00FF00")
        assert self.manager.get_field_config("test").color == "#00FF00"

        self.manager.update_field_enabled("test", False)
        assert len(self.manager.get_enabled_field_configs()) == 0

        removed = self.manager.remove_field_config("test")
        assert removed is not None
        assert self.manager.get_field_config("test") is None

    def test_time_range_property(self):
        """时间范围属性"""
        assert self.manager.time_range is None

        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 10:00:00:000", {"v": 2.0}, cmd_id=4)

        time_range = self.manager.time_range
        assert time_range is not None
        assert time_range[0].hour == 9
        assert time_range[1].hour == 10

    def test_clear(self):
        """清空数据"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        assert self.manager.data_count == 1

        self.manager.clear()
        assert self.manager.data_count == 0

    def test_reset_clears_everything(self):
        """reset() 清空数据点、字段配置、录制状态和颜色计数器"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        assert self.manager.data_count == 1
        assert len(self.manager.get_all_field_configs()) == 1
        assert len(self.manager.recording_fields) > 0

        self.manager.reset()

        assert self.manager.data_count == 0
        assert len(self.manager.get_all_field_configs()) == 0
        assert len(self.manager.recording_fields) == 0

    def test_reset_then_reload_no_stale_fields(self):
        """reset() 后重新加载不同字段的数据，不应残留旧字段配置"""
        # 第一次加载：字段 v, i
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0, "i": 2.0}, cmd_id=4)
        assert len(self.manager.get_all_field_configs()) == 2

        # reset 后加载不同字段：p, t
        self.manager.reset()
        self.manager.set_record_all(True)
        self.manager.add_entry("2024-08-29 10:00:00:000", {"p": 3.0, "t": 4.0}, cmd_id=5)

        configs = self.manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}
        assert field_paths == {"p", "t"}
        assert "v" not in field_paths
        assert "i" not in field_paths

    def test_reset_resets_color_index(self):
        """reset() 后颜色分配从头开始"""
        # 添加数据触发颜色分配
        self.manager.add_entry("2024-08-29 09:00:00:000", {"a": 1.0, "b": 2.0}, cmd_id=4)
        configs_before = self.manager.get_all_field_configs()
        colors_before = [c.color for c in configs_before]

        # reset 后重新添加
        self.manager.reset()
        self.manager.set_record_all(True)
        self.manager.add_entry("2024-08-29 10:00:00:000", {"x": 3.0, "y": 4.0}, cmd_id=5)
        configs_after = self.manager.get_all_field_configs()
        colors_after = [c.color for c in configs_after]

        # 颜色应该重新从索引0开始分配
        assert colors_before == colors_after

    def test_clear_preserves_field_configs(self):
        """clear() 仅清空数据点，保留字段配置（对比 reset）"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        assert self.manager.data_count == 1
        assert len(self.manager.get_all_field_configs()) == 1

        self.manager.clear()

        assert self.manager.data_count == 0
        # clear 保留字段配置
        assert len(self.manager.get_all_field_configs()) == 1

    def test_add_entries_batch(self):
        """批量添加"""
        entries = [
            ("2024-08-29 09:00:00:000", {"v": 1.0}, 4, "Recv"),
            ("2024-08-29 09:00:01:000", {"v": 2.0}, 4, "Recv"),
            ("2024-08-29 09:00:02:000", None, 4, "Recv"),  # 空内容
        ]
        count = self.manager.add_entries(entries)
        assert count == 2

    def test_export_import_json(self):
        """JSON导入导出"""
        # 添加测试数据
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0, "开关": True}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:01:000", {"v": 2.0, "开关": False}, cmd_id=4)

        # 导出
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            count = self.manager.export_to_json(tmp_path)
            assert count == 2

            # 验证JSON文件内容
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data["data_points"]) == 2
            assert len(data["field_configs"]) == 2

            # 导入到新管理器
            new_manager = WaveDataManager()
            import_count = new_manager.import_from_json(tmp_path)
            assert import_count == 2
            assert new_manager.data_count == 2

            # 验证字段配置被恢复
            configs = new_manager.get_all_field_configs()
            assert len(configs) == 2
        finally:
            os.unlink(tmp_path)

    def test_export_csv(self):
        """CSV导出"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:01:000", {"v": 2.0}, cmd_id=4)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            count = self.manager.export_to_csv(tmp_path)
            assert count == 2

            # 验证CSV内容
            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
            assert len(lines) == 3  # 表头 + 2行数据
            assert "v" in lines[0]  # 表头包含字段名
        finally:
            os.unlink(tmp_path)

    def test_yaml_field_order_preferred_over_alphabetical_content_order(self):
        """有协议配置时，字段顺序应以 YAML 为准，而不是字典键名顺序"""
        protocol = YamlCmdFormat(Path("configs") / "v8" / "protocol.yaml")
        manager = WaveDataManager(protocol_config=protocol)
        manager.set_record_all(True)

        fields = protocol.get_cmd_layout(201)
        total_len = sum(getattr(f, "len", 0) for f in fields)
        parsed = protocol.parse_cmd_data(201, bytes([0]) * total_len)

        # 模拟上游字典已被按字段名排序
        alphabetical_content = dict(sorted(parsed.items(), key=lambda kv: kv[0]))
        manager.add_entry("2024-08-29 09:00:00:000", alphabetical_content, cmd_id=201)

        names = [c.field_path for c in manager.get_all_field_configs()]
        assert names.index("工作状态") < names.index("1路功率")
        assert names.index("当前电表读数") < names.index("并充组网状态")

    def test_json_roundtrip_preserves_field_order_without_protocol_config(self):
        """导出/导入 JSON 后（无协议配置）仍应保持已计算的字段顺序"""
        protocol = YamlCmdFormat(Path("configs") / "v8" / "protocol.yaml")
        manager1 = WaveDataManager(protocol_config=protocol)
        manager1.set_record_all(True)

        fields = protocol.get_cmd_layout(201)
        total_len = sum(getattr(f, "len", 0) for f in fields)
        parsed = protocol.parse_cmd_data(201, bytes([0]) * total_len)
        alphabetical_content = dict(sorted(parsed.items(), key=lambda kv: kv[0]))
        manager1.add_entry("2024-08-29 09:00:00:000", alphabetical_content, cmd_id=201)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            manager1.export_to_json(tmp_path, enabled_only=False)
            manager2 = WaveDataManager()
            manager2.import_from_json(tmp_path)
            names = [c.field_path for c in manager2.get_all_field_configs()]
            assert names.index("工作状态") < names.index("1路功率")
            assert names.index("当前电表读数") < names.index("并充组网状态")
        finally:
            os.unlink(tmp_path)

    def test_export_json_enabled_only(self):
        """JSON导出仅包含 enabled 字段"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0, "i": 2.0, "t": 30}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:01:000", {"v": 2.0, "i": 3.0, "t": 31}, cmd_id=4)

        # 禁用 "i" 和 "t" 字段
        self.manager.update_field_enabled("i", False)
        self.manager.update_field_enabled("t", False)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            count = self.manager.export_to_json(tmp_path)
            assert count == 2

            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 字段配置仅含 "v"
            exported_fields = {c["field_path"] for c in data["field_configs"]}
            assert exported_fields == {"v"}

            # 数据值仅含 "v"
            for pt in data["data_points"]:
                assert "v" in pt["values"]
                assert "i" not in pt["values"]
                assert "t" not in pt["values"]
        finally:
            os.unlink(tmp_path)

    def test_export_json_all_fields(self):
        """JSON导出 enabled_only=False 包含全部字段"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0, "i": 2.0}, cmd_id=4)
        self.manager.update_field_enabled("i", False)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            count = self.manager.export_to_json(tmp_path, enabled_only=False)
            assert count == 1

            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            exported_fields = {c["field_path"] for c in data["field_configs"]}
            assert exported_fields == {"v", "i"}
        finally:
            os.unlink(tmp_path)

    def test_export_csv_enabled_only(self):
        """CSV导出仅包含 enabled 字段"""
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0, "i": 2.0}, cmd_id=4)
        self.manager.update_field_enabled("i", False)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            count = self.manager.export_to_csv(tmp_path)
            assert count == 1

            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()

            # 解析表头列名，精确判断字段
            header_cols = lines[0].strip().split(",")
            assert "v" in header_cols
            assert "i" not in header_cols
        finally:
            os.unlink(tmp_path)

    def test_export_csv_skips_irrelevant_rows(self):
        """CSV导出跳过不包含选中字段数据的行"""
        # cmd_id=4 有字段 v，cmd_id=5 有字段 p
        self.manager.add_entry("2024-08-29 09:00:00:000", {"v": 1.0}, cmd_id=4)
        self.manager.add_entry("2024-08-29 09:00:01:000", {"p": 2.0}, cmd_id=5)

        # 禁用 "p"，仅保留 "v"
        self.manager.update_field_enabled("p", False)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            count = self.manager.export_to_csv(tmp_path)
            assert count == 1  # 只有cmd_id=4的行包含 "v"

            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
            assert len(lines) == 2  # 表头 + 1行数据
        finally:
            os.unlink(tmp_path)

    def test_flatten_skips_nested_dict(self):
        """扁平化跳过嵌套字典（非枚举）"""
        content = {
            "电压": 220.0,
            "位字段": {"bit0": 1, "bit1": 0},
            "状态": {"value": 1, "name": "正常"},
        }
        self.manager.add_entry("2024-08-29 09:00:00:000", content, cmd_id=4)

        configs = self.manager.get_all_field_configs()
        field_paths = [c.field_path for c in configs]
        assert "电压" in field_paths
        assert "状态" in field_paths
        assert "位字段" not in field_paths  # 非枚举字典被跳过


# ============== LTTB 降采样测试 ==============


class TestLttbDownsample:
    """LTTB 降采样算法测试"""

    def test_small_data_no_downsample(self):
        """数据量小于目标时不降采样"""
        x = np.arange(10, dtype=np.float64)
        y = np.sin(x)
        rx, ry = lttb_downsample(x, y, 20)
        assert len(rx) == 10

    def test_exact_target(self):
        """数据量等于目标时不降采样"""
        x = np.arange(100, dtype=np.float64)
        y = np.sin(x)
        rx, ry = lttb_downsample(x, y, 100)
        assert len(rx) == 100

    def test_downsample_preserves_endpoints(self):
        """降采样保留首尾点"""
        x = np.arange(1000, dtype=np.float64)
        y = np.sin(x * 0.1)
        rx, ry = lttb_downsample(x, y, 100)
        assert len(rx) == 100
        assert rx[0] == x[0]
        assert rx[-1] == x[-1]

    def test_downsample_reduces_points(self):
        """降采样后点数正确"""
        x = np.arange(50000, dtype=np.float64)
        y = np.random.randn(50000)
        rx, ry = lttb_downsample(x, y, 2000)
        assert len(rx) == 2000
        assert len(ry) == 2000

    def test_downsample_preserves_shape(self):
        """降采样保留视觉特征（峰值附近有采样点）"""
        x = np.linspace(0, 2 * np.pi, 10000)
        y = np.sin(x)
        rx, ry = lttb_downsample(x, y, 100)
        # 降采样后的最大最小值应接近原始数据
        assert np.max(ry) > 0.9
        assert np.min(ry) < -0.9

    def test_target_less_than_3(self):
        """目标点数小于3时不降采样"""
        x = np.arange(100, dtype=np.float64)
        y = np.sin(x)
        rx, ry = lttb_downsample(x, y, 2)
        assert len(rx) == 100
