# 波形展示交互优化与性能提升设计

## 概述

本设计解决波形展示模块的三个问题：
1. 横轴缩放交互优化
2. 数据回放自动适应功能
3. 大数据量性能优化

## 一、横轴缩放交互调整

### 问题描述
当前在绘图区域内滚动会触发 X 轴缩放，用户容易误操作。

### 改动文件
`gui/wave/widgets/wave_chart_widget.py`

### 改动点
`_handle_wheel()` 方法（第 424-459 行）

### 当前逻辑
```python
if y_axis_scene_rect.contains(scene_pos):
    # Y 轴区域：缩放 Y 轴
elif x_axis_scene_rect.contains(scene_pos) or vb_scene_rect.contains(scene_pos):
    # X 轴区域或绘图区域：缩放 X 轴
```

### 修改后
```python
if y_axis_scene_rect.contains(scene_pos):
    # Y 轴区域：缩放 Y 轴
elif x_axis_scene_rect.contains(scene_pos):
    # 仅 X 轴区域：缩放 X 轴
# 绘图区域：不触发缩放
```

### 交互效果
| 位置 | 行为 |
|------|------|
| Y 轴标签区域 | 缩放 Y 轴 |
| X 轴标签区域 | 缩放 X 轴 |
| 绘图区域 | 不缩放 |

---

## 二、数据回放自动适应功能

### 问题描述
点击"自动缩放"按钮时，数据回放场景下 X 轴不能展示全部数据。

### 改动文件
`gui/wave/widgets/wave_chart_widget.py`

### 新增方法
`auto_fit_all()` - 自动适配全部数据

### 实现逻辑
```python
def auto_fit_all(self) -> None:
    """自动适配全部数据（X轴展示所有数据，Y轴适配值范围）"""
    # 1. 收集所有曲线的时间戳范围
    x_min, x_max = None, None
    for plot_item in self._plot_items.values():
        x_data = plot_item.xData
        if x_data is not None and len(x_data) > 0:
            if x_min is None or x_data[0] < x_min:
                x_min = x_data[0]
            if x_max is None or x_data[-1] > x_max:
                x_max = x_data[-1]

    # 2. 设置 X 轴范围
    if x_min is not None and x_max is not None:
        self.set_x_range(x_min, x_max)

    # 3. Y 轴自动适配
    self._plot_widget.enableAutoRange(axis="y", enable=True)
    self._plot_widget.getViewBox().autoRange(items=None)
```

### 调用方式
`WaveReplayPage._on_auto_range()` 改为调用 `self._chart.auto_fit_all()`

---

## 三、多级精度性能优化

### 问题描述
几十万数据点的初始加载和滚动缩放都存在性能问题。

### 数据规模
- 典型数据量：几十万个点
- 性能目标：展示延迟 < 1s，滚动缩放响应流畅

### 改动文件
- `gui/wave/widgets/wave_chart_widget.py` - 多级精度渲染逻辑
- `gui/wave/models/wave_data_manager.py` - 可选，预计算多级数据

### 核心设计

#### 1. 精度级别定义
```python
# 多级精度配置（阈值，目标点数）
LOD_LEVELS = [
    (5000, 500),    # Level 0: 数据点 > 5000 时降采样到 500
    (20000, 2000),  # Level 1: 数据点 > 20000 时降采样到 2000
    (100000, 5000), # Level 2: 数据点 > 100000 时降采样到 5000
]
```

#### 2. 根据视口宽度自动选择精度
```python
def _select_lod_level(self, visible_points: int) -> int:
    """根据可见数据点数选择精度级别"""
    for i, (threshold, target) in enumerate(LOD_LEVELS):
        if visible_points <= threshold:
            return i
    return len(LOD_LEVELS)  # 最高精度
```

#### 3. 缓存降采样结果
- 首次渲染时计算并缓存各级精度的降采样数据
- 缩放/平移时复用缓存，仅切换精度级别
- 新数据到达时增量更新缓存

#### 4. 渲染流程
```
数据更新 → 检测数据量 → 计算多级降采样 → 缓存
    ↓
用户缩放 → 计算可见范围 → 选择精度级别 → 使用缓存渲染
```

### 性能目标
- 初始加载 < 1s
- 滚动/缩放响应 < 100ms

### 自动化测试要求
- 性能基准测试：验证初始加载和交互响应时间
- 回归测试：确保优化后数据准确性不受影响

---

## 实现计划

### 阶段 1：交互优化（当前分支）
- [ ] 横轴缩放交互调整
- [ ] 数据回放自动适应功能

### 阶段 2：性能优化（Worktree 专项）
- [ ] 多级精度缓存机制
- [ ] 视口自适应精度切换
- [ ] 性能自动化测试
