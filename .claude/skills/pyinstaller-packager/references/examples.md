# PyInstaller 打包示例

本文档提供各种应用场景的完整打包示例。

## 示例 1：PySide6 GUI 应用

### 项目结构
```
myapp/
├── main.py              # 主入口
├── src/
│   ├── ui/
│   └── core/
├── configs/
│   └── app.yaml
└── requirements.txt
```

### 打包命令
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --name MyApp ^
  --paths src ^
  --add-data "configs;configs" ^
  --hidden-import PySide6.QtWidgets ^
  --hidden-import PySide6.QtCore ^
  main.py
```

### main.py 路径处理
```python
import sys
import os
from PySide6.QtWidgets import QApplication

def resource_path(relative_path):
    """获取打包后的资源文件绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 确保模块导入
bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
sys.path.insert(0, bundle_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 加载配置文件
    config_path = resource_path("configs/app.yaml")
    # ... 应用逻辑
```

## 示例 2：纯 CLI 应用

### 项目结构
```
cli_tool/
├── main.py
├── src/
│   ├── parsers.py
│   └── utils.py
└── requirements.txt
```

### 打包命令
```bash
pyinstaller ^
  --onefile ^
  --console ^
  --name cli_tool ^
  --paths src ^
  main.py
```

## 示例 3：混合应用（GUI + CLI）

### 项目结构
```
hybrid_app/
├── main.py
├── gui.py
├── cli.py
├── src/
└── requirements.txt
```

### 打包命令
```bash
# 打包为 GUI 应用（默认）
pyinstaller ^
  --onefile ^
  --windowed ^
  --name HybridApp ^
  main.py

# 打包为 CLI 应用（通过命令行参数）
pyinstaller ^
  --onefile ^
  --console ^
  --name HybridAppCLI ^
  main.py
```

### main.py 动态窗口控制
```python
import sys

def main():
    # 检测命令行参数
    if "--cli" in sys.argv:
        # CLI 模式：显示控制台
        from cli import run_cli
        run_cli()
    else:
        # GUI 模式：隐藏控制台（已通过 --windowed 实现）
        from gui import run_gui
        run_gui()

if __name__ == "__main__":
    main()
```

## 示例 4：包含多个数据目录的应用

### 项目结构
```
data_app/
├── main.py
├── data/
│   ├── templates/
│   └── assets/
├── configs/
└── requirements.txt
```

### 打包命令
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --name DataApp ^
  --add-data "data/templates;data/templates" ^
  --add-data "data/assets;data/assets" ^
  --add-data "configs;configs" ^
  main.py
```

## 示例 5：使用图标的应用

### Windows 打包
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --icon=assets/icon.ico ^
  --name MyApp ^
  main.py
```

### macOS 打包
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --icon=assets/icon.icns ^
  --name MyApp ^
  main.py
```

## 示例 6：带有插件系统的应用

### 项目结构
```
plugin_app/
├── main.py
├── plugins/
│   ├── plugin1.py
│   └── plugin2.py
└── requirements.txt
```

### 打包命令
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --name PluginApp ^
  --add-data "plugins;plugins" ^
  --hidden-import plugin1 ^
  --hidden-import plugin2 ^
  main.py
```

### main.py 插件加载
```python
import sys
import os
import importlib.util

def load_plugins():
    """动态加载插件"""
    plugins_dir = resource_path("plugins")

    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            plugin_name = filename[:-3]
            plugin_path = os.path.join(plugins_dir, filename)

            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
```

## 示例 7：多进程应用

### 打包命令
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --name MultiprocessApp ^
  --hidden-import multiprocessing ^
  main.py
```

### main.py 多进程处理
```python
import multiprocessing
import sys

def worker():
    """工作进程"""
    # 必须重新初始化 sys._MEIPASS
    if hasattr(sys, 'frozen'):
        sys._MEIPASS = sys._MEIPASS

if __name__ == "__main__":
    multiprocessing.freeze_support()  # 必须添加
    # ... 启动多进程
```

## 示例 8：使用 NumPy/Pandas 等科学计算库

### 打包命令
```bash
pyinstaller ^
  --onefile ^
  --console ^
  --name DataAnalysis ^
  --hidden-import numpy ^
  --hidden-import pandas ^
  --hidden-import sklearn ^
  --hidden-import matplotlib ^
  main.py
```

## 常用参数组合

### 最小化打包
```bash
pyinstaller --onefile --clean main.py
```

### 调试模式（保留构建文件）
```bash
pyinstaller --onefile --debug all main.py
```

### 优化打包大小
```bash
pyinstaller --onefile --exclude-module tkinter main.py
```

### UPX 压缩（减小 exe 体积）
```bash
pyinstaller --onefile --upx-dir=path/to/upx main.py
```

## 自动化打包脚本

详见 [build_template.py](../scripts/build_template.py)
