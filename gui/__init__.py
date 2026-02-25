# gui/__init__.py
"""
文件名称: __init__.py
内容摘要: V8Parse GUI 模块包初始化
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# 注意：此处不要在 import 时强制加载 PySide6 相关模块，
# 否则会导致在无 GUI 依赖的环境中无法导入 gui.wave.*（例如仅运行算法/数据管理单测）。

__all__ = [
    "MainWindow",
    "ProtocolPanel",
    "DetailPanel",
    "LogPanel",
]

if TYPE_CHECKING:
    from .detail_panel import DetailPanel
    from .log_panel import LogPanel
    from .main_window import MainWindow
    from .protocol_panel import ProtocolPanel


def __getattr__(name: str) -> Any:
    if name == "MainWindow":
        from .main_window import MainWindow as _MainWindow

        return _MainWindow
    if name == "ProtocolPanel":
        from .protocol_panel import ProtocolPanel as _ProtocolPanel

        return _ProtocolPanel
    if name == "DetailPanel":
        from .detail_panel import DetailPanel as _DetailPanel

        return _DetailPanel
    if name == "LogPanel":
        from .log_panel import LogPanel as _LogPanel

        return _LogPanel
    raise AttributeError(f"module 'gui' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + __all__))
