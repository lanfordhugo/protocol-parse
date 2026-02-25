"""
文件名称: downsample.py
内容摘要: 波形下采样/LOD 相关算法（不依赖 PySide6，便于单测与复用）
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-25
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

# 多级精度（LOD）配置：(阈值, 目标点数)
# 当数据点数超过阈值时，降采样到目标点数
LOD_LEVELS = [
    (5000, 500),  # Level 0: 数据点 > 5000 时降采样到 500
    (20000, 2000),  # Level 1: 数据点 > 20000 时降采样到 2000
    (100000, 5000),  # Level 2: 数据点 > 100000 时降采样到 5000
]

# 最高精度级别索引（使用原始数据）
LOD_MAX_LEVEL = len(LOD_LEVELS)


def lttb_downsample(
    x: np.ndarray,
    y: np.ndarray,
    target_points: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    LTTB（Largest Triangle Three Buckets）降采样算法（NumPy 向量化版本）

    在保留视觉特征的前提下减少数据点数量。
    备注：该实现仍包含按 bucket 迭代的 Python 循环，但每个 bucket 内的计算使用 NumPy 向量化。
    """
    n = len(x)
    if n <= target_points or target_points < 3:
        return x, y

    # 始终保留首尾点
    sampled_indices = [0]
    bucket_size = (n - 2) / (target_points - 2)

    for i in range(1, target_points - 1):
        # 当前桶的范围
        bucket_start = int((i - 1) * bucket_size) + 1
        bucket_end = min(int(i * bucket_size) + 1, n)

        # 下一个桶的范围
        next_start = int(i * bucket_size) + 1
        next_end = min(int((i + 1) * bucket_size) + 1, n)

        # 向量化计算下一个桶的平均值
        avg_x = np.mean(x[next_start:next_end])
        avg_y = np.mean(y[next_start:next_end])

        # 向量化计算当前桶内所有点的三角形面积
        a_idx = sampled_indices[-1]
        bucket_slice = slice(bucket_start, bucket_end)

        areas = np.abs(
            (x[a_idx] - avg_x) * (y[bucket_slice] - y[a_idx])
            - (x[a_idx] - x[bucket_slice]) * (avg_y - y[a_idx])
        )

        # 找到面积最大的点索引
        max_local_idx = int(np.argmax(areas))
        sampled_indices.append(bucket_start + max_local_idx)

    sampled_indices.append(n - 1)

    indices = np.array(sampled_indices)
    return x[indices], y[indices]

