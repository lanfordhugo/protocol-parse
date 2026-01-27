#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyInstaller 通用打包脚本模板

功能:
    - 自动检测项目结构
    - 清理历史构建产物
    - 跨平台路径处理
    - 支持配置文件定制

使用方法:
    python build_template.py                    # 默认配置打包
    python build_template.py --gui             # GUI 应用打包
    python build_template.py --cli             # CLI 应用打包
    python build_template.py --debug           # 调试模式打包
    python build_template.py --config config.yaml  # 使用配置文件

作者: [Your Name]
日期: 2025-01-27
"""

import os
import sys
import shutil
import argparse
import platform
import subprocess
from pathlib import Path
from typing import List, Optional


class BuildConfig:
    """打包配置类"""

    def __init__(self):
        # 项目配置
        self.main_script = "main.py"          # 主入口脚本
        self.app_name = None                  # 应用名称（自动从脚本名推导）
        self.version = "1.0.0"                # 应用版本

        # 打包参数
        self.is_gui = False                   # 是否为 GUI 应用
        self.onefile = True                   # 是否打包为单文件
        self.clean = True                     # 是否清理历史构建
        self.debug = False                    # 调试模式

        # 路径配置
        self.paths = []                       # 模块搜索路径
        self.data_files = []                  # 资源文件列表 [(src, dest)]
        self.hidden_imports = []              # 隐式导入模块列表
        self.excludes = []                    # 排除的模块列表

        # 图标配置
        self.icon = None                      # 图标文件路径

        # 平台特定配置
        self.platform = platform.system()
        self.separator = ";" if self.platform == "Windows" else ":"

    def validate(self) -> bool:
        """验证配置"""
        if not os.path.exists(self.main_script):
            print(f"❌ 错误: 主入口脚本不存在: {self.main_script}")
            return False

        if self.app_name is None:
            # 自动从脚本名推导应用名
            self.app_name = Path(self.main_script).stem.replace("_", "-").title()

        return True


class Builder:
    """PyInstaller 打包器"""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.project_root = Path.cwd()

    def clean_build(self) -> None:
        """清理历史构建产物"""
        print("🧹 清理历史构建产物...")

        dirs_to_clean = ["build", "dist"]
        files_to_clean = list(self.project_root.glob("*.spec"))

        for dir_name in dirs_to_clean:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  ✓ 删除目录: {dir_name}")

        for spec_file in files_to_clean:
            spec_file.unlink()
            print(f"  ✓ 删除文件: {spec_file.name}")

    def detect_project_structure(self) -> None:
        """自动检测项目结构"""
        print("🔍 检测项目结构...")

        # 检测源码目录
        src_dirs = ["src", "source", "app", "lib"]
        for src_dir in src_dirs:
            if (self.project_root / src_dir).exists():
                self.config.paths.append(src_dir)
                print(f"  ✓ 添加源码路径: {src_dir}")
                break

        # 检测资源目录
        resource_dirs = ["configs", "data", "assets", "resources", "templates"]
        for res_dir in resource_dirs:
            res_path = self.project_root / res_dir
            if res_path.exists():
                self.config.data_files.append((res_dir, res_dir))
                print(f"  ✓ 添加资源目录: {res_dir}")

    def detect_gui_framework(self) -> None:
        """自动检测 GUI 框架"""
        print("🖼️  检测 GUI 框架...")

        gui_imports = {
            "PyQt6": "PyQt6",
            "PySide6": "PySide6",
            "PyQt5": "PyQt5",
            "tkinter": "tkinter",
            "wx": "wxPython",
            "kivy": "Kivy"
        }

        # 读取主脚本检测导入
        try:
            with open(self.config.main_script, "r", encoding="utf-8") as f:
                content = f.read()
                for module, package in gui_imports.items():
                    if module in content or package.lower() in content.lower():
                        print(f"  ✓ 检测到 GUI 框架: {package}")
                        self.config.is_gui = True
                        self.config.hidden_imports.extend([
                            f"{package}.QtWidgets",
                            f"{package}.QtCore",
                            f"{package}.QtGui"
                        ] if "Qt" in package else [package])
                        break
        except Exception as e:
            print(f"  ⚠ 无法读取主脚本: {e}")

    def build_command(self) -> List[str]:
        """构建 PyInstaller 命令"""
        cmd = ["pyinstaller"]

        # 基本参数
        if self.config.onefile:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        # GUI/Console 参数
        if self.config.is_gui:
            cmd.append("--windowed")
        else:
            cmd.append("--console")

        # 应用名称
        cmd.extend(["--name", self.config.app_name])

        # 清理参数
        if self.config.clean:
            cmd.append("--clean")

        # 调试模式
        if self.config.debug:
            cmd.append("--debug all")

        # 图标
        if self.config.icon and os.path.exists(self.config.icon):
            cmd.extend(["--icon", self.config.icon])

        # 搜索路径
        for path in self.config.paths:
            cmd.extend(["--paths", path])

        # 资源文件
        for src, dest in self.config.data_files:
            cmd.extend(["--add-data", f"{src}{self.config.separator}{dest}"])

        # 隐式导入
        for imp in self.config.hidden_imports:
            cmd.extend(["--hidden-import", imp])

        # 排除模块
        for exc in self.config.excludes:
            cmd.extend(["--exclude-module", exc])

        # 主入口脚本
        cmd.append(self.config.main_script)

        return cmd

    def build(self) -> bool:
        """执行打包"""
        print("\n🚀 开始打包...")
        print(f"  应用名称: {self.config.app_name}")
        print(f"  应用类型: {'GUI' if self.config.is_gui else 'CLI'}")
        print(f"  打包模式: {'单文件' if self.config.onefile else '目录'}")
        print(f"  平台系统: {self.config.platform}\n")

        # 清理历史构建
        if self.config.clean:
            self.clean_build()

        # 构建命令
        cmd = self.build_command()

        # 打印命令
        print("📦 执行命令:")
        print(f"  {' '.join(cmd)}\n")

        # 执行打包
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=not self.config.debug,
                text=True
            )

            if not self.config.debug:
                print("\n✅ 打包成功!")
                print(f"  可执行文件位置: dist/{self.config.app_name}")

                # 显示文件大小
                exe_path = Path(f"dist/{self.config.app_name}")
                if exe_path.exists():
                    size = exe_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    print(f"  文件大小: {size_mb:.2f} MB")

            return True

        except subprocess.CalledProcessError as e:
            print(f"\n❌ 打包失败!")
            if e.stdout:
                print(f"  标准输出:\n{e.stdout}")
            if e.stderr:
                print(f"  错误输出:\n{e.stderr}")
            return False

        except FileNotFoundError:
            print("\n❌ 错误: 未找到 PyInstaller")
            print("  请先安装: pip install pyinstaller")
            return False


def load_config_from_yaml(config_path: str) -> BuildConfig:
    """从 YAML 文件加载配置（需要 PyYAML）"""
    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = BuildConfig()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    except ImportError:
        print("⚠ 警告: 未安装 PyYAML，使用默认配置")
        print("  安装: pip install pyyaml")
        return BuildConfig()
    except Exception as e:
        print(f"⚠ 警告: 读取配置文件失败: {e}")
        return BuildConfig()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PyInstaller 通用打包脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build_template.py                    # 默认配置打包
  python build_template.py --gui             # GUI 应用打包
  python build_template.py --cli             # CLI 应用打包
  python build_template.py --onedir          # 打包为目录
  python build_template.py --debug           # 调试模式打包
  python build_template.py --no-clean        # 不清理历史构建
        """
    )

    parser.add_argument("--main", default="main.py", help="主入口脚本 (默认: main.py)")
    parser.add_argument("--name", help="应用名称")
    parser.add_argument("--gui", action="store_true", help="GUI 应用打包")
    parser.add_argument("--cli", action="store_true", help="CLI 应用打包")
    parser.add_argument("--onedir", action="store_true", help="打包为目录而非单文件")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--no-clean", action="store_true", help="不清理历史构建")
    parser.add_argument("--icon", help="图标文件路径")
    parser.add_argument("--config", help="从 YAML 文件加载配置")
    parser.add_argument("--add-data", action="append", help="添加资源文件 (格式: src;dest)")
    parser.add_argument("--hidden-import", action="append", help="添加隐式导入模块")
    parser.add_argument("--exclude", action="append", help="排除模块")

    args = parser.parse_args()

    # 加载配置
    if args.config:
        config = load_config_from_yaml(args.config)
    else:
        config = BuildConfig()

    # 命令行参数覆盖配置
    if args.main:
        config.main_script = args.main
    if args.name:
        config.app_name = args.name
    if args.gui:
        config.is_gui = True
    if args.cli:
        config.is_gui = False
    if args.onedir:
        config.onefile = False
    if args.debug:
        config.debug = True
    if args.no_clean:
        config.clean = False
    if args.icon:
        config.icon = args.icon
    if args.add_data:
        for item in args.add_data:
            parts = item.split(config.separator)
            if len(parts) == 2:
                config.data_files.append((parts[0], parts[1]))
    if args.hidden_import:
        config.hidden_imports.extend(args.hidden_import)
    if args.exclude:
        config.excludes.extend(args.exclude)

    # 验证配置
    if not config.validate():
        sys.exit(1)

    # 创建打包器
    builder = Builder(config)

    # 自动检测项目结构
    builder.detect_project_structure()

    # 检测 GUI 框架
    if not args.gui and not args.cli:
        builder.detect_gui_framework()

    # 执行打包
    success = builder.build()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
