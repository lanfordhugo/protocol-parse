"""
文件名称: sender_gui.py
内容摘要: TCP Log Sender GUI - 协议报文发送测试工具
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QTextEdit, QProgressBar, QMessageBox,
    QCompleter, QMenu, QMenuBar
)
from PySide6.QtCore import Qt, Signal, QObject, QStringListModel, QSettings
from PySide6.QtGui import QFont, QTextCursor, QAction, QActionGroup

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tcp_log.tcp_client import TcpLogClient, ClientState, SendProgress
from tcp_log.log_entry_parser import LogEntryParser
from tcp_log.themes import get_theme


class SignalBridge(QObject):
    """信号桥接，用于线程间通信"""
    state_changed = Signal(str)
    progress_updated = Signal(object)
    log_message = Signal(str)
    error_message = Signal(str)


class TcpLogSenderWindow(QMainWindow):
    """TCP Log Sender 主窗口"""
    
    def __init__(self):
        super().__init__()
        self._client = TcpLogClient()
        self._signal_bridge = SignalBridge()
        self._log_files = {}  # {display_name: full_path}
        
        # 设置
        self._settings = QSettings("V8Parse", "TcpLogSender")
        self._current_theme = self._settings.value("theme", "dark")
        
        self._setup_ui()
        self._setup_menu()
        self._setup_connections()
        self._scan_log_files()
        self._apply_theme(self._current_theme)
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("TCP Log Sender - 协议报文发送工具")
        self.setMinimumSize(600, 500)
        self.resize(650, 550)
        
        # 设置等宽字体
        mono_font = QFont("Consolas", 9)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # === 服务器配置组 ===
        server_group = QGroupBox("服务器配置")
        server_layout = QHBoxLayout(server_group)
        
        server_layout.addWidget(QLabel("目标地址:"))
        self._host_input = QLineEdit("127.0.0.1")
        self._host_input.setFixedWidth(120)
        server_layout.addWidget(self._host_input)
        
        server_layout.addWidget(QLabel("端口:"))
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(9999)
        self._port_input.setFixedWidth(80)
        server_layout.addWidget(self._port_input)
        
        self._connect_btn = QPushButton("连接")
        self._connect_btn.setFixedWidth(70)
        server_layout.addWidget(self._connect_btn)
        
        self._disconnect_btn = QPushButton("断开")
        self._disconnect_btn.setFixedWidth(70)
        self._disconnect_btn.setEnabled(False)
        server_layout.addWidget(self._disconnect_btn)
        
        server_layout.addStretch()
        
        self._status_label = QLabel("状态: ● 未连接")
        self._status_label.setStyleSheet("color: gray;")
        server_layout.addWidget(self._status_label)
        
        main_layout.addWidget(server_group)
        
        # === 日志选择组 ===
        log_group = QGroupBox("日志选择")
        log_layout = QVBoxLayout(log_group)
        
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("日志文件:"))
        
        self._log_combo = QComboBox()
        self._log_combo.setEditable(True)
        self._log_combo.setInsertPolicy(QComboBox.NoInsert)
        self._log_combo.setMinimumWidth(350)
        
        # 设置模糊匹配
        self._completer = QCompleter()
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._log_combo.setCompleter(self._completer)
        
        select_layout.addWidget(self._log_combo)
        select_layout.addStretch()
        
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setFixedWidth(60)
        select_layout.addWidget(self._refresh_btn)
        
        log_layout.addLayout(select_layout)
        
        self._log_info_label = QLabel("请选择日志文件")
        self._log_info_label.setStyleSheet("color: #666;")
        log_layout.addWidget(self._log_info_label)
        
        main_layout.addWidget(log_group)
        
        # === 发送控制组 ===
        control_group = QGroupBox("发送控制")
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(10, 20, 10, 10)  # 上边距留给标题
        control_layout.setSpacing(8)
        
        # 第一行：发送间隔和选项
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)
        
        options_layout.addWidget(QLabel("发送间隔:"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(10, 10000)
        self._interval_spin.setValue(100)
        self._interval_spin.setSuffix(" ms")
        self._interval_spin.setFixedWidth(100)
        options_layout.addWidget(self._interval_spin)
        
        self._loop_check = QCheckBox("循环发送")
        options_layout.addWidget(self._loop_check)
        
        self._disconnect_after_check = QCheckBox("发送完成后断开")
        options_layout.addWidget(self._disconnect_after_check)
        
        options_layout.addStretch()
        control_layout.addLayout(options_layout)
        
        # 第二行：控制按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self._start_btn = QPushButton("▶ 开始发送")
        self._start_btn.setFixedWidth(100)
        self._start_btn.setFixedHeight(30)
        self._start_btn.setEnabled(False)
        buttons_layout.addWidget(self._start_btn)
        
        self._pause_btn = QPushButton("⏸ 暂停")
        self._pause_btn.setFixedWidth(80)
        self._pause_btn.setFixedHeight(30)
        self._pause_btn.setEnabled(False)
        buttons_layout.addWidget(self._pause_btn)
        
        self._stop_btn = QPushButton("⏹ 停止")
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setFixedHeight(30)
        self._stop_btn.setEnabled(False)
        buttons_layout.addWidget(self._stop_btn)
        
        buttons_layout.addStretch()
        control_layout.addLayout(buttons_layout)
        
        # 第三行：进度条（与按钮间隔）
        control_layout.addSpacing(5)
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(20)
        control_layout.addWidget(self._progress_bar)
        
        self._progress_label = QLabel("进度: 0/0 条  |  已发送: 0 KB  |  耗时: 00:00")
        self._progress_label.setStyleSheet("color: #666;")
        control_layout.addWidget(self._progress_label)
        
        main_layout.addWidget(control_group)
        
        # === 发送日志组 ===
        log_output_group = QGroupBox("发送日志")
        log_output_layout = QVBoxLayout(log_output_group)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(mono_font)
        self._log_text.setMaximumHeight(150)
        log_output_layout.addWidget(self._log_text)
        
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        self._clear_log_btn = QPushButton("清空")
        self._clear_log_btn.setFixedWidth(60)
        clear_layout.addWidget(self._clear_log_btn)
        log_output_layout.addLayout(clear_layout)
        
        main_layout.addWidget(log_output_group)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        # 主题子菜单
        theme_menu = view_menu.addMenu("主题")
        
        # 主题选项组（互斥）
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        
        # 深色主题
        self._dark_action = QAction("深色主题", self)
        self._dark_action.setCheckable(True)
        self._dark_action.setData("dark")
        self._theme_group.addAction(self._dark_action)
        theme_menu.addAction(self._dark_action)
        
        # 浅色主题
        self._light_action = QAction("浅色主题", self)
        self._light_action.setCheckable(True)
        self._light_action.setData("light")
        self._theme_group.addAction(self._light_action)
        theme_menu.addAction(self._light_action)
        
        # 设置当前主题选中状态
        if self._current_theme == "dark":
            self._dark_action.setChecked(True)
        else:
            self._light_action.setChecked(True)
        
        # 连接主题切换信号
        self._theme_group.triggered.connect(self._on_theme_changed)
    
    def _on_theme_changed(self, action: QAction):
        """主题切换"""
        theme = action.data()
        if theme != self._current_theme:
            self._current_theme = theme
            self._apply_theme(theme)
            self._settings.setValue("theme", theme)
    
    def _apply_theme(self, theme: str):
        """应用主题"""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme(theme))
    
    def _setup_connections(self):
        """设置信号连接"""
        # 按钮
        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        self._refresh_btn.clicked.connect(self._scan_log_files)
        self._start_btn.clicked.connect(self._on_start)
        self._pause_btn.clicked.connect(self._on_pause)
        self._stop_btn.clicked.connect(self._on_stop)
        self._clear_log_btn.clicked.connect(self._log_text.clear)
        
        # 下拉框
        self._log_combo.currentTextChanged.connect(self._on_log_selected)
        
        # 信号桥接
        self._signal_bridge.state_changed.connect(self._update_state)
        self._signal_bridge.progress_updated.connect(self._update_progress)
        self._signal_bridge.log_message.connect(self._append_log)
        self._signal_bridge.error_message.connect(self._show_error)
        
        # 设置客户端回调
        self._client.set_callbacks(
            on_state_changed=lambda s: self._signal_bridge.state_changed.emit(s.value),
            on_progress=lambda p: self._signal_bridge.progress_updated.emit(p),
            on_log=lambda m: self._signal_bridge.log_message.emit(m),
            on_error=lambda m: self._signal_bridge.error_message.emit(m)
        )
    
    def _scan_log_files(self):
        """扫描日志文件目录"""
        log_dir = project_root / "input_logs"
        self._log_files.clear()
        self._log_combo.clear()
        
        if not log_dir.exists():
            self._log_info_label.setText("日志目录不存在")
            return
        
        items = []
        for log_file in log_dir.glob("*.log"):
            try:
                size = log_file.stat().st_size
                count = LogEntryParser.count_entries(str(log_file))
                
                size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
                display_name = f"{log_file.name}  ({count}条, {size_str})"
                
                self._log_files[display_name] = str(log_file)
                items.append(display_name)
            except Exception:
                pass
        
        self._log_combo.addItems(items)
        
        # 更新Completer
        model = QStringListModel(items)
        self._completer.setModel(model)
        
        if items:
            self._log_combo.setCurrentIndex(0)
            self._on_log_selected(items[0])
        else:
            self._log_info_label.setText("未找到日志文件")
    
    def _on_log_selected(self, text: str):
        """日志文件选择改变"""
        if text in self._log_files:
            path = self._log_files[text]
            self._log_info_label.setText(f"已选: {Path(path).name}")
        else:
            self._log_info_label.setText("请选择日志文件")
    
    def _on_connect(self):
        """连接按钮点击"""
        host = self._host_input.text().strip()
        port = self._port_input.value()
        
        if not host:
            QMessageBox.warning(self, "警告", "请输入服务器地址")
            return
        
        self._client.connect(host, port)
    
    def _on_disconnect(self):
        """断开按钮点击"""
        self._client.disconnect()
    
    def _on_start(self):
        """开始发送按钮点击"""
        current_text = self._log_combo.currentText()
        
        if current_text not in self._log_files:
            QMessageBox.warning(self, "警告", "请选择有效的日志文件")
            return
        
        log_file = self._log_files[current_text]
        interval = self._interval_spin.value()
        loop_send = self._loop_check.isChecked()
        disconnect_after = self._disconnect_after_check.isChecked()
        
        self._client.start_send(log_file, interval, loop_send, disconnect_after)
    
    def _on_pause(self):
        """暂停/恢复按钮点击"""
        if self._client.state == ClientState.SENDING:
            self._client.pause_send()
            self._pause_btn.setText("▶ 恢复")
        elif self._client.state == ClientState.PAUSED:
            self._client.resume_send()
            self._pause_btn.setText("⏸ 暂停")
    
    def _on_stop(self):
        """停止按钮点击"""
        self._client.stop_send()
    
    def _update_state(self, state_text: str):
        """更新状态显示"""
        state_colors = {
            "未连接": ("#888888", False),
            "连接中": ("#FFA500", False),
            "已连接": ("#4CAF50", True),
            "发送中": ("#00CED1", True),  # 青色，更醒目
            "已暂停": ("#FFA500", True),
            "错误": ("#F44336", False),
        }
        
        color, connected = state_colors.get(state_text, ("gray", False))
        self._status_label.setText(f"状态: ● {state_text}")
        self._status_label.setStyleSheet(f"color: {color};")
        
        # 更新按钮状态
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._start_btn.setEnabled(state_text == "已连接")
        self._pause_btn.setEnabled(state_text in ("发送中", "已暂停"))
        self._stop_btn.setEnabled(state_text in ("发送中", "已暂停"))
        
        # 重置暂停按钮文本
        if state_text not in ("发送中", "已暂停"):
            self._pause_btn.setText("⏸ 暂停")
    
    def _update_progress(self, progress: SendProgress):
        """更新进度显示"""
        percent = int(progress.current * 100 / progress.total) if progress.total > 0 else 0
        self._progress_bar.setValue(percent)
        
        elapsed = int(progress.elapsed_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        
        kb_sent = progress.bytes_sent / 1024
        
        self._progress_label.setText(
            f"进度: {progress.current}/{progress.total} 条  |  "
            f"已发送: {kb_sent:.1f} KB  |  "
            f"耗时: {minutes:02d}:{seconds:02d}"
        )
        
        # 显示当前发送的条目
        if progress.current_entry:
            entry = progress.current_entry
            self._append_log(f"#{progress.current} cmd={entry.cmd_id}, {entry.byte_count}B")
    
    def _append_log(self, message: str):
        """追加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{timestamp}] {message}")
        
        # 滚动到底部
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._log_text.setTextCursor(cursor)
    
    def _show_error(self, message: str):
        """显示错误"""
        self._append_log(f"[错误] {message}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self._client.disconnect()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = TcpLogSenderWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
