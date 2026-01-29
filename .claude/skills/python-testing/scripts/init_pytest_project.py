#!/usr/bin/env python3
"""
pytest 项目初始化脚本
自动创建测试目录结构和配置文件
"""

import os
import sys
from pathlib import Path


def create_directory_structure(project_root: Path):
    """创建标准测试目录结构"""

    directories = [
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/functional",
        "tests/data",
    ]

    print("创建目录结构...")
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

        # 创建 __init__.py
        init_file = full_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Test package\n")
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ⊙ {dir_path}/ (已存在)")


def create_pyproject_toml(project_root: Path):
    """创建或更新 pyproject.toml"""

    config_file = project_root / "pyproject.toml"
    pytest_config = """

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (slower, may use external resources)",
    "functional: Functional tests (end-to-end)",
    "slow: Slow running tests",
    "network: Tests requiring network access"
]

addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "-v"
]

log_cli = true
log_cli_level = "INFO"
log_cli_format = "%(asctime)s [%(levelname)8s] %(message)s"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"

[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/__init__.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:"
]
"""

    print("\n配置 pyproject.toml...")
    if config_file.exists():
        # 检查是否已包含 pytest 配置
        content = config_file.read_text(encoding='utf-8')
        if "[tool.pytest.ini_options]" in content:
            print("  ⊙ pyproject.toml 已包含 pytest 配置")
            return

        # 追加配置
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(pytest_config)
        print("  ✓ pyproject.toml 已更新")
    else:
        config_file.write_text(f"[tool.poetry]\nname = \"project\"\nversion = \"0.1.0\"\n{pytest_config}", encoding='utf-8')
        print("  ✓ pyproject.toml 已创建")


def create_pytest_ini(project_root: Path):
    """创建 pytest.ini（如果 pyproject.toml 不存在）"""

    config_file = project_root / "pytest.ini"

    if config_file.exists():
        print("\n  ⊙ pytest.ini 已存在")
        return

    print("\n创建 pytest.ini...")
    config_content = """[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower)
    functional: Functional tests (end-to-end)
    slow: Slow running tests
    network: Tests requiring network access

addopts =
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    -v

log_cli = true
log_cli_level = INFO
"""
    config_file.write_text(config_content, encoding='utf-8')
    print("  ✓ pytest.ini 已创建")


def create_conftest(project_root: Path):
    """创建 conftest.py"""

    conftest_file = project_root / "tests" / "conftest.py"

    if conftest_file.exists():
        print("\n  ⊙ tests/conftest.py 已存在")
        return

    print("\n创建 tests/conftest.py...")
    conftest_content = '''"""
pytest 共享 fixtures 和配置
"""

import pytest
import sys
from pathlib import Path


# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def test_data_dir():
    """返回测试数据目录"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture(scope="function")
def sample_config():
    """返回测试配置"""
    return {
        "debug": True,
        "log_level": "DEBUG",
        "max_retries": 3
    }


def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
'''
    conftest_file.write_text(conftest_content, encoding='utf-8')
    print("  ✓ tests/conftest.py 已创建")


def create_example_test(project_root: Path):
    """创建示例测试文件"""

    test_file = project_root / "tests" / "test_example.py"

    if test_file.exists():
        print("\n  ⊙ tests/test_example.py 已存在")
        return

    print("\n创建示例测试文件...")
    example_content = '''"""
示例测试文件
"""

import pytest


@pytest.mark.unit
def test_example():
    """示例测试"""
    assert True


@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    """参数化测试示例"""
    assert input * 2 == expected
'''
    test_file.write_text(example_content, encoding='utf-8')
    print("  ✓ tests/test_example.py 已创建")


def create_gitignore(project_root: Path):
    """更新 .gitignore"""

    gitignore = project_root / ".gitignore"

    pytest_ignore = """
# pytest
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# 测试输出
.pytest_cache/
__pycache__/
"""

    print("\n更新 .gitignore...")
    if gitignore.exists():
        content = gitignore.read_text(encoding='utf-8')
        if ".pytest_cache/" in content:
            print("  ⊙ .gitignore 已包含 pytest 配置")
            return

        with open(gitignore, 'a', encoding='utf-8') as f:
            f.write(pytest_ignore)
        print("  ✓ .gitignore 已更新")
    else:
        gitignore.write_text(pytest_ignore, encoding='utf-8')
        print("  ✓ .gitignore 已创建")


def main():
    """主函数"""

    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        project_path = Path.cwd()

    print(f"初始化 pytest 项目: {project_path}")
    print("=" * 50)

    if not project_path.exists():
        print(f"错误: 目录不存在 - {project_path}")
        sys.exit(1)

    # 检查是否为项目根目录
    indicators = ["src", "pyproject.toml", "setup.py", ".git"]
    is_project_root = any((project_path / ind).exists() for ind in indicators)

    if not is_project_root:
        print("警告: 当前目录可能不是项目根目录")
        response = input("是否继续? (y/N): ")
        if response.lower() != 'y':
            print("取消操作")
            sys.exit(0)

    try:
        # 创建目录结构
        create_directory_structure(project_path)

        # 创建配置文件（优先使用 pyproject.toml）
        if (project_path / "pyproject.toml").exists() or os.path.exists(project_path / "pyproject.toml"):
            create_pyproject_toml(project_path)
        else:
            create_pytest_ini(project_path)

        # 创建其他文件
        create_conftest(project_path)
        create_example_test(project_path)
        create_gitignore(project_path)

        print("\n" + "=" * 50)
        print("✓ pytest 项目初始化完成!")
        print("\n后续步骤:")
        print("  1. 安装依赖: pip install pytest pytest-cov pytest-mock")
        print("  2. 运行测试: pytest")
        print("  3. 查看覆盖率: pytest --cov=src --cov-report=html")

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
