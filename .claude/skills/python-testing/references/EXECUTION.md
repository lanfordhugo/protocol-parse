# 测试执行命令与流程

## 测试执行前置步骤

**1. 确保位于项目根目录**
```bash
cd /path/to/project
```

**2. 激活虚拟环境**
```bash
# venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# conda
conda activate myenv

# poetry
poetry shell
```

**3. 安装测试依赖**
```bash
# pip
pip install -e .[test]

# poetry
poetry install --with dev

# pipenv
pipenv install --dev
```

## 基础测试命令

### 运行所有测试
```bash
pytest
```

### 运行单个测试文件
```bash
pytest tests/unit/test_user_manager.py -v
```

### 运行单个测试函数
```bash
pytest tests/unit/test_user_manager.py::test_create_user -v
```

### 运行单个测试类
```bash
pytest tests/unit/test_user_manager.py::TestUserManager -v
```

### 运行单个测试类的方法
```bash
pytest tests/unit/test_user_manager.py::TestUserManager::test_create_user -v
```

## 覆盖率测试

### 生成覆盖率报告
```bash
# HTML 报告（推荐）
pytest --cov=src --cov-report=html

# 终端报告（显示缺失行）
pytest --cov=src --cov-report=term-missing

# 组合报告
pytest --cov=src --cov-report=html --cov-report=term-missing

# 设置覆盖率最低要求
pytest --cov=src --cov-report=term-missing --cov-fail-under=85
```

### 只测试特定模块的覆盖率
```bash
pytest --cov=src.user --cov=src.api tests/
```

### 排除文件不参与覆盖率计算
```bash
pytest --cov=src --cov-report=html --cov-config=.coveragerc
```

**.coveragerc 配置：**
```ini
[run]
omit =
    */tests/*
    */__init__.py
    */migrations/*
```

## 测试标记过滤

### 运行特定标记的测试
```bash
pytest -m unit                    # 只运行单元测试
pytest -m integration             # 只运行集成测试
pytest -m "not slow"              # 跳过慢速测试
pytest -m "network and not slow"  # 网络+非慢速测试
```

### 跳过特定测试
```python
import pytest

@pytest.mark.skip(reason="暂时跳过")
def test_something():
    pass

@pytest.mark.skipif(sys.version_info < (3, 8), reason="需要 Python 3.8+")
def test_python38_feature():
    pass
```

## 调试选项

### 失败时停止
```bash
pytest -x                    # 第一个失败后停止
pytest -x --tb=short        # 简短的错误信息
```

### 显示详细输出
```bash
pytest -v                   # 详细模式
pytest -vv                  # 更详细的模式
pytest -s                   # 显示 print 输出
```

### 进入调试器
```bash
pytest --pdb                # 失败时进入 pdb
pytest --trace              # 每个测试前进入调试器
pytest --pdbcls=IPython.terminal.debugger:TerminalPdb  # 使用 IPython
```

### 只运行上次失败的测试
```bash
pytest --lf                 # last-failed
pytest --ff                 # failed-first（先运行失败的）
```

## 并行测试执行

### 安装 pytest-xdist
```bash
pip install pytest-xdist
```

### 并行运行测试
```bash
pytest -n auto              # 自动检测 CPU 核心数
pytest -n 4                 # 使用 4 个进程
pytest -n logical           # 使用逻辑 CPU 数量
```

## 日志捕获

### 捕获日志
```bash
pytest --log-cli-level=INFO
pytest --log-cli-level=DEBUG
```

### 实时显示日志
```bash
pytest -s --log-cli-level=INFO
pytest --log-cli-level=DEBUG --log-cli-format="%(asctime)s [%(levelname)8s] %(message)s"
```

## 常用命令组合

### 快速开发测试
```bash
# 快速反馈，第一个失败后停止
pytest -x -v tests/unit/

# 跳过慢速测试，详细输出
pytest -v -m "not slow"

# 并行运行，详细输出
pytest -v -n auto -m "not slow"
```

### 完整 CI 测试
```bash
# 运行所有测试，生成覆盖率报告，设置最低要求
pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=85 -v
```

### 调试特定测试
```bash
# 单个测试，详细输出，print 可见
pytest -s -v tests/unit/test_user.py::test_create_user

# 失败时进入调试器
pytest --pdb tests/unit/test_user.py::test_create_user
```

## 禁止的操作

| 禁止操作 | 原因 | 正确做法 |
|---------|------|---------|
| 在未激活虚拟环境时运行测试 | 可能使用错误的 Python 版本 | 先激活虚拟环境 |
| 忽略测试失败直接提交代码 | 破坏代码质量 | 修复所有失败 |
| 运行测试时不检查覆盖率 | 无法验证测试充分性 | 始终检查覆盖率 |
| 使用过时的测试依赖版本 | 可能导致测试不稳定 | 定期更新依赖 |

## CI/CD 集成示例

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .[test]
      - run: pytest --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=85
```

### GitLab CI
```yaml
test:
  script:
    - pip install -e .[test]
    - pytest --cov=src --cov-report=term-missing --cov-fail-under=85
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

## 执行策略总结

| 场景 | 推荐命令 |
|------|---------|
| 开发调试 | `pytest -x -v tests/unit/` |
| 快速反馈 | `pytest -m "not slow" -n auto` |
| 完整验证 | `pytest --cov=src --cov-report=html --cov-fail-under=85 -v` |
| 调试失败 | `pytest -s -v <test_file>::<test_function>` |
| CI 环境 | `pytest --cov=src --cov-report=xml --cov-fail-under=85` |
