"""
文件名称: config.py
内容摘要: GUI 统一配置常量，集中管理所有硬编码值
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """
    获取项目根目录（支持 PyInstaller 打包）

    Returns:
        Path: 项目根目录路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的可执行文件目录
        return Path(sys.executable).parent
    else:
        # 开发模式：使用当前工作目录
        return Path.cwd()


# ============== 路径常量 ==============
PROJECT_ROOT = get_project_root()
CONFIGS_DIR = PROJECT_ROOT / "configs"
INPUT_LOGS_DIR = PROJECT_ROOT / "input_logs"
PARSED_LOG_DIR = PROJECT_ROOT / "parsed_log"
TCP_OUTPUT_DIR = PROJECT_ROOT / "tcp_output"

# ============== UI 尺寸常量 ==============
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
PROTOCOL_PANEL_MIN_WIDTH = 250
PROTOCOL_PANEL_MAX_WIDTH = 350
LOG_PANEL_MIN_HEIGHT = 150

# ============== 文件过滤 ==============
LOG_FILE_FILTER = "日志文件 (*.log *.txt);;所有文件 (*.*)"

# ============== 默认值 ==============
DEFAULT_PROTOCOL = "sinexcel"
DEFAULT_THEME = "dark"
