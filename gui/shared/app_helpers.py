"""
文件名称: app_helpers.py
内容摘要: 应用辅助函数 - 跨平台文件/目录操作
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-24
"""

import os
import subprocess
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """
    获取应用程序所在目录(支持打包后的exe)

    Returns:
        Path: 应用程序根目录路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的可执行文件目录
        return Path(sys.executable).parent
    else:
        # 开发模式:使用当前工作目录
        return Path.cwd()


def open_directory(path: Path) -> None:
    """
    打开目录(跨平台)

    Args:
        path: 要打开的目录路径
    """
    path.mkdir(parents=True, exist_ok=True)

    if sys.platform == 'win32':
        os.startfile(str(path))
    elif sys.platform == 'darwin':
        subprocess.run(['open', str(path)])
    else:
        subprocess.run(['xdg-open', str(path)])


def open_file(file_path: str) -> None:
    """
    打开文件(跨平台)

    Args:
        file_path: 要打开的文件路径
    """
    if sys.platform == 'win32':
        os.startfile(file_path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', file_path])
    else:
        subprocess.run(['xdg-open', file_path])
