# PyInstaller 打包问题排查指南

本文档提供常见问题的诊断和解决方案。

## 模块导入问题

### 问题 1: ModuleNotFoundError

**症状:**
```
ModuleNotFoundError: No module named 'xxx'
```

**诊断步骤:**
1. 检查模块是否在 requirements.txt 中
2. 检查是否使用了 `--paths` 指定源码目录
3. 检查模块是否为动态导入

**解决方案:**
```bash
# 方案 1: 使用 --hidden-import 强制包含
pyinstaller --hidden-import xxx main.py

# 方案 2: 添加源码路径
pyinstaller --paths src main.py

# 方案 3: 多次指定 --hidden-import
pyinstaller --hidden-import package.module --hidden-import package.submodule main.py
```

### 问题 2: 相对导入失败

**症状:**
```
ImportError: attempted relative import with no known parent package
```

**解决方案:**
```python
# 在主入口开头添加
import sys
import os
bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
sys.path.insert(0, bundle_dir)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

## 资源文件问题

### 问题 3: 资源文件找不到

**症状:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'configs/app.yaml'
```

**解决方案:**
```python
import sys
import os

def resource_path(relative_path):
    """获取打包后的资源文件绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境目录
    return os.path.join(os.path.abspath("."), relative_path)

# 使用
config_path = resource_path("configs/app.yaml")
```

### 问题 4: --add-data 路径错误

**Windows vs Unix 分隔符:**
```bash
# Windows
pyinstaller --add-data "src;src" main.py

# Linux/macOS
pyinstaller --add-data "src:src" main.py

# 跨平台 Python 脚本
import platform
sep = ';' if platform.system() == 'Windows' else ':'
```

## GUI 应用问题

### 问题 5: GUI 应用启动后立即退出

**可能原因:**
1. 未使用 `--windowed` 参数
2. 未正确处理异常
3. Qt 事件循环未启动

**解决方案:**
```bash
# 确保使用 --windowed
pyinstaller --onefile --windowed main.py
```

```python
# 在 main.py 中添加异常捕获
import sys
from PySide6.QtWidgets import QApplication

def main():
    try:
        app = QApplication(sys.argv)
        # ... 应用代码
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
```

### 问题 6: Qt 插件缺失（如图片格式、平台插件）

**症状:**
```
QtPlugin: Could not load the Qt platform plugin "windows"
```

**解决方案:**
```bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --hidden-import PySide6.QtWidgets ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  main.py
```

## 性能问题

### 问题 7: 打包后体积过大

**优化方案:**

1. **排除不需要的模块**
```bash
pyinstaller --onefile --exclude-module tkinter --exclude-module matplotlib main.py
```

2. **使用 UPX 压缩**
```bash
pyinstaller --onefile --upx-dir=path/to/upx main.py
```

3. **使用虚拟环境**
```bash
# 创建干净的虚拟环境
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --onefile main.py
```

4. **分析依赖**
```bash
# 使用 pyinstaller 分析器
pyinstaller --onefile --debug all main.py
# 查看 warn-xxx.txt 文件
```

### 问题 8: 启动速度慢

**可能原因:**
1. 解压临时文件到 `sys._MEIPASS`
2. 导入过多模块
3. 初始化逻辑复杂

**解决方案:**
```python
# 延迟导入模块
def heavy_operation():
    import numpy  # 延迟到实际使用时导入
    # ...

# 使用 --onedir 替代 --onefile（更快启动）
pyinstaller --onedir main.py
```

## 多进程问题

### 问题 9: 多进程应用打包后失败

**症状:**
子进程无法启动或找不到模块

**解决方案:**
```python
import multiprocessing

# 必须在 if __name__ == "__main__": 块中
if __name__ == "__main__":
    multiprocessing.freeze_support()  # 必须添加
    # ... 启动多进程
```

## 调试技巧

### 启用调试模式
```bash
pyinstaller --onefile --debug all main.py
```

### 查看警告文件
打包后查看 `build/xxx/warn-xxx.txt`:
- 缺失的模块
- 隐式导入
- 未使用的模块

### 保留构建文件
```bash
# 不清理 build/ 目录
pyinstaller --onefile --noconfirm main.py

# 检查 build/xxx/Analysis-xx.toc 了解打包内容
```

### 运行未打包版本测试
```bash
# 先在开发环境测试
python main.py

# 再在虚拟环境测试
python -m venv test_env
test_env\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 平台特定问题

### Windows

#### UAC 权限问题
```bash
# 创建 manifest 文件请求管理员权限
pyinstaller --onefile --manifest app.manifest main.py
```

#### 杀毒软件误报
- 使用代码签名证书
- 添加排除规则到杀毒软件

### Linux

#### 缺少共享库
```bash
# 使用 ldd 检查依赖
ldd dist/myapp

# 使用 --add-binary 包含共享库
pyinstaller --add-binary "/path/to/lib.so:." main.py
```

### macOS

#### 代码签名
```bash
# ad-hoc 签名
codesign --force --deep --sign - dist/MyApp.app

# 移除隔离属性
xattr -cr dist/MyApp.app
```

## 版本兼容性问题

### Python 版本不匹配
```bash
# 检查 Python 版本
python --version

# 使用与 PyInstaller 兼容的版本
# PyInstaller 6.x 支持 Python 3.8+
```

### PyInstaller 版本问题
```bash
# 固定 PyInstaller 版本
pip install pyinstaller==6.11.0

# 查看兼容性
# https://pyinstaller.org/en/stable/requirements.html
```

## 检查清单

打包前检查:
- [ ] requirements.txt 中所有依赖已固定版本号
- [ ] 所有资源文件路径使用 `resource_path()` 函数
- [ ] 主入口添加了 `sys.path` 注入逻辑
- [ ] GUI 应用使用 `--windowed`，CLI 应用不使用
- [ ] 多进程应用添加 `multiprocessing.freeze_support()`
- [ ] 测试虚拟环境中的依赖

打包后检查:
- [ ] 在干净系统中测试可执行文件
- [ ] 检查 warn-xxx.txt 中的警告
- [ ] 验证所有资源文件可访问
- [ ] 测试所有功能是否正常
- [ ] 检查启动速度和内存占用

## 获取帮助

- PyInstaller 官方文档: https://pyinstaller.org/
- GitHub Issues: https://github.com/pyinstaller/pyinstaller/issues
- Stack Overflow: 标签 `[pyinstaller]`
