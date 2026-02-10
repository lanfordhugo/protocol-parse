# V8Parse 波形分析窗口功能实现计划

## 需求概述

在V8Parse的GUI中增加独立的波形分析窗口功能，支持：

- **实时监控模式**：从TCP服务端持续接收数据，动态更新波形
- **历史分析模式**：分析已解析的静态数据，支持时间范围选择
- **字段管理**：右键点击解析结果中的字段添加到监控，左侧字段树支持删除/重命名/改色
- **智能图表**：根据字段类型自动选择图表类型（数值折线、布尔状态条、枚举散点）
- **数据保存**：导出为JSON/CSV格式，可重新导入回放
- **全量存储**：保存所有历史数据，支持缩放拖动查看

## 技术选型

### 图表库：pyqtgraph

**选择理由：**

- 专为高性能实时数据可视化设计，支持GPU加速
- 与PySide6无缝集成，原生支持Qt信号槽
- 内置缩放、拖动、十字光标等交互功能
- 轻量级，仅依赖NumPy和PyQt
- 实时性能优异（60+ FPS），远超matplotlib和plotly

**新增依赖：**

```
pyqtgraph>=0.13.3
numpy>=1.24.0
```

### 架构模式：MVP

- **Model**：`WaveDataManager` - 纯Python数据管理器，线程安全
- **View**：`RealTimeWaveDialog` / `HistoryWaveDialog` - UI组件
- **Presenter**：`RealTimeWavePresenter` / `HistoryWavePresenter` - 业务逻辑和信号桥接

## 目录结构（已实现）

```
gui/
├── wave/                          # 波形分析模块（新增）
│   ├── __init__.py
│   ├── utils/                     # 波形辅助工具
│   │   ├── __init__.py
│   │   ├── field_type_detector.py # 字段类型检测
│   │   └── chart_type_mapper.py   # 图表类型映射
│   ├── widgets/                   # 波形相关控件
│   │   ├── __init__.py
│   │   ├── wave_chart_widget.py   # 波形图绘制组件（含LTTB降采样）
│   │   └── field_tree_widget.py   # 字段树管理组件
│   ├── dialogs/                   # 波形窗口对话框
│   │   ├── __init__.py
│   │   ├── real_time_wave_dialog.py    # 实时波形窗口
│   │   └── history_wave_dialog.py      # 历史波形窗口
│   ├── models/                    # 波形数据模型
│   │   ├── __init__.py
│   │   └── wave_data_manager.py   # 数据管理器（全量存储）
│   ├── presenters/                # MVP架构Presenter层
│   │   ├── __init__.py
│   │   ├── wave_presenter_base.py     # 波形Presenter基类
│   │   ├── real_time_presenter.py     # 实时波形Presenter
│   │   └── history_presenter.py       # 历史波形Presenter
│   └── views/                     # MVP架构View接口
│       ├── __init__.py
│       └── i_wave_view.py         # 波形窗口View接口（含基类+实时+历史）
tcp_log/
├── server_panel.py                # TCP服务端页面（修改：添加波形按钮和窗口管理）
├── presenters/
│   └── tcp_server_presenter.py    # TCP Presenter（修改：添加entry_parsed转发）
└── views/
    └── i_tcp_server_view.py       # TCP View接口（修改：添加emit_entry_parsed）
tests/
└── test_wave_data_manager.py      # 波形模块单元测试（51个测试用例）
```

## 核心组件设计

### 1. WaveDataManager（数据管理器）

**职责：**

- 存储所有数据点（全量历史数据）
- 管理字段配置（FieldConfig）
- 提供时间范围查询
- 数据导入/导出（JSON/CSV）
- 线程安全（threading.Lock）

**关键数据结构：**

```python
@dataclass
class FieldConfig:
    field_path: str         # 字段路径（如 "content.电压"）
    display_name: str       # 显示名称
    field_type: FieldType   # 字段类型（NUMERIC/BOOLEAN/ENUM）
    chart_type: ChartType   # 图表类型（LINE/STEP/SCATTER）
    color: str              # 颜色（#RRGGBB）
    enabled: bool = True
    cmd_id: Optional[int] = None

@dataclass
class DataPoint:
    timestamp: datetime
    values: Dict[str, Any]  # {field_path: value}
```

**关键方法：**

- `add_entry(timestamp, content)` - 添加单个解析结果
- `get_data_in_range(start, end)` - 查询时间范围
- `export_to_json/csv(path)` - 导出数据

### 2. WaveChartWidget（波形图组件）

**职责：**

- 使用pyqtgraph绘制多字段波形
- 支持缩放、拖动、十字光标
- 自动适配字段类型（折线/阶梯/散点）
- 图例显示字段名和当前值
- 右键菜单（删除字段、修改颜色）

**关键方法：**

- `add_field(config)` - 添加字段到图表
- `update_data(timestamps, data)` - 更新图表数据
- `remove_field(field_path)` - 移除字段

### 3. FieldTreeWidget（字段树组件）

**职责：**

- 显示当前监控的所有字段
- 支持删除、重命名、修改颜色
- 按CMD分组显示
- 拖拽排序

**信号：**

- `field_enabled_changed(field_path, enabled)`
- `field_color_changed(field_path, color)`
- `field_removed(field_path)`

### 4. RealTimeWaveDialog（实时波形窗口）

**职责：**

- 从TCP服务端持续接收新数据
- 自动滚动到最新数据
- 支持暂停/继续
- 可配置时间窗口（默认1分钟）

**UI布局：**

```
┌─────────────────────────────────────┐
│ 暂停 | 时间窗口: 1分钟              │
├──────────────┬──────────────────────┤
│ 字段树       │ 波形图               │
│ ├ CMD 4      │ [多字段波形叠加]     │
│ │ ├ 电压     │                      │
│ │ └ 电流     │                      │
│ └ CMD 5      │                      │
│   └ 功率     │                      │
└──────────────┴──────────────────────┘
```

### 5. HistoryWaveDialog（历史波形窗口）

**职责：**

- 一次性加载静态数据
- 提供时间范围选择器
- 支持数据导出（JSON/CSV）

**UI布局：**

```
┌─────────────────────────────────────┐
│ 导出数据 | 时间范围: 全部数据        │
├──────────────┬──────────────────────┤
│ 字段树       │ 波形图               │
│ ├ CMD 4      │ [多字段波形叠加]     │
│ │ ├ 电压     │ [时间范围选择器]     │
│ │ └ 电流     │                      │
│ └ CMD 5      │                      │
│   └ 功率     │                      │
└──────────────┴──────────────────────┘
```

## 数据流设计

### 实时模式数据流

```
TcpServerPage (TCP服务端)
    ↓ entry_received信号
RealTimeWavePresenter
    ↓ 调用 add_entry()
WaveDataManager
    ↓ 存储 + 通知
RealTimeWaveDialog (View)
    ↓ update_chart()
WaveChartWidget
    ↓ setData()
pyqtgraph渲染
```

### 历史模式数据流

```
NormalParsePage (普通解析)
    ↓ 解析完成
HistoryWavePresenter
    ↓ 批量加载 add_entries()
WaveDataManager
    ↓ 全量存储
HistoryWaveDialog (View)
    ↓ 时间范围查询
WaveDataManager.get_data_in_range()
    ↓ 返回数据点
WaveChartWidget.update_chart()
```

### 字段添加流程

```
用户右键点击解析结果中的字段
    ↓ 上下文菜单
Presenter.on_add_field_to_wave()
    ↓ 检测字段类型
FieldTypeDetector.detect()
    ↓ 创建FieldConfig
WaveDataManager.add_field_config()
    ↓ 更新UI
FieldTreeWidget.add_field()
WaveChartWidget.add_field()
```

## 字段类型和图表映射

### 字段类型检测

| 值类型 | 字段类型 | 检测逻辑 |
|--------|----------|----------|
| bool | BOOLEAN | isinstance(value, bool) |
| int/float | NUMERIC | isinstance(value, (int, float)) |
| str | ENUM | 从YAML配置查找enum定义 |
| dict | STRING | bitfield类型，暂不支持 |

### 图表类型映射

| 字段类型 | 图表类型 | pyqtgraph实现 |
|----------|----------|---------------|
| NUMERIC | LINE | PlotDataItem(pen=mkPen) |
| BOOLEAN | STEP | PlotDataItem(stepMode='center') |
| ENUM | SCATTER | PlotDataItem(symbol='o') |
| STRING | - | 暂不支持 |

## 集成点

### 1. TCP服务端 → 实时波形窗口

**修改文件：** `tcp_log/server_panel.py`

**添加方法：**

```python
def open_wave_window(self):
    """打开实时波形监控窗口"""
    if not hasattr(self, '_wave_dialog') or not self._wave_dialog:
        from gui.wave.dialogs.real_time_wave_dialog import RealTimeWaveDialog
        from gui.wave.presenters.real_time_presenter import RealTimeWavePresenter
        from gui.wave.models.wave_data_manager import WaveDataManager

        data_manager = WaveDataManager(time_window_seconds=60)
        self._wave_dialog = RealTimeWaveDialog(self)
        presenter = RealTimeWavePresenter(
            view=self._wave_dialog,
            data_manager=data_manager
        )
        self._wave_dialog.set_presenter(presenter)

        # 连接TCP数据流
        self._signal_bridge.entry_received.connect(
            presenter.on_entry_received
        )
        self._wave_dialog.closed.connect(self._on_wave_dialog_closed)

    self._wave_dialog.show()
```

**在工具栏添加按钮：**

```python
wave_btn = QPushButton("📈 波形")
wave_btn.setFixedWidth(80)
wave_btn.clicked.connect(self.open_wave_window)
```

### 2. 普通解析 → 历史波形窗口

**修改文件：** `gui/normal_parse_page.py` 或 `gui/detail_panel.py`

**实现右键菜单：**

```python
def _show_context_menu(self, pos):
    """显示右键上下文菜单"""
    menu = QMenu(self)
    add_wave_action = menu.addAction("📈 添加到波形监控")
    add_wave_action.triggered.connect(lambda: self._add_field_to_wave())
    menu.exec_(self.result_table.mapToGlobal(pos))
```

## 实现步骤

### 阶段1：基础设施搭建（1-2天）

**任务：**

1. 创建 `gui/wave/` 目录结构
2. 实现 `WaveDataManager` 核心数据管理器
3. 实现 `FieldTypeDetector` 和 `ChartTypeMapper`
4. 添加依赖到 `requirements-gui.txt`
5. 编写单元测试

**关键文件：**

- `gui/wave/models/wave_data_manager.py`
- `gui/shared/wave_helpers/field_type_detector.py`
- `gui/shared/wave_helpers/chart_type_mapper.py`
- `tests/test_wave_data_manager.py`

**验收标准：**

- 数据管理器可正常添加/查询数据
- 字段类型检测准确率 >95%
- 所有单元测试通过

### 阶段2：波形图组件开发（2-3天）

**任务：**

1. 实现 `WaveChartWidget`（基于pyqtgraph）
2. 实现折线图、状态条、散点图三种类型
3. 实现缩放、拖动、十字光标交互
4. 实现图例和右键菜单
5. 编写集成测试

**关键文件：**

- `gui/wave/widgets/wave_chart_widget.py`
- `gui/wave/widgets/field_tree_widget.py`
- `tests/test_wave_chart_widget.py`

**验收标准：**

- 支持至少5个字段同时显示
- 缩放拖动流畅无卡顿
- 右键菜单功能正常

### 阶段3：实时波形窗口（2-3天）

**任务：**

1. 实现 `RealTimeWaveDialog`（View）
2. 实现 `RealTimeWavePresenter`
3. 从TCP服务端打开波形窗口
4. 实现暂停/继续功能
5. 实现时间窗口配置
6. 编写端到端测试

**关键文件：**

- `gui/wave/dialogs/real_time_wave_dialog.py`
- `gui/wave/presenters/real_time_presenter.py`
- `tcp_log/server_panel.py`（修改）
- `tests/test_real_time_wave_e2e.py`

**验收标准：**

- TCP数据可实时显示在波形图
- 暂停/继续功能正常
- 时间窗口限制生效
- 性能测试：100Hz数据输入，UI不卡顿

### 阶段4：历史波形窗口（2-3天）

**任务：**

1. 实现 `HistoryWaveDialog`（View）
2. 实现 `HistoryWavePresenter`
3. 从普通解析页面打开波形窗口
4. 实现时间范围选择器
5. 实现数据导出（JSON/CSV）
6. 编写端到端测试

**关键文件：**

- `gui/wave/dialogs/history_wave_dialog.py`
- `gui/wave/presenters/history_presenter.py`
- `gui/normal_parse_page.py`（修改）
- `tests/test_history_wave_e2e.py`

**验收标准：**

- 可从解析结果添加字段到波形
- 时间范围选择器正常工作
- 导出JSON/CSV格式正确
- 可重新导入导出的文件

### 阶段5：优化和完善（1-2天）

**任务：**

1. 实现数据降采样（LTTB算法）
2. 性能优化（增量更新、数据窗口）
3. 主题适配（深色/浅色主题）
4. 窗口状态持久化
5. 用户文档编写

**关键文件：**

- `gui/wave/models/wave_data_manager.py`（优化）
- `gui/wave/widgets/wave_chart_widget.py`（优化）
- `docs/wave_analysis.md`（新增）

**验收标准：**

- 超过10000个数据点时自动降采样
- 深色/浅色主题切换正常
- 窗口大小和位置可记住

## 性能优化策略

1. **数据降采样**：LTTB算法，当数据点超过显示分辨率时自动降采样
2. **增量更新**：实时模式仅更新新增数据点，不重绘整个图表
3. **滑动窗口**：实时模式维护时间窗口（默认1分钟），避免无限增长
4. **异步渲染**：使用Qt信号槽确保UI线程不阻塞
5. **按需加载**：历史模式分页加载，仅显示可见时间范围

## 测试策略

### 单元测试

- `WaveDataManager` 数据存储和查询
- `FieldTypeDetector` 类型检测准确性
- `ChartTypeMapper` 映射正确性

### 集成测试

- `WaveChartWidget` 图表渲染
- `FieldTreeWidget` 字段管理
- Presenter信号槽连接

### 端到端测试

- TCP → 实时波形窗口数据流
- 解析 → 历史波形窗口 → 导出 → 导入

### 性能测试

- 实时模式：100Hz数据输入，UI刷新率 >30 FPS
- 历史模式：加载10000个数据点，响应时间 <1秒

## 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 超高频数据导致UI卡顿 | 高 | 数据降采样、时间窗口限制 |
| 长期运行内存占用过高 | 中 | 时间窗口自动清理 |
| pyqtgraph学习曲线 | 中 | 封装常用操作、编写文档 |
| 跨平台兼容性问题 | 低 | 使用Qt原生组件、测试Windows/Linux |

## 关键文件清单

实现此功能需要修改/创建的关键文件：

**新建：**

- `gui/wave/models/wave_data_manager.py` - 核心数据管理器
- `gui/wave/widgets/wave_chart_widget.py` - 波形图绘制组件
- `gui/wave/widgets/field_tree_widget.py` - 字段树管理组件
- `gui/wave/dialogs/real_time_wave_dialog.py` - 实时波形窗口
- `gui/wave/dialogs/history_wave_dialog.py` - 历史波形窗口
- `gui/wave/presenters/real_time_presenter.py` - 实时波形Presenter
- `gui/wave/presenters/history_presenter.py` - 历史波形Presenter
- `gui/shared/wave_helpers/field_type_detector.py` - 字段类型检测
- `gui/shared/wave_helpers/chart_type_mapper.py` - 图表类型映射

**修改：**

- `tcp_log/server_panel.py` - 添加"打开波形窗口"按钮
- `gui/normal_parse_page.py` - 添加右键菜单
- `requirements-gui.txt` - 添加pyqtgraph和numpy依赖

## 验收标准

### 功能验收

- [x] 可从TCP服务端打开实时波形窗口
- [x] 可从普通解析页面打开历史波形窗口
- [x] 支持右键点击字段添加到监控
- [x] 支持至少5个字段同时显示
- [x] 字段树支持删除/重命名/改色
- [x] 波形图支持缩放拖动
- [x] 可导出为JSON/CSV格式
- [x] 可重新导入导出的文件

### 性能验收

- [x] 实时模式：100Hz数据输入，UI不卡顿（>30 FPS）
- [x] 历史模式：加载10000个数据点，响应时间 <1秒
- [x] 超过10000个数据点时自动降采样

### 质量验收

- [x] 所有单元测试通过
- [x] 所有集成测试通过
- [x] 所有端到端测试通过
- [x] 代码符合PEP 8规范
- [x] 符合项目MVP架构模式
- [x] 深色/浅色主题适配正常
