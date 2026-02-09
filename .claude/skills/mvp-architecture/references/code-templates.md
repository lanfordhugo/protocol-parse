# MVP 代码模板

## 目录

- [View 接口定义](#view-接口定义)
- [View 实现](#view-实现)
- [Presenter 实现](#presenter-实现)
- [Worker 实现](#worker-实现)
- [Model 层设计](#model-层设计)
- [主窗口组装](#主窗口组装)
- [进度回调链](#进度回调链)

## View 接口定义

```python
"""gui/views/interfaces.py — View 接口定义（纯 typing.Protocol，无 Qt 依赖）"""
from typing import Protocol, Optional, List, Tuple


class IMainPageView(Protocol):
    """主页面 View 接口"""

    # === UI 更新 ===
    def set_progress(self, current: int, total: int) -> None: ...
    def reset_progress(self) -> None: ...
    def set_parsing_state(self, parsing: bool) -> None: ...

    # === 日志输出 ===
    def log_info(self, message: str) -> None: ...
    def log_success(self, message: str) -> None: ...
    def log_warning(self, message: str) -> None: ...
    def log_error(self, message: str) -> None: ...

    # === 用户交互 ===
    def get_selected_item_name(self) -> Optional[str]: ...
    def get_filter_settings(self) -> dict: ...
    def show_warning(self, title: str, message: str) -> None: ...
    def show_complete_dialog(self, output_path: str) -> bool: ...

    # === 状态信号 ===
    def emit_status_changed(self, message: str) -> None: ...
```

## View 实现

```python
"""gui/views/main_page.py — View 实现（只管 UI 渲染）"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QPushButton
from PySide6.QtCore import Signal


class MainPage(QWidget):
    """主页面 View — 实现 IMainPageView 接口"""

    # 用户操作信号（连接到 Presenter）
    parse_clicked = Signal()
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presenter = None
        self._setup_ui()

    def set_presenter(self, presenter) -> None:
        """注入 Presenter 并绑定信号"""
        self._presenter = presenter
        self.parse_clicked.connect(presenter.on_parse_clicked)

    # === IMainPageView 接口实现 ===

    def set_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress_bar.setValue(int(current / total * 100))

    def reset_progress(self) -> None:
        self._progress_bar.setValue(0)

    def set_parsing_state(self, parsing: bool) -> None:
        self._parse_btn.setEnabled(not parsing)

    def log_info(self, message: str) -> None:
        self._log_panel.append(f"[INFO] {message}")

    # ... 其他接口方法类似

    def emit_status_changed(self, message: str) -> None:
        self.status_changed.emit(message)

    # === 内部方法 ===

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._progress_bar = QProgressBar()
        self._parse_btn = QPushButton("开始解析")
        self._parse_btn.clicked.connect(self.parse_clicked)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._parse_btn)

    def cleanup(self) -> None:
        """窗口关闭时调用"""
        if self._presenter:
            self._presenter.cleanup()
```

## Presenter 实现

```python
"""gui/presenters/main_presenter.py — Presenter（继承 QObject）"""
from typing import Optional
from PySide6.QtCore import QObject, QThread, Qt, QSettings

from gui.views.interfaces import IMainPageView
from gui.workers.task_worker import TaskWorker
from src.data_model import DataModel


class MainPresenter(QObject):
    """
    主页面 Presenter

    职责：
    - 响应 View 的用户交互事件
    - 调用 Model 层获取/处理数据
    - 通过 View 接口更新 UI 展示
    - 管理工作线程的生命周期

    关键设计：
    - 继承 QObject，确保 QueuedConnection 的 slot 在主线程执行
    - 持有 View 接口引用（typing.Protocol），不依赖具体 QWidget
    """

    def __init__(
        self,
        view: IMainPageView,
        model: DataModel,
        settings: Optional[QSettings] = None,
    ):
        super().__init__()  # 必须调用 QObject.__init__
        self._view = view
        self._model = model
        self._settings = settings
        self._thread: Optional[QThread] = None
        self._worker: Optional[TaskWorker] = None

    # ============== 用户操作响应 ==============

    def on_parse_clicked(self) -> None:
        """用户点击「开始」"""
        # 1. 从 View 获取用户输入
        item_name = self._view.get_selected_item_name()
        if not item_name:
            self._view.show_warning("提示", "请先选择项目")
            return

        filter_settings = self._view.get_filter_settings()

        # 2. 创建工作线程（QObject + moveToThread 模式）
        self._thread = QThread()
        self._worker = TaskWorker(item_name, filter_settings)
        self._worker.moveToThread(self._thread)

        # 3. 连接信号
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._view.set_progress)
        self._worker.log_info.connect(self._view.log_info)
        self._worker.finished.connect(
            self._on_task_finished,
            Qt.ConnectionType.QueuedConnection,  # 关键！确保主线程执行
        )

        # 4. 更新 UI 状态
        self._view.set_parsing_state(True)
        self._view.reset_progress()

        # 5. 启动线程
        self._thread.start()

    # ============== 线程回调 ==============

    def _on_task_finished(self, success: bool, message: str) -> None:
        """任务完成回调（通过 QueuedConnection 在主线程执行）"""
        # 安全清理线程
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None
            self._worker = None

        # 更新 UI
        self._view.set_parsing_state(False)
        if success:
            self._view.log_success(message)
        else:
            self._view.log_error(message)

    # ============== 资源管理 ==============

    def cleanup(self) -> None:
        """清理资源（窗口关闭时调用）

        步骤：
        1. 请求工作线程停止
        2. 通知线程事件循环退出
        3. 等待线程自然结束（最多5秒）
        4. 超时则强制终止
        """
        if self._worker:
            self._worker.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(5000):
                self._thread.terminate()
                self._thread.wait(2000)
```

## Worker 实现

```python
"""gui/workers/task_worker.py — Worker（QObject，在工作线程执行）"""
from PySide6.QtCore import QObject, Signal, Slot


class TaskWorker(QObject):
    """工作线程执行体

    关键设计：
    - 继承 QObject（非 QThread），通过 moveToThread 移动到工作线程
    - 信号作为唯一的跨线程通信方式
    - _should_stop 标志支持优雅停止
    - 进度信号只做转发，不自己生成进度值（避免与 Model 层冲突）
    """

    # 信号定义
    started = Signal()
    progress = Signal(int, int)      # (current, total)
    log_info = Signal(str)
    log_success = Signal(str)
    log_warning = Signal(str)
    log_error = Signal(str)
    finished = Signal(bool, str)     # (success, message)

    def __init__(self, item_name: str, filter_settings: dict):
        super().__init__()
        self.item_name = item_name
        self.filter_settings = filter_settings
        self._should_stop = False

    @Slot()
    def run(self) -> None:
        """在工作线程执行（由 QThread.started 触发）"""
        try:
            self.started.emit()

            # 创建 Model 层对象
            from src.processor import Processor
            processor = Processor(self.item_name)

            # 设置进度回调（单一来源：由 Model 层控制进度值）
            processor.set_progress_callback(
                lambda current, total: self.progress.emit(current, total)
            )

            # 应用过滤条件
            self._apply_filters(processor)

            # 如果已请求停止
            if self._should_stop:
                processor.set_should_stop(True)

            # 执行处理
            result = processor.run()

            if self._should_stop:
                self.finished.emit(False, "已停止")
                return

            if result:
                self.log_success.emit(f"完成: {result}")
                self.finished.emit(True, "处理完成")
            else:
                self.log_warning.emit("完成但无输出")
                self.finished.emit(True, "完成（无数据）")

        except Exception as e:
            if self._should_stop:
                self.finished.emit(False, "已停止")
            else:
                self.log_error.emit(f"失败: {e}")
                self.finished.emit(False, str(e))

    def stop(self) -> None:
        """请求停止（线程安全，可从主线程调用）"""
        self._should_stop = True

    def _apply_filters(self, processor) -> None:
        """应用过滤条件到处理器"""
        include = self.filter_settings.get('include_items')
        exclude = self.filter_settings.get('exclude_items')
        time_range = self.filter_settings.get('time_range')

        # 分别调用，避免互相覆盖（Model 层使用哨兵值模式）
        if include:
            processor.set_include_items(include)
        if exclude:
            processor.set_exclude_items(exclude)
        if time_range:
            processor.set_time_range(*time_range)
```

## Model 层设计

```python
"""src/processor.py — Model 层（零 Qt 依赖）"""
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict


class Processor:
    """数据处理器（纯 Python）

    关键设计：
    - 无任何 Qt 导入
    - progress_callback 由外部注入
    - 过滤器使用哨兵值模式防止互相覆盖
    """

    _UNSET = object()

    def __init__(self, config_name: str):
        self._config_name = config_name
        self._progress_callback: Optional[Callable] = None
        self._should_stop = False
        # 过滤条件（初始为 None 表示不过滤）
        self._include_items = None
        self._exclude_items = None
        self._time_range = None

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        self._progress_callback = callback

    def set_should_stop(self, value: bool) -> None:
        self._should_stop = value

    def set_filters(
        self,
        include_items=_UNSET,
        exclude_items=_UNSET,
        time_range=_UNSET,
    ) -> None:
        """设置过滤条件（哨兵值模式：只更新显式传入的参数）"""
        if include_items is not self._UNSET:
            self._include_items = include_items
        if exclude_items is not self._UNSET:
            self._exclude_items = exclude_items
        if time_range is not self._UNSET:
            self._time_range = time_range

    def set_include_items(self, items: List[int]) -> None:
        self.set_filters(include_items=items)

    def set_exclude_items(self, items: List[int]) -> None:
        self.set_filters(exclude_items=items)

    def set_time_range(self, start, end) -> None:
        self.set_filters(time_range=(start, end))

    def _emit_progress(self, current: int, total: int) -> None:
        """安全发射进度"""
        if self._progress_callback:
            try:
                self._progress_callback(current, total)
            except Exception:
                pass

    def run(self) -> Optional[str]:
        """运行处理流程

        进度分布：
        - 0-5%   初始化
        - 5-10%  数据提取
        - 10-80% 数据处理（逐条）
        - 80-98% 格式化输出（逐条）
        - 98-100% 文件写入
        """
        self._emit_progress(5, 100)
        data = self._extract_data()
        if not data:
            return None

        self._emit_progress(10, 100)

        # 处理阶段（10-80%，逐条更新）
        results = self._process_data(data)
        if self._should_stop:
            return None

        # 格式化阶段（80-98%，逐条更新）
        output = self._format_results(results)

        self._emit_progress(100, 100)
        return output

    def _process_data(self, data: List[Dict]) -> List[Dict]:
        total = len(data)
        results = []
        for i, item in enumerate(data):
            if self._should_stop:
                break
            # 逐条进度（10-80%）
            if i % max(1, total // 100) == 0:
                self._emit_progress(10 + int(i / total * 70), 100)
            results.append(self._process_item(item))
        return results

    def _format_results(self, results: List[Dict]) -> Optional[str]:
        total = len(results)
        for i, item in enumerate(results):
            if self._should_stop:
                break
            # 逐条进度（80-98%）
            if i % max(1, total // 100) == 0:
                self._emit_progress(80 + int(i / total * 18), 100)
            self._format_item(item)
        self._emit_progress(98, 100)
        return self._write_output()
```

## 主窗口组装

```python
"""gui/main_window.py — 主窗口（组装 MVP）"""
from PySide6.QtWidgets import QMainWindow

from src.data_model import DataModel
from gui.views.main_page import MainPage
from gui.presenters.main_presenter import MainPresenter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. 创建 Model（纯 Python，无 Qt 依赖）
        self._model = DataModel()

        # 2. 创建 View（QWidget）
        self._page = MainPage(self)

        # 3. 创建 Presenter（QObject，连接 Model 和 View）
        self._presenter = MainPresenter(
            view=self._page,
            model=self._model,
        )

        # 4. 注入 Presenter 到 View
        self._page.set_presenter(self._presenter)

        self.setCentralWidget(self._page)

    def closeEvent(self, event) -> None:
        """窗口关闭时清理所有资源"""
        self._page.cleanup()
        super().closeEvent(event)
```

## 进度回调链

```
Worker.run()
  └─ processor.set_progress_callback(lambda c, t: self.progress.emit(c, t))
       └─ Processor.run()
            ├─ _emit_progress(5, 100)          # 初始化
            ├─ _emit_progress(10, 100)         # 提取完成
            ├─ _process_data()
            │    └─ _emit_progress(10-80)      # 逐条处理
            ├─ _format_results()
            │    └─ _emit_progress(80-98)      # 逐条格式化
            └─ _emit_progress(100, 100)        # 完成

信号传递链：
Processor._progress_callback → Worker.progress.emit → View.set_progress
（所有进度值由 Processor 统一管理，Worker 只做信号转发）
```
