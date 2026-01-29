"""
pytest 配置文件和共享 fixtures
为所有测试提供公共的测试数据和工具函数
"""

import sys
from pathlib import Path
from typing import Generator

import pytest

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def project_root() -> Path:
    """项目根目录"""
    return Path(__file__).parent.parent


@pytest.fixture
def configs_dir(project_root: Path) -> Path:
    """配置文件目录"""
    return project_root / "configs"


@pytest.fixture
def v8_config_path(configs_dir: Path) -> Path:
    """V8协议配置文件路径"""
    return configs_dir / "v8" / "protocol.yaml"


@pytest.fixture
def xiaoju_config_path(configs_dir: Path) -> Path:
    """小桔协议配置文件路径"""
    return configs_dir / "xiaoju" / "protocol.yaml"


@pytest.fixture
def yunwei_config_path(configs_dir: Path) -> Path:
    """运维协议配置文件路径"""
    return configs_dir / "yunwei" / "protocol.yaml"


@pytest.fixture
def sinexcel_config_path(configs_dir: Path) -> Path:
    """Sinexcel协议配置文件路径"""
    return configs_dir / "sinexcel" / "protocol.yaml"


@pytest.fixture
def input_logs_dir(project_root: Path) -> Path:
    """输入日志目录"""
    return project_root / "input_logs"


@pytest.fixture
def parsed_log_dir(project_root: Path) -> Path:
    """解析结果目录"""
    return project_root / "parsed_log"


@pytest.fixture
def sample_hex_data() -> bytes:
    """示例十六进制数据"""
    return bytes(
        [
            0xAA,
            0xF5,  # 帧头
            0x00,
            0x02,  # 命令码
            0x00,
            0x01,  # 序列号
            0x01,  # 设备类型
            0x01,  # 地址
            0x01,  # 枪号
            0x01,
            0x02,
            0x03,
            0x04,  # 数据
        ]
    )


@pytest.fixture
def sample_hex_string() -> str:
    """示例十六进制字符串"""
    return "AA F5 00 02 00 01 01 01 01 02 03 04"


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Generator[Path, None, None]:
    """创建临时配置文件"""
    import yaml

    config_data = {
        "meta": {"protocol": "test_protocol", "version": 1, "default_endian": "LE"},
        "compatibility": {"head_len": 11, "tail_len": 2, "frame_head": "AA F5", "head_fields": []},
        "types": {
            "uint8": {"base": "uint", "bytes": 1, "signed": False},
            "uint16": {"base": "uint", "bytes": 2, "signed": False},
        },
        "enums": {"test_enum": {0: "值0", 1: "值1"}},
        "cmds": {
            1: [
                {"len": 1, "name": "字段1", "type": "uint8"},
                {"len": 2, "name": "字段2", "type": "uint16"},
            ],
            2: [
                {"len": 1, "name": "计数", "type": "uint8", "id": "count"},
                {"repeat_by": "count", "fields": [{"len": 1, "name": "重复字段", "type": "uint8"}]},
            ],
        },
    }

    config_file = tmp_path / "test_protocol.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True)

    yield config_file

    # 清理（tmp_path 会自动清理）


@pytest.fixture
def invalid_config_file(tmp_path: Path) -> Generator[Path, None, None]:
    """创建无效的临时配置文件（用于测试错误处理）"""
    import yaml

    # 缺少必需字段的配置
    invalid_data = {
        "meta": {
            # 缺少 protocol 字段
            "version": 1
        },
        "types": {},
        "enums": {},
        "cmds": {},
    }

    config_file = tmp_path / "invalid_protocol.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(invalid_data, f, allow_unicode=True)

    yield config_file


# pytest 配置
def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "slow: 慢速测试标记")
