"""
文件名称: test_wave_integration.py
内容摘要: 波形分析模块集成测试 - 从YAML协议解析到波形数据管理的全链路验证
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import json
import os
import struct
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
from src.yaml_cmdformat import YamlCmdFormat

# 测试协议配置路径（放在configs/目录下，与标准协议加载流程一致）
TEST_PROTOCOL_PATH = Path(__file__).parent.parent / "configs" / "wave_test" / "protocol.yaml"


# ============== 报文构造工具 ==============


def build_cmd1_data(
    voltage_raw: int,
    current_raw: int,
    env_temp: int,
    gun_temp: int,
    energy_raw: int,
    power_raw: int,
) -> bytes:
    """
    构造 CMD 1 数据（纯数值型：电气参数）

    字段布局：
    - 输出电压: uint16 (scale 0.1) → 实际值 = raw * 0.1
    - 输出电流: uint16 (scale 0.1)
    - 环境温度: uint8
    - 枪头温度: uint8
    - 累计电量: uint32 (scale 0.001)
    - 功率:     uint16 (scale 0.1)
    """
    return struct.pack("<HHBBiH", voltage_raw, current_raw, env_temp, gun_temp, energy_raw, power_raw)


def build_cmd2_data(
    work_status: int,
    charge_mode: int,
    switch_state: int,
) -> bytes:
    """
    构造 CMD 2 数据（纯枚举型：状态监控）

    字段布局：
    - 工作状态: uint8 (enum work_status)
    - 充电模式: uint8 (enum charge_mode)
    - 开关状态: uint8 (enum switch_state)
    """
    return struct.pack("<BBB", work_status, charge_mode, switch_state)


def build_cmd3_data(
    bms_voltage_raw: int,
    bms_current_raw: int,
    soc: int,
    work_status: int,
    demand_voltage_raw: int,
    demand_current_raw: int,
) -> bytes:
    """
    构造 CMD 3 数据（混合型：数值 + 枚举）

    字段布局：
    - BMS电压:   uint16 (scale 0.1)
    - BMS电流:   int16  (scale 0.1)
    - SOC:       uint8
    - 工作状态:  uint8  (enum work_status)
    - 需求电压:  uint16 (scale 0.1)
    - 需求电流:  int16  (scale 0.1)
    """
    return struct.pack("<HhBBHh", bms_voltage_raw, bms_current_raw, soc, work_status,
                       demand_voltage_raw, demand_current_raw)


def build_cmd4_data(ch1: int, ch2: int, ch3: int, ch4: int) -> bytes:
    """
    构造 CMD 4 数据（多通道数值）

    字段布局：4个 uint16 (scale 0.01)
    """
    return struct.pack("<HHHH", ch1, ch2, ch3, ch4)


def generate_timestamps(
    start: str,
    count: int,
    interval_ms: int = 1000,
) -> List[str]:
    """
    生成时间戳序列

    Args:
        start: 起始时间字符串
        count: 数量
        interval_ms: 间隔毫秒

    Returns:
        时间戳字符串列表
    """
    base_dt = parse_timestamp(start)
    timestamps = []
    for i in range(count):
        dt = base_dt + timedelta(milliseconds=i * interval_ms)
        timestamps.append(dt.strftime("%Y-%m-%d %H:%M:%S:%f")[:-3])
    return timestamps


# ============== 测试场景数据集 ==============


class WaveTestDataset:
    """
    波形测试数据集

    提供预构造的测试报文，模拟真实充电过程。
    """

    def __init__(self):
        self.cmd_format = YamlCmdFormat(TEST_PROTOCOL_PATH)

    def scenario_charging_ramp(self, count: int = 50) -> List[Tuple[str, Dict, int, str]]:
        """
        场景1：充电爬坡过程（CMD1 - 纯数值）

        模拟电压从300V爬升到400V，电流从0A爬升到100A，温度缓慢上升。

        Returns:
            列表 [(timestamp_str, parsed_content, cmd_id, direction), ...]
        """
        timestamps = generate_timestamps("2024-08-29 09:00:00:000", count, 1000)
        entries = []
        for i, ts in enumerate(timestamps):
            progress = i / max(count - 1, 1)
            voltage_raw = int((300 + 100 * progress) * 10)   # 300.0V → 400.0V
            current_raw = int((0 + 100 * progress) * 10)     # 0.0A → 100.0A
            env_temp = 25 + int(5 * progress)                 # 25°C → 30°C
            gun_temp = 30 + int(15 * progress)                # 30°C → 45°C
            energy_raw = int(progress * 50000)                 # 0 → 50.000 kWh
            power_raw = int(voltage_raw * current_raw / 1000)  # V*A/10

            data = build_cmd1_data(voltage_raw, current_raw, env_temp, gun_temp, energy_raw, power_raw)
            parsed = self.cmd_format.parse_cmd_data(1, data)
            entries.append((ts, parsed, 1, "Recv"))
        return entries

    def scenario_status_changes(self, count: int = 20) -> List[Tuple[str, Dict, int, str]]:
        """
        场景2：状态切换过程（CMD2 - 纯枚举）

        模拟工作状态在 空闲→运行→故障→维护→空闲 之间切换。

        Returns:
            列表 [(timestamp_str, parsed_content, cmd_id, direction), ...]
        """
        timestamps = generate_timestamps("2024-08-29 10:00:00:000", count, 5000)
        # 预定义状态序列
        status_sequence = [0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 3, 1, 1, 1, 1, 0, 0, 0]
        mode_sequence =   [1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1]
        switch_sequence = [0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0]

        entries = []
        for i, ts in enumerate(timestamps[:count]):
            idx = i % len(status_sequence)
            data = build_cmd2_data(status_sequence[idx], mode_sequence[idx], switch_sequence[idx])
            parsed = self.cmd_format.parse_cmd_data(2, data)
            entries.append((ts, parsed, 2, "Recv"))
        return entries

    def scenario_mixed_monitoring(self, count: int = 30) -> List[Tuple[str, Dict, int, str]]:
        """
        场景3：混合类型监控（CMD3 - 数值+枚举）

        模拟充电中BMS数据上报，包含电压、电流（有符号）、SOC和状态。

        Returns:
            列表 [(timestamp_str, parsed_content, cmd_id, direction), ...]
        """
        timestamps = generate_timestamps("2024-08-29 11:00:00:000", count, 2000)
        entries = []
        for i, ts in enumerate(timestamps):
            progress = i / max(count - 1, 1)
            bms_v_raw = int((350 + 50 * progress) * 10)      # 350V → 400V
            bms_i_raw = int((-100 + 50 * progress) * 10)     # -100A → -50A (负值=充入)
            soc = int(20 + 60 * progress)                      # 20% → 80%
            status = 3 if progress < 0.9 else 0                # 充电中→空闲
            demand_v_raw = int(400 * 10)                       # 固定400V
            demand_i_raw = int(-80 * 10)                       # 固定-80A

            data = build_cmd3_data(bms_v_raw, bms_i_raw, soc, status, demand_v_raw, demand_i_raw)
            parsed = self.cmd_format.parse_cmd_data(3, data)
            entries.append((ts, parsed, 3, "Recv"))
        return entries

    def scenario_multichannel(self, count: int = 100) -> List[Tuple[str, Dict, int, str]]:
        """
        场景4：多通道高频采样（CMD4 - 4通道）

        模拟4个传感器通道的正弦波数据。

        Returns:
            列表 [(timestamp_str, parsed_content, cmd_id, direction), ...]
        """
        timestamps = generate_timestamps("2024-08-29 12:00:00:000", count, 100)
        entries = []
        for i, ts in enumerate(timestamps):
            t = i * 0.1
            ch1 = int((50 + 30 * np.sin(t * 1.0)) * 100)    # 正弦波 freq=1.0
            ch2 = int((50 + 20 * np.sin(t * 2.0)) * 100)    # 正弦波 freq=2.0
            ch3 = int((50 + 10 * np.sin(t * 0.5)) * 100)    # 正弦波 freq=0.5
            ch4 = int((50 + 25 * np.sin(t * 3.0)) * 100)    # 正弦波 freq=3.0

            data = build_cmd4_data(ch1, ch2, ch3, ch4)
            parsed = self.cmd_format.parse_cmd_data(4, data)
            entries.append((ts, parsed, 4, "Recv"))
        return entries

    def scenario_all_combined(self) -> List[Tuple[str, Dict, int, str]]:
        """
        场景5：全部CMD混合（模拟真实TCP数据流）

        交替发送不同CMD的数据，模拟多个命令共存的场景。

        Returns:
            列表 [(timestamp_str, parsed_content, cmd_id, direction), ...]
        """
        all_entries = []
        # 交叉合并各场景（每5条交替）
        s1 = self.scenario_charging_ramp(20)
        s2 = self.scenario_status_changes(10)
        s3 = self.scenario_mixed_monitoring(15)

        idx1, idx2, idx3 = 0, 0, 0
        base_ts = parse_timestamp("2024-08-29 14:00:00:000")
        tick = 0

        while idx1 < len(s1) or idx2 < len(s2) or idx3 < len(s3):
            ts_str = (base_ts + timedelta(milliseconds=tick * 500)).strftime(
                "%Y-%m-%d %H:%M:%S:%f"
            )[:-3]

            if idx1 < len(s1):
                _, parsed, cmd_id, direction = s1[idx1]
                all_entries.append((ts_str, parsed, cmd_id, direction))
                idx1 += 1
                tick += 1

            ts_str = (base_ts + timedelta(milliseconds=tick * 500)).strftime(
                "%Y-%m-%d %H:%M:%S:%f"
            )[:-3]
            if idx2 < len(s2):
                _, parsed, cmd_id, direction = s2[idx2]
                all_entries.append((ts_str, parsed, cmd_id, direction))
                idx2 += 1
                tick += 1

            ts_str = (base_ts + timedelta(milliseconds=tick * 500)).strftime(
                "%Y-%m-%d %H:%M:%S:%f"
            )[:-3]
            if idx3 < len(s3):
                _, parsed, cmd_id, direction = s3[idx3]
                all_entries.append((ts_str, parsed, cmd_id, direction))
                idx3 += 1
                tick += 1

        return all_entries


# ============== 集成测试 ==============


class TestYamlProtocolParsing:
    """验证测试协议配置可正确加载和解析"""

    def setup_method(self):
        self.cmd_format = YamlCmdFormat(TEST_PROTOCOL_PATH)

    def test_protocol_loaded(self):
        """协议配置正确加载"""
        info = self.cmd_format.get_protocol_info()
        assert info["protocol"] == "wave_test"
        assert 1 in info["supported_cmds"]
        assert 2 in info["supported_cmds"]
        assert 3 in info["supported_cmds"]
        assert 4 in info["supported_cmds"]

    def test_parse_cmd1_numeric(self):
        """CMD1 数值型字段解析"""
        # 电压=350.0V(raw=3500), 电流=80.0A(raw=800), 环温=28, 枪温=35, 电量=12345(12.345kWh), 功率=280(28.0kW)
        data = build_cmd1_data(3500, 800, 28, 35, 12345, 280)
        parsed = self.cmd_format.parse_cmd_data(1, data)

        assert parsed["输出电压"] == 350.0
        assert parsed["输出电流"] == 80.0
        assert parsed["环境温度"] == 28
        assert parsed["枪头温度"] == 35
        assert parsed["累计电量"] == 12.345
        assert parsed["功率"] == 28.0

    def test_parse_cmd2_enum(self):
        """CMD2 枚举型字段解析"""
        data = build_cmd2_data(1, 2, 0)
        parsed = self.cmd_format.parse_cmd_data(2, data)

        # 枚举解析结果应为 {"value": x, "name": "xxx"}
        assert parsed["工作状态"]["value"] == 1
        assert parsed["工作状态"]["name"] == "运行中"
        assert parsed["充电模式"]["value"] == 2
        assert parsed["充电模式"]["name"] == "恒流充电"
        assert parsed["开关状态"]["value"] == 0
        assert parsed["开关状态"]["name"] == "关闭"

    def test_parse_cmd3_mixed(self):
        """CMD3 混合型字段解析"""
        # BMS电压=380V, BMS电流=-60A(负值), SOC=50%, 状态=充电中(3)
        data = build_cmd3_data(3800, -600, 50, 3, 4000, -800)
        parsed = self.cmd_format.parse_cmd_data(3, data)

        assert parsed["BMS电压"] == 380.0
        assert parsed["BMS电流"] == -60.0
        assert parsed["SOC"] == 50
        assert parsed["工作状态"]["value"] == 3
        assert parsed["工作状态"]["name"] == "维护"
        assert parsed["需求电压"] == 400.0
        assert parsed["需求电流"] == -80.0

    def test_parse_cmd4_multichannel(self):
        """CMD4 多通道数值解析"""
        data = build_cmd4_data(5000, 3000, 7000, 1000)
        parsed = self.cmd_format.parse_cmd_data(4, data)

        assert parsed["通道1"] == 50.0
        assert parsed["通道2"] == 30.0
        assert parsed["通道3"] == 70.0
        assert parsed["通道4"] == 10.0


class TestWaveIntegrationPipeline:
    """波形全链路集成测试：协议解析 → 数据管理 → 字段检测 → 图表映射 → 绘图数据"""

    def setup_method(self):
        self.dataset = WaveTestDataset()
        self.manager = WaveDataManager()
        # 测试场景：开启全字段录制（模拟历史加载）
        self.manager.set_record_all(True)

    def test_charging_ramp_pipeline(self):
        """场景1：充电爬坡 - 数值型字段全链路"""
        entries = self.dataset.scenario_charging_ramp(50)
        count = self.manager.add_entries(entries)

        # 验证数据加载
        assert count == 50
        assert self.manager.data_count == 50

        # 验证字段自动注册
        configs = self.manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}
        assert "输出电压" in field_paths
        assert "输出电流" in field_paths
        assert "环境温度" in field_paths
        assert "功率" in field_paths

        # 验证字段类型检测
        v_config = self.manager.get_field_config("输出电压")
        assert v_config.field_type == FieldType.NUMERIC
        assert v_config.chart_type == ChartType.LINE

        # 验证绘图数据
        timestamps, values = self.manager.get_plot_data("输出电压")
        assert len(timestamps) == 50
        assert len(values) == 50
        # 电压应从300V附近爬升到400V附近
        assert values[0] < values[-1]
        assert values[0] >= 295  # 约300V
        assert values[-1] <= 405  # 约400V

        # 验证时间范围
        time_range = self.manager.time_range
        assert time_range is not None
        duration = (time_range[1] - time_range[0]).total_seconds()
        assert 45 <= duration <= 55  # 约49秒

    def test_status_changes_pipeline(self):
        """场景2：状态切换 - 枚举型字段全链路"""
        entries = self.dataset.scenario_status_changes(20)
        count = self.manager.add_entries(entries)

        assert count == 20

        # 验证枚举字段检测
        configs = self.manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}
        assert "工作状态" in field_paths
        assert "充电模式" in field_paths
        assert "开关状态" in field_paths

        # 枚举型应检测为 ENUM + SCATTER
        ws_config = self.manager.get_field_config("工作状态")
        assert ws_config.field_type == FieldType.ENUM
        assert ws_config.chart_type == ChartType.SCATTER

        # 验证绘图数据 - 枚举值应提取 value 字段
        timestamps, values = self.manager.get_plot_data("工作状态")
        assert len(timestamps) == 20
        # 值应包含 0(空闲), 1(运行中), 2(故障), 3(维护)
        unique_values = set(values)
        assert 0.0 in unique_values
        assert 1.0 in unique_values

    def test_mixed_monitoring_pipeline(self):
        """场景3：混合类型 - 数值+枚举共存"""
        entries = self.dataset.scenario_mixed_monitoring(30)
        count = self.manager.add_entries(entries)

        assert count == 30

        configs = self.manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}

        # 数值型字段
        assert "BMS电压" in field_paths
        assert "BMS电流" in field_paths
        assert "SOC" in field_paths

        # 枚举型字段
        assert "工作状态" in field_paths

        # BMS电流为有符号数，应为NUMERIC
        i_config = self.manager.get_field_config("BMS电流")
        assert i_config.field_type == FieldType.NUMERIC

        # SOC 应为 NUMERIC
        soc_config = self.manager.get_field_config("SOC")
        assert soc_config.field_type == FieldType.NUMERIC

        # 验证SOC数据递增
        _, soc_values = self.manager.get_plot_data("SOC")
        assert soc_values[0] < soc_values[-1]
        assert soc_values[0] >= 18   # ~20%
        assert soc_values[-1] <= 82  # ~80%

    def test_multichannel_pipeline(self):
        """场景4：多通道高频采样"""
        entries = self.dataset.scenario_multichannel(100)
        count = self.manager.add_entries(entries)

        assert count == 100

        # 4个通道都应注册
        configs = self.manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}
        for ch_name in ["通道1", "通道2", "通道3", "通道4"]:
            assert ch_name in field_paths
            config = self.manager.get_field_config(ch_name)
            assert config.field_type == FieldType.NUMERIC
            assert config.chart_type == ChartType.LINE

        # 正弦波数据应在合理范围内
        _, ch1_values = self.manager.get_plot_data("通道1")
        assert len(ch1_values) == 100
        assert min(ch1_values) >= 15   # ~20 (50-30)
        assert max(ch1_values) <= 85   # ~80 (50+30)

    def test_all_combined_pipeline(self):
        """场景5：多CMD混合数据流"""
        entries = self.dataset.scenario_all_combined()
        count = self.manager.add_entries(entries)

        # 应该有 20+10+15=45 条
        assert count == 45

        # 应来自多个CMD的字段
        configs = self.manager.get_all_field_configs()
        field_paths = {c.field_path for c in configs}

        # CMD1 字段
        assert "输出电压" in field_paths
        # CMD2 字段（枚举名冲突会自动处理）
        assert "充电模式" in field_paths
        # CMD3 字段
        assert "BMS电压" in field_paths

    def test_time_range_query(self):
        """时间范围查询正确性"""
        entries = self.dataset.scenario_charging_ramp(50)
        self.manager.add_entries(entries)

        # 查询前半段数据
        time_range = self.manager.time_range
        mid_time = time_range[0] + (time_range[1] - time_range[0]) / 2
        first_half = self.manager.get_data_in_range(time_range[0], mid_time)
        second_half = self.manager.get_data_in_range(mid_time, time_range[1])

        # 两部分之和应等于总数（不算边界重叠）
        assert len(first_half) + len(second_half) >= 49
        assert len(first_half) > 0
        assert len(second_half) > 0


class TestWaveExportImportIntegration:
    """数据导出/导入集成测试"""

    def setup_method(self):
        self.dataset = WaveTestDataset()

    def test_json_roundtrip(self):
        """JSON 导出→导入 数据完整性"""
        # 加载数据
        manager1 = WaveDataManager()
        manager1.set_record_all(True)
        entries = self.dataset.scenario_charging_ramp(30)
        manager1.add_entries(entries)

        # 导出
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            export_count = manager1.export_to_json(tmp_path)
            assert export_count == 30

            # 导入到新管理器
            manager2 = WaveDataManager()
            import_count = manager2.import_from_json(tmp_path)
            assert import_count == 30

            # 验证字段配置一致
            configs1 = {c.field_path: c for c in manager1.get_all_field_configs()}
            configs2 = {c.field_path: c for c in manager2.get_all_field_configs()}
            assert set(configs1.keys()) == set(configs2.keys())

            for path in configs1:
                assert configs1[path].field_type == configs2[path].field_type
                assert configs1[path].chart_type == configs2[path].chart_type

            # 验证绘图数据一致
            ts1, vals1 = manager1.get_plot_data("输出电压")
            ts2, vals2 = manager2.get_plot_data("输出电压")
            assert len(ts1) == len(ts2)
            for v1, v2 in zip(vals1, vals2):
                assert abs(v1 - v2) < 0.01
        finally:
            os.unlink(tmp_path)

    def test_csv_export(self):
        """CSV 导出完整性"""
        manager = WaveDataManager()
        manager.set_record_all(True)
        entries = self.dataset.scenario_mixed_monitoring(10)
        manager.add_entries(entries)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            count = manager.export_to_csv(tmp_path)
            assert count == 10

            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()

            # 表头 + 10行数据
            assert len(lines) == 11

            # 验证表头包含所有字段
            header = lines[0].strip()
            assert "BMS电压" in header
            assert "SOC" in header
            assert "工作状态" in header
        finally:
            os.unlink(tmp_path)

    def test_mixed_type_json_roundtrip(self):
        """混合类型数据的JSON导入导出"""
        manager1 = WaveDataManager()
        manager1.set_record_all(True)
        entries = self.dataset.scenario_all_combined()
        manager1.add_entries(entries)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            manager1.export_to_json(tmp_path)

            manager2 = WaveDataManager()
            manager2.import_from_json(tmp_path)

            assert manager2.data_count == manager1.data_count

            # 验证各类型字段的绘图数据长度一致
            for config in manager1.get_all_field_configs():
                ts1, _ = manager1.get_plot_data(config.field_path)
                ts2, _ = manager2.get_plot_data(config.field_path)
                assert len(ts1) == len(ts2), f"字段 {config.field_path} 数据不一致"
        finally:
            os.unlink(tmp_path)


class TestFieldTypeDetectionIntegration:
    """字段类型检测与真实解析数据的集成"""

    def setup_method(self):
        self.detector = FieldTypeDetector()
        self.cmd_format = YamlCmdFormat(TEST_PROTOCOL_PATH)

    def test_detect_numeric_from_parsed(self):
        """从实际解析结果检测数值类型"""
        data = build_cmd1_data(3500, 800, 28, 35, 12345, 280)
        parsed = self.cmd_format.parse_cmd_data(1, data)

        assert self.detector.detect(parsed["输出电压"]) == FieldType.NUMERIC
        assert self.detector.detect(parsed["环境温度"]) == FieldType.NUMERIC

    def test_detect_enum_from_parsed(self):
        """从实际解析结果检测枚举类型"""
        data = build_cmd2_data(1, 2, 0)
        parsed = self.cmd_format.parse_cmd_data(2, data)

        # 枚举解析后为 {"value": x, "name": "xxx"} 格式
        assert self.detector.detect(parsed["工作状态"]) == FieldType.ENUM
        assert self.detector.detect(parsed["充电模式"]) == FieldType.ENUM

    def test_detect_signed_int_from_parsed(self):
        """从实际解析结果检测有符号整数"""
        data = build_cmd3_data(3800, -600, 50, 3, 4000, -800)
        parsed = self.cmd_format.parse_cmd_data(3, data)

        # 有符号整数（负值）应检测为 NUMERIC
        assert self.detector.detect(parsed["BMS电流"]) == FieldType.NUMERIC

    def test_extract_enum_numeric_value(self):
        """枚举类型数值提取"""
        data = build_cmd2_data(2, 1, 1)
        parsed = self.cmd_format.parse_cmd_data(2, data)

        # 枚举的 value 应可提取为 float
        value = self.detector.extract_numeric_value(parsed["工作状态"], FieldType.ENUM)
        assert value == 2.0

    def test_chart_type_mapping_consistency(self):
        """图表类型映射一致性验证"""
        # 数值 → 折线
        assert ChartTypeMapper.get_chart_type(FieldType.NUMERIC) == ChartType.LINE
        assert ChartTypeMapper.is_chartable(FieldType.NUMERIC)

        # 枚举 → 散点
        assert ChartTypeMapper.get_chart_type(FieldType.ENUM) == ChartType.SCATTER
        assert ChartTypeMapper.is_chartable(FieldType.ENUM)

        # 布尔 → 阶梯
        assert ChartTypeMapper.get_chart_type(FieldType.BOOLEAN) == ChartType.STEP
        assert ChartTypeMapper.is_chartable(FieldType.BOOLEAN)


class TestLargeDatasetPerformance:
    """大数据量性能测试"""

    def setup_method(self):
        self.dataset = WaveTestDataset()

    def test_large_dataset_add_performance(self):
        """大数据量添加性能（1000条 < 2秒）"""
        import time

        manager = WaveDataManager()
        manager.set_record_all(True)
        entries = self.dataset.scenario_multichannel(1000)

        start = time.perf_counter()
        count = manager.add_entries(entries)
        elapsed = time.perf_counter() - start

        assert count == 1000
        assert elapsed < 2.0, f"添加1000条数据耗时 {elapsed:.2f}s，超过2秒"

    def test_large_dataset_plot_data_performance(self):
        """大数据量绘图数据获取性能"""
        import time

        manager = WaveDataManager()
        manager.set_record_all(True)
        entries = self.dataset.scenario_multichannel(1000)
        manager.add_entries(entries)

        start = time.perf_counter()
        for config in manager.get_all_field_configs():
            timestamps, values = manager.get_plot_data(config.field_path)
            assert len(timestamps) == 1000
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"获取4通道绘图数据耗时 {elapsed:.2f}s，超过1秒"

    def test_export_json_performance(self):
        """大数据量JSON导出性能"""
        import time

        manager = WaveDataManager()
        manager.set_record_all(True)
        entries = self.dataset.scenario_multichannel(1000)
        manager.add_entries(entries)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            start = time.perf_counter()
            count = manager.export_to_json(tmp_path)
            elapsed = time.perf_counter() - start

            assert count == 1000
            assert elapsed < 2.0, f"导出1000条JSON耗时 {elapsed:.2f}s，超过2秒"

            # 验证文件大小合理（不为空）
            file_size = os.path.getsize(tmp_path)
            assert file_size > 1000, f"JSON文件过小: {file_size} bytes"
        finally:
            os.unlink(tmp_path)
