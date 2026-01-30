# GUI MVP 重构设计文档

**文档版本**: v1.0.0
**创建日期**: 2026-01-29
**作者**: lanford
**状态**: 设计阶段

---

## 一、重构目标

### 1.1 核心目标

将当前 GUI 代码从**面向对象风格**重构为 **MVP (Model-View-Presenter) 架构风格**，实现：

- ✅ **视图与业务逻辑分离**：View 只负责 UI 显示和用户输入捕获
- ✅ **可测试性提升**：Presenter 可独立进行单元测试
- ✅ **可维护性增强**：职责清晰，降低耦合度
- ✅ **扩展性改善**：便于添加新功能或修改 UI

### 1.2 重构范围

**Phase 1 - View 层重构**（当前阶段）：
- 定义 View 接口抽象
- 重构现有 View 组件实现接口
- 保持向后兼容，不破坏现有功能

**Phase 2 - Presenter 层实现**（下一阶段）：
- 提取业务逻辑到 Presenter
- 实现 View 与 Model 的协调
- 添加单元测试

**Phase 3 - Model 层优化**（未来阶段）：
- 优化数据模型设计
- 实现数据持久化
- 添加数据验证

---

## 二、当前架构分析

### 2.1 现有 GUI 模块结构

```
gui/
├── unified_main_window.py      # 统一主窗口 (220行)
├── normal_parse_page.py        # 普通解析页面 (400+行)
├── protocol_panel.py           # 协议列表面板 (150行)
├── detail_panel.py             # 详情面板 (400+行)
├── log_panel.py                # 日志面板 (150行)
├── sidebar.py                  # 侧边栏导航 (100行)
├── themes.py                   # 主题管理 (200行)
├── widgets/                    # 自定义控件目录
│   ├── searchable_list.py      # 可搜索列表 (200行)
│   ├── datetime_picker.py      # 时间选择器 (150行)
│   ├── multi_select_combo.py   # 多选下拉框 (120行)
│   ├── log_time_scanner.py     # 日志时间扫描器 (180行)
│   └── time_range_slider.py    # 时间范围滑块 (150行)
├── workers/                    # 工作线程目录
│   ├── parse_worker.py         # 解析工作线程 (150行)
│   └── validate_worker.py      # 验证工作线程 (100行)
└── shared/                     # 共享模块目录
    ├── app_helpers.py          # 应用辅助工具 (100行)
    ├── time_utils.py           # 时间工具 (80行)
    └── window_manager.py       # 窗口管理混入 (150行)
```

**总代码量**: 约 5500 行（包含注释和空行）

### 2.2 当前架构问题

#### 问题 1：业务逻辑与 UI 耦合

**示例**（`normal_parse_page.py`）：
```python
def _on_protocol_selected(self, protocol_name: str):
    """协议选择变化"""
    info = self.protocol_panel.get_protocol_info(protocol_name)
    # ❌ 业务逻辑：加载配置、验证、统计
    from src.yaml_config import YamlConfigLoader
    loader = YamlConfigLoader()
    config = loader.load_protocol_config(info['config_path'])
    # ... 复杂的配置处理逻辑
```

**问题**：
- View 直接调用业务逻辑（加载配置、验证协议）
- 难以对业务逻辑进行单元测试
- UI 代码与业务代码混杂

#### 问题 2：状态管理分散

**示例**：
```python
# normal_parse_page.py
self._parse_thread: Optional[QThread] = None
self._parse_worker: Optional[ParseWorker] = None
self._validate_thread: Optional[QThread] = None
self._validate_worker: Optional[ValidateWorker] = None
self._settings = None  # 由主窗口传入
self._app_dir = get_app_dir()
self._configs_dir = self._app_dir / "configs"
self._output_dir = self._app_dir / "parsed_log"
```

**问题**：
- 状态分散在多个属性中
- 缺乏统一的状态管理
- 难以追踪状态变化

#### 问题 3：测试困难

**现状**：
- 无法独立测试 UI 组件
- 无法 mock 业务逻辑
- 集成测试成本高

---

## 三、MVP 架构设计

### 3.1 架构分层

```
┌─────────────────────────────────────────────┐
│                View Layer                   │
│  (UI 组件，只负责显示和用户输入捕获)          │
│                                             │
│  - IUnifiedMainWindowView                  │
│  - INormalParsePageView                    │
│  - IProtocolPanelView                      │
│  - IDetailPanelView                        │
│  - ILogPanelView                           │
└─────────────────┬───────────────────────────┘
                  │ Signal/Slot (Qt 信号机制)
                  │ 用户事件 → Presenter
                  │ Presenter → View 更新
┌─────────────────▼───────────────────────────┐
│             Presenter Layer                 │
│  (业务逻辑协调器，连接 View 和 Model)         │
│                                             │
│  - UnifiedMainWindowPresenter              │
│  - NormalParsePagePresenter                │
│  - ProtocolPanelPresenter                  │
│  - DetailPanelPresenter                    │
│  - LogPanelPresenter                       │
└─────────────────┬───────────────────────────┘
                  │ 方法调用
                  │ Presenter → Model 数据访问
┌─────────────────▼───────────────────────────┐
│               Model Layer                   │
│  (数据模型和业务逻辑)                        │
│                                             │
│  - ProtocolConfigModel                     │
│  - ParseTaskModel                          │
│  - FilterSettingsModel                     │
│  - AppSettingsModel                        │
└─────────────────────────────────────────────┘
```

### 3.2 职责划分

#### View 层职责

✅ **应该做的**：
- UI 组件的创建和布局
- 捕获用户输入（点击、输入、选择等）
- 通过 Signal 向 Presenter 发送用户事件
- 提供 Presenter 调用的更新方法（如 `update_protocol_info()`）
- 显示数据（不处理数据）

❌ **不应该做的**：
- 业务逻辑处理
- 数据验证和转换
- 直接访问 Model 层
- 状态管理（由 Presenter 负责）

#### Presenter 层职责

✅ **应该做的**：
- 响应 View 的用户事件
- 调用 Model 层处理业务逻辑
- 验证数据有效性
- 状态管理
- 通过 View 接口更新 UI

❌ **不应该做的**：
- 直接操作 Qt 组件
- 包含 UI 相关代码
- 知道具体的 View 实现

#### Model 层职责

✅ **应该做的**：
- 数据结构定义
- 业务逻辑实现
- 数据验证
- 数据持久化

❌ **不应该做的**：
- 知道 View 或 Presenter 的存在
- 包含 UI 相关代码

---

## 四、View 层接口设计

### 4.1 接口定义原则

1. **面向接口编程**：View 通过接口与 Presenter 交互
2. **最小接口原则**：只定义必要的方法
3. **单一职责原则**：每个 View 接口只关注自己的显示逻辑
4. **Qt 信号机制**：使用 Signal 传递用户事件

### 4.2 核心 View 接口

#### IProtocolPanelView

```python
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from gui.widgets.searchable_list import ProtocolItem


class IProtocolPanelView(QObject):
    """协议列表面板接口"""

    # === 信号：用户事件 ===
    protocol_selected = Signal(str)  # 用户选择协议

    # === Presenter 调用的方法 ===
    def load_protocols(self, protocols: List[ProtocolItem]) -> None:
        """加载协议列表"""
        raise NotImplementedError

    def set_selected_protocol(self, protocol_name: str) -> None:
        """设置选中的协议"""
        raise NotImplementedError

    def update_protocol_status(
        self,
        protocol_name: str,
        config_valid: bool,
        log_exists: bool,
        log_size: int
    ) -> None:
        """更新协议状态显示"""
        raise NotImplementedError

    def get_selected_protocol(self) -> Optional[str]:
        """获取当前选中的协议名称"""
        raise NotImplementedError
```

#### IDetailPanelView

```python
from typing import List, Tuple, Optional
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class IDetailPanelView(QObject):
    """详情面板接口"""

    # === 信号：用户事件 ===
    parse_clicked = Signal()                      # 点击解析按钮
    stop_clicked = Signal()                       # 点击停止按钮
    validate_clicked = Signal()                   # 点击验证按钮
    open_output_dir_clicked = Signal()            # 点击打开输出目录
    select_log_clicked = Signal()                 # 点击选择日志文件
    time_range_changed = Signal(datetime, datetime)  # 时间范围变化
    command_filter_changed = Signal(List[str])    # 命令过滤变化

    # === Presenter 调用的方法 ===
    def update_protocol_info(
        self,
        name: str,
        config_path: str,
        config_valid: bool,
        log_path: str,
        log_exists: bool,
        log_size: int,
        cmd_count: int,
        enum_count: int,
        type_count: int,
        commands: List[Tuple[str, str]]
    ) -> None:
        """更新协议详情显示"""
        raise NotImplementedError

    def set_parse_button_enabled(self, enabled: bool) -> None:
        """启用/禁用解析按钮"""
        raise NotImplementedError

    def set_stop_button_enabled(self, enabled: bool) -> None:
        """启用/禁用停止按钮"""
        raise NotImplementedError

    def set_progress(self, current: int, total: int) -> None:
        """设置进度"""
        raise NotImplementedError

    def get_filter_settings(self) -> Dict[str, Any]:
        """获取当前过滤设置"""
        raise NotImplementedError

    def set_log_path(self, path: str) -> None:
        """设置日志文件路径"""
        raise NotImplementedError
```

#### ILogPanelView

```python
from PySide6.QtCore import QObject, Signal


class ILogPanelView(QObject):
    """日志面板接口"""

    # === 信号：用户事件 ===
    clear_clicked = Signal()  # 点击清空按钮

    # === Presenter 调用的方法 ===
    def log_info(self, message: str) -> None:
        """输出信息日志"""
        raise NotImplementedError

    def log_success(self, message: str) -> None:
        """输出成功日志"""
        raise NotImplementedError

    def log_warning(self, message: str) -> None:
        """输出警告日志"""
        raise NotImplementedError

    def log_error(self, message: str) -> None:
        """输出错误日志"""
        raise NotImplementedError

    def clear_log(self) -> None:
        """清空日志"""
        raise NotImplementedError

    def set_progress(self, value: int, total: int) -> None:
        """设置进度条（0-100）"""
        raise NotImplementedError

    def reset_progress(self) -> None:
        """重置进度条"""
        raise NotImplementedError
```

#### INormalParsePageView

```python
from typing import Dict, Any
from PySide6.QtCore import QObject, Signal


class INormalParsePageView(QObject):
    """普通解析页面接口"""

    # === 信号：用户事件 ===
    protocol_selected = Signal(str)              # 协议选择变化
    parse_requested = Signal(str, Dict[str, Any])  # 请求解析
    stop_requested = Signal()                    # 请求停止
    validate_requested = Signal(str)             # 请求验证

    # === Presenter 调用的方法 ===
    def set_parse_state(self, is_parsing: bool) -> None:
        """设置解析状态"""
        raise NotImplementedError

    def show_error_message(self, title: str, message: str) -> None:
        """显示错误消息"""
        raise NotImplementedError

    def show_info_message(self, title: str, message: str) -> None:
        """显示信息消息"""
        raise NotImplementedError
```

### 4.3 接口继承关系

```
QObject
    ├── IProtocolPanelView
    ├── IDetailPanelView
    ├── ILogPanelView
    └── INormalParsePageView
        └── 组合上述三个 View 接口
```

---

## 五、重构实现方案

### 5.1 Phase 1：View 层重构

#### 步骤 1：创建 View 接口模块

创建 `gui/views/` 目录：
```
gui/views/
├── __init__.py
├── i_protocol_panel_view.py
├── i_detail_panel_view.py
├── i_log_panel_view.py
└── i_normal_parse_page_view.py
```

#### 步骤 2：重构现有 View 组件

**重构原则**：
- 保持现有类名不变（向后兼容）
- 让现有类实现对应的 View 接口
- 移除业务逻辑代码（标记为 TODO）
- 只保留 UI 相关代码

**示例**（`ProtocolPanel`）：

**重构前**：
```python
class ProtocolPanel(QWidget):
    def load_protocols(self, configs_dir: Path):
        # ❌ 业务逻辑：扫描目录、验证配置
        for protocol_dir in sorted(configs_dir.iterdir()):
            # ... 复杂的目录遍历逻辑
```

**重构后**：
```python
class ProtocolPanel(QWidget, IProtocolPanelView):
    def load_protocols(self, protocols: List[ProtocolItem]):
        # ✅ 只负责 UI 显示
        self._protocols.clear()
        self.protocol_list.set_protocols(protocols)
```

#### 步骤 3：创建 Presenter 占位符

创建 `gui/presenters/` 目录：
```
gui/presenters/
├── __init__.py
├── protocol_panel_presenter.py  # 占位符
├── detail_panel_presenter.py    # 占位符
├── log_panel_presenter.py       # 占位符
└── normal_parse_page_presenter.py  # 占位符
```

**Presenter 占位符示例**：
```python
class ProtocolPanelPresenter:
    """协议面板 Presenter（占位符）"""

    def __init__(self, view: IProtocolPanelView):
        self._view = view

    def load_protocols(self) -> None:
        """加载协议列表（待实现）"""
        # TODO: Phase 2 实现业务逻辑
        pass
```

### 5.2 Phase 2：Presenter 层实现

（在 Phase 1 完成后进行）

#### 步骤 1：实现业务逻辑

**示例**（`ProtocolPanelPresenter`）：
```python
class ProtocolPanelPresenter:
    def __init__(
        self,
        view: IProtocolPanelView,
        model: ProtocolConfigModel
    ):
        self._view = view
        self._model = model

    def load_protocols(self) -> None:
        """加载协议列表"""
        # 业务逻辑：扫描目录、验证配置
        protocols = self._model.scan_protocols()

        # 调用 View 更新 UI
        self._view.load_protocols(protocols)

    def on_protocol_selected(self, protocol_name: str) -> None:
        """处理协议选择事件"""
        # 业务逻辑：加载配置、验证、统计
        info = self._model.get_protocol_info(protocol_name)
        # 通知其他 Presenter 更新
```

#### 步骤 2：连接 View 和 Presenter

```python
class NormalParsePage(QWidget, INormalParsePageView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建 View 组件
        self.protocol_panel = ProtocolPanel()
        self.detail_panel = DetailPanel()
        self.log_panel = LogPanel()

        # TODO: Phase 2 创建 Presenter
        # self._presenter = NormalParsePagePresenter(
        #     view=self,
        #     model=ParseTaskModel()
        # )

    def _on_protocol_selected(self, protocol_name: str):
        """协议选择变化（由 Presenter 处理）"""
        # TODO: Phase 2 移除，由 Presenter 处理
        self.protocol_selected.emit(protocol_name)
```

### 5.3 Phase 3：Model 层优化

（在 Phase 2 完成后进行）

创建 `gui/models/` 目录：
```
gui/models/
├── __init__.py
├── protocol_config_model.py
├── parse_task_model.py
├── filter_settings_model.py
└── app_settings_model.py
```

---

## 六、重构实施计划

### 6.1 任务分解

#### Phase 1：View 层重构（预计 3-5 天）

**任务列表**：

- [ ] **任务 1.1**：创建 View 接口模块结构
  - 创建 `gui/views/` 目录
  - 创建接口文件模板
  - 编写 `__init__.py` 导出接口

- [ ] **任务 1.2**：定义核心 View 接口
  - 实现 `IProtocolPanelView`
  - 实现 `IDetailPanelView`
  - 实现 `ILogPanelView`
  - 实现 `INormalParsePageView`

- [ ] **任务 1.3**：重构 `ProtocolPanel`
  - 实现 `IProtocolPanelView` 接口
  - 移除业务逻辑（标记 TODO）
  - 保持 UI 显示功能

- [ ] **任务 1.4**：重构 `DetailPanel`
  - 实现 `IDetailPanelView` 接口
  - 移除业务逻辑（标记 TODO）
  - 保持 UI 显示功能

- [ ] **任务 1.5**：重构 `LogPanel`
  - 实现 `ILogPanelView` 接口
  - 移除业务逻辑（标记 TODO）
  - 保持 UI 显示功能

- [ ] **任务 1.6**：重构 `NormalParsePage`
  - 实现 `INormalParsePageView` 接口
  - 移除业务逻辑（标记 TODO）
  - 保持 UI 显示功能

- [ ] **任务 1.7**：创建 Presenter 占位符
  - 创建 `gui/presenters/` 目录
  - 创建 Presenter 占位符类
  - 添加 TODO 注释标记待实现功能

- [ ] **任务 1.8**：验证重构结果
  - 运行 GUI 应用确保功能正常
  - 检查所有 TODO 标记
  - 更新文档

#### Phase 2：Presenter 层实现（预计 5-7 天）

**任务列表**：

- [ ] **任务 2.1**：创建 Model 层基础
  - 创建 `gui/models/` 目录
  - 定义数据模型类
  - 实现基础业务逻辑

- [ ] **任务 2.2**：实现 `ProtocolPanelPresenter`
  - 实现协议加载逻辑
  - 实现协议选择处理
  - 连接 Model 和 View

- [ ] **任务 2.3**：实现 `DetailPanelPresenter`
  - 实现详情显示逻辑
  - 实现过滤设置处理
  - 连接 Model 和 View

- [ ] **任务 2.4**：实现 `LogPanelPresenter`
  - 实现日志输出逻辑
  - 实现进度更新逻辑
  - 连接 Model 和 View

- [ ] **任务 2.5**：实现 `NormalParsePagePresenter`
  - 协调各个子 Presenter
  - 实现解析流程控制
  - 连接 Model 和 View

- [ ] **任务 2.6**：添加单元测试
  - 为 Presenter 添加测试
  - 为 Model 添加测试
  - 确保测试覆盖率 > 85%

- [ ] **任务 2.7**：验证重构结果
  - 运行 GUI 应用确保功能正常
  - 运行所有测试
  - 性能测试

#### Phase 3：Model 层优化（预计 3-5 天）

**任务列表**：

- [ ] **任务 3.1**：优化数据模型
  - 完善数据结构
  - 添加数据验证
  - 实现数据持久化

- [ ] **任务 3.2**：性能优化
  - 优化数据加载
  - 优化内存使用
  - 性能测试

- [ ] **任务 3.3**：文档完善
  - 更新 API 文档
  - 更新使用手册
  - 添加架构说明

### 6.2 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 破坏现有功能 | 高 | 中 | 分阶段重构，每阶段验证功能 |
| 接口设计不当 | 高 | 低 | 充分讨论，参考成熟框架 |
| 性能下降 | 中 | 低 | 性能测试，优化热点 |
| 开发周期延长 | 中 | 中 | 任务拆分，每日同步 |

---

## 七、测试策略

### 7.1 View 层测试

**测试重点**：
- UI 组件是否正确创建
- Signal 是否正确发送
- 接口方法是否正确实现

**测试工具**：
- `pytest-qt`（Qt 测试框架）
- `unittest.mock`（Mock 对象）

**示例**：
```python
def test_protocol_panel_load_protocols(qtbot):
    """测试协议面板加载协议列表"""
    view = ProtocolPanel()
    qtbot.addWidget(view)

    protocols = [
        ProtocolItem(name="v8", config_valid=True, log_exists=False, log_size=0)
    ]

    view.load_protocols(protocols)

    assert view.get_selected_protocol() is None
```

### 7.2 Presenter 层测试

**测试重点**：
- 业务逻辑正确性
- 状态管理正确性
- 与 Model 和 View 的交互

**测试工具**：
- `pytest`
- `unittest.mock`（Mock View 和 Model）

**示例**：
```python
def test_protocol_presenter_load_protocols():
    """测试协议 Presenter 加载协议列表"""
    # Arrange
    mock_view = Mock(spec=IProtocolPanelView)
    mock_model = Mock(spec=ProtocolConfigModel)
    mock_model.scan_protocols.return_value = [
        ProtocolItem(name="v8", config_valid=True, log_exists=False, log_size=0)
    ]

    presenter = ProtocolPanelPresenter(mock_view, mock_model)

    # Act
    presenter.load_protocols()

    # Assert
    mock_model.scan_protocols.assert_called_once()
    mock_view.load_protocols.assert_called_once()
```

### 7.3 Model 层测试

**测试重点**：
- 数据结构正确性
- 业务逻辑正确性
- 数据持久化

**测试工具**：
- `pytest`
- `tmpdir`（临时目录）

---

## 八、向后兼容性

### 8.1 兼容性原则

1. **渐进式重构**：分阶段进行，每阶段保持功能可用
2. **接口稳定**：View 接口一旦定义，尽量不修改
3. **保留旧代码**：暂时保留旧的业务逻辑代码（标记为 TODO）
4. **测试覆盖**：每阶段完成后运行现有测试

### 8.2 兼容性措施

#### 措施 1：保留旧接口

```python
class ProtocolPanel(QWidget, IProtocolPanelView):
    def load_protocols_from_dir(self, configs_dir: Path):
        """旧接口：保持兼容性"""
        # TODO: Phase 2 后移除
        protocols = self._scan_protocols_from_dir(configs_dir)
        self.load_protocols(protocols)
```

#### 措施 2：双模式运行

```python
class NormalParsePage(QWidget, INormalParsePageView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 检查是否使用 MVP 模式
        self._use_mvp = os.getenv('USE_MVP', 'false').lower() == 'true'

        if self._use_mvp:
            # 使用 Presenter
            self._presenter = NormalParsePagePresenter(self)
        else:
            # 使用旧模式
            pass
```

---

## 九、成功标准

### 9.1 代码质量

- [ ] 所有 View 组件实现对应接口
- [ ] View 代码不包含业务逻辑
- [ ] 代码行数减少 > 20%
- [ ] 测试覆盖率 > 85%

### 9.2 功能完整性

- [ ] 所有现有功能正常工作
- [ ] 无新增 bug
- [ ] 性能无明显下降

### 9.3 可维护性

- [ ] 职责清晰，易于理解
- [ ] 便于添加新功能
- [ ] 便于修复 bug

---

## 十、参考资料

### 10.1 MVP 架构参考

- [Martin Fowler - Passive View](https://martinfowler.com/eaaDev/PassiveScreen.html)
- [Martin Fowler - Supervising Controller](https://martinfowler.com/eaaDev/SupervisingController.html)
- [PySide6 官方文档](https://doc.qt.io/qtforpython/)

### 10.2 项目参考

- 当前 GUI 代码：`gui/` 目录
- 测试代码：`tests/` 目录
- 编码规范：`.claude/rules/python-coding-style.md`

---

**文档版本历史**：

| 版本 | 日期 | 作者 | 变更说明 |
|-----|------|------|---------|
| v1.0.0 | 2026-01-29 | lanford | 初始版本 |
