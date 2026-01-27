#!/usr/bin/env python3
# build_gui.py
"""
V8Parse GUI 打包脚本
使用 PyInstaller 将 GUI 应用打包为独立可执行文件

使用方法:
    python build_gui.py          # 默认打包
    python build_gui.py --clean  # 清理后打包
    python build_gui.py --debug  # 调试模式（显示控制台）
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


# 项目配置
APP_NAME = "V8Parse"
ENTRY_SCRIPT = "main_gui.py"
ICON_FILE = None  # 可选：设置图标文件路径，如 "assets/icon.ico"

# 需要包含的数据目录
DATA_DIRS = [
    "configs",      # 协议配置目录
]

# 需要包含的数据文件
DATA_FILES = [
    # ("source_path", "dest_path")
]

# 隐式导入（PyInstaller 可能无法自动检测的模块）
HIDDEN_IMPORTS = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "yaml",
    # src 模块
    "src.yaml_unified_protocol",
    "src.yaml_config",
    "src.yaml_cmdformat",
    "src.yaml_field_parser",
    "src.validate_configs",
    "src.logger_instance",
    "src.m_print",
    # gui 主模块
    "gui.unified_main_window",
    "gui.sidebar",
    "gui.normal_parse_page",
    "gui.protocol_panel",
    "gui.detail_panel",
    "gui.log_panel",
    "gui.themes",
    # gui 共享模块
    "gui.shared.app_helpers",
    "gui.shared.time_utils",
    "gui.shared.window_manager",
    "shared.unified_themes",
    # gui 自定义控件
    "gui.widgets.searchable_list",
    "gui.widgets.multi_select_combo",
    "gui.widgets.datetime_picker",
    "gui.widgets.log_time_scanner",
    "gui.widgets.time_range_slider",
    "gui.widgets.visual_time_picker_dialog",
    # gui 工作线程
    "gui.workers.parse_worker",
    "gui.workers.validate_worker",
]

# 排除的模块（减小打包体积）
EXCLUDES = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "cv2",
    "PySide6.QtNetwork",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtOpenGL",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtRemoteObjects",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSvg",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
]


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.resolve()


def clean_build_artifacts():
    """清理构建产物"""
    project_root = get_project_root()
    
    dirs_to_clean = ["build", "dist"]
    files_to_clean = [f"{APP_NAME}.spec"]
    
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"清理目录: {dir_path}")
            shutil.rmtree(dir_path)
    
    for file_name in files_to_clean:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"清理文件: {file_path}")
            file_path.unlink()
    
    # 清理 __pycache__
    for pycache in project_root.rglob("__pycache__"):
        if pycache.is_dir():
            print(f"清理缓存: {pycache}")
            shutil.rmtree(pycache)


def build_add_data_args() -> list:
    """构建 --add-data 参数列表"""
    project_root = get_project_root()
    args = []
    
    # Windows 使用分号，Linux/macOS 使用冒号
    separator = ";" if sys.platform == "win32" else ":"
    
    # 添加数据目录
    for dir_name in DATA_DIRS:
        dir_path = project_root / dir_name
        if dir_path.exists():
            args.extend(["--add-data", f"{dir_path}{separator}{dir_name}"])
        else:
            print(f"警告: 数据目录不存在: {dir_path}")
    
    # 添加数据文件
    for src, dest in DATA_FILES:
        src_path = project_root / src
        if src_path.exists():
            args.extend(["--add-data", f"{src_path}{separator}{dest}"])
        else:
            print(f"警告: 数据文件不存在: {src_path}")
    
    return args


def build_pyinstaller_command(debug: bool = False) -> list:
    """构建 PyInstaller 命令"""
    project_root = get_project_root()
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",        # 打包为单文件
        "--clean",          # 清理临时文件
        "--noconfirm",      # 覆盖已有输出
        "--paths", str(project_root),           # 添加项目根目录到搜索路径
        "--paths", str(project_root / "src"),   # 添加 src 目录到搜索路径
        "--paths", str(project_root / "gui"),   # 添加 gui 目录到搜索路径
    ]
    
    # GUI 模式（隐藏控制台）或调试模式（显示控制台）
    if debug:
        cmd.append("--console")
    else:
        cmd.append("--windowed")
    
    # 添加图标
    if ICON_FILE:
        icon_path = project_root / ICON_FILE
        if icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])
    
    # 添加隐式导入
    for module in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", module])
    
    # 添加排除模块
    for module in EXCLUDES:
        cmd.extend(["--exclude-module", module])
    
    # 添加数据文件
    cmd.extend(build_add_data_args())
    
    # 入口脚本
    cmd.append(str(project_root / ENTRY_SCRIPT))
    
    return cmd


def run_build(debug: bool = False):
    """执行打包"""
    project_root = get_project_root()
    
    print("=" * 60)
    print(f"开始打包 {APP_NAME}")
    print("=" * 60)
    
    # 检查入口文件
    entry_path = project_root / ENTRY_SCRIPT
    if not entry_path.exists():
        print(f"错误: 入口文件不存在: {entry_path}")
        return False
    
    # 检查 PyInstaller
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        print("错误: PyInstaller 未安装，请运行: pip install pyinstaller")
        return False
    
    # 构建命令
    cmd = build_pyinstaller_command(debug)
    
    print("\n执行命令:")
    print(" ".join(cmd))
    print()
    
    # 执行打包
    try:
        result = subprocess.run(cmd, cwd=project_root)
        if result.returncode != 0:
            print("\n打包失败!")
            return False
    except Exception as e:
        print(f"\n打包出错: {e}")
        return False
    
    # 检查输出
    if sys.platform == "win32":
        output_file = project_root / "dist" / f"{APP_NAME}.exe"
    else:
        output_file = project_root / "dist" / APP_NAME
    
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print("打包成功!")
        print(f"输出文件: {output_file}")
        print(f"文件大小: {size_mb:.2f} MB")
        print("=" * 60)

        # 复制 configs 目录到 dist
        dist_dir = project_root / "dist"
        configs_src = project_root / "configs"
        configs_dest = dist_dir / "configs"

        if configs_src.exists():
            if configs_dest.exists():
                shutil.rmtree(configs_dest)
            shutil.copytree(configs_src, configs_dest)
            print(f"\n已复制配置目录: {configs_dest}")

        # 自动清理 build 目录
        build_dir = project_root / "build"
        if build_dir.exists():
            print(f"\n清理临时构建目录: {build_dir}")
            shutil.rmtree(build_dir)

        # 清理 .spec 文件
        spec_file = project_root / f"{APP_NAME}.spec"
        if spec_file.exists():
            print(f"清理配置文件: {spec_file}")
            spec_file.unlink()

        # 发布目录结构提示
        print("\n发布目录结构:")
        print(f"  dist/")
        print(f"    {APP_NAME}.exe")
        print("    configs/          # 协议配置目录")

        return True
    else:
        print("\n打包失败: 输出文件未生成")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description=f"{APP_NAME} GUI 打包脚本")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="打包前清理构建产物"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式（显示控制台窗口）"
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="仅清理构建产物，不执行打包"
    )
    
    args = parser.parse_args()
    
    if args.clean or args.clean_only:
        print("清理构建产物...")
        clean_build_artifacts()
        if args.clean_only:
            print("清理完成")
            return
    
    success = run_build(debug=args.debug)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
