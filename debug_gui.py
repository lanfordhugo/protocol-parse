#!/usr/bin/env python3
"""临时调试脚本 - 定位 QThread 崩溃根因"""
import sys
import threading
import faulthandler
from pathlib import Path
from unittest.mock import patch

faulthandler.enable()
sys.path.insert(0, str(Path(__file__).parent))

# 猴子补丁 QThread，追踪所有 QThread 创建和销毁
from PySide6.QtCore import QThread as _OrigQThread

_orig_init = _OrigQThread.__init__
_orig_start = _OrigQThread.start
_orig_wait = _OrigQThread.wait

def _debug_init(self, *args, **kwargs):
    import traceback
    print(f"[QThread] __init__ {self.__class__.__name__} id={id(self)}")
    traceback.print_stack(limit=6)
    _orig_init(self, *args, **kwargs)

def _debug_start(self, *args, **kwargs):
    print(f"[QThread] start {self.__class__.__name__} id={id(self)}")
    _orig_start(self, *args, **kwargs)

def _debug_wait(self, *args, **kwargs):
    print(f"[QThread] wait {self.__class__.__name__} id={id(self)} isRunning={self.isRunning()}")
    import traceback
    traceback.print_stack(limit=6)
    return _orig_wait(self, *args, **kwargs)

_OrigQThread.__init__ = _debug_init
_OrigQThread.start = _debug_start
_OrigQThread.wait = _debug_wait

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

print("[1] 创建 QApplication...")
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
app = QApplication(sys.argv)
app.setApplicationName("V8Parse")
app.setApplicationVersion("1.0.0")
app.setOrganizationName("V8Parse")
font = QFont()
font.setFamily("Microsoft YaHei UI")
font.setPointSize(9)
app.setFont(font)
app.setStyle("Fusion")

print("[2] 创建 UnifiedMainWindow...")
from gui.unified_main_window import UnifiedMainWindow
window = UnifiedMainWindow()

print("[3] 显示窗口...")
window.show()

print("[4] 进入事件循环 (45秒后自动关闭)...")
QTimer.singleShot(45000, lambda: (print("[5] 关闭窗口..."), window.close()))
ret = app.exec()
print(f"[6] 退出码={ret}")
