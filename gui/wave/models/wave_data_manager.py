"""
文件名称: wave_data_manager.py
内容摘要: 波形数据管理器，负责数据存储、字段配置管理、时间范围查询和数据导入导出
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import csv
import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

from gui.wave.utils.field_type_detector import FieldType, FieldTypeDetector
from gui.wave.utils.chart_type_mapper import ChartType, ChartTypeMapper

logger = logging.getLogger(__name__)

# 时间戳解析格式（兼容多种分隔符）
_TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S:%f",   # 2024-08-29 09:26:16:261
    "%Y-%m-%d %H:%M:%S.%f",   # 2025-06-30 08:51:52.804
    "%Y-%m-%d %H:%M:%S",      # 无毫秒
]


def parse_timestamp(ts_str: str) -> datetime:
    """
    解析时间戳字符串为 datetime 对象

    Args:
        ts_str: 时间戳字符串

    Returns:
        datetime 对象

    Raises:
        ValueError: 无法解析的时间戳格式
    """
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(ts_str.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间戳: {ts_str}")


@dataclass
class FieldConfig:
    """字段配置"""
    field_path: str          # 字段路径（如 "电压" 或 "content.电压"）
    display_name: str        # 显示名称
    field_type: FieldType    # 字段类型
    chart_type: ChartType    # 图表类型
    color: str               # 颜色（#RRGGBB）
    enabled: bool = True     # 是否启用
    cmd_id: Optional[int] = None  # 关联的命令ID
    field_order: int = 0     # 字段在 YAML 定义中的顺序（用于排序显示）


@dataclass
class DataPoint:
    """单个数据点"""
    timestamp: datetime                # 时间戳
    values: Dict[str, Any] = field(default_factory=dict)  # {field_path: value}
    cmd_id: Optional[int] = None       # 命令ID
    direction: Optional[str] = None    # 方向（Recv/Send）


class WaveDataManager:
    """
    波形数据管理器

    职责：
    - 全量存储所有历史数据点
    - 管理字段配置（FieldConfig）
    - 提供时间范围查询
    - 数据导入/导出（JSON/CSV）
    - 线程安全（threading.Lock）

    注意：本类为纯 Python 实现，不依赖 PySide6
    """

    # 默认波形缓存大小
    DEFAULT_MAX_DATA_POINTS = 50000

    def __init__(
        self,
        protocol_config: Optional[Any] = None,
        max_data_points: int = DEFAULT_MAX_DATA_POINTS,
    ):
        """
        初始化数据管理器

        Args:
            protocol_config: 可选的协议配置对象，用于字段类型检测
            max_data_points: 最大数据点缓存数（默认50000）
        """
        self._lock = threading.Lock()
        self._max_data_points = max(1000, max_data_points)

        # 数据存储（deque 逐条淘汰，满时自动丢弃最旧数据点）
        self._data_points: Deque[DataPoint] = deque(maxlen=self._max_data_points)

        # 字段配置 {field_path: FieldConfig}
        self._field_configs: Dict[str, FieldConfig] = {}

        # 正在录制的字段集合（控制数据层：仅这些字段的数据会被 add_data_point 存储）
        # 注意：与 FieldConfig.enabled（控制展示层：字段是否在图表上显示）是两个独立维度：
        #   - recording=True, enabled=True  → 录制并显示（实时监控正常状态）
        #   - recording=True, enabled=False → 录制但不显示（后台采集，稍后分析）
        #   - recording=False, enabled=True → 仅显示已有数据（历史回放）
        self._recording_fields: set = set()
        # 是否自动录制所有字段（历史加载模式）
        self._record_all_mode: bool = False

        # 字段类型检测器
        self._type_detector = FieldTypeDetector(protocol_config)
        # YAML 字段顺序映射 {cmd_id: {field_name: order}}
        self._yaml_field_order_by_cmd: Dict[int, Dict[str, int]] = {}
        self.set_protocol_config(protocol_config)

        # 颜色分配计数器
        self._color_index = 0

        # 时间索引（加速范围查询）
        self._timestamp_array: Optional[np.ndarray] = None
        self._timestamp_dirty: bool = True
        self._data_points_list: Optional[List[DataPoint]] = None

    # ============== 数据操作 ==============

    def add_entry(
        self,
        timestamp_str: str,
        parsed_content: Optional[Dict[str, Any]],
        cmd_id: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> Tuple[Optional[DataPoint], List[FieldConfig]]:
        """
        添加单个解析结果

        自动发现新字段（注册为 enabled=False），但仅存储 recording_fields 中的字段值。

        Args:
            timestamp_str: 时间戳字符串
            parsed_content: 解析后的内容字典
            cmd_id: 命令ID
            direction: 数据方向

        Returns:
            (创建的DataPoint或None, 新发现的FieldConfig列表)
        """
        if not parsed_content:
            return None, []

        try:
            timestamp = parse_timestamp(timestamp_str)
        except ValueError as e:
            logger.warning("时间戳解析失败: %s", e)
            return None, []

        # 提取扁平化的字段值
        values = self.flatten_parsed_content(parsed_content)

        new_configs: List[FieldConfig] = []
        point = None

        with self._lock:
            # 自动检测并注册新字段（enabled=False，仅发现）
            for observed_order, (field_path, value) in enumerate(values.items()):
                if field_path not in self._field_configs:
                    field_order = self._resolve_field_order(field_path, cmd_id, observed_order)
                    config = self._auto_register_field(field_path, value, cmd_id, field_order)
                    if config:
                        new_configs.append(config)

            # 仅存储正在记录的字段
            recorded_values = {
                k: v for k, v in values.items()
                if k in self._recording_fields
            }

            if recorded_values:
                point = DataPoint(
                    timestamp=timestamp,
                    values=recorded_values,
                    cmd_id=cmd_id,
                    direction=direction,
                )
                self._data_points.append(point)
                self._timestamp_dirty = True
                self._data_points_list = None

        return point, new_configs

    def add_entries(
        self,
        entries: List[Tuple[str, Optional[Dict[str, Any]], Optional[int], Optional[str]]],
    ) -> int:
        """
        批量添加解析结果

        Args:
            entries: 列表，每项为 (timestamp_str, parsed_content, cmd_id, direction)

        Returns:
            成功添加的数据点数量
        """
        count = 0
        for ts_str, content, cmd_id, direction in entries:
            point, _ = self.add_entry(ts_str, content, cmd_id, direction)
            if point:
                count += 1
        return count

    def get_data_in_range(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[DataPoint]:
        """
        查询时间范围内的数据点（使用二分查找加速）

        Args:
            start: 起始时间（None 表示不限）
            end: 结束时间（None 表示不限）

        Returns:
            时间范围内的数据点列表
        """
        with self._lock:
            if not self._data_points:
                return []

            # 无范围限制，返回全部
            if start is None and end is None:
                return list(self._data_points)

            # 重建时间索引（如果需要）
            if self._timestamp_dirty or self._timestamp_array is None:
                self._rebuild_timestamp_index_unlocked()

            if self._timestamp_array is None or len(self._timestamp_array) == 0:
                return []

            # 使用二分查找定位范围
            start_ts = start.timestamp() if start else float(self._timestamp_array[0])
            end_ts = end.timestamp() if end else float(self._timestamp_array[-1])

            start_idx = int(np.searchsorted(self._timestamp_array, start_ts, "left"))
            end_idx = int(np.searchsorted(self._timestamp_array, end_ts, "right"))

            # 直接切片缓存的 list，避免每次把 deque 转 list
            if self._data_points_list is None:
                self._data_points_list = list(self._data_points)
            return self._data_points_list[start_idx:end_idx]

    def _rebuild_timestamp_index_unlocked(self) -> None:
        """重建时间索引（调用时已持有锁）"""
        if not self._data_points:
            self._timestamp_array = None
            self._timestamp_dirty = False
            self._data_points_list = None
            return

        self._data_points_list = list(self._data_points)
        self._timestamp_array = np.fromiter(
            (p.timestamp.timestamp() for p in self._data_points_list),
            dtype=np.float64,
            count=len(self._data_points_list),
        )
        self._timestamp_dirty = False

    def get_latest_data(self, seconds: float) -> List[DataPoint]:
        """
        获取最近 N 秒的数据

        Args:
            seconds: 时间窗口（秒）

        Returns:
            最近 N 秒内的数据点列表
        """
        with self._lock:
            if not self._data_points:
                return []
            latest_time = self._data_points[-1].timestamp
            cutoff = latest_time.timestamp() - seconds
            result = []
            for point in reversed(self._data_points):
                if point.timestamp.timestamp() < cutoff:
                    break
                result.append(point)
            result.reverse()
            return result

    def clear(self) -> None:
        """清空所有数据"""
        with self._lock:
            self._data_points.clear()
            self._timestamp_dirty = True
            self._data_points_list = None

    def reset(self) -> None:
        """完整重置：清空数据点、字段配置、录制状态和颜色计数器"""
        with self._lock:
            self._data_points.clear()
            self._field_configs.clear()
            self._recording_fields.clear()
            self._record_all_mode = False
            self._color_index = 0
            self._timestamp_dirty = True
            self._data_points_list = None

    @property
    def data_count(self) -> int:
        """数据点总数"""
        with self._lock:
            return len(self._data_points)

    @property
    def max_data_points(self) -> int:
        """最大数据点缓存数"""
        return self._max_data_points

    def set_max_data_points(self, size: int) -> None:
        """
        运行时调整波形缓存大小

        如果新大小比当前数据量小，最旧的数据会被自动丢弃。

        Args:
            size: 新的最大数据点数（最小1000）
        """
        size = max(1000, size)
        with self._lock:
            self._max_data_points = size
            # 重建 deque，超出部分自动从左侧（最旧）丢弃
            self._data_points = deque(self._data_points, maxlen=size)
            self._timestamp_dirty = True
            self._data_points_list = None

    @property
    def time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """数据时间范围"""
        with self._lock:
            if not self._data_points:
                return None
            return (self._data_points[0].timestamp, self._data_points[-1].timestamp)

    # ============== 字段配置管理 ==============

    def add_field_config(self, config: FieldConfig) -> None:
        """
        添加或更新字段配置

        Args:
            config: 字段配置
        """
        with self._lock:
            self._field_configs[config.field_path] = config

    def detect_field_type(
        self,
        sample_value: Any,
        type_def: Optional[Any] = None,
        field: Optional[Any] = None,
    ) -> "FieldType":
        """
        检测字段类型（优先 YAML 配置，回退值类型检测）

        对外暴露类型检测能力，避免外部直接访问私有 _type_detector。

        Args:
            sample_value: 字段样本值
            type_def: YAML 类型定义（可选）
            field: YAML 字段定义（可选）

        Returns:
            检测到的字段类型
        """
        return self._type_detector.detect_with_fallback(
            sample_value, type_def, field
        )

    def set_protocol_config(self, protocol_config: Optional[Any]) -> None:
        """
        设置协议配置并重建 YAML 字段顺序映射。

        Args:
            protocol_config: 协议配置对象（YamlCmdFormat 或 ProtocolConfig）
        """
        with self._lock:
            self._type_detector = FieldTypeDetector(protocol_config)
            self._yaml_field_order_by_cmd = self._build_yaml_field_order_map(protocol_config)

    def remove_field_config(self, field_path: str) -> Optional[FieldConfig]:
        """
        移除字段配置

        Args:
            field_path: 字段路径

        Returns:
            移除的配置，不存在返回 None
        """
        with self._lock:
            # 同步停止录制，防止移除配置后 _recording_fields 中残留悬挂条目
            self._recording_fields.discard(field_path)
            return self._field_configs.pop(field_path, None)

    def get_field_config(self, field_path: str) -> Optional[FieldConfig]:
        """获取字段配置"""
        with self._lock:
            return self._field_configs.get(field_path)

    def get_all_field_configs(self) -> List[FieldConfig]:
        """
        获取所有字段配置

        按 cmd_id 分组，每组内按 field_order 排序返回。
        """
        with self._lock:
            configs = list(self._field_configs.values())
            # 按 cmd_id 分组，组内按 field_order 排序
            # None (未分组) 排在最前面
            configs.sort(key=lambda c: (c.cmd_id if c.cmd_id is not None else -1, c.field_order))
            return configs

    def get_enabled_field_configs(self) -> List[FieldConfig]:
        """获取所有启用的字段配置"""
        with self._lock:
            return [c for c in self._field_configs.values() if c.enabled]

    def update_field_color(self, field_path: str, color: str) -> bool:
        """更新字段颜色"""
        with self._lock:
            config = self._field_configs.get(field_path)
            if config:
                config.color = color
                return True
            return False

    def update_field_enabled(self, field_path: str, enabled: bool) -> bool:
        """更新字段启用状态"""
        with self._lock:
            config = self._field_configs.get(field_path)
            if config:
                config.enabled = enabled
                return True
            return False

    def update_field_display_name(self, field_path: str, display_name: str) -> bool:
        """更新字段显示名称"""
        with self._lock:
            config = self._field_configs.get(field_path)
            if config:
                config.display_name = display_name
                return True
            return False

    # ============== 录制控制 ==============

    def start_recording(self, field_path: str) -> None:
        """开始记录指定字段的数据"""
        with self._lock:
            self._recording_fields.add(field_path)
            logger.debug("开始记录字段: %s", field_path)

    def stop_recording(self, field_path: str) -> None:
        """停止记录指定字段的数据（已有数据保留）"""
        with self._lock:
            self._recording_fields.discard(field_path)
            logger.debug("停止记录字段: %s", field_path)

    def is_recording(self, field_path: str) -> bool:
        """指定字段是否正在记录"""
        with self._lock:
            return field_path in self._recording_fields

    def set_record_all(self, enabled: bool) -> None:
        """
        设置全字段录制模式

        启用后，后续新发现的字段也会自动加入录制。
        用于历史加载、测试等需要记录所有数据的场景。
        """
        with self._lock:
            self._record_all_mode = enabled
            if enabled:
                self._recording_fields = set(self._field_configs.keys())
            else:
                self._recording_fields.clear()

    @property
    def recording_fields(self) -> set:
        """获取当前正在记录的字段集合"""
        with self._lock:
            return set(self._recording_fields)

    # ============== 数据提取（供图表使用） ==============

    def get_plot_data(
        self,
        field_path: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Tuple[List[float], List[Optional[float]]]:
        """
        获取指定字段的绘图数据

        Args:
            field_path: 字段路径
            start: 起始时间
            end: 结束时间

        Returns:
            (时间戳列表, 值列表) - 时间戳为 epoch 秒数
        """
        with self._lock:
            config = self._field_configs.get(field_path)
        if not config:
            return [], []

        points = self.get_data_in_range(start, end)

        timestamps: List[float] = []
        values: List[Optional[float]] = []

        for point in points:
            if field_path not in point.values:
                continue
            raw_value = point.values[field_path]
            numeric_value = self._type_detector.extract_numeric_value(
                raw_value, config.field_type
            )
            if numeric_value is not None:
                timestamps.append(point.timestamp.timestamp())
                values.append(numeric_value)

        return timestamps, values

    def get_plot_data_batch(
        self,
        field_paths: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Tuple[List[float], List[Optional[float]]]]:
        """
        批量获取多个字段的绘图数据（单次遍历数据点）
        Args:
            field_paths: 字段路径列表
            start: 起始时间
            end: 结束时间

        Returns:
            {field_path: (timestamps, values)}
        """
        points = self.get_data_in_range(start, end)
        return self.get_plot_data_batch_from_points(field_paths, points)

    def get_plot_data_batch_from_points(
        self,
        field_paths: List[str],
        points: List[DataPoint],
    ) -> Dict[str, Tuple[List[float], List[Optional[float]]]]:
        """
        批量获取多个字段的绘图数据（给定已筛选的数据点列表）。

        注意：按字段路径迭代，而不是遍历 point.values 的所有键，
        这样复杂度为 O(len(points) * len(field_paths))，避免 record_all 模式下
        每个点都遍历大量无关字段。
        """
        if not field_paths:
            return {}

        if not points:
            return {}

        with self._lock:
            config_by_field = {fp: self._field_configs.get(fp) for fp in field_paths}
        config_by_field = {fp: cfg for fp, cfg in config_by_field.items() if cfg is not None}

        if not config_by_field:
            return {}

        timestamps_map: Dict[str, List[float]] = {fp: [] for fp in config_by_field}
        values_map: Dict[str, List[Optional[float]]] = {fp: [] for fp in config_by_field}
        extract_numeric_value = self._type_detector.extract_numeric_value
        field_configs = list(config_by_field.items())

        for point in points:
            ts = point.timestamp.timestamp()
            point_values = point.values
            for fp, config in field_configs:
                if fp not in point_values:
                    continue
                numeric_value = extract_numeric_value(point_values[fp], config.field_type)
                if numeric_value is None:
                    continue
                timestamps_map[fp].append(ts)
                values_map[fp].append(numeric_value)

        return {fp: (timestamps_map[fp], values_map[fp]) for fp in config_by_field}

    # ============== 数据导入/导出 ==============

    def export_to_json(self, file_path: str, enabled_only: bool = True) -> int:
        """
        导出数据为 JSON 格式（委托给 WaveDataIO）

        Args:
            file_path: 输出文件路径
            enabled_only: 仅导出用户选中的字段（默认True）

        Returns:
            导出的数据点数量
        """
        from gui.wave.models.wave_data_io import WaveDataIO

        with self._lock:
            configs_snapshot = dict(self._field_configs)
            points_snapshot = list(self._data_points)
        return WaveDataIO.export_to_json(
            file_path, configs_snapshot, points_snapshot, enabled_only
        )

    def export_to_csv(self, file_path: str, enabled_only: bool = True) -> int:
        """
        导出数据为 CSV 格式（委托给 WaveDataIO）

        Args:
            file_path: 输出文件路径
            enabled_only: 仅导出用户选中的字段（默认True）

        Returns:
            导出的数据点数量
        """
        from gui.wave.models.wave_data_io import WaveDataIO

        with self._lock:
            configs_snapshot = dict(self._field_configs)
            points_snapshot = list(self._data_points)
        return WaveDataIO.export_to_csv(
            file_path, configs_snapshot, points_snapshot, enabled_only
        )

    def import_from_json(self, file_path: str) -> int:
        """
        从 JSON 文件导入数据（委托给 WaveDataIO）

        Args:
            file_path: 输入文件路径

        Returns:
            导入的数据点数量
        """
        from gui.wave.models.wave_data_io import WaveDataIO

        result = WaveDataIO.import_from_json(
            file_path,
            resolve_field_order_fn=self._resolve_field_order,
        )

        # 恢复字段配置
        for config in result["field_configs"]:
            self.add_field_config(config)

        # 恢复数据点
        count = 0
        with self._lock:
            for point in result["data_points"]:
                self._data_points.append(point)
                count += 1

            # 按时间排序（deque不支持sort，需转换）
            sorted_points = sorted(self._data_points, key=lambda p: p.timestamp)
            self._data_points = deque(sorted_points, maxlen=self._max_data_points)
            self._timestamp_dirty = True
            self._data_points_list = None

        logger.info("已从 %s 导入 %d 个数据点", file_path, count)
        return count

    # ============== 内部方法 ==============

    def flatten_parsed_content(
        self,
        content: Dict[str, Any],
        prefix: str = "",
    ) -> Dict[str, Any]:
        """
        将解析结果扁平化为 {field_path: value} 字典

        跳过嵌套的 dict（bitfield等），保留顶层字段。
        枚举类型（含 value/name 的 dict）保持原样。

        Args:
            content: 解析后的内容字典
            prefix: 字段路径前缀

        Returns:
            扁平化的字段值字典
        """
        result: Dict[str, Any] = {}
        for key, value in content.items():
            field_path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"

            if isinstance(value, dict):
                # 枚举类型保持原样
                if "value" in value and "name" in value:
                    result[field_path] = value
                # 其他字典类型（bitfield等）跳过
            elif isinstance(value, list):
                # 列表类型跳过
                pass
            else:
                result[field_path] = value

        return result

    # 保持旧名称的兼容性
    _flatten_parsed_content = flatten_parsed_content

    def _auto_register_field(
        self,
        field_path: str,
        value: Any,
        cmd_id: Optional[int] = None,
        field_order: int = 0,
    ) -> Optional[FieldConfig]:
        """
        自动注册新发现的字段（默认不启用，不记录数据）

        注意：调用时已持有锁

        Args:
            field_path: 字段路径
            value: 字段值
            cmd_id: 命令ID
            field_order: 字段在 YAML 定义中的顺序（用于排序显示）

        Returns:
            创建的字段配置，不可绘图类型返回 None
        """
        field_type = self._type_detector.detect(value)
        chart_type = ChartTypeMapper.get_chart_type(field_type)

        if chart_type is None:
            # 不可绘图的类型不注册
            return None

        color = ChartTypeMapper.get_color(self._color_index)
        self._color_index += 1

        # record_all_mode 下自动启用并录制
        auto_enabled = self._record_all_mode

        config = FieldConfig(
            field_path=field_path,
            display_name=field_path.split(".")[-1],
            field_type=field_type,
            chart_type=chart_type,
            color=color,
            enabled=auto_enabled,
            field_order=field_order,
            cmd_id=cmd_id,
        )
        self._field_configs[field_path] = config

        if auto_enabled:
            self._recording_fields.add(field_path)

        logger.debug("发现字段: %s (类型=%s, 图表=%s, 录制=%s)", field_path, field_type.name, chart_type.name, auto_enabled)
        return config

    def _resolve_field_order(
        self,
        field_path: str,
        cmd_id: Optional[int],
        observed_order: int,
    ) -> int:
        """
        计算字段显示顺序。

        优先使用 YAML 定义顺序；若未知字段则落在 YAML 字段之后，
        并保持其在当前报文中的出现顺序。
        """
        if cmd_id is None:
            return observed_order

        try:
            cmd_key = int(cmd_id)
        except (TypeError, ValueError):
            return observed_order

        cmd_order_map = self._yaml_field_order_by_cmd.get(cmd_key)
        if not cmd_order_map:
            return observed_order

        return cmd_order_map.get(field_path, len(cmd_order_map) + observed_order)

    def _build_yaml_field_order_map(
        self,
        protocol_config: Optional[Any],
    ) -> Dict[int, Dict[str, int]]:
        """
        从协议配置构建 {cmd_id: {field_name: order}} 映射。
        """
        if protocol_config is None:
            return {}

        cmds = None
        if hasattr(protocol_config, "config") and hasattr(protocol_config.config, "cmds"):
            cmds = protocol_config.config.cmds
        elif hasattr(protocol_config, "cmds"):
            cmds = protocol_config.cmds

        if not isinstance(cmds, dict):
            return {}

        result: Dict[int, Dict[str, int]] = {}
        for raw_cmd_id, field_items in cmds.items():
            try:
                cmd_id = int(raw_cmd_id)
            except (TypeError, ValueError):
                continue

            order_map: Dict[str, int] = {}
            for index, field_def in enumerate(self._iter_field_defs(field_items)):
                field_name = getattr(field_def, "name", None)
                if not field_name:
                    continue
                if field_name not in order_map:
                    order_map[field_name] = index

            if order_map:
                result[cmd_id] = order_map

        return result

    def _iter_field_defs(self, field_items: Any):
        """
        递归遍历字段定义（展开 group 和 bit_groups）。
        """
        if not field_items:
            return
        for item in field_items:
            if hasattr(item, "name"):
                yield item
                # 处理 bitfield 的 bit_groups 子字段
                if hasattr(item, "bit_groups") and item.bit_groups:
                    for bit_group in item.bit_groups:
                        # bit_group 可能是 dict 或对象
                        name = bit_group.get("name") if isinstance(bit_group, dict) else getattr(bit_group, "name", None)
                        if name:
                            yield type("_BitGroupRef", (), {"name": name})()
            elif hasattr(item, "fields"):
                yield from self._iter_field_defs(getattr(item, "fields", []))

    @staticmethod
    def _serialize_values(values: Dict[str, Any]) -> Dict[str, Any]:
        """序列化字段值（确保JSON可序列化）"""
        result = {}
        for key, val in values.items():
            if isinstance(val, (int, float, bool, str)):
                result[key] = val
            elif isinstance(val, dict):
                result[key] = val
            elif val is None:
                result[key] = None
            else:
                result[key] = str(val)
        return result
