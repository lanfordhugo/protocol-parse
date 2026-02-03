# GUI 重构阶段1：基础架构层重构计划

**文档版本**: v1.0
**创建日期**: 2025-02-02
**预计工期**: 6.5天
**风险等级**: 中等

## 一、阶段目标

建立分层架构，解决最严重的耦合问题，实现 UI 与业务逻辑分离。

### 核心目标
1. ✅ 创建服务层（Service Layer）封装业务逻辑
2. ✅ 引入 ViewModel 模式分离 UI 逻辑
3. ✅ 统一配置管理，消除硬编码
4. ✅ 保持向后兼容，确保现有功能正常

### 验证标准
- [ ] 所有现有功能正常工作（协议选择、日志解析、结果显示）
- [ ] 服务层单元测试覆盖率 >80%
- [ ] UI 代码不再直接导入 `YamlConfigLoader` 等核心模块
- [ ] PyInstaller 打包成功且应用正常运行
- [ ] 所有硬编码常量迁移到 `gui/config.py`

---

## 二、架构设计

### 2.1 分层架构图

```
┌─────────────────────────────────────────────┐
│         Presentation Layer (UI)              │
│  ┌─────────────────────────────────────┐    │
│  │   NormalParsePage (现有组件)          │    │
│  │   - 仅处理 UI 事件和用户交互          │    │
│  └──────────────┬──────────────────────┘    │
└─────────────────┼──────────────────────────┘
                  │ Signal/Slot
                  ▼
┌─────────────────────────────────────────────┐
│           ViewModel Layer (新增)             │
│  ┌─────────────────────────────────────┐    │
│  │   NormalParsePageViewModel           │    │
│  │   - UI 状态管理                        │    │
│  │   - 用户交互处理                        │    │
│  │   - 服务调用封装                        │    │
│  └──────────────┬──────────────────────┘    │
└─────────────────┼──────────────────────────┘
                  │ 方法调用
                  ▼
┌─────────────────────────────────────────────┐
│           Service Layer (新增)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │Protocol  │ │  Parse   │ │  Config  │    │
│  │ Service  │ │ Service  │ │ Service  │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘    │
└───────┼────────────┼────────────┼───────────┘
        │            │            │
        └────────────┴────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│            Core Layer (现有)                 │
│  YamlConfigLoader, YamlUnifiedProtocol      │
└─────────────────────────────────────────────┘
```

### 2.2 目录结构变化

```
gui/
├── services/                    # 新增：服务层
│   ├── __init__.py
│   ├── protocol_service.py      # 协议管理服务
│   ├── parse_service.py         # 解析服务
│   └── config_service.py        # 配置服务
├── viewmodels/                  # 新增：ViewModel层
│   ├── __init__.py
│   ├── base_vm.py              # ViewModel基类
│   └── normal_parse_vm.py      # 普通解析页ViewModel
├── config.py                    # 新增：统一配置管理
├── pages/                       # 现有：页面组件（修改）
│   ├── normal_parse_page.py     # 修改：注入ViewModel
│   └── tcp_log/
│       └── server_panel.py      # 暂不修改
├── widgets/                     # 现有：自定义控件
├── workers/                     # 现有：工作线程
└── unified_main_window.py       # 现有：主窗口（可选修改）

tests/gui/                       # 新增：GUI测试
├── conftest.py
├── services/
│   ├── test_protocol_service.py
│   ├── test_parse_service.py
│   └── test_config_service.py
└── viewmodels/
    └── test_normal_parse_vm.py
```

---

## 三、核心服务设计

### 3.1 ConfigService（配置服务）

**文件位置**: `gui/services/config_service.py`

**职责**：
- 统一管理应用配置（路径、UI参数、性能参数）
- 提供配置读写接口
- 持久化配置到文件

**接口设计**：
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:
    """应用配置对象"""
    # 路径配置
    project_root: Path
    configs_dir: Path
    input_logs_dir: Path
    parsed_log_dir: Path

    # UI 配置
    window_min_width: int = 1000
    window_min_height: int = 700
    sidebar_width: int = 250
    detail_panel_min_width: int = 400
    log_panel_min_height: int = 150

    # 性能配置
    max_worker_threads: int = 2
    parse_timeout_seconds: int = 300

    # 主题配置
    theme_name: str = "dark"

class ConfigService:
    """配置管理服务"""

    def __init__(self, project_root: Path = None):
        """初始化配置服务"""

    @property
    def config(self) -> AppConfig:
        """获取配置对象"""

    def get(self, key: str) -> Any:
        """获取配置项"""

    def set(self, key: str, value: Any):
        """设置配置项"""

    def save(self):
        """保存配置到文件"""
```

**依赖关系**：
- 无依赖（最底层服务）

### 3.2 ProtocolService（协议管理服务）

**文件位置**: `gui/services/protocol_service.py`

**职责**：
- 协议自动发现（扫描 `configs/` 和 `input_logs/`）
- 协议配置加载
- 协议验证
- 协议元数据管理

**接口设计**：
```python
from PySide6.QtCore import QObject, Signal
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ProtocolMetadata:
    """协议元数据"""
    name: str
    display_name: str
    config_path: Path
    log_path: Optional[Path]
    is_valid: bool
    version: str = ""
    description: str = ""

class ProtocolService(QObject):
    """协议管理服务"""

    # 信号定义
    protocols_loaded = Signal(list)  # List[ProtocolMetadata]
    protocol_validated = Signal(bool, str)  # success, message

    def __init__(self, config_service: ConfigService):
        """初始化协议服务"""

    def discover_protocols(self) -> List[ProtocolMetadata]:
        """自动发现所有可用协议"""

    def load_protocol(self, name: str) -> Optional[YamlUnifiedProtocol]:
        """加载指定协议"""

    def validate_protocol(self, name: str) -> tuple[bool, str]:
        """验证协议配置"""

    def get_protocol_metadata(self, name: str) -> Optional[ProtocolMetadata]:
        """获取协议元数据"""

    def get_all_protocols(self) -> List[ProtocolMetadata]:
        """获取所有协议列表"""
```

**依赖关系**：
- 依赖 `ConfigService` 获取路径配置
- 调用核心模块 `YamlConfigLoader`、`YamlUnifiedProtocol`

### 3.3 ParseService（解析服务）

**文件位置**: `gui/services/parse_service.py`

**职责**：
- 日志解析任务管理
- 解析进度跟踪
- 解析结果处理
- 任务取消支持

**接口设计**：
```python
from PySide6.QtCore import QObject, Signal
from typing import Optional
from pathlib import Path

class ParseService(QObject):
    """日志解析服务"""

    # 信号定义
    parse_started = Signal(str)  # protocol_name
    parse_progress = Signal(int, str)  # progress, message
    parse_finished = Signal(bool, str, Optional[Path])  # success, message, output_file
    parse_error = Signal(str)  # error_message
    parse_cancelled = Signal()

    def __init__(self, protocol_service: ProtocolService):
        """初始化解析服务"""

    def parse_log(
        self,
        protocol_name: str,
        log_content: str,
        output_callback: Optional[callable] = None
    ) -> Optional[Path]:
        """解析日志内容"""

    def cancel_parse(self):
        """取消当前解析任务"""

    def get_last_result(self) -> Optional[ParseResult]:
        """获取最后一次解析结果"""
```

**依赖关系**：
- 依赖 `ProtocolService` 获取协议实例
- 调用核心模块 `YamlUnifiedProtocol` 执行解析
- 使用 `gui.workers.ParseWorker` 执行异步任务

---

## 四、ViewModel 设计

### 4.1 NormalParsePageViewModel

**文件位置**: `gui/viewmodels/normal_parse_vm.py`

**职责**：
- 管理 UI 状态（选中的协议、日志文件、解析状态）
- 处理用户交互（选择协议、选择文件、开始解析）
- 调用服务层方法
- 转换服务信号为 UI 信号

**接口设计**：
```python
from PySide6.QtCore import QObject, Signal, Property
from typing import Optional
from pathlib import Path

class NormalParsePageViewModel(QObject):
    """普通解析页面的 ViewModel"""

    # UI 状态信号
    protocol_list_changed = Signal()
    selected_protocol_changed = Signal()
    log_file_changed = Signal()
    is_parsing_changed = Signal()
    parse_progress_changed = Signal(int, str)

    # 操作结果信号
    parse_finished = Signal(bool, str)
    validation_finished = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(
        self,
        protocol_service: ProtocolService,
        parse_service: ParseService
    ):
        """初始化 ViewModel"""

    # === 协议管理 ===
    def load_protocols(self) -> List[ProtocolMetadata]:
        """加载协议列表"""

    def select_protocol(self, name: str):
        """选择协议"""

    def validate_selected_protocol(self) -> tuple[bool, str]:
        """验证选中的协议"""

    # === 文件管理 ===
    def select_log_file(self, file_path: Path):
        """选择日志文件"""

    def get_log_file_content(self) -> str:
        """获取日志文件内容"""

    # === 解析管理 ===
    def start_parse(self):
        """开始解析"""

    def stop_parse(self):
        """停止解析"""

    def can_parse(self) -> bool:
        """检查是否可以开始解析"""

    # === 状态查询 ===
    @Property(bool, notify=is_parsing_changed)
    def isParsing(self) -> bool:
        """是否正在解析"""

    @Property(str, notify=selected_protocol_changed)
    def selectedProtocol(self) -> str:
        """当前选中的协议"""

    @Property(str, notify=log_file_changed)
    def logFile(self) -> str:
        """当前日志文件路径"""
```

**依赖关系**：
- 依赖 `ProtocolService` 执行协议操作
- 依赖 `ParseService` 执行解析操作
- 连接服务信号到 ViewModel 信号

---

## 五、统一配置管理

### 5.1 gui/config.py

**文件位置**: `gui/config.py`

**职责**：
- 集中定义所有硬编码常量
- 提供路径计算方法
- 定义主题颜色和样式

**内容设计**：
```python
"""
GUI 统一配置模块
集中管理所有硬编码常量和配置项
"""

from pathlib import Path

# ============== 路径常量 ==============
def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent

PROJECT_ROOT = get_project_root()
CONFIGS_DIR = PROJECT_ROOT / "configs"
INPUT_LOGS_DIR = PROJECT_ROOT / "input_logs"
PARSED_LOG_DIR = PROJECT_ROOT / "parsed_log"
TCP_OUTPUT_DIR = PROJECT_ROOT / "tcp_output"

# ============== UI 尺寸常量 ==============
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700
SIDEBAR_WIDTH = 180
PROTOCOL_PANEL_MIN_WIDTH = 250
PROTOCOL_PANEL_MAX_WIDTH = 350
DETAIL_PANEL_MIN_WIDTH = 400
LOG_PANEL_MIN_HEIGHT = 150

# ============== 颜色主题 ==============
class ThemeColors:
    """主题颜色定义"""
    PRIMARY = "#2196F3"
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    INFO = "#2196F3"

    # 亮色主题
    BACKGROUND_LIGHT = "#FFFFFF"
    TEXT_PRIMARY_LIGHT = "#212121"
    TEXT_SECONDARY_LIGHT = "#757575"

    # 暗色主题
    BACKGROUND_DARK = "#2E2E2E"
    TEXT_PRIMARY_DARK = "#E0E0E0"
    TEXT_SECONDARY_DARK = "#B0B0B0"

# ============== 性能配置 ==============
MAX_PARSE_THREADS = 2
PARSE_TIMEOUT_SECONDS = 300
MAX_LOG_CACHE_SIZE = 1000

# ============== 文件过滤 ==============
LOG_FILE_FILTER = "日志文件 (*.log);;所有文件 (*.*)"
CONFIG_FILE_FILTER = "配置文件 (*.yaml);;所有文件 (*.*)"

# ============== 默认值 ==============
DEFAULT_PROTOCOL = "sinexcel"
DEFAULT_THEME = "dark"
```

---

## 六、迁移策略

### 6.1 渐进式迁移原则

**关键原则**：
1. **保留旧代码**：作为 fallback，确保新代码失败时可回退
2. **并行开发**：新代码独立开发，不破坏现有功能
3. **逐步替换**：优先使用新代码，失败时使用旧代码
4. **持续验证**：每步都验证功能正常

### 6.2 具体迁移步骤

#### 步骤1：创建服务层（0.5天）
```bash
# 1.1 创建目录
mkdir -p gui/services
touch gui/services/__init__.py

# 1.2 创建服务文件（实现框架，不修改现有代码）
# - config_service.py
# - protocol_service.py
# - parse_service.py

# 1.3 添加单元测试验证服务层正确性
mkdir -p tests/gui/services
touch tests/gui/conftest.py
```

#### 步骤2：创建 ViewModel（1天）
```bash
# 2.1 创建目录
mkdir -p gui/viewmodels
touch gui/viewmodels/__init__.py

# 2.2 创建 ViewModel 文件
# - base_vm.py（ViewModel基类）
# - normal_parse_vm.py（普通解析页ViewModel）

# 2.3 添加 ViewModel 测试
```

#### 步骤3：渐进式迁移 NormalParsePage（2天）

**迁移策略**：
```python
# normal_parse_page.py 修改示例
class NormalParsePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # === 旧代码保留 ===
        self._app_dir = get_app_dir()
        self._configs_dir = self._app_dir / "configs"
        # ... 其他旧代码

        # === 新代码注入 ===
        try:
            # 初始化服务层
            from gui.services import ServiceContainer
            container = ServiceContainer()
            self._vm = NormalParsePageViewModel(
                protocol_service=container.get('protocol'),
                parse_service=container.get('parse')
            )

            # 连接 ViewModel 信号
            self._vm.protocol_list_changed.connect(self._on_protocol_list_loaded)
            self._vm.parse_finished.connect(self._on_parse_finished)

            # 使用 ViewModel 加载协议
            self._vm.load_protocols()
            self._use_new_code = True
        except Exception as e:
            # 新代码失败，使用旧代码
            self.log_panel.log_warning(f"ViewModel初始化失败，使用旧代码: {e}")
            self._load_protocols_legacy()
            self._use_new_code = False

    def _load_protocols_legacy(self):
        """旧代码保留作为 fallback"""
        # 原有的 _load_protocols() 逻辑
        pass
```

**关键点**：
- 使用 try-except 包裹新代码
- 新代码失败时自动回退到旧代码
- 通过标志位 `self._use_new_code` 跟踪使用哪套代码
- 保持所有信号接口不变

#### 步骤4：验证和优化（1天）

**验证清单**：
- [ ] 启动应用，检查协议列表是否正确加载
- [ ] 选择协议，检查详情是否正确显示
- [ ] 选择日志文件，检查解析是否正常
- [ ] 检查验证功能是否正常
- [ ] 检查停止按钮是否正常
- [ ] 运行所有单元测试

**优化点**：
- 移除已确认不再使用的旧代码
- 添加更多错误处理
- 优化性能（减少重复加载等）

---

## 七、测试策略

### 7.1 单元测试

#### 服务层测试
```python
# tests/gui/services/test_protocol_service.py
import pytest
from gui.services.protocol_service import ProtocolService
from gui.services.config_service import ConfigService

class TestProtocolService:
    """协议服务测试"""

    def test_discover_protocols(self, tmp_path):
        """测试协议发现"""
        # 创建临时协议
        config_svc = ConfigService(project_root=tmp_path)
        proto_svc = ProtocolService(config_svc)

        # 验证协议发现
        protocols = proto_svc.discover_protocols()
        assert isinstance(protocols, list)

    def test_load_protocol(self, proto_service):
        """测试协议加载"""
        # 加载存在的协议
        protocol = proto_service.load_protocol("v8")
        assert protocol is not None

    def test_load_invalid_protocol(self, proto_service):
        """测试加载无效协议"""
        protocol = proto_service.load_protocol("nonexistent")
        assert protocol is None
```

#### ViewModel 测试
```python
# tests/gui/viewmodels/test_normal_parse_vm.py
import pytest
from gui.viewmodels.normal_parse_vm import NormalParsePageViewModel
from gui.services.protocol_service import ProtocolService
from gui.services.parse_service import ParseService

class TestNormalParsePageViewModel:
    """ViewModel 测试"""

    @pytest.fixture
    def vm(self, protocol_service, parse_service):
        """创建 ViewModel 实例"""
        return NormalParsePageViewModel(
            protocol_service=protocol_service,
            parse_service=parse_service
        )

    def test_load_protocols(self, vm):
        """测试加载协议"""
        vm.load_protocols()
        # 验证信号触发
        # 验证协议列表

    def test_select_protocol(self, vm):
        """测试选择协议"""
        vm.select_protocol("v8")
        assert vm.selectedProtocol == "v8"

    def test_can_parse(self, vm):
        """测试解析前置条件"""
        # 未选择协议和文件
        assert vm.can_parse() == False

        # 选择协议和文件后
        vm.select_protocol("v8")
        vm.select_log_file(Path("test.log"))
        assert vm.can_parse() == True
```

### 7.2 集成测试

```python
# tests/gui/integration/test_normal_parse_flow.py
import pytest
from PySide6.QtWidgets import QApplication
from gui.pages.normal_parse_page import NormalParsePage

class TestNormalParseFlow:
    """普通解析流程集成测试"""

    @pytest.fixture
    def page(self, qapp):
        """创建页面实例"""
        return NormalParsePage()

    def test_complete_parse_flow(self, page):
        """测试完整解析流程"""
        # 1. 选择协议
        page.protocol_panel.select_item("v8")
        assert page.detail_panel.protocol_name == "v8"

        # 2. 选择日志文件
        log_file = Path("input_logs/v8.log")
        page._on_select_log_clicked(log_file)

        # 3. 开始解析
        page.detail_panel.start_parse()
        # 验证解析状态
        # 验证结果显示
```

### 7.3 覆盖率目标

- 服务层测试覆盖率：>80%
- ViewModel 测试覆盖率：>80%
- 关键流程集成测试：100%

---

## 八、风险评估

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 服务层接口设计不合理 | 中 | 中 | 1. 先写测试验证接口<br>2. 保留旧代码 fallback |
| ViewModel 性能开销 | 低 | 低 | 1. 使用属性缓存<br>2. 避免过度信号触发 |
| 配置迁移遗漏 | 高 | 中 | 1. 创建配置检查工具<br>2. 运行时验证完整性 |
| 信号连接错误 | 中 | 中 | 1. 使用 SignalManager<br>2. 添加连接检查工具 |

### 8.2 进度风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 旧代码理解不充分 | 中 | 低 | 提前阅读现有代码，做好注释 |
| 测试编写耗时超预期 | 低 | 中 | 优先测试关键路径，细节逐步补充 |
| 打包验证失败 | 高 | 低 | 阶段末提前打包测试，留出修复时间 |

---

## 九、验收标准

### 9.1 功能验收
- [ ] 所有现有功能正常工作
  - [ ] 协议列表正确加载和显示
  - [ ] 协议选择和详情显示正常
  - [ ] 日志文件选择和拖拽支持
  - [ ] 解析功能正常（开始/停止/结果显示）
  - [ ] 验证功能正常
  - [ ] TCP 服务端页面正常（未修改但需验证）

### 9.2 架构验收
- [ ] 服务层无 UI 依赖（不导入 PySide6）
- [ ] UI 代码不直接导入核心模块（YamlConfigLoader 等）
- [ ] 所有硬编码常量迁移到 `gui/config.py`
- [ ] ViewModel 完全分离 UI 和业务逻辑
- [ ] 依赖注入正确实现

### 9.3 质量验收
- [ ] 服务层单元测试覆盖率 >80%
- [ ] ViewModel 测试覆盖率 >80%
- [ ] 所有单元测试通过
- [ ] 关键流程集成测试通过
- [ ] PyInstaller 打包成功
- [ ] 打包后应用正常启动和运行

### 9.4 性能验收
- [ ] 启动时间无明显增加（<5% 误差）
- [ ] 协议加载速度无明显降低
- [ ] 解析性能无明显降低

---

## 十、后续步骤

完成阶段1后，进入**阶段2：组件重构层**，主要工作：
1. 拆分 TCP 服务端页面（796行 → 3-4个文件）
2. 统一信号管理
3. 统一工作线程管理模式

详见：[gui-refactor-phase2-plan.md](./gui-refactor-phase2-plan.md)

---

**文档结束**
