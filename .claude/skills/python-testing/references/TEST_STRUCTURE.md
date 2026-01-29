# 测试文件结构与组织

## 文件命名与组织规则

| 测试类型 | 文件命名 | 目录结构 | 示例 |
|---------|---------|---------|------|
| 单元测试 | `test_<module>.py` | `tests/unit/` | `test_user_manager.py` |
| 集成测试 | `test_<feature>_integration.py` | `tests/integration/` | `test_api_integration.py` |
| 功能测试 | `test_<feature>_functional.py` | `tests/functional/` | `test_login_functional.py` |

**重要：** 测试文件必须以 `test_` 开头，测试函数必须以 `test_` 开头

## 项目目录结构示例

```
project/
├── src/
│   ├── user/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── models.py
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # 共享 fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_user_manager.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_api_integration.py
│   └── functional/
│       ├── __init__.py
│       └── test_login_functional.py
├── pyproject.toml               # pytest 配置
└── requirements.txt
```

## pytest 配置

### pyproject.toml 配置

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# 标记定义
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "functional: Functional tests",
    "slow: Slow running tests",
    "network: Tests requiring network access"
]

# 覆盖率配置
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=85"
]

# 日志配置
log_cli = true
log_cli_level = "INFO"
log_cli_format = "%(asctime)s [%(levelname)8s] %(message)s"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"
```

### pytest.ini 配置（替代方案）

```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests

addopts =
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85
```

## conftest.py 使用

**共享 fixtures 和测试配置：**

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """返回测试数据目录"""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="function")
def temp_db(tmp_path):
    """创建临时数据库"""
    db_path = tmp_path / "test.db"
    # 初始化数据库
    db = create_test_database(db_path)
    yield db
    # 清理
    db.cleanup()

@pytest.fixture
def sample_config():
    """返回测试配置"""
    return {
        "debug": True,
        "log_level": "DEBUG",
        "max_retries": 3
    }
```

## 测试标记使用

**定义标记：**
```python
import pytest

@pytest.mark.unit
def test_calculator_add():
    assert 2 + 2 == 4

@pytest.mark.integration
@pytest.mark.slow
def test_database_integration():
    # 集成测试代码
    pass

@pytest.mark.network
def test_api_call():
    # 需要网络的测试
    pass
```

**运行特定标记的测试：**
```bash
pytest -m unit              # 只运行单元测试
pytest -m "not slow"        # 跳过慢速测试
pytest -m "network or slow" # 运行网络或慢速测试
```

## 测试发现规则

**pytest 自动发现测试的规则：**

1. **文件发现：** 匹配 `test_*.py` 或 `*_test.py`
2. **类发现：** 匹配 `Test*` 开头的类（无 `__init__` 方法）
3. **函数发现：** 匹配 `test_*` 开头的函数

**示例：**
```
tests/
├── test_utils.py           # ✓ 会被发现
├── utils_test.py           # ✓ 会被发现
├── test_helper.py          # ✓ 会被发现
├── helper.py               # ✗ 不会被发现
└── fixtures.py             # ✗ 不会被发现
```

## 测试类组织

**相关测试方法组织到类中：**

```python
class TestUserManager:
    """用户管理器测试"""

    def test_create_user(self, sample_user):
        assert sample_user.id is not None

    def test_delete_user(self, sample_user, db):
        db.delete(sample_user)
        assert db.get_user(sample_user.id) is None

    def test_update_user_email(self, sample_user, db):
        sample_user.email = "new@example.com"
        db.save(sample_user)
        updated = db.get_user(sample_user.id)
        assert updated.email == "new@example.com"
```
