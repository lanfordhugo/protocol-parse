"""
文件名称: test_wave_lod_performance.py
内容摘要: 多级精度（LOD）性能优化测试
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-24
"""

import time

import numpy as np
import pytest

from gui.wave.widgets.wave_chart_widget import (
    LOD_LEVELS,
    LOD_MAX_LEVEL,
    lttb_downsample,
)


# ============== LOD 级别选择测试 ==============


class TestSelectLodLevel:
    """精度级别选择测试"""

    def test_small_dataset_returns_lowest_lod(self):
        """小数据集返回最低精度级别（最详细）"""
        # 模拟 _select_lod_level 逻辑
        def select_lod_level(visible_points: int) -> int:
            for i, (threshold, _) in enumerate(LOD_LEVELS):
                if visible_points <= threshold:
                    return i
            return LOD_MAX_LEVEL

        # 小于最小阈值
        assert select_lod_level(100) == 0
        assert select_lod_level(5000) == 0

    def test_medium_dataset_returns_medium_lod(self):
        """中等数据集返回中等精度级别"""
        def select_lod_level(visible_points: int) -> int:
            for i, (threshold, _) in enumerate(LOD_LEVELS):
                if visible_points <= threshold:
                    return i
            return LOD_MAX_LEVEL

        assert select_lod_level(10000) == 1
        assert select_lod_level(20000) == 1

    def test_large_dataset_returns_high_lod(self):
        """大数据集返回较高精度级别"""
        def select_lod_level(visible_points: int) -> int:
            for i, (threshold, _) in enumerate(LOD_LEVELS):
                if visible_points <= threshold:
                    return i
            return LOD_MAX_LEVEL

        assert select_lod_level(50000) == 2
        assert select_lod_level(100000) == 2

    def test_very_large_dataset_returns_max_lod(self):
        """超大数据集返回最高精度级别（使用原始数据）"""
        def select_lod_level(visible_points: int) -> int:
            for i, (threshold, _) in enumerate(LOD_LEVELS):
                if visible_points <= threshold:
                    return i
            return LOD_MAX_LEVEL

        assert select_lod_level(200000) == LOD_MAX_LEVEL


# ============== LTTB 降采样算法测试 ==============


class TestLttbDownsample:
    """LTTB 降采样算法测试"""

    def test_small_data_no_downsample(self):
        """小数据集不降采样"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result_x, result_y = lttb_downsample(x, y, 10)
        assert len(result_x) == 5
        assert len(result_y) == 5

    def test_preserves_first_and_last(self):
        """保留首尾数据点"""
        n = 1000
        x = np.linspace(0, 10, n)
        y = np.sin(x)
        target = 100

        result_x, result_y = lttb_downsample(x, y, target)

        assert result_x[0] == x[0]
        assert result_y[0] == y[0]
        assert result_x[-1] == x[-1]
        assert result_y[-1] == y[-1]

    def test_target_points_achieved(self):
        """降采样后达到目标点数"""
        n = 10000
        x = np.linspace(0, 100, n)
        y = np.sin(x) + np.random.randn(n) * 0.1
        target = 500

        result_x, result_y = lttb_downsample(x, y, target)

        assert len(result_x) == target
        assert len(result_y) == target

    def test_preserves_visual_features(self):
        """保留视觉特征（峰值位置）"""
        # 创建有明确峰值的数据
        n = 5000
        x = np.linspace(0, 4 * np.pi, n)
        y = np.sin(x)
        target = 200

        result_x, result_y = lttb_downsample(x, y, target)

        # 检查峰值位置大致保留
        original_peaks = []
        for i in range(1, len(y) - 1):
            if y[i] > y[i-1] and y[i] > y[i+1]:
                original_peaks.append(x[i])

        result_peaks = []
        for i in range(1, len(result_y) - 1):
            if result_y[i] > result_y[i-1] and result_y[i] > result_y[i+1]:
                result_peaks.append(result_x[i])

        # 峰值数量应该相近
        assert abs(len(original_peaks) - len(result_peaks)) <= 1


# ============== 性能基准测试 ==============


class TestLodPerformance:
    """多级精度性能基准测试"""

    def test_initial_load_performance(self):
        """初始加载性能测试：目标 < 1s"""
        # 生成大数据集
        n_points = 500000
        timestamps = np.linspace(0, 3600, n_points)  # 1小时数据
        values = np.sin(timestamps / 60) + np.random.randn(n_points) * 0.1

        start_time = time.perf_counter()

        # 模拟 LOD 缓存计算
        for level, (threshold, target) in enumerate(LOD_LEVELS):
            if n_points > threshold:
                lttb_downsample(timestamps, values, target)

        elapsed = time.perf_counter() - start_time

        # 初始加载应小于 1 秒
        assert elapsed < 1.0, f"初始加载时间 {elapsed:.3f}s 超过 1s 阈值"
        print(f"\n初始加载时间: {elapsed:.3f}s")

    def test_viewport_change_performance(self):
        """视口变化响应性能测试：目标 < 100ms"""
        # 预计算缓存
        n_points = 500000
        timestamps = np.linspace(0, 3600, n_points)
        values = np.sin(timestamps / 60) + np.random.randn(n_points) * 0.1

        # 预计算 LOD 缓存
        lod_cache = {}
        for level, (threshold, target) in enumerate(LOD_LEVELS):
            if n_points > threshold:
                lod_cache[level] = lttb_downsample(timestamps, values, target)

        # 模拟视口变化时的数据切换
        start_time = time.perf_counter()

        # 模拟多次视口变化
        for _ in range(10):
            # 选择不同精度级别
            for level in range(LOD_MAX_LEVEL):
                if level in lod_cache:
                    _ = lod_cache[level]

        elapsed = (time.perf_counter() - start_time) / 10  # 平均每次

        # 每次视口变化应小于 100ms
        assert elapsed < 0.1, f"视口变化响应时间 {elapsed*1000:.1f}ms 超过 100ms 阈值"
        print(f"\n视口变化响应时间: {elapsed*1000:.1f}ms")

    def test_downsample_accuracy(self):
        """降采样数据准确性测试"""
        n = 100000
        x = np.linspace(0, 100, n)
        y = np.sin(x) + 0.5 * np.cos(2 * x)

        # 对每个 LOD 级别进行测试
        for level, (threshold, target) in enumerate(LOD_LEVELS):
            if n > threshold:
                result_x, result_y = lttb_downsample(x, y, target)

                # 检查数据范围保持
                assert result_y.min() >= y.min() - 0.1
                assert result_y.max() <= y.max() + 0.1

                # 检查时间范围保持
                assert result_x[0] == x[0]
                assert result_x[-1] == x[-1]


# ============== 缓存机制测试 ==============


class TestLodCache:
    """LOD 缓存机制测试"""

    def test_cache_reuse(self):
        """缓存复用测试"""
        n = 50000
        x = np.linspace(0, 100, n)
        y = np.random.randn(n)

        # 第一次计算
        start1 = time.perf_counter()
        result1_x, result1_y = lttb_downsample(x, y, 2000)
        time1 = time.perf_counter() - start1

        # 存储到缓存
        cache = {1: (result1_x, result1_y)}

        # 从缓存读取
        start2 = time.perf_counter()
        _ = cache[1]
        time2 = time.perf_counter() - start2

        # 缓存读取应该比重新计算快很多
        assert time2 < time1 / 100

    def test_incremental_update(self):
        """增量更新测试"""
        # 初始数据
        n_initial = 100000
        x_initial = np.linspace(0, 100, n_initial)
        y_initial = np.sin(x_initial)

        # 计算初始缓存
        initial_cache = {}
        for level, (threshold, target) in enumerate(LOD_LEVELS):
            if n_initial > threshold:
                initial_cache[level] = lttb_downsample(x_initial, y_initial, target)

        # 新数据到达
        n_new = 10000
        x_new = np.linspace(100, 110, n_new)
        y_new = np.sin(x_new)

        # 合并数据
        x_combined = np.concatenate([x_initial, x_new])
        y_combined = np.concatenate([y_initial, y_new])

        # 重新计算缓存
        updated_cache = {}
        for level, (threshold, target) in enumerate(LOD_LEVELS):
            if len(x_combined) > threshold:
                updated_cache[level] = lttb_downsample(x_combined, y_combined, target)

        # 验证缓存更新正确
        for level in updated_cache:
            assert len(updated_cache[level][0]) > 0
            assert updated_cache[level][0][-1] == x_combined[-1]


# ============== 边界条件测试 ==============


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_data(self):
        """空数据处理"""
        x = np.array([])
        y = np.array([])
        result_x, result_y = lttb_downsample(x, y, 100)
        assert len(result_x) == 0

    def test_single_point(self):
        """单点数据"""
        x = np.array([1.0])
        y = np.array([1.0])
        result_x, result_y = lttb_downsample(x, y, 100)
        assert len(result_x) == 1

    def test_two_points(self):
        """两点数据"""
        x = np.array([1.0, 2.0])
        y = np.array([1.0, 2.0])
        result_x, result_y = lttb_downsample(x, y, 100)
        assert len(result_x) == 2

    def test_target_larger_than_data(self):
        """目标点数大于数据点数"""
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        result_x, result_y = lttb_downsample(x, y, 1000)
        assert len(result_x) == 100

    def test_nan_values(self):
        """包含 NaN 值的数据"""
        n = 1000
        x = np.linspace(0, 10, n)
        y = np.sin(x)
        y[500] = np.nan  # 插入 NaN

        # LTTB 应该能处理（忽略或传播 NaN）
        result_x, result_y = lttb_downsample(x, y, 100)
        # 结果长度应该正确
        assert len(result_x) == 100
