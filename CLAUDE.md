# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

V8Parse 是一个专业的多协议通信报文解析工具，采用现代化的 **YAML 配置驱动架构**。核心特性是零代码扩展新协议——只需添加 YAML 配置文件，无需修改 Python 代码。

### 技术栈
- **Python 3.7+**（仅使用标准库，无第三方依赖）
- **YAML 配置**：协议定义、字段类型、枚举映射、过滤器等全部通过 YAML 配置
- **PyInstaller**：GUI 打包（可选）

### 核心设计模式
- **配置驱动**：所有协议通过 `configs/<protocol>/protocol.yaml` 定义
- **抽象工厂模式**：通过协议名称动态创建解析器
- **策略模式**：不同协议实现不同解析策略，由配置驱动

## 常用命令

### 基本使用

```bash
# 解析指定协议
python main.py v8
python main.py xiaoju
python main.py yunwei
python main.py sinexcel
python main.py yunkuaichong

# 列出所有可用协议
python main.py --list
python main.py -l

# 验证所有协议配置
python main.py --validate
python main.py -v

# 单独验证配置（不运行解析）
python src/validate_configs.py --all
python src/validate_configs.py configs/v8/protocol.yaml
```

### 测试与打包

```bash
# 运行测试（如果存在）
pytest

# GUI 打包（使用 PyInstaller）
python build_gui.py          # 默认打包
python build_gui.py --clean  # 清理后打包
python build_gui.py --debug  # 调试模式（显示控制台）
```

## 核心架构

### 配置驱动的三层架构

```
configs/                  # YAML 协议配置目录
├── v8/protocol.yaml      # V8 协议配置
├── xiaoju/protocol.yaml  # 小桔协议配置
└── ...

src/                      # 核心源码
├── yaml_config.py         # YAML 配置加载器和验证器
├── yaml_cmdformat.py      # 命令格式管理器（从 YAML 加载）
├── yaml_field_parser.py   # 字段解析器（基于 YAML 类型定义）
├── yaml_unified_protocol.py # 统一协议解析器
└── validate_configs.py    # 配置验证工具

main.py                   # 主入口（自动发现 configs/ 下的协议）
```

### 协议发现机制

`main.py` 使用 `get_available_protocols()` 自动发现协议：
1. 扫描 `configs/` 目录下的所有子目录
2. 检查每个子目录是否存在 `protocol.yaml`
3. 日志文件命名为 `input_logs/<protocol_name>.log`
4. 配置和日志都存在才识别为有效协议

### YAML 配置结构

每个协议的 `protocol.yaml` 包含：

```yaml
meta:              # 协议元数据
  protocol: v8
  version: 1
  default_endian: LE

types:             # 类型定义（uint, ascii, bcd, bitset 等）
enums:             # 枚举映射
cmds:              # 命令格式定义（支持 repeat_const/repeat_by 循环）
filters:           # 过滤器（include_cmds/exclude_cmds）
```

### 关键类职责

- **YamlConfig**：加载和验证 YAML 配置，提供类型系统
- **YamlCmdFormat**：管理命令格式，处理循环结构
- **YamlFieldParser**：根据类型定义解析字段（支持 scale/unit/enum）
- **YamlUnifiedProtocol**：统一协议类，协调整个解析流程
- **logger_instance.log**：日志实例（仅在需要时创建输出文件）

## 添加新协议（零代码）

### 步骤

1. **创建 YAML 配置**
   ```bash
   mkdir configs/new_protocol
   # 复制 protocol_template.yaml 作为起点
   ```

2. **定义协议结构**（在 `configs/new_protocol/protocol.yaml`）
   - `meta`：协议名称、字节序等
   - `types`：数据类型定义
   - `enums`：枚举映射
   - `cmds`：命令格式（字段列表、循环结构）
   - `filters`：命令过滤规则

3. **放置日志文件**
   ```bash
   cp your_log.log input_logs/new_protocol.log
   ```

4. **运行解析**
   ```bash
   python main.py new_protocol
   ```

### 支持的数据类型

- **uint/int**：整数（可配置 bytes、signed、字节序）
- **str**：字符串（ASCII/UTF-8）
- **hex**：十六进制显示
- **bcd**：BCD 编码
- **cp56time2a**：IEC 104 时间格式
- **binary_str**：二进制串
- **bitset**：位段（支持多字段定义）

### 高级特性

**循环结构**：
```yaml
# 固定次数循环
- repeat_const: 28
  fields:
    - {len: 1, name: 枪状态, type: uint8}

# 按字段值循环
- {len: 1, name: 时段数量, type: uint8, id: period_count}
- repeat_by: period_count
  fields:
    - {len: 2, name: 开始时间, type: uint16}
```

**数值处理**：
```yaml
- {len: 4, name: 电压, type: uint32, scale: 0.1, unit: V}
- {len: 1, name: 状态, type: uint8, enum: device_status}
```

## 输出结果

解析结果保存在 `parsed_log/` 目录：
- 文件名：`parsed_<protocol>_log_YYYY-MM-DD HH-MM-SS.txt`
- 内容：时间戳、方向、命令码、解析后的结构化数据

## 重要约定

### 命名规范
- **协议目录名** = **日志文件名** = `protocol_name`
- 配置文件必须是 `protocol.yaml`
- 日志文件必须是 `<protocol_name>.log`

### 错误处理
- 空日志文件会提示用户拷贝内容
- 配置不存在会报错并退出
- 解析错误会打印堆栈跟踪

### 配置验证
- **语法验证**：YAML 格式检查
- **语义验证**：类型一致性、字段引用、循环闭合性
- 使用 `src/validate_configs.py --all` 验证所有配置

## Cursor 规则要点

本项目使用 `.cursor/rules/` 定义代码质量标准：
- **code_review.mdc**：Python 代码质量检查清单（PEP 8、类型注解、文档字符串）
- **testing.mdc**：pytest 测试规范（AAA 模式、覆盖率 >85%）
- **packaging-pyinstaller.mdc**：PyInstaller 打包最佳实践

## 常见任务

### 扩展数据类型

在 `src/yaml_field_parser.py` 中：
1. 在 `_build_type_parsers()` 添加类型定义
2. 实现对应的 `_parse_xxx()` 方法
3. 在 YAML 配置的 `types` 中使用

### 调试解析问题

1. 使用 `--validate` 检查配置
2. 检查日志文件格式（时间戳 + 十六进制数据）
3. 在 `yaml_unified_protocol.py` 中查看性能统计

### 性能优化

- YAML 配置会自动缓存
- 字段解析器使用预编译类型映射
- 支持大文件流式处理

## 设计原则

### 以配置为中心
- **新协议只需要 YAML 配置，不需要修改代码**
- 配置验证工具确保配置正确性
- 自动发现机制简化协议管理

### 可扩展性
- 类型系统可扩展（添加新类型解析器）
- 支持复杂的循环结构和嵌套
- 丰富的过滤器系统

### 用户友好
- 清晰的错误提示
- 自动创建空日志文件
- 按协议+时间戳命名输出文件
