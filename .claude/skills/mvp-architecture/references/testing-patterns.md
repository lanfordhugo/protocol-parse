# MVP 测试策略

## 目录

- [测试分层](#测试分层)
- [Model 层测试](#model-层测试)
- [Presenter 层测试](#presenter-层测试)
- [集成测试](#集成测试)
- [pytest 配置](#pytest-配置)

## 测试分层

```
tests/
├── test_model.py              # Model 层：纯 pytest，无 Qt
├── test_presenter.py          # Presenter 层：Mock View + Mock Model
├── test_worker.py             # Worker：可选，复杂逻辑才测
└── test_integration.py        # 集成：pytest-qt，真实 QApplication
```

| 层 | 依赖 | Mock 对象 | 覆盖率目标 |
| --- | --- | --- | --- |
| Model | pytest | 无（或 Mock 文件 I/O） | 85%+ |
| Presenter | pytest + unittest.mock | View（Protocol）+ Model | 80%+ |
| 集成 | pytest-qt | 无 | 关键路径 |

## Model 层测试

Model 零 Qt 依赖，直接用 pytest 测试。

```python
"""tests/test_processor.py"""
import pytest
from unittest.mock import MagicMock
from src.processor import Processor


class TestProcessor:
    """Processor 单元测试"""

    def setup_method(self):
        self.processor = Processor("test_config")

    def test_set_filters_independent(self):
        """验证：多次 set_filters 不互相覆盖"""
        self.processor.set_filters(include_items=[1, 2])
        self.processor.set_filters(time_range=("2024-01-01", "2024-12-31"))
        # include_items 不应被重置
        assert self.processor._include_items == [1, 2]
        assert self.processor._time_range == ("2024-01-01", "2024-12-31")

    def test_set_filters_explicit_none_resets(self):
        """验证：显式传 None 可以清除过滤条件"""
        self.processor.set_filters(include_items=[1, 2])
        self.processor.set_filters(include_items=None)
        assert self.processor._include_items is None

    def test_progress_callback_called(self):
        """验证：进度回调被正确调用"""
        progress_values = []
        self.processor.set_progress_callback(
            lambda c, t: progress_values.append((c, t))
        )
        self.processor._emit_progress(50, 100)
        assert progress_values == [(50, 100)]

    def test_progress_callback_exception_ignored(self):
        """验证：回调异常不中断处理"""
        self.processor.set_progress_callback(
            lambda c, t: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        # 不应抛出异常
        self.processor._emit_progress(50, 100)

    def test_should_stop_flag(self):
        """验证：停止标志生效"""
        self.processor.set_should_stop(True)
        assert self.processor._should_stop is True
```

## Presenter 层测试

Presenter 依赖 View 接口（typing.Protocol），用 Mock 对象替代。

```python
"""tests/test_main_presenter.py"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from gui.presenters.main_presenter import MainPresenter


@pytest.fixture
def mock_view():
    """创建 Mock View（符合 IMainPageView Protocol）"""
    view = MagicMock()
    view.get_selected_item_name.return_value = "test_item"
    view.get_filter_settings.return_value = {
        'include_items': None,
        'exclude_items': None,
        'time_range': None,
    }
    return view


@pytest.fixture
def mock_model():
    return MagicMock()


@pytest.fixture
def presenter(mock_view, mock_model):
    return MainPresenter(view=mock_view, model=mock_model)


class TestMainPresenter:
    """MainPresenter 单元测试"""

    def test_parse_clicked_no_selection(self, presenter, mock_view):
        """未选择项目时应弹出警告"""
        mock_view.get_selected_item_name.return_value = None
        presenter.on_parse_clicked()
        mock_view.show_warning.assert_called_once()

    def test_parse_clicked_starts_thread(self, presenter, mock_view):
        """正常情况应启动工作线程"""
        with patch('gui.presenters.main_presenter.QThread') as MockThread, \
             patch('gui.presenters.main_presenter.TaskWorker') as MockWorker:
            mock_thread = MagicMock()
            MockThread.return_value = mock_thread
            mock_worker = MagicMock()
            MockWorker.return_value = mock_worker

            presenter.on_parse_clicked()

            # 验证线程启动
            mock_worker.moveToThread.assert_called_once_with(mock_thread)
            mock_thread.start.assert_called_once()
            # 验证 UI 状态更新
            mock_view.set_parsing_state.assert_called_with(True)
            mock_view.reset_progress.assert_called_once()

    def test_on_task_finished_success(self, presenter, mock_view):
        """任务成功完成后应更新 UI 并清理线程"""
        presenter._thread = MagicMock()
        presenter._worker = MagicMock()

        presenter._on_task_finished(True, "完成")

        mock_view.set_parsing_state.assert_called_with(False)
        mock_view.log_success.assert_called_with("完成")
        assert presenter._thread is None
        assert presenter._worker is None

    def test_on_task_finished_failure(self, presenter, mock_view):
        """任务失败应显示错误"""
        presenter._thread = MagicMock()
        presenter._worker = MagicMock()

        presenter._on_task_finished(False, "出错了")

        mock_view.log_error.assert_called_with("出错了")

    def test_cleanup_no_thread(self, presenter):
        """无线程时 cleanup 不报错"""
        presenter.cleanup()  # 不应抛异常

    def test_cleanup_running_thread(self, presenter):
        """运行中线程应被正确停止"""
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True
        mock_thread.wait.return_value = True  # 5秒内结束
        mock_worker = MagicMock()

        presenter._thread = mock_thread
        presenter._worker = mock_worker

        presenter.cleanup()

        mock_worker.stop.assert_called_once()
        mock_thread.quit.assert_called_once()
        mock_thread.wait.assert_called_once_with(5000)
        # wait 返回 True，不应调用 terminate
        mock_thread.terminate.assert_not_called()

    def test_cleanup_thread_timeout_triggers_terminate(self, presenter):
        """线程超时应触发 terminate"""
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True
        mock_thread.wait.side_effect = [False, True]  # 第一次超时，terminate后成功
        mock_worker = MagicMock()

        presenter._thread = mock_thread
        presenter._worker = mock_worker

        presenter.cleanup()

        mock_thread.terminate.assert_called_once()
        assert mock_thread.wait.call_count == 2
```

## 集成测试

使用 pytest-qt 进行信号传递验证。

```python
"""tests/test_integration.py"""
import pytest
from PySide6.QtCore import Qt


@pytest.fixture
def app(qtbot):
    """创建完整的 MVP 应用"""
    from gui.main_window import MainWindow
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


class TestIntegration:
    """集成测试 — 验证信号传递链"""

    def test_window_opens(self, app):
        """窗口正常打开"""
        assert app.isVisible()

    def test_close_event_cleanup(self, app, qtbot):
        """关闭窗口触发 cleanup"""
        app.close()
        # 不应崩溃或报错
```

## pytest 配置

```ini
# pytest.ini
[pytest]
testpaths = tests
markers =
    unit: 单元测试（纯 Python，无 Qt）
    gui: GUI 测试（需要 QApplication）
    integration: 集成测试
qt_api = pyside6
asyncio_mode = strict
```

```python
# conftest.py
import pytest


@pytest.fixture(autouse=True)
def _reset_singletons():
    """每个测试后重置单例状态"""
    yield
    # 清理全局状态
```

## 测试检查清单

- [ ] Model 层所有公共方法有测试
- [ ] set_filters 哨兵值模式有独立测试
- [ ] 进度回调异常不中断处理有测试
- [ ] Presenter 的每个用户操作方法有测试
- [ ] cleanup 正常/超时两种路径有测试
- [ ] 线程完成后状态清理有验证
- [ ] 关闭窗口不崩溃有集成测试
