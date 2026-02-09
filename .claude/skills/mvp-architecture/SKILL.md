---
name: mvp-architecture
description: |
  Use when designing or refactoring PySide6/PyQt GUI applications with MVP architecture,
  fixing thread crashes with QThread::wait errors, optimizing signal/slot communication,
  or creating testable desktop application architectures.
  Triggers: thread lifecycle management, cross-thread signals, progress callbacks,
  Qt metaclass conflicts, or separating business logic from UI.
---

# MVP Architecture for PySide6/PyQt

## 核心原则

```text
Model（纯 Python）  ←→  Presenter（QObject）  ←→  View（QWidget + Protocol 接口）
     ↑ 无 Qt 依赖          ↑ 信号枢纽              ↑ 只管 UI 渲染
     ↑ 可独立测试           ↑ 管理线程生命周期        ↑ 不含业务逻辑
```

### 三条铁律

1. **Model 零 Qt 依赖** — 纯 Python + typing，可脱离 GUI 独立测试
2. **View 只做渲染** — 通过 `typing.Protocol` 接口与 Presenter 通信，不含业务逻辑
3. **Presenter 是 QObject** — 继承 QObject 才能正确接收跨线程 QueuedConnection 信号

## When to Use

```
需要创建或重构 PySide6/PyQt GUI？
    ↓
是否涉及后台任务、进度显示、多线程？
    ↓
是否需要可测试的架构？
    ↓
使用 MVP 模式
```

**Use when:**
- 从零设计 PySide6/PyQt 桌面应用架构
- 重构现有 GUI 代码到 MVP 模式
- 修复 `QThread::wait: Thread tried to wait on itself` 错误
- 修复 `QThread: Destroyed while thread is still running` 错误
- 优化跨线程信号槽通信
- 解决进度条倒退/卡顿问题
- 修复 Qt 元类冲突（TypeError metaclass conflict）
- 创建可独立测试的业务逻辑层

**Don't use for:**
- 简单的无状态 UI 工具
- 纯命令行应用
- 非 Qt 框架的 GUI（Tkinter, wxPython 等）

## Quick Reference

| 问题 | 修复 |
| ---- | ---- |
| Qt 元类冲突 | View 接口用 `typing.Protocol`，不用 ABC |
| `QThread::wait: Thread tried to wait on itself` | Presenter 继承 `QObject` + `QueuedConnection` |
| `QThread: Destroyed while thread is still running` | cleanup 加 `wait(5000)` + `terminate` 兜底 |
| 进度条倒退/卡顿 | 统一进度信号来源 + 回调链 |
| 进度长时间不动 | 耗时阶段加逐项 `progress_callback` |
| `set_filters` 互相覆盖 | 哨兵值 `_UNSET` 模式 |
| 关闭窗口后程序不退出 | `closeEvent` 调用 `cleanup()` |

## Directory Structure

```text
project/
├── src/                    # Model 层（纯 Python）
│   ├── data_model.py
│   ├── parser.py
│   └── formatter.py
├── gui/
│   ├── views/              # View 层（QWidget）
│   │   ├── interfaces.py   # typing.Protocol 接口定义
│   │   └── main_page.py    # QWidget 实现
│   ├── presenters/         # Presenter 层（QObject）
│   │   └── main_presenter.py
│   └── workers/            # Worker（QObject, moveToThread）
│       └── task_worker.py
├── tests/
│   ├── test_model.py       # 纯 Python 测试
│   └── test_presenter.py   # Mock View 测试
└── main.py
```

## Critical Rules

### Rule 1: View 接口用 typing.Protocol

**禁止** View 接口继承 ABC/QObject — 会导致 Qt 元类冲突。

```python
# ✅ 正确
class IMainPageView(Protocol):
    def set_progress(self, current: int, total: int) -> None: ...
    def log_info(self, msg: str) -> None: ...

# ❌ 错误 — 元类冲突
class IMainPageView(ABC):
    @abstractmethod
    def set_progress(self, current: int, total: int) -> None: ...
```

### Rule 2: Presenter 必须继承 QObject

非 QObject 的 Presenter 无法作为 QueuedConnection 的接收者，
导致跨线程信号回调在 **工作线程** 执行，调用 `QThread.wait()` 时触发
`QThread::wait: Thread tried to wait on itself`。

```python
# ✅ 正确
class MainPresenter(QObject):
    def __init__(self, view: IMainPageView, model: DataModel):
        super().__init__()  # 必须调用
        ...
        worker.finished.connect(
            self._on_finished,
            Qt.ConnectionType.QueuedConnection,  # 关键：确保主线程执行
        )
```

### Rule 3: Worker 用 QObject + moveToThread

**禁止**继承 QThread 重写 run()（除非是简单一次性任务）。

```python
class TaskWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(bool, str)

    def __init__(self, ...):
        super().__init__()
        self._should_stop = False

    @Slot()
    def run(self) -> None:
        """在工作线程执行"""
        ...

    def stop(self) -> None:
        self._should_stop = True

# 使用
thread = QThread()
worker = TaskWorker(...)
worker.moveToThread(thread)
thread.started.connect(worker.run)
thread.start()
```

### Rule 4: 线程清理必须完整

```python
def cleanup(self) -> None:
    """安全关闭线程（窗口 closeEvent 调用）"""
    if self._worker:
        self._worker.stop()           # 1. 请求停止
    if self._thread and self._thread.isRunning():
        self._thread.quit()           # 2. 退出事件循环
        if not self._thread.wait(5000):  # 3. 等待 5 秒
            self._thread.terminate()  # 4. 超时强制终止
            self._thread.wait(2000)   # 5. 等待终止完成

def _on_task_finished(self, success, msg) -> None:
    """任务正常完成后清理（通过 QueuedConnection 在主线程执行）"""
    if self._thread:
        self._thread.quit()
        self._thread.wait()
        self._thread.deleteLater()
        self._thread = None
        self._worker = None
```

### Rule 5: 进度信号单一来源

**禁止**多个层级同时发射进度信号 — 会导致进度倒退和卡顿。

```python
# ✅ 正确：统一由最底层通过回调链上报
# Model 层
def process(self, data, progress_callback=None):
    for i, item in enumerate(data):
        if progress_callback:
            progress_callback(10 + int(i / len(data) * 70), 100)

# Worker 层：只设置回调，不自己发射进度
model.set_progress_callback(lambda c, t: self.progress.emit(c, t))

# ❌ 错误：Worker 和 Model 都发射进度
self.progress.emit(10, 100)    # Worker 发了 10
output = model.run()           # Model 内部也发 10-80
self.progress.emit(90, 100)    # Worker 又发 90 → 进度倒退！
```

### Rule 6: 过滤器设置用哨兵值防覆盖

多次调用 setter 设置不同过滤条件时，未传的参数不能被重置为 None。

```python
_UNSET = object()

def set_filters(self, include=_UNSET, exclude=_UNSET, time_range=_UNSET):
    if include is not self._UNSET:
        self._include = include
    if exclude is not self._UNSET:
        self._exclude = exclude
    if time_range is not self._UNSET:
        self._time_range = time_range
```

### Rule 7: 进度分布要线性

每个耗时阶段都必须有逐项进度更新，避免长时间卡在某个百分比。

```text
0-5%    初始化
5-10%   数据提取（如果耗时，也要逐项报告）
10-80%  数据处理（逐条回调）
80-98%  格式化输出（逐条回调，每处理 1% 数据量更新一次）
98-100% 文件写入
```

控制信号频率避免 UI 刷新过于频繁：

```python
if i % max(1, total // 100) == 0:  # 最多发 100 次
    progress_callback(80 + int(i / total * 18), 100)
```

## Testing Strategy

- **Model 测试**：纯 pytest，无 Qt 依赖，覆盖率目标 85%+
- **Presenter 测试**：Mock View（符合 Protocol 接口），Mock Model，验证交互逻辑
- **集成测试**：pytest-qt，真实 QApplication，验证信号传递

详见 [references/testing-patterns.md](references/testing-patterns.md)。

## Common Mistakes

| 症状 | 根因 | 修复 |
| ---- | ---- | ---- |
| `QThread::wait: Thread tried to wait on itself` | 回调在工作线程执行了 wait() | Presenter 继承 QObject + QueuedConnection |
| `QThread: Destroyed while thread is still running` | cleanup 等待不足 | wait(5000) + terminate 兜底 |
| 进度条倒退/卡顿 | 多层重复发射进度信号 | 统一单一来源 + 回调链 |
| 进度在某百分比长时间不动 | 耗时阶段无逐项更新 | 给每个阶段加 progress_callback |
| Qt 元类冲突 TypeError | View 接口继承了 ABC | 改用 typing.Protocol |
| set_filters 互相覆盖 | 默认参数 None 重置已有值 | 哨兵值 _UNSET 模式 |
| 关闭窗口后程序不退出 | 工作线程未停止 | closeEvent → cleanup() |

## Code Templates

完整代码示例见 [references/code-templates.md](references/code-templates.md)，包含：
- View 接口定义（typing.Protocol）
- View 实现（QWidget）
- Presenter 实现（QObject + QueuedConnection）
- Worker 实现（QObject + moveToThread）
- Model 层设计（纯 Python）
- 主窗口组装（MVP 依赖注入）
- 进度回调链（单一来源设计）
