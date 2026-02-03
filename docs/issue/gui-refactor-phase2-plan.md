# GUI 重构阶段2：组件重构层重构计划

**文档版本**: v1.0
**创建日期**: 2025-02-02
**预计工期**: 5天
**前置依赖**: 阶段1完成
**风险等级**: 中等

## 一、阶段目标

重构大文件，统一信号和线程管理，提高代码可维护性。

### 核心目标
1. ✅ 拆分 TCP 服务端页面（796行 → 3-4个文件）
2. ✅ 统一信号管理，防止信号泄漏
3. ✅ 统一工作线程管理模式
4. ✅ 减少代码重复，提取通用模式

### 验证标准
- [ ] 单文件代码量 <600行
- [ ] 所有信号正确连接和断开（无泄漏）
- [ ] 工作线程正常创建和销毁
- [ ] 圈复杂度 <10（关键函数）
- [ ] 代码重复率 <5%
- [ ] 所有现有功能正常工作
- [ ] 内存泄漏检查通过（长时间运行稳定性）

---

## 二、拆分 TCP 服务端页面

### 2.1 现状分析

**文件位置**: `tcp_log/server_panel.py`
**当前行数**: 796行
**主要问题**:
- 职责过多（UI + 服务控制 + 日志显示 + 客户端管理）
- 单一文件过大，难以维护
- 代码重复（日志处理、状态管理等）

### 2.2 拆分方案

#### 新目录结构
```
tcp_log/
├── __init__.py
├── server_panel.py              # 主面板容器（~150行）
├── server_control.py            # 服务控制（启动/停止/状态）（~200行）
├── log_table_widget.py          # 日志表格控件（~250行）
├── client_manager.py            # 客户端管理（~150行）
└── server_settings.py           # 设置对话框（~100行）
```

#### 职责划分

**1. server_panel.py：主容器**
```python
"""
文件名称: server_panel.py
职责: TCP 服务端主面板容器，组合子组件
行数目标: ~150行
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from .server_control import ServerControl
from .log_table_widget import LogTableWidget
from .client_manager import ClientManager

class TcpServerPage(QWidget):
    """TCP 服务端主面板"""

    # 信号：状态变化（通知主窗口更新状态栏）
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建子组件
        self._control = ServerControl(self)
        self._log_table = LogTableWidget(self)
        self._client_mgr = ClientManager(self)

        # 组装 UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """组装 UI 布局"""
        layout = QVBoxLayout(self)

        # 顶部：服务控制区域
        layout.addWidget(self._control)

        # 中部：分割布局（日志表格 + 客户端列表）
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._log_table)
        splitter.addWidget(self._client_mgr)
        layout.addWidget(splitter)

    def _connect_signals(self):
        """连接子组件信号"""
        self._control.status_changed.connect(self._on_status_changed)
        self._log_table.log_selected.connect(self._on_log_selected)
```

**2. server_control.py：服务控制**
```python
"""
文件名称: server_control.py
职责: TCP 服务器启动、停止、状态管理
行数目标: ~200行
"""
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget, QGroupBox, QPushButton

class ServerControl(QObject):
    """TCP 服务器控制组件"""

    # 信号定义
    started = Signal(int)  # port
    stopped = Signal()
    status_changed = Signal(str)  # 状态消息
    error_occurred = Signal(str)  # 错误消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = None
        self._is_running = False
        self._setup_ui()

    def _setup_ui(self):
        """创建控制界面"""
        # 创建 UI：地址输入、端口输入、启动/停止按钮等

    def start_server(self, host: str, port: int, protocol: str):
        """启动服务器"""
        if self._is_running:
            self.error_occurred.emit("服务器已在运行")
            return

        try:
            # 创建 TCP 服务器实例
            from tcp_log.tcp_server import TcpServer
            self._server = TcpServer(host, port, protocol)
            self._server.started.connect(self._on_server_started)
            self._server.stopped.connect(self._on_server_stopped)
            self._server.start()

            self._is_running = True
            self.status_changed.emit(f"服务器启动中... {host}:{port}")

        except Exception as e:
            self.error_occurred.emit(f"启动失败: {e}")

    def stop_server(self):
        """停止服务器"""
        if not self._is_running:
            return

        if self._server:
            self._server.stop()
            self._is_running = False
            self.status_changed.emit("服务器已停止")

    def get_server_status(self) -> dict:
        """获取服务器状态"""
        return {
            'is_running': self._is_running,
            'host': self._server.host if self._server else '',
            'port': self._server.port if self._server else 0,
            'protocol': self._server.protocol if self._server else '',
            'connected_clients': len(self._server.clients) if self._server else 0
        }

    def _on_server_started(self):
        """服务器启动回调"""
        self.started.emit(self._server.port)
        self.status_changed.emit(f"服务器已启动 {self._server.host}:{self._server.port}")

    def _on_server_stopped(self):
        """服务器停止回调"""
        self.stopped.emit()
        self.status_changed.emit("服务器已停止")
```

**3. log_table_widget.py：日志表格控件**
```python
"""
文件名称: log_table_widget.py
职责: 日志显示表格，支持过滤、导出
行数目标: ~250行
"""
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QMenu
from PySide6.QtCore import Signal, Qt

class LogTableWidget(QTableWidget):
    """日志显示表格控件"""

    # 信号定义
    log_selected = Signal(dict)  # 选中的日志数据
    log_count_changed = Signal(int)  # 日志数量变化

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logs = []  # 缓存日志数据
        self._max_logs = 1000  # 最大日志数
        self._setup_ui()

    def _setup_ui(self):
        """初始化表格"""
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["时间", "客户端", "协议", "原始数据", "解析结果", "状态"])

        # 设置表格属性
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)

    def append_log(self, log_data: dict):
        """追加日志"""
        # 限制最大日志数
        if len(self._logs) >= self._max_logs:
            self._remove_oldest_log()

        self._logs.append(log_data)
        self._update_table()
        self.log_count_changed.emit(len(self._logs))

    def clear_logs(self):
        """清空日志"""
        self._logs.clear()
        self.setRowCount(0)
        self.log_count_changed.emit(0)

    def export_logs(self, file_path: str):
        """导出日志到文件"""
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self._logs, f, ensure_ascii=False, indent=2)

    def filter_logs(self, filter_text: str):
        """过滤日志"""
        # 实现日志过滤逻辑
        pass

    def _remove_oldest_log(self):
        """删除最旧的日志"""
        if self._logs:
            self._logs.pop(0)
            self.removeRow(0)

    def _update_table(self):
        """更新表格显示"""
        # 根据 self._logs 更新表格内容
        pass
```

**4. client_manager.py：客户端管理**
```python
"""
文件名称: client_manager.py
职责: 客户端连接管理，显示连接列表
行数目标: ~150行
"""
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu
from PySide6.QtCore import Signal, QObject
from dataclasses import dataclass
from typing import List

@dataclass
class ClientInfo:
    """客户端信息"""
    client_id: str
    ip: str
    port: int
    connected_time: str
    protocol: str

class ClientManager(QObject):
    """客户端连接管理组件"""

    # 信号定义
    client_connected = Signal(ClientInfo)
    client_disconnected = Signal(str)  # client_id
    disconnect_requested = Signal(str)  # 请求断开指定客户端

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clients: List[ClientInfo] = []
        self._setup_ui()

    def _setup_ui(self):
        """创建客户端列表 UI"""
        # 创建 QListWidget 或 QTableWidget
        pass

    def add_client(self, client: ClientInfo):
        """添加客户端"""
        self._clients.append(client)
        self._update_client_list()
        self.client_connected.emit(client)

    def remove_client(self, client_id: str):
        """移除客户端"""
        self._clients = [c for c in self._clients if c.client_id != client_id]
        self._update_client_list()
        self.client_disconnected.emit(client_id)

    def get_connected_clients(self) -> List[ClientInfo]:
        """获取所有连接的客户端"""
        return self._clients.copy()

    def disconnect_client(self, client_id: str):
        """断开指定客户端"""
        self.disconnect_requested.emit(client_id)

    def disconnect_all(self):
        """断开所有客户端"""
        for client in self._clients:
            self.disconnect_requested.emit(client.client_id)

    def _update_client_list(self):
        """更新客户端列表显示"""
        # 更新 UI
        pass
```

**5. server_settings.py：设置对话框**
```python
"""
文件名称: server_settings.py
职责: 服务器设置对话框（端口、协议等配置）
行数目标: ~100行
"""
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox

class ServerSettingsDialog(QDialog):
    """服务器设置对话框"""

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self._settings = current_settings.copy()
        self._setup_ui()

    def _setup_ui(self):
        """创建设置界面"""
        layout = QFormLayout(self)

        # 地址输入
        self._host_input = QLineEdit(self._settings.get('host', '0.0.0.0'))
        layout.addRow("监听地址:", self._host_input)

        # 端口输入
        self._port_input = QLineEdit(str(self._settings.get('port', 9999)))
        layout.addRow("监听端口:", self._port_input)

        # 协议选择
        self._protocol_combo = QComboBox()
        # 填充协议列表
        layout.addRow("协议:", self._protocol_combo)

    def get_settings(self) -> dict:
        """获取设置"""
        return {
            'host': self._host_input.text(),
            'port': int(self._port_input.text()),
            'protocol': self._protocol_combo.currentText()
        }
```

### 2.3 迁移步骤

```python
# 步骤1：创建新文件（保留原文件）
# 1.1 创建 server_control.py、log_table_widget.py 等文件
# 1.2 从原文件复制相关代码，粘贴到新文件
# 1.3 调整导入路径和类名

# 步骤2：调整原文件为主容器
# 2.1 修改 server_panel.py，只保留容器逻辑
# 2.2 导入并使用新的子组件

# 步骤3：验证功能
# 3.1 运行应用，测试所有功能
# 3.2 确保没有破坏现有功能

# 步骤4：清理代码
# 4.1 移除重复代码
# 4.2 优化接口设计
```

---

## 三、统一信号管理

### 3.1 当前问题

**问题分析**：
- 信号定义分散在各个组件中
- 信号连接和断开没有统一管理
- 容易出现信号泄漏（重复连接、未断开）
- 难以追踪信号流向

**影响**：
- 内存泄漏风险
- 调试困难
- 代码维护成本高

### 3.2 解决方案

#### 3.2.1 集中信号定义

**文件位置**: `gui/signals.py`

```python
"""
GUI 统一信号定义
所有跨组件通信的信号集中定义
"""
from PySide6.QtCore import Signal, QObject

class AppSignals(QObject):
    """应用级全局信号"""

    # === 协议相关 ===
    protocol_loaded = Signal(str)  # protocol_name
    protocol_validated = Signal(bool, str)  # success, message
    protocol_selected = Signal(str)  # protocol_name

    # === 解析相关 ===
    parse_started = Signal(str)  # protocol_name
    parse_progress = Signal(int, str)  # progress, message
    parse_finished = Signal(bool, str)  # success, message
    parse_cancelled = Signal()
    parse_error = Signal(str)  # error_message

    # === TCP 服务相关 ===
    server_started = Signal(int)  # port
    server_stopped = Signal()
    client_connected = Signal(str, int)  # ip, port
    client_disconnected = Signal(str)  # client_id
    server_log_received = Signal(dict)  # log_data

    # === UI 相关 ===
    status_message_changed = Signal(str)  # 状态栏消息
    progress_changed = Signal(int, str)  # 进度条
    theme_changed = Signal(str)  # theme_name

    # === 文件相关 ===
    file_selected = Signal(str)  # file_path
    directory_selected = Signal(str)  # directory_path

# 全局单例
_app_signals = AppSignals()

def app_signals() -> AppSignals:
    """获取全局信号实例"""
    return _app_signals
```

#### 3.2.2 信号连接管理器

**文件位置**: `gui/signal_manager.py`

```python
"""
信号连接管理器
统一管理信号连接和断开，防止内存泄漏
"""
from typing import Callable, List, Dict
from PySide6.QtCore import QObject, Signal
from weakref import WeakSet

class SignalConnection:
    """信号连接封装"""

    def __init__(self, signal: Signal, slot: Callable):
        self.signal = signal
        self.slot = slot
        signal.connect(slot)

    def disconnect(self):
        """断开连接"""
        try:
            self.signal.disconnect(self.slot)
        except RuntimeError:
            # 信号或槽已被销毁
            pass

class SignalManager:
    """信号管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connections: WeakSet[SignalConnection] = WeakSet()
        return cls._instance

    def connect(self, signal: Signal, slot: Callable) -> SignalConnection:
        """连接信号"""
        conn = SignalConnection(signal, slot)
        self._connections.add(conn)
        return conn

    def disconnect_all(self):
        """断开所有连接"""
        for conn in list(self._connections):
            conn.disconnect()
        self._connections.clear()

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self._connections)

# 全局单例
_signal_manager = SignalManager()

def signal_manager() -> SignalManager:
    """获取信号管理器实例"""
    return _signal_manager
```

#### 3.2.3 使用示例

```python
# 旧代码：直接连接信号
class OldStyle:
    def __init__(self):
        self.some_signal.connect(self._on_some_event)

    def _on_some_event(self):
        pass

# 新代码：使用信号管理器
class NewStyle:
    def __init__(self):
        self._signal_mgr = signal_manager()
        self._conn = self._signal_mgr.connect(
            self.some_signal,
            self._on_some_event
        )

    def cleanup(self):
        """清理资源"""
        self._conn.disconnect()

    def _on_some_event(self):
        pass
```

### 3.3 迁移步骤

```python
# 步骤1：创建统一信号定义（0.5天）
# 1.1 创建 gui/signals.py
# 1.2 定义所有应用级信号
# 1.3 编写单元测试验证信号定义

# 步骤2：创建信号管理器（0.5天）
# 2.1 创建 gui/signal_manager.py
# 2.2 实现 SignalConnection 和 SignalManager
# 2.3 编写单元测试验证连接和断开

# 步骤3：逐步替换现有信号连接（1天）
# 3.1 优先替换关键组件（NormalParsePage, TcpServerPage）
# 3.2 逐个替换信号连接为使用 SignalManager
# 3.3 验证功能正常

# 步骤4：验证和优化（0.5天）
# 4.1 检查所有信号是否正确断开
# 4.2 使用内存分析工具检测泄漏
# 4.3 优化信号连接逻辑
```

---

## 四、统一工作线程管理模式

### 4.1 当前问题

**问题分析**：
- 线程创建和销毁逻辑分散
- 没有统一的线程池管理
- 线程生命周期管理不当（可能泄漏）
- 缺少线程状态监控

**影响**：
- 资源泄漏风险
- 界面卡死风险
- 调试困难

### 4.2 解决方案

#### 4.2.1 工作线程基类

**文件位置**: `gui/workers/base_worker.py`

```python
"""
工作线程基类
统一管理线程生命周期，防止内存泄漏
"""
from PySide6.QtCore import QRunnable, QObject, Signal
from typing import Any

class WorkerSignals(QObject):
    """工作线程信号"""
    started = Signal()
    finished = Signal(bool)  # success
    progress = Signal(int, str)  # progress, message
    error = Signal(str)
    cancelled = Signal()

class BaseWorker(QRunnable):
    """工作线程基类"""

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.signals = WorkerSignals()
        self._is_cancelled = False
        self._auto_delete = True

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._is_cancelled

    def run(self):
        """执行任务（模板方法）"""
        try:
            if self._is_cancelled:
                self.signals.cancelled.emit()
                return

            self.signals.started.emit()
            result = self.execute()

            if not self._is_cancelled:
                self.signals.finished.emit(True)
        except Exception as e:
            if not self._is_cancelled:
                self.signals.error.emit(str(e))
                self.signals.finished.emit(False)

    def execute(self) -> Any:
        """具体任务逻辑（子类实现）"""
        raise NotImplementedError
```

#### 4.2.2 工作线程管理器

**文件位置**: `gui/workers/worker_manager.py`

```python
"""
工作线程管理器
统一管理所有后台任务的生命周期
"""
from typing import Dict, Optional
from PySide6.QtCore import QObject, QThreadPool, Signal
from .base_worker import BaseWorker

class WorkerManager(QObject):
    """工作线程管理器（单例）"""

    task_started = Signal(str)  # task_id
    task_finished = Signal(str, bool)  # task_id, success
    task_failed = Signal(str, str)  # task_id, error
    task_cancelled = Signal(str)  # task_id

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = QThreadPool()
            cls._instance._pool.setMaxThreadCount(2)  # 限制并发数
            cls._instance._active_tasks: Dict[str, BaseWorker] = {}
        return cls._instance

    def submit_task(self, task: BaseWorker) -> str:
        """提交任务"""
        task_id = task.task_id

        # 连接信号
        task.signals.started.connect(lambda: self.task_started.emit(task_id))
        task.signals.finished.connect(
            lambda success: self._on_task_finished(task_id, success)
        )
        task.signals.error.connect(
            lambda error: self.task_failed.emit(task_id, error)
        )
        task.signals.cancelled.connect(
            lambda: self.task_cancelled.emit(task_id)
        )

        # 添加到活跃任务
        self._active_tasks[task_id] = task

        # 启动任务
        self._pool.start(task)

        return task_id

    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            task.cancel()
            del self._active_tasks[task_id]

    def cancel_all_tasks(self):
        """取消所有任务"""
        for task_id in list(self._active_tasks.keys()):
            self.cancel_task(task_id)

    def get_active_task_count(self) -> int:
        """获取活跃任务数"""
        return len(self._active_tasks)

    def _on_task_finished(self, task_id: str, success: bool):
        """任务完成回调"""
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
        self.task_finished.emit(task_id, success)

# 全局单例
_worker_manager = None

def worker_manager() -> WorkerManager:
    """获取工作线程管理器实例"""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager()
    return _worker_manager
```

#### 4.2.3 重构现有 Worker

```python
# 旧代码：gui/workers/parse_worker.py
class ParseWorker(QRunnable):
    def __init__(self, protocol, log_content):
        super().__init__()
        # ...

# 新代码：继承 BaseWorker
from gui.workers.base_worker import BaseWorker

class ParseWorker(BaseWorker):
    def __init__(self, task_id: str, protocol: str, log_content: str):
        super().__init__(task_id)
        self._protocol = protocol
        self._log_content = log_content

    def execute(self):
        """执行解析任务"""
        try:
            # 原有的解析逻辑
            for progress, message in parse_logic:
                if self.is_cancelled():
                    break
                self.signals.progress.emit(progress, message)

            return result
        except Exception as e:
            self.signals.error.emit(str(e))
            raise
```

### 4.3 迁移步骤

```python
# 步骤1：创建工作线程基类（0.5天）
# 1.1 创建 gui/workers/base_worker.py
# 1.2 实现 BaseWorker 和 WorkerSignals
# 1.3 编写单元测试验证基类功能

# 步骤2：创建工作线程管理器（0.5天）
# 2.1 创建 gui/workers/worker_manager.py
# 2.2 实现 WorkerManager 单例
# 2.3 编写单元测试验证任务管理

# 步骤3：重构现有 Worker（1天）
# 3.1 重构 ParseWorker 继承 BaseWorker
# 3.2 重构 ValidateWorker 继承 BaseWorker
# 3.3 修改调用代码使用 WorkerManager

# 步骤4：验证和优化（0.5天）
# 4.1 测试线程创建和销毁
# 4.2 测试任务取消功能
# 4.3 使用内存分析工具检测泄漏
```

---

## 五、提取通用模式

### 5.1 统一错误处理

**文件位置**: `gui/shared/error_handler.py`

```python
"""
统一错误处理
提供一致的错误处理和用户提示
"""
from PySide6.QtWidgets import QMessageBox
from typing import Optional

class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def handle_config_error(error: Exception, parent=None) -> str:
        """处理配置错误"""
        message = f"配置错误: {str(error)}"
        ErrorHandler.show_error(message, parent)
        return message

    @staticmethod
    def handle_parse_error(error: Exception, parent=None) -> str:
        """处理解析错误"""
        message = f"解析错误: {str(error)}"
        ErrorHandler.show_error(message, parent)
        return message

    @staticmethod
    def handle_file_error(error: Exception, parent=None) -> str:
        """处理文件错误"""
        message = f"文件错误: {str(error)}"
        ErrorHandler.show_error(message, parent)
        return message

    @staticmethod
    def show_error(message: str, parent=None):
        """显示错误消息"""
        QMessageBox.critical(parent, "错误", message)

    @staticmethod
    def show_warning(message: str, parent=None):
        """显示警告消息"""
        QMessageBox.warning(parent, "警告", message)

    @staticmethod
    def show_info(message: str, parent=None):
        """显示信息消息"""
        QMessageBox.information(parent, "提示", message)
```

### 5.2 统一文件对话框

**文件位置**: `gui/shared/file_dialogs.py`

```python
"""
统一文件对话框
提供一致的文件选择体验
"""
from pathlib import Path
from PySide6.QtWidgets import QFileDialog
from gui.config import LOG_FILE_FILTER, CONFIG_FILE_FILTER

class FileDialogs:
    """文件对话框工具"""

    @staticmethod
    def select_log_file(parent=None) -> Optional[Path]:
        """选择日志文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "选择日志文件",
            str(INPUT_LOGS_DIR),
            LOG_FILE_FILTER
        )
        return Path(file_path) if file_path else None

    @staticmethod
    def select_config_file(parent=None) -> Optional[Path]:
        """选择配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "选择配置文件",
            str(CONFIGS_DIR),
            CONFIG_FILE_FILTER
        )
        return Path(file_path) if file_path else None

    @staticmethod
    def select_output_directory(parent=None) -> Optional[Path]:
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            parent,
            "选择输出目录",
            str(PARSED_LOG_DIR)
        )
        return Path(dir_path) if dir_path else None
```

---

## 六、测试策略

### 6.1 单元测试

#### 信号管理器测试
```python
# tests/gui/test_signal_manager.py
import pytest
from gui.signal_manager import SignalManager, signal_manager
from PySide6.QtCore import Signal, QObject

class TestSignalManager:
    """信号管理器测试"""

    def test_connect_disconnect(self):
        """测试连接和断开"""
        mgr = signal_manager()

        # 创建测试信号
        emitter = QObject()
        test_signal = Signal(str)
        emitter.test_signal = test_signal

        # 连接信号
        received = []
        def slot(msg):
            received.append(msg)

        conn = mgr.connect(test_signal, slot)

        # 触发信号
        test_signal.emit("test")
        assert "test" in received

        # 断开信号
        conn.disconnect()
        received.clear()

        # 再次触发，不应收到
        test_signal.emit("test2")
        assert "test2" not in received

    def test_disconnect_all(self):
        """测试断开所有连接"""
        mgr = signal_manager()

        # 创建多个连接
        emitter = QObject()
        test_signal = Signal(str)
        emitter.test_signal = test_signal

        conn1 = mgr.connect(test_signal, lambda x: None)
        conn2 = mgr.connect(test_signal, lambda x: None)

        assert mgr.get_connection_count() == 2

        # 断开所有
        mgr.disconnect_all()
        assert mgr.get_connection_count() == 0
```

#### 工作线程管理器测试
```python
# tests/gui/test_worker_manager.py
import pytest
import time
from gui.workers.worker_manager import worker_manager, BaseWorker

class TestWorker(BaseWorker):
    """测试用 Worker"""
    def __init__(self, task_id: str, should_fail=False):
        super().__init__(task_id)
        self._should_fail = should_fail

    def execute(self):
        if self._should_fail:
            raise ValueError("Test error")
        time.sleep(0.1)  # 模拟工作
        return "success"

class TestWorkerManager:
    """工作线程管理器测试"""

    def test_submit_task(self):
        """测试提交任务"""
        mgr = worker_manager()

        task = TestWorker("task1")
        task_id = mgr.submit_task(task)

        assert task_id == "task1"
        assert mgr.get_active_task_count() == 1

        # 等待任务完成
        time.sleep(0.2)
        assert mgr.get_active_task_count() == 0

    def test_cancel_task(self):
        """测试取消任务"""
        mgr = worker_manager()

        task = TestWorker("task2")
        task_id = mgr.submit_task(task)

        mgr.cancel_task(task_id)
        assert mgr.get_active_task_count() == 0
```

### 6.2 集成测试

```python
# tests/gui/integration/test_tcp_server_page.py
import pytest
from tcp_log.server_panel import TcpServerPage

class TestTcpServerPageIntegration:
    """TCP 服务端页面集成测试"""

    @pytest.fixture
    def page(self, qapp):
        """创建页面实例"""
        return TcpServerPage()

    def test_server_lifecycle(self, page):
        """测试服务器完整生命周期"""
        # 1. 启动服务器
        page._control.start_server("127.0.0.1", 9999, "v8")
        assert page._control.get_server_status()['is_running'] == True

        # 2. 停止服务器
        page._control.stop_server()
        assert page._control.get_server_status()['is_running'] == False

    def test_log_display(self, page):
        """测试日志显示"""
        # 模拟日志数据
        log_data = {
            'time': '2025-02-02 12:00:00',
            'client': '127.0.0.1:12345',
            'protocol': 'v8',
            'raw_data': 'AABBCCDD',
            'parsed': '成功解析',
            'status': 'success'
        }

        page._log_table.append_log(log_data)
        assert page._log_table.log_count_changed.emit(1)
```

---

## 七、验收标准

### 7.1 代码质量验收
- [ ] 单文件代码量 <600行
- [ ] 圈复杂度 <10（关键函数）
- [ ] 代码重复率 <5%
- [ ] 所有函数有中文注释

### 7.2 功能验收
- [ ] TCP 服务端所有功能正常
  - [ ] 服务器启动和停止
  - [ ] 客户端连接管理
  - [ ] 日志显示和过滤
  - [ ] 日志导出功能
  - [ ] 设置对话框
- [ ] 普通解析页面所有功能正常（阶段1已重构，需验证兼容性）
- [ ] 信号连接正确，无内存泄漏
- [ ] 工作线程正常创建和销毁

### 7.3 性能验收
- [ ] 内存泄漏检查通过（使用内存分析工具）
- [ ] 长时间运行稳定性（>4小时无崩溃）
- [ ] 线程池利用率合理
- [ ] 信号连接数合理（无过度连接）

### 7.4 测试验收
- [ ] 信号管理器单元测试覆盖率 >90%
- [ ] 工作线程管理器单元测试覆盖率 >90%
- [ ] TCP 服务端集成测试通过
- [ ] 内存泄漏测试通过

---

## 八、风险评估

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 拆分文件破坏功能 | 高 | 中 | 1. 先复制再重构<br>2. 保留原文件备份<br>3. 充分测试 |
| 信号连接泄漏 | 中 | 高 | 1. 使用 SignalManager<br>2. 添加连接检查工具<br>3. 内存分析测试 |
| 线程管理混乱 | 高 | 中 | 1. 统一使用 WorkerManager<br>2. 添加线程监控<br>3. 压力测试 |
| 组件接口不兼容 | 中 | 中 | 1. 保持原有信号接口<br>2. 渐进式迁移<br>3. 充分集成测试 |

### 8.2 进度风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| TCP 页面理解不充分 | 中 | 低 | 提前阅读代码，绘制架构图 |
| 测试编写耗时超预期 | 低 | 中 | 优先测试关键路径，使用测试工具辅助 |
| 内存泄漏调试困难 | 中 | 中 | 使用专业内存分析工具，预留调试时间 |

---

## 九、后续步骤

完成阶段2后，进入**阶段3：质量提升层**，主要工作：
1. 添加 GUI 测试框架（pytest-qt）
2. 补充单元测试和集成测试
3. 性能优化和文档完善

详见：[gui-refactor-phase3-plan.md](./gui-refactor-phase3-plan.md)

---

**文档结束**
