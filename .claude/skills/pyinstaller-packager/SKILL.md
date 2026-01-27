---
name: pyinstaller-packager
description: Python PyInstaller 打包规范与最佳实践。统一打包参数、依赖管理和构建流程。适用于 GUI 应用（--windowed）、CLI 应用（--console）和混合应用打包。包含项目结构识别、路径兼容性处理（sys._MEIPASS）、平台差异处理和常见问题解决方案。
---

# PyInstaller 打包规范

统一 Python 应用打包流程，确保可执行文件的一致性和可维护性。

## 快速开始

### 基本打包

```bash
# GUI 应用（隐藏控制台）
pyinstaller --onefile --windowed --name MyApp main.py

# CLI 应用（显示控制台）
pyinstaller --onefile --console --name MyApp main.py
```

### 核心参数

- `--onefile`: 打包为单个可执行文件
- `--windowed`: 隐藏控制台（GUI 应用）
- `--console`: 显示控制台（CLI 应用）
- `--name`: 指定可执行文件名
- `--clean`: 清理临时文件和缓存
- `--paths <path>`: 添加模块搜索路径
- `--add-data <src;dest>`: 包含资源文件（Windows 用 `;`，Unix 用 `:`）

## 项目结构识别

| 组件 | 优先查找 |
|------|---------|
| 主入口 | `main.py`、`app.py`、`__main__.py` |
| 打包脚本 | `build.py`、`build.bat`/`build.sh` |
| 依赖清单 | `requirements.txt`（固定版本号） |
| 配置文件 | 通过 `--add-data` 包含 |
| 源码目录 | 使用 `--paths` 指定 |

## 应用类型检测

### GUI 应用

使用 `--windowed`，自动检测框架：
- tkinter、PyQt、PySide、wxPython、Kivy 等

### CLI 应用

使用 `--console` 或默认设置

### 混合应用

根据启动参数动态决定窗口显示，代码中处理控制台创建逻辑

## 路径兼容性

### 主入口必须处理 `sys._MEIPASS`

```python
import sys
import os

def resource_path(relative_path):
    """获取打包后的资源文件绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 确保模块导入
bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
sys.path.insert(0, bundle_dir)
```

## 依赖管理

- **固定版本号**：`requirements.txt` 中使用 `==` 固定版本
- **包含 PyInstaller**：`pyinstaller==6.11.0`
- **检测实际依赖**：使用 `pipreqs` 自动生成

## 构建流程标准

1. 清理历史产物：`build/`、`dist/`、`*.spec`、`__pycache__`
2. 安装固定版本依赖
3. 执行 PyInstaller 命令
4. 验证可执行文件生成
5. 清理中间产物，保留最终 exe

## 平台差异

| 项目 | Windows | Linux/macOS |
|------|---------|-------------|
| `--add-data` 分隔符 | `;` | `:` |
| 可执行文件扩展名 | `.exe` | 无扩展名 |
| 图标格式 | `.ico` | `.icns` (macOS) |

使用 `platform.system()` 检测平台差异

## 常见问题

### 模块导入失败
- 确保 `--paths` 指定源码目录
- 检查 `sys.path` 注入逻辑
- 使用 `--hidden-import` 强制包含模块

### 资源文件缺失
- 使用 `--add-data` 包含所有资源
- 代码中使用 `resource_path()` 获取路径

### 窗口显示异常
- GUI 应用必须使用 `--windowed`
- CLI 应用移除 `--windowed`
- 混合应用在代码中动态控制

## 参考资源

- **完整打包示例**：[examples.md](references/examples.md)
- **构建脚本模板**：[build_template.py](scripts/build_template.py)
- **问题排查指南**：[troubleshooting.md](references/troubleshooting.md)
