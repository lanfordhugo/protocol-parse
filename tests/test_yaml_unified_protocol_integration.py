"""
YamlUnifiedProtocol 集成测试
测试重构后的 YamlUnifiedProtocol 类的完整功能
"""

import os
from datetime import datetime

import pytest

from src.yaml_unified_protocol import YamlUnifiedProtocol


class TestYamlUnifiedProtocolInit:
    """测试 YamlUnifiedProtocol 初始化"""

    def test_init(self, sample_protocol_config, sample_log_file):
        """测试初始化"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        assert protocol.log_file_name == sample_log_file
        assert protocol.protocol_yaml_path == sample_protocol_config
        assert protocol.yaml_format is not None
        assert protocol.yaml_config is not None
        assert protocol.extractor is not None
        assert protocol.parser is not None
        assert protocol.formatter is not None

    def test_init_loads_config(self, sample_protocol_config, sample_log_file):
        """测试初始化时加载配置"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        assert protocol.yaml_config.meta.protocol == "v8"


class TestProgressCallbacks:
    """测试进度回调"""

    def test_set_progress_callback(self, sample_protocol_config, sample_log_file):
        """测试设置进度回调"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        callback_called = []

        def test_callback(current, total):
            callback_called.append((current, total))

        protocol.set_progress_callback(test_callback)
        protocol._emit_progress(50, 100)

        assert len(callback_called) == 1
        assert callback_called[0] == (50, 100)

    def test_set_should_stop(self, sample_protocol_config, sample_log_file):
        """测试设置停止标志"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        assert protocol._check_should_stop() is False

        protocol.set_should_stop(True)
        assert protocol._check_should_stop() is True

        protocol.set_should_stop(False)
        assert protocol._check_should_stop() is False


class TestCommandFilters:
    """测试命令过滤"""

    def test_set_include_cmds(self, sample_protocol_config, sample_log_file):
        """测试设置包含命令"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        cmd_list = [1, 2, 3]
        protocol.set_include_cmds(cmd_list)

        # 验证设置成功（通过检查 parser 的过滤器）
        assert protocol.parser._include_cmds == cmd_list

    def test_set_exclude_cmds(self, sample_protocol_config, sample_log_file):
        """测试设置排除命令"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        cmd_list = [4, 5, 6]
        protocol.set_exclude_cmds(cmd_list)

        assert protocol.parser._exclude_cmds == cmd_list

    def test_set_time_range(self, sample_protocol_config, sample_log_file):
        """测试设置时间范围"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 12, 31, 23, 59, 59)

        protocol.set_time_range(start_time, end_time)

        assert protocol.parser._time_range == (start_time, end_time)


class TestExtractDataFromFile:
    """测试从文件提取数据"""

    def test_extract_data_from_file(self, sample_protocol_config, sample_log_file):
        """测试提取数据"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        data_groups = protocol.extract_data_from_file(sample_log_file)

        assert len(data_groups) > 0
        assert "time" in data_groups[0]
        assert "direction" in data_groups[0]
        assert "data" in data_groups[0]

    def test_extract_data_from_nonexistent_file(self, sample_protocol_config):
        """测试从不存在的文件提取数据"""
        protocol = YamlUnifiedProtocol("nonexistent.log", sample_protocol_config)

        with pytest.raises(IOError):
            protocol.extract_data_from_file("nonexistent.log")


class TestParseDataContent:
    """测试解析数据内容"""

    def test_parse_data_content(self, sample_protocol_config, sample_log_file):
        """测试解析数据内容"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        # 先提取数据
        data_groups = protocol.extract_data_from_file(sample_log_file)

        # 解析数据
        parsed_data = protocol.parse_data_content(data_groups)

        assert isinstance(parsed_data, list)

    def test_parse_data_content_with_filters(self, sample_protocol_config, sample_log_file):
        """测试使用过滤器解析数据"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        # 设置包含过滤器
        protocol.set_include_cmds([1])

        data_groups = protocol.extract_data_from_file(sample_log_file)
        parsed_data = protocol.parse_data_content(data_groups)

        # 验证只有命令ID为1的数据被解析
        for item in parsed_data:
            assert item.get("cmd") == 1


class TestScreenParseData:
    """测试筛选和打印数据"""

    def test_screen_parse_data(self, sample_protocol_config, sample_log_file, tmp_path):
        """测试筛选和打印数据"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        # 准备测试数据
        parse_data = [
            {
                "timestamp": "2024-01-28 10:30:45.123",
                "direction": "Send",
                "terminal_id": 1,
                "cmd": 1,
                "content": {"field1": "value1"},
            }
        ]

        # 性能统计数据（用于验证解析过程）
        _ = {
            "total": [1.5],
            "extract": [0.5],
            "parse": [0.8],
            "screen": [0.2],
            "cmd_counts": {1: 1},
            "errors": 0,
        }

        # 保存到临时目录
        os.makedirs(os.path.join(tmp_path, "parsed_log"), exist_ok=True)
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            output_path = protocol.screen_parse_data(parse_data)

            assert output_path is not None
            assert os.path.exists(output_path)

            # 验证文件内容
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "成功解析 1 条数据" in content
            assert "field1: value1" in content
        finally:
            os.chdir(original_cwd)

    def test_screen_parse_data_empty(self, sample_protocol_config, sample_log_file):
        """测试空数据"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        output_path = protocol.screen_parse_data([])

        assert output_path is None


class TestRun:
    """测试完整运行流程"""

    def test_run_success(self, sample_protocol_config, sample_log_file, tmp_path):
        """测试成功运行"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        # 临时切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            output_path = protocol.run()

            # 验证输出文件
            if output_path:
                assert os.path.exists(output_path)
        finally:
            os.chdir(original_cwd)

    def test_run_with_stop(self, sample_protocol_config, sample_log_file, tmp_path):
        """测试中途停止"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        # 设置立即停止
        protocol.set_should_stop(True)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            output_path = protocol.run()

            # 被停止应该返回 None
            assert output_path is None
        finally:
            os.chdir(original_cwd)


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_backward_compatibility(self, sample_protocol_config, sample_log_file):
        """测试向后兼容的接口"""
        protocol = YamlUnifiedProtocol(sample_log_file, sample_protocol_config)

        # 测试旧的接口仍然可用
        assert hasattr(protocol, "field_parser")
        assert hasattr(protocol, "extract_data_from_file")
        assert hasattr(protocol, "parse_data_content")
        assert hasattr(protocol, "screen_parse_data")
        assert hasattr(protocol, "run")

        # 测试旧的过滤器接口
        protocol.set_include_cmds([1, 2])
        protocol.set_exclude_cmds([3, 4])
        protocol.set_time_range(datetime(2024, 1, 1), datetime(2024, 12, 31))

        # 测试旧的进度回调接口
        progress_updates = []
        protocol.set_progress_callback(lambda c, t: progress_updates.append((c, t)))
        protocol._emit_progress(50, 100)

        assert len(progress_updates) == 1


# Fixtures
@pytest.fixture
def sample_protocol_config():
    """获取示例协议配置文件路径"""
    # 使用项目中的实际配置文件
    config_path = "configs/v8/protocol.yaml"
    if os.path.exists(config_path):
        return config_path
    else:
        pytest.skip(f"示例配置文件不存在: {config_path}")


@pytest.fixture
def sample_log_file(tmp_path):
    """创建示例日志文件"""
    # V8协议的帧头是 AA F5，不是 68 68
    content = """
2024-01-28 10:30:45.123 Send [1] TX:
AA F5 01 00 64 68 04 08 00 01 02 03 04 05 06 07 08 16

2024-01-28 10:30:46.456 Recv [2] RX:
AA F5 02 00 32 68 28 08 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13 14 15 16 17 18 D8
"""
    log_file = tmp_path / "test.log"
    log_file.write_text(content, encoding="utf-8")
    return str(log_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
