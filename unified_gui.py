#!/usr/bin/env python3
# unified_gui.py
"""
文件名称: unified_gui.py
内容摘要: V8Parse 统一 GUI 程序入口
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-10

使用方法:
    python unified_gui.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """检查依赖是否已安装"""
    missing = []

    try:
        import PySide6
    except ImportError:
        missing.append("PySide6")

    try:
        import yaml
    except ImportError:
        missing.append("PyYAML")

    if missing:
        print("缺少必要的依赖库:")
        for lib in missing:
            print(f"  - {lib}")
        print("\n请运行以下命令安装:")
        print("  pip install -r requirements-gui.txt")
        sys.exit(1)


def main():
    """主函数"""
    check_dependencies()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName("V8Parse")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("V8Parse")

    # 设置默认字体
    font = QFont()
    font.setFamily("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)

    # 设置样式
    app.setStyle("Fusion")

    # 创建统一主窗口
    from gui.unified_main_window import UnifiedMainWindow
    window = UnifiedMainWindow()
    window.show()

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
