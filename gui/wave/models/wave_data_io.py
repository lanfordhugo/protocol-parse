"""
文件名称: wave_data_io.py
内容摘要: 波形数据导入/导出模块，从 WaveDataManager 中拆分出 JSON/CSV 的读写职责
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-25
"""

import csv
import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from gui.wave.utils.field_type_detector import FieldType
from gui.wave.utils.chart_type_mapper import ChartType

logger = logging.getLogger(__name__)


class WaveDataIO:
    """
    波形数据导入/导出

    职责：
    - 导出数据为 JSON/CSV 格式
    - 从 JSON 文件导入数据（恢复字段配置和数据点）

    本类为无状态工具类，所有方法接收数据管理器实例作为参数，
    避免持有对数据管理器的引用以保持单向依赖。
    """

    @staticmethod
    def export_to_json(
        file_path: str,
        field_configs: Dict[str, Any],
        data_points: Any,
        enabled_only: bool = True,
    ) -> int:
        """
        导出数据为 JSON 格式

        Args:
            file_path: 输出文件路径
            field_configs: 字段配置字典 {field_path: FieldConfig}
            data_points: 数据点序列（deque 或 list）
            enabled_only: 仅导出用户选中的字段（默认True）

        Returns:
            导出的数据点数量
        """
        # 确定导出的字段集合
        if enabled_only:
            export_configs = [
                c for c in field_configs.values() if c.enabled
            ]
        else:
            export_configs = list(field_configs.values())
        export_field_paths = {c.field_path for c in export_configs}

        export_data = {
            "field_configs": [
                {
                    "field_path": c.field_path,
                    "display_name": c.display_name,
                    "field_type": c.field_type.name,
                    "chart_type": c.chart_type.name,
                    "color": c.color,
                    "enabled": c.enabled,
                    "cmd_id": c.cmd_id,
                    "field_order": c.field_order,
                }
                for c in export_configs
            ],
            "data_points": [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "values": _serialize_values(
                        {k: v for k, v in point.values.items()
                         if k in export_field_paths}
                    ),
                    "cmd_id": point.cmd_id,
                    "direction": point.direction,
                }
                for point in data_points
                if any(k in export_field_paths for k in point.values)
            ],
        }

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        count = len(export_data["data_points"])
        logger.info("已导出 %d 个数据点到 %s", count, file_path)
        return count

    @staticmethod
    def export_to_csv(
        file_path: str,
        field_configs: Dict[str, Any],
        data_points: Any,
        enabled_only: bool = True,
    ) -> int:
        """
        导出数据为 CSV 格式

        Args:
            file_path: 输出文件路径
            field_configs: 字段配置字典 {field_path: FieldConfig}
            data_points: 数据点序列（deque 或 list）
            enabled_only: 仅导出用户选中的字段（默认True）

        Returns:
            导出的数据点数量
        """
        # 收集导出的字段路径
        if enabled_only:
            all_fields = [
                fp for fp, c in field_configs.items() if c.enabled
            ]
        else:
            all_fields = list(field_configs.keys())
        if not all_fields:
            return 0

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            # 表头
            header = ["timestamp", "cmd_id", "direction"] + all_fields
            writer.writerow(header)

            # 数据行（仅输出包含选中字段数据的行）
            field_set = set(all_fields)
            count = 0
            for point in data_points:
                if not any(k in field_set for k in point.values):
                    continue
                row = [
                    point.timestamp.isoformat(),
                    point.cmd_id or "",
                    point.direction or "",
                ]
                for fp in all_fields:
                    value = point.values.get(fp, "")
                    if isinstance(value, dict):
                        # 枚举类型输出 "value(name)" 格式
                        if "value" in value and "name" in value:
                            value = f"{value['value']}({value['name']})"
                        else:
                            value = json.dumps(value, ensure_ascii=False)
                    row.append(value)
                writer.writerow(row)
                count += 1
        logger.info("已导出 %d 个数据点到 %s", count, file_path)
        return count

    @staticmethod
    def import_from_json(
        file_path: str,
        resolve_field_order_fn=None,
    ) -> Dict[str, Any]:
        """
        从 JSON 文件读取数据

        Args:
            file_path: 输入文件路径
            resolve_field_order_fn: 字段顺序解析回调 (field_path, cmd_id, index) -> int

        Returns:
            字典，包含 'field_configs' 和 'data_points' 两个键
        """
        from gui.wave.models.wave_data_manager import DataPoint, FieldConfig

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 解析字段配置
        configs: List[Any] = []
        for import_order, cfg_data in enumerate(data.get("field_configs", [])):
            cmd_id = cfg_data.get("cmd_id")
            field_path = cfg_data["field_path"]
            order = cfg_data.get("field_order", 0)
            if order == 0 and resolve_field_order_fn:
                order = resolve_field_order_fn(field_path, cmd_id, import_order)
            config = FieldConfig(
                field_path=field_path,
                display_name=cfg_data["display_name"],
                field_type=FieldType[cfg_data["field_type"]],
                chart_type=ChartType[cfg_data["chart_type"]],
                color=cfg_data["color"],
                enabled=cfg_data.get("enabled", True),
                cmd_id=cmd_id,
                field_order=order,
            )
            configs.append(config)

        # 解析数据点
        points: List[DataPoint] = []
        for pt_data in data.get("data_points", []):
            try:
                timestamp = datetime.fromisoformat(pt_data["timestamp"])
                point = DataPoint(
                    timestamp=timestamp,
                    values=pt_data.get("values", {}),
                    cmd_id=pt_data.get("cmd_id"),
                    direction=pt_data.get("direction"),
                )
                points.append(point)
            except (ValueError, KeyError) as e:
                logger.warning("导入数据点失败: %s", e)
                continue

        logger.info("已从 %s 读取 %d 个数据点", file_path, len(points))
        return {"field_configs": configs, "data_points": points}


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
