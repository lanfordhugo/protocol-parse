# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

V8Parse 是一个基于 **YAML 配置驱动**的多协议通信报文解析工具。核心架构特点是**零代码扩展**：添加新协议只需创建 YAML 配置文件，无需修改任何 Python 代码。

### 核心理念

**配置优先于代码**：所有协议定义、字段类型、枚举映射、过滤规则都通过 YAML 配置实现。CLI 版本无第三方依赖，仅使用 Python 标准库。

### 双入口架构

1. **CLI 版本** (`main.py`): 批量解析日志文件，适合自动化和脚本调用
2. **GUI 版本** (`main_gui.py`): PySide6 桌面应用，提供可视化解析界面和 TCP 实时监控

## 快速参考

### 最常用命令

```bash
# 解析协议日志
python main.py <protocol_name>

# 列出所有可用协议
python main.py --list

# 验证配置
python main.py --validate

# 运行所有测试
python -m pytest tests/ -v

# 启动 GUI
python main_gui.py

# 打包 GUI 应用
python build_gui.py
```

## 常用命令

### CLI 解析工具

```bash
# 解析指定协议的日志文件
python main.py v8              # 解析 V8 协议
python main.py xiaoju          # 解析小桔协议
python main.py yunwei          # 解析运维协议
python main.py sinexcel        # 解析 Sinexcel 协议
python main.py yunkuaichong    # 解析云快充协议
python main.py beijingSanyou   # 解析北京三友协议

# 列出所有可用协议
python main.py --list
python main.py -l

# 验证协议配置
python main.py --validate
python main.py -v

# 单独验证配置（不运行解析）
python src/validate_configs.py --all
python src/validate_configs.py configs/v8/protocol.yaml
```

### 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_yaml_config.py -v
python -m pytest tests/test_bitfield.py -v

# 运行单个测试
python -m pytest tests/test_yaml_config.py::test_meta_parsing -v

# 查看测试覆盖率
python -m pytest tests/ --cov=src --cov-report=html
```

### GUI 应用

```bash
# 启动 GUI 应用
python main_gui.py

# 安装 GUI 依赖
pip install -r requirements-gui.txt

# 打包 GUI 应用（自动清理 build 目录）
python build_gui.py            # 标准打包（自动清理 build/）
python build_gui.py --clean    # 清理后打包
python build_gui.py --debug    # 调试模式（显示控制台）
python build_gui.py --clean-only  # 仅清理不打包
```

## 核心架构

### 配置驱动的解析流程

```
用户请求 (main.py / main_gui.py)
    ↓
协议发现 (扫描 configs/ 目录)
    ↓
YamlUnifiedProtocol (统一协议解析器)
    ├── YamlCmdFormat (命令格式管理)
    │   └── yaml_config.py (配置加载和验证)
    └── YamlFieldParser (字段解析器，支持 10+ 数据类型)
```

### 协议自动发现机制

`main.py` 通过以下步骤自动发现协议：

1. 扫描 `configs/` 下所有子目录
2. 检查是否存在 `protocol.yaml`
3. 验证 `input_logs/<protocol_name>.log` 是否存在
4. 配置和日志都存在才识别为有效协议

### YAML 配置结构（必需）

每个协议的 `protocol.yaml` 包含：

```yaml
meta:              # 协议元数据（名称、版本、字节序）
types:             # 类型定义（uint, ascii, bcd, bitset 等）
enums:             # 枚举映射
cmds:              # 命令格式（支持循环结构和条件字段）
filters:           # 过滤器（include_cmds/exclude_cmds）
```

### 关键模块职责

- **yaml_config.py**: YAML 配置加载器，定义数据模型（Meta, TypeDef, FieldDef）
- **yaml_cmdformat.py**: 命令格式管理器，处理协议头/尾、命令定义
- **yaml_field_parser.py**: 字段解析器，实现各种数据类型的解析逻辑
- **yaml_unified_protocol.py**: 统一协议解析器，整合上述组件
- **validate_configs.py**: 配置验证工具，提供语法和语义检查

### GUI 架构

```
main_gui.py
    └── gui/unified_main_window.py (统一主窗口，侧边栏导航)
        ├── normal_parse_page.py (普通解析)
        │   ├── protocol_panel.py (协议选择)
        │   ├── detail_panel.py (详情面板)
        │   └── log_panel.py (日志输出)
        └── tcp_log/server_panel.py (TCP 服务端)
```

**关键目录：**

- `gui/widgets/`: 自定义控件（可搜索列表、时间选择器等）
- `gui/workers/`: 工作线程（异步解析、配置验证）
- `gui/shared/`: 共享模块（应用辅助、时间工具）

## 添加新协议

### 零代码添加流程

```bash
# 1. 创建配置目录
mkdir configs/new_protocol

# 2. 创建 protocol.yaml（参考 protocol_template.yaml）

# 3. 放置日志文件
cp your_log.log input_logs/new_protocol.log

# 4. 运行解析
python main.py new_protocol
```

### 高级 YAML 特性

**循环结构：**

```yaml
- repeat_const: 28              # 固定次数
  fields: [...]

- {len: 1, name: count, type: uint8, id: count}
- repeat_by: count              # 按字段值
  fields: [...]
```

**条件字段：**

```yaml
- {len: 4, name: 扩展数据, type: uint32, when: "data_type == 1"}
```

**数值处理：**

```yaml
- {len: 4, name: 电压, type: uint32, scale: 0.1, unit: V}
- {len: 1, name: 状态, type: uint8, enum: device_status}
```

支持的数据类型：uint/int, str, hex, bcd, time.cp56time2a, binary_str, bitset, bitfield 等。详见 [README.md](README.md#yaml配置详解)。

## 输出结果

解析结果保存在 `parsed_log/` 目录，文件名格式：`parsed_<protocol>_log_YYYY-MM-DD HH-MM-SS.txt`

## 重要约定

### 命名规范

- **协议目录名** = **日志文件名** = `protocol_name`
- 配置文件必须是 `protocol.yaml`
- 日志文件必须是 `<protocol_name>.log`

### 代码规范

1. **所有代码和注释使用中文**
2. **单文件不超过 600 行**，合理拆分模块
3. **YAML 配置优先于代码配置**，保持零代码扩展特性
4. **添加新类型时**，需在 `yaml_field_parser.py` 和 `yaml_config.py` 同步更新
5. **尊重现有架构**：抽象工厂、策略模式等设计模式

### 打包发布

使用 `build_gui.py` 打包时：

- **自动清理**: 打包成功后自动删除 `build/` 目录和 `*.spec` 文件
- **保留产物**: 只保留 `dist/` 目录用于发布
- `configs/` 目录会自动复制到 `dist/`

## Claude Code 规则系统

本项目使用 `.claude/rules/` 目录管理代码质量标准。Claude Code 会根据文件类型自动应用相应规则：

- `**/*.py` → Python 代码质量和编码风格规范
- `**/test_*.py`、`**/*_test.py` → Python 测试规范
- `build*.py`, `*.spec` → PyInstaller 打包规范

**规则文件：**

- `python-code-review.md`: 代码质量检查清单（PEP 8、类型注解、文档字符串、SOLID）
- `python-coding-style.md`: 编码风格规范（DRY/KISS/YAGNI、命名规范）
- `python-testing.md`: pytest 测试规范（AAA 模式、覆盖率 >85%）
- `python-test-review.md`: 测试代码质量检查（断言质量、FIRST 原则）
- `pyinstaller-packaging.md`: PyInstaller 打包最佳实践

## 常见任务

### 扩展数据类型

在 `src/yaml_field_parser.py` 中：

1. 在 `_build_type_parsers()` 添加类型定义
2. 实现对应的 `_parse_xxx()` 方法
3. 在 `src/yaml_config.py` 的 `TypeDef` 中添加类型验证逻辑
4. 在 YAML 配置的 `types` 中使用

### 调试解析问题

1. 使用 `python main.py --validate` 检查配置
2. 检查日志文件格式（时间戳 + 十六进制数据）
3. 查看 `yaml_unified_protocol.py` 的性能统计（解析完成后自动输出）
4. 使用 `python src/validate_configs.py <config>` 单独验证配置

### GUI 开发

- **依赖安装**: `pip install -r requirements-gui.txt`
- **主题定制**: 修改 `gui/themes.py` 中的颜色方案
- **组件扩展**: 自定义控件放在 `gui/widgets/` 目录
- **打包测试**: 使用 `python build_gui.py --debug` 先测试控制台版本

## 设计原则

- **配置优先于代码**：新协议只需 YAML 配置，无需修改 Python 代码
- **自动发现机制**：简化协议管理，`main.py` 自动扫描 `configs/` 目录
- **类型安全**：完整的类型检查和验证系统
- **零技术债务**：现代化架构，代码简洁
- **双入口设计**：CLI 适合自动化，GUI 提供可视化界面
