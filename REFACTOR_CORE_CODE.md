# NormalParsePage MVP 重构核心代码摘要

## 1. 类声明和依赖注入

```python
class NormalParsePage(QWidget, INormalParsePageView):
    """普通解析页面（MVP 架构 - View 层）

    职责：
    - 协调协议面板、详情面板、日志面板的布局和显示
    - 捕获页面级用户事件并转发给 Presenter
    - 响应 Presenter 的指令更新 UI 状态

    TODO: Phase 2 逐步将业务逻辑迁移到 Presenter
    """

    status_changed = Signal(str)

    def __init__(self, presenter: NormalParsePagePresenter, parent=None):
        """初始化页面

        Args:
            presenter: 业务逻辑协调器（依赖注入）
            parent: 父窗口
        """
        super().__init__(parent)
        self._presenter = presenter
        # ... 初始化代码

        # 请求 Presenter 加载协议列表并初始化
        self._presenter.initialize()
```

## 2. 信号转发机制

```python
def _connect_signals(self):
    """连接信号（转发到 Presenter）"""
    # 子面板信号 -> View 信号 -> Presenter
    self.protocol_panel.protocol_selected.connect(
        lambda name: self.protocol_selected.emit(name)
    )
    self.detail_panel.parse_clicked.connect(self._on_parse_clicked)
    self.detail_panel.stop_clicked.connect(
        lambda: self.stop_requested.emit()
    )
    self.detail_panel.validate_clicked.connect(
        lambda: self.validate_requested.emit(
            self.protocol_panel.get_selected_protocol() or ""
        )
    )
    self.detail_panel.open_output_dir_clicked.connect(
        lambda: self.open_output_dir_requested.emit()
    )
    self.detail_panel.select_log_clicked.connect(
        lambda: self.select_log_requested.emit(
            self.protocol_panel.get_selected_protocol() or ""
        )
    )

    # TODO: Phase 2 连接 Presenter 信号到 View
    # 临时：直接连接到处理方法
    self.validate_requested.connect(self._handle_validate_requested)
    self.select_log_requested.connect(self._handle_select_log_requested)
    self.open_output_dir_requested.connect(self._handle_open_output_dir_requested)
```

## 3. 接口方法实现

```python
# === INormalParsePageView 接口实现 ===

def set_parse_state(self, is_parsing: bool) -> None:
    """设置解析状态"""
    self.detail_panel.set_parsing(is_parsing)

def show_error_message(self, title: str, message: str) -> None:
    """显示错误消息对话框"""
    QMessageBox.critical(self, title, message)

def show_info_message(self, title: str, message: str) -> None:
    """显示信息消息对话框"""
    QMessageBox.information(self, title, message)

def show_warning_message(self, title: str, message: str) -> None:
    """显示警告消息对话框"""
    QMessageBox.warning(self, title, message)

def get_protocol_panel_view(self):
    """获取协议面板 View 接口"""
    # TODO: Phase 2 ProtocolPanel 实现接口后返回
    return self.protocol_panel

def get_detail_panel_view(self):
    """获取详情面板 View 接口"""
    # TODO: Phase 2 DetailPanel 实现接口后返回
    return self.detail_panel

def get_log_panel_view(self):
    """获取日志面板 View 接口"""
    # TODO: Phase 2 LogPanel 实现接口后返回
    return self.log_panel
```

## 4. 业务逻辑标记（Phase 2 迁移）

```python
def _on_parse_clicked(self):
    """开始解析（向 Presenter 发送请求）"""
    # TODO: Phase 2 完全迁移到 Presenter
    protocol_name = self.protocol_panel.get_selected_protocol()
    # ... 验证逻辑

    # 发送解析请求到 Presenter
    self.parse_requested.emit(protocol_name, filter_settings)

    # 临时：直接创建工作线程（Phase 2 迁移到 Presenter）
    self._start_parse_worker(protocol_name, info, filter_settings)

def _start_parse_worker(self, protocol_name: str, info: dict, filter_settings: dict):
    """启动解析工作线程（TODO: Phase 2 迁移到 Presenter）"""
    # 创建工作线程
    self._parse_thread = QThread()
    self._parse_worker = ParseWorker(...)
    # ... 线程管理逻辑
```

## 5. 临时处理方法（Phase 2 删除）

```python
# === 临时处理方法（Presenter 信号转发） ===
# TODO: Phase 2 删除这些方法，改为从 Presenter 接收指令

def _handle_validate_requested(self, protocol_name: str):
    """处理验证请求（临时）"""
    # TODO: Phase 2 迁移到 Presenter

def _handle_select_log_requested(self, protocol_name: str):
    """处理选择日志请求（临时）"""
    # TODO: Phase 2 迁移到 Presenter

def _handle_open_output_dir_requested(self):
    """处理打开输出目录请求（临时）"""
    # TODO: Phase 2 迁移到 Presenter
```

## 6. MVP 架构流程

```
用户交互
    ↓
子面板事件 (protocol_selected, parse_clicked, etc.)
    ↓
NormalParsePage._connect_signals()
    ↓
发射 View 信号 (protocol_selected.emit(), parse_requested.emit(), etc.)
    ↓
NormalParsePagePresenter 接收信号
    ↓
Presenter 处理业务逻辑
    ↓
Presenter 调用 View 方法 (set_parse_state(), show_error_message(), etc.)
    ↓
NormalParsePage 更新 UI
```

## 关键设计决策

1. **依赖注入**：Presenter 通过构造函数注入，而非在 View 中创建
2. **信号转发**：子面板信号转发到 Presenter，保持 View 被动
3. **临时方法**：Phase 2 期间保留临时处理方法，逐步迁移到 Presenter
4. **TODO 标记**：明确标记需要迁移的代码，便于 Phase 2 工作

## 验证清单

- [x] 实现 INormalParsePageView 接口
- [x] 所有接口方法已实现
- [x] Presenter 依赖注入
- [x] 信号转发机制建立
- [x] 代码符合规范（509 行 < 600 行）
- [x] 所有公共方法有文档字符串
- [x] Phase 2 待办事项已标记

---
核心代码版本：v2.0.0
重构日期：2026-01-29
