"""
文件名称: lod_cache_manager.py
内容摘要: 多级精度（LOD）缓存管理器，从 WaveChartWidget 中拆分出 LOD 数据的存储、计算和查询职责
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-25
"""

import logging
from typing import Dict, Optional, Tuple

import numpy as np

from gui.wave.utils.downsample import LOD_LEVELS, LOD_MAX_LEVEL, lttb_downsample

logger = logging.getLogger(__name__)


class LodCacheManager:
    """
    多级精度（LOD）缓存管理器

    职责：
    - 存储原始数据和各级降采样缓存
    - 按需（lazy）计算降采样数据
    - 根据可见数据点数选择合适的精度级别

    本类为纯数据管理类，不依赖 PySide6 或 pyqtgraph。
    """

    def __init__(self):
        # 多级精度缓存: {field_path: {lod_level: (x_data, y_data)}}
        self._lod_cache: Dict[str, Dict[int, Tuple[np.ndarray, np.ndarray]]] = {}
        # 原始数据缓存: {field_path: (x_data, y_data)}
        self._raw_data_cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        # 上次使用的 LOD 级别
        self._last_lod_level: Optional[int] = None
        # 上次 X 轴范围宽度（用于判断是否需要重算）
        self._last_x_range_width: Optional[float] = None

    @property
    def raw_data_cache(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """获取原始数据缓存的只读引用"""
        return self._raw_data_cache

    @property
    def last_lod_level(self) -> Optional[int]:
        """获取上次使用的 LOD 级别"""
        return self._last_lod_level

    def store_raw_data(
        self,
        field_path: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
    ) -> None:
        """
        存储原始数据并清空该字段的 LOD 缓存

        Args:
            field_path: 字段路径
            x_data: 原始 X 轴数据
            y_data: 原始 Y 轴数据
        """
        # 缓存原始数据
        # x_data/y_data 由调用方新建（np.array），无需额外 copy
        self._raw_data_cache[field_path] = (x_data, y_data)

        # 初始化该字段的 LOD 缓存
        if field_path not in self._lod_cache:
            self._lod_cache[field_path] = {}

        # 数据更新后清空旧的 LOD 缓存，按需在 get_lod_data 中计算
        self._lod_cache[field_path].clear()

    def get_lod_data(
        self,
        field_path: str,
        level: int,
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        获取指定字段和精度级别的数据（按需计算）

        Args:
            field_path: 字段路径
            level: 精度级别

        Returns:
            (x_data, y_data) 或 None
        """
        # 原始数据级别
        if level >= LOD_MAX_LEVEL:
            return self._raw_data_cache.get(field_path)

        raw_data = self._raw_data_cache.get(field_path)
        if raw_data is None:
            return None
        raw_x, raw_y = raw_data

        # 降采样级别：按需（lazy）计算并写入缓存
        field_cache = self._lod_cache.setdefault(field_path, {})
        if level in field_cache:
            return field_cache[level]

        target = LOD_LEVELS[level][1]
        if len(raw_x) <= target:
            return raw_data

        try:
            sampled_x, sampled_y = lttb_downsample(raw_x, raw_y, target)
            field_cache[level] = (sampled_x, sampled_y)
            return field_cache[level]
        except Exception as e:
            logger.debug("LOD downsample failed (field=%s level=%s): %s", field_path, level, e)
            return raw_data

    def select_lod_level(self, visible_points: int, pixel_width: int) -> int:
        """
        根据可见数据点数和像素宽度自适应选择精度级别

        Args:
            visible_points: 当前视口内可见的数据点数
            pixel_width: 绘图区域像素宽度

        Returns:
            精度级别索引（0-2 为降采样级别，LOD_MAX_LEVEL 为原始数据）
        """
        # 像素自适应：每像素最多显示 2 个数据点
        max_points_for_pixels = max(1, pixel_width) * 2

        # 如果可见点数在像素容量内，使用原始数据
        if visible_points <= max_points_for_pixels:
            return LOD_MAX_LEVEL

        # 根据数据密度选择降采样级别
        for i, (threshold, _target) in enumerate(LOD_LEVELS):
            if visible_points <= threshold:
                return i

        return LOD_MAX_LEVEL - 1  # 超大数据量使用最粗精度

    def remove_field(self, field_path: str) -> None:
        """移除指定字段的所有缓存"""
        self._lod_cache.pop(field_path, None)
        self._raw_data_cache.pop(field_path, None)

    def clear(self) -> None:
        """清空所有缓存"""
        self._lod_cache.clear()
        self._raw_data_cache.clear()
        self._last_lod_level = None
        self._last_x_range_width = None

    def should_rerender(self, current_x_range_width: float) -> bool:
        """
        判断是否需要因缩放变化而重新渲染

        注意：本方法有副作用——返回 True 时会更新内部记录的 X 轴宽度。
        设计上仅由 _apply_lod_rendering 单一调用点使用。

        Args:
            current_x_range_width: 当前 X 轴范围宽度

        Returns:
            True 表示需要重新渲染
        """
        if self._last_x_range_width is not None:
            if abs(current_x_range_width - self._last_x_range_width) < 1e-6:
                return False
        self._last_x_range_width = current_x_range_width
        return True

    def update_lod_level(self, level: int) -> bool:
        """
        更新 LOD 级别，返回是否发生了变化

        Args:
            level: 新的 LOD 级别

        Returns:
            True 表示级别发生了变化
        """
        if level == self._last_lod_level:
            return False
        self._last_lod_level = level
        return True
