# 测试指南

**项目**: V8Parse - 多协议通信报文解析工具
**测试框架**: pytest
**当前覆盖率**: 78%
**目标覆盖率**: 90%

---

## 快速开始

### 运行所有测试

```bash
pytest
```

### 运行特定测试

```bash
# 运行单个测试文件
pytest tests/test_yaml_field_parser.py

# 运行单个测试类
pytest tests/test_yaml_field_parser.py::TestBasicTypes

# 运行单个测试用例
pytest tests/test_yaml_field_parser.py::TestBasicTypes::test_uint8_le

# 运行多个测试文件
pytest tests/test_yaml_field_parser.py tests/test_yaml_cmdformat.py
```

### 生成覆盖率报告

```bash
# 终端报告（显示未覆盖的行号）
pytest --cov=src --cov-report=term-missing

# HTML报告（生成详细的HTML覆盖率报告）
pytest --cov=src --cov-report=html

# 同时生成终端和HTML报告
pytest --cov=src --cov-report=term-missing --cov-report=html

# 查看HTML覆盖率报告
# Windows:
start htmlcov/index.html

# Linux/macOS:
open htmlcov/index.html
```

### 调试测试

```bash
# 显示打印输出
pytest -s

# 显示详细输出
pytest -v

# 遇到第一个失败就停止
pytest -x

# 只运行失败的测试
pytest --lf

# 进入调试器（需要在失败时）
pytest --pdb

# 降低日志级别
pytest --log-cli-level=INFO
```

---

## 测试规范

### AAA 模式

所有测试用例遵循 **Arrange-Act-Assert** 模式：

```python
def test_example():
    # Arrange - 准备测试数据和环境
    input_data = prepare_data()
    expected_result = create_expected()

    # Act - 执行被测试的功能
    actual_result = function_under_test(input_data)

    # Assert - 验证结果
    assert actual_result == expected_result
```

**示例**：

```python
def test_uint8_le():
    """测试小端序 uint8 解析"""
    # Arrange
    data = bytes([0x12, 0x34])
    field_def = create_field_def(len=1, name="test", type="uint8")
    parser = YamlFieldParser()

    # Act
    result = parser.parse_field(data, 0, field_def, "LE")

    # Assert
    assert result["value"] == 0x12
    assert result["name"] == "test"
```

### 测试命名规范

**测试文件命名**：
- 格式：`test_<module_name>.py`
- 示例：`test_yaml_field_parser.py`、`test_yaml_cmdformat.py`

**测试类命名**：
- 格式：`Test<ClassName>` 或 `Test<FeatureName>`
- 示例：`TestBasicTypes`、`TestTimeParsing`、`TestBitfieldParsing`

**测试方法命名**：
- 格式：`test_<specific_behavior>`
- 示例：`test_uint8_le`、`test_bcd_byte_to_int`、`test_parse_cp56time2a`

**测试描述**：
- 每个测试函数应有清晰的文档字符串
- 使用中文注释说明测试意图
- 格式：`"""测试<功能>的<场景>"""`

```python
def test_parse_field_with_scale():
    """测试字段解析时的数值缩放功能"""
    # 测试代码...
```

### Fixtures 使用

优先使用 `conftest.py` 中定义的共享 fixtures：

```python
# 使用共享 fixture
def test_with_config_fixture(v8_config):
    """使用 v8_config fixture 测试配置加载"""
    parser = YamlCmdFormat(v8_config)
    assert parser.get_cmd_ids() == [1, 2, 3]
```

**可用的共享 fixtures**：

- `v8_config`: V8 协议配置
- `sample_config`: 简单的示例配置
- `field_parser`: 字段解析器实例
- `byte_builder`: 字节数据构建器

---

## 测试结构

### 目录结构

```
tests/
├── conftest.py                          # 共享 fixtures
├── helpers/                             # 测试辅助工具
│   └── byte_data_builder.py             # 字节数据构建器
├── test_yaml_field_parser.py            # 字段解析器测试
├── test_yaml_cmdformat.py               # 命令格式管理器测试
├── test_yaml_config.py                  # YAML配置加载器测试
├── test_protocol_data_extractor.py      # 数据提取器测试
├── test_protocol_parser.py              # 协议解析器测试
├── test_protocol_output_formatter.py    # 输出格式化器测试
├── test_yaml_unified_protocol_integration.py  # 集成测试
└── test_validate_configs.py             # 配置验证测试
```

### 测试分类

**单元测试**：
- 测试单个函数或类的行为
- 不依赖外部资源（文件、网络等）
- 快速执行

**集成测试**：
- 测试多个组件协同工作
- 可能依赖配置文件
- 执行时间较长

**测试标记**（可选）：

```python
import pytest

@pytest.mark.unit
def test_single_function():
    """单元测试标记"""
    pass

@pytest.mark.integration
def test_multiple_components():
    """集成测试标记"""
    pass

@pytest.mark.slow
def test_slow_operation():
    """慢速测试标记"""
    pass
```

使用标记运行测试：

```bash
# 只运行单元测试
pytest -m unit

# 跳过慢速测试
pytest -m "not slow"
```

---

## 添加新测试

### 步骤

1. **创建测试文件**

   在 `tests/` 目录下创建 `test_<module_name>.py`

2. **导入必要的模块**

   ```python
   import pytest
   from src.yaml_field_parser import YamlFieldParser
   from src.yaml_config import FieldDef
   ```

3. **编写测试类**

   ```python
   class TestNewFeature:
       """测试新功能"""

       def test_basic_behavior(self):
           """测试基本行为"""
           # Arrange
           # Act
           # Assert
           pass
       ```

4. **运行测试**

   ```bash
   pytest tests/test_new_feature.py -v
   ```

5. **检查覆盖率**

   ```bash
   pytest tests/test_new_feature.py --cov=src.module --cov-report=term-missing
   ```

6. **确保通过**

   - 所有测试用例通过
   - 覆盖率提升
   - 代码符合规范

### 测试最佳实践

**DO（应该做的）**：

- ✅ 使用 AAA 模式组织代码
- ✅ 使用中文注释说明测试意图
- ✅ 每个测试只测试一个行为
- ✅ 使用有意义的测试名称
- ✅ 使用 fixtures 复用测试数据
- ✅ 测试边界情况和异常情况
- ✅ 保持测试简单和独立

**DON'T（不应该做的）**：

- ❌ 在测试中使用复杂的逻辑
- ❌ 测试多个行为在一个测试中
- ❌ 依赖测试执行顺序
- ❌ 使用魔法数字和字符串
- ❌ 忽略失败的测试
- ❌ 编写过于复杂的测试

---

## 测试覆盖率

### 当前覆盖率状态

**整体覆盖率：78%**

核心模块覆盖率：

| 模块 | 语句数 | 覆盖率 | 状态 |
|------|--------|--------|------|
| yaml_field_parser.py | 314 | 92% | ✅ |
| yaml_cmdformat.py | 47 | 100% | ✅ |
| yaml_config.py | 195 | 90% | ✅ |
| yaml_unified_protocol.py | 87 | 92% | ✅ |
| protocol_data_extractor.py | 61 | 100% | ✅ |
| protocol_parser.py | 122 | 89% | ✅ |
| protocol_output_formatter.py | 109 | 94% | ✅ |
| validate_configs.py | 132 | 98% | ✅ |
| time_parser.py | 108 | 94% | ✅ |
| log_scanner.py | 177 | 51% | ⚠️ |
| m_print.py | 291 | 37% | ⚠️ |

### 提升覆盖率策略

1. **识别未覆盖代码**

   ```bash
   pytest --cov=src --cov-report=term-missing
   ```

2. **分析未覆盖原因**

   - 是否为边界情况？
   - 是否为错误处理路径？
   - 是否为废弃代码？
   - 是否为难以测试的代码？

3. **补充测试用例**

   - 添加边界测试
   - 添加异常测试
   - 添加集成测试

4. **验证覆盖率提升**

   ```bash
   pytest --cov=src --cov-report=term-missing --cov-report=html
   ```

---

## 常见问题

### Q: 如何测试文件操作？

**A**: 使用 `tmp_path` fixture：

```python
def test_file_operations(tmp_path):
    """测试文件操作"""
    # 创建临时文件
    test_file = tmp_path / "test.log"
    test_file.write_text("test content")

    # 测试文件读取
    result = read_file(str(test_file))
    assert result == "test content"
```

### Q: 如何测试异常情况？

**A**: 使用 `pytest.raises`：

```python
def test_invalid_input():
    """测试无效输入"""
    with pytest.raises(ValueError, match="无效的字段类型"):
        parser.parse_field(data, 0, invalid_field_def, "LE")
```

### Q: 如何 Mock 依赖？

**A**: 使用 `unittest.mock`：

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """测试 Mock 依赖"""
    mock_parser = Mock()
    mock_parser.parse.return_value = {"value": 123}

    result = process_data(mock_parser, data)
    assert result == 123
    mock_parser.parse.assert_called_once()
```

### Q: 测试运行太慢怎么办？

**A**:
- 使用 `pytest -m "not slow"` 跳过慢速测试
- 使用 Mock 避免文件 I/O
- 并行运行测试（安装 `pytest-xdist`）：`pytest -n auto`

---

## 附录：测试命令参考

### 基础命令

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_yaml_field_parser.py

# 运行特定类
pytest tests/test_yaml_field_parser.py::TestBasicTypes

# 运行特定测试
pytest tests/test_yaml_field_parser.py::TestBasicTypes::test_uint8_le
```

### 输出控制

```bash
# 详细输出
pytest -v

# 显示打印输出
pytest -s

# 简洁输出
pytest -q

# 只显示失败测试的详细信息
pytest -tb=short
```

### 测试选择

```bash
# 只运行失败的测试
pytest --lf

# 从第一个失败开始
pytest -x

# 运行上次失败的测试（如果上次全部通过则运行全部）
pytest --ff

# 运行匹配的测试
pytest -k "test_uint"
```

### 覆盖率

```bash
# 终端覆盖率报告
pytest --cov=src --cov-report=term-missing

# HTML覆盖率报告
pytest --cov=src --cov-report=html

# 组合报告
pytest --cov=src --cov-report=term-missing --cov-report=html
```

### 调试

```bash
# 进入调试器
pytest --pdb

# 失败时进入调试器
pytest --pdb -x

# 显示本地变量
pytest -l
```

---

## 相关文档

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-cov 覆盖率工具](https://pytest-cov.readthedocs.io/)
- [项目 README.md](../README.md)
- [CLAUDE.md 开发指南](../CLAUDE.md)
- [测试完善计划](../docs/测试完善计划.md)

---

**最后更新**: 2026-01-28
**维护者**: V8Parse 开发团队
