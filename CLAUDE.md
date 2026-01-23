# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

V8Parse 是一个基于 **YAML 配置驱动**的多协议通信报文解析工具。核心架构特点是**零代码扩展**：添加新协议只需创建 YAML 配置文件，无需修改任何 Python 代码。

### 双入口架构

项目提供两个独立入口：

1. **CLI 版本** (`main.py`): 命令行工具，用于批量解析日志文件
2. **GUI 版本** (`main_gui.py`): PySide6 桌面应用，提供图形化解析界面

### 技术栈

- **Python 3.7+**
  - CLI 版本：仅使用标准库，**无第三方依赖**
  - GUI 版本：PySide6（Qt 框架）、PyYAML
- **YAML 配置**：协议定义、字段类型、枚举映射、过滤器等全部通过 YAML 配置
- **PyInstaller**：GUI 打包为独立可执行文件

### 核心设计模式

- **配置驱动**：所有协议通过 `configs/<protocol>/protocol.yaml` 定义
- **抽象工厂模式**：通过协议名称动态创建解析器
- **策略模式**：不同协议实现不同解析策略，由配置驱动

## 常用命令

### CLI 解析工具

```bash
# 解析指定协议的日志文件
python main.py v8              # 解析 V8 协议
python main.py xiaoju          # 解析小桔协议
python main.py yunwei          # 解析运维协议
python main.py sinexcel        # 解析 Sinexcel 协议
python main.py yunkuaichong    # 解析云快充协议

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

### 核心模块关系

```
main.py / main_gui.py (入口)
    ↓
YamlUnifiedProtocol (统一协议解析器)
    ↓
    ├── YamlCmdFormat (命令格式管理)
    │   └── yaml_config.py (配置加载器)
    └── YamlFieldParser (字段解析器)
```

**关键文件说明：**

- `src/yaml_config.py`: YAML 配置加载器，定义数据模型（Meta, TypeDef, FieldDef 等）
- `src/yaml_cmdformat.py`: 命令格式管理器，处理协议头/尾、命令定义
- `src/yaml_field_parser.py`: 字段解析器，实现各种数据类型的解析逻辑
- `src/yaml_unified_protocol.py`: 统一协议解析器，整合上述组件提供完整解析流程

### GUI 架构

GUI 应用基于 PySide6，采用统一侧边栏导航的多页面架构：

```
main_gui.py (入口)
    ↓
gui/unified_main_window.py (统一主窗口)
    ├── gui/sidebar.py (侧边栏导航)
    ├── gui/normal_parse_page.py (普通解析页面)
    │   ├── gui/protocol_panel.py (协议选择面板)
    │   ├── gui/detail_panel.py (详情面板)
    │   └── gui/log_panel.py (日志输出面板)
    └── tcp_log/server_panel.py (TCP 服务端页面)
```

**GUI 自定义组件：**

- `gui/widgets/searchable_list.py`: 可搜索列表控件
- `gui/widgets/multi_select_combo.py`: 多选下拉框
- `gui/widgets/datetime_picker.py`: 日期时间选择器

**页面功能：**

- **普通解析**: 批量解析日志文件，支持协议选择、命令过滤、时间范围过滤
- **TCP 服务端**: 实时接收 TCP 连接并解析报文（集成在统一 GUI 中）

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

#### 支持的数据类型

- **uint/int**：整数（可配置 bytes、signed、字节序）
- **str**：字符串（ASCII/UTF-8）
- **hex**：十六进制显示
- **bcd**：BCD 编码
- **time.cp56time2a**：IEC 104 时间格式
- **binary_str**：二进制串
- **bitset**：位段（支持多字段定义）
- **bitfield**：位段组（支持命名位段和位重叠检查）

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

**条件字段**：

```yaml
- {len: 1, name: 数据类型, type: uint8, id: data_type}
- {len: 2, name: 基础数据, type: uint16}
- {len: 4, name: 扩展数据, type: uint32, when: "data_type == 1"}  # 仅当 data_type=1 时解析
```

**数值处理**：

```yaml
- {len: 4, name: 电压, type: uint32, scale: 0.1, unit: V}  # 实际值 = 原始值 * 0.1
- {len: 1, name: 状态, type: uint8, enum: device_status}    # 枚举映射
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
- 解析结果文件：`parsed_<protocol>_log_<timestamp>.txt`

### 错误处理

- 空日志文件会自动创建并提示用户拷贝内容
- 配置不存在会报错并退出
- 解析错误会打印堆栈跟踪

### 配置验证

- **语法验证**：YAML 格式检查
- **语义验证**：类型一致性、字段引用、循环闭合性
- 使用 `src/validate_configs.py --all` 验证所有配置

### 代码规范

**项目特定规则：**

1. **所有代码和注释使用中文**
2. **单文件不超过 600 行**，合理拆分模块
3. **YAML 配置优先于代码配置**，保持零代码扩展特性
4. **保持类型系统一致性**：添加新类型需在 `yaml_field_parser.py` 和 `yaml_config.py` 同步更新
5. **尊重现有架构**：项目采用抽象工厂、策略模式等设计模式，保持代码风格一致

**.gitignore 管理：**

- `build/` 和 `dist/` 已配置忽略（PyInstaller 产物）
- `*.spec` 文件已配置忽略（自动生成的配置）
- `parsed_log/` 和 `input_logs/` 已配置忽略（用户数据）
- `.windsurfrules` 等 IDE 配置已忽略

**打包发布：**

使用 `build_gui.py` 打包时：

- **自动清理**: 打包成功后自动删除 `build/` 目录和 `*.spec` 文件
- **保留产物**: 只保留 `dist/` 目录用于发布
- **配置包含**: `configs/` 目录会自动复制到 `dist/`

## Claude Code 规则系统

本项目使用 `.claude/rules/` 目录管理代码质量标准和开发规范。Claude Code 会根据文件类型自动加载相应的规则文件。

### 规则文件清单

**Python 代码质量规范：**

- **python-code-review.md**：Python 代码质量检查清单（PEP 8、类型注解、文档字符串、SOLID 原则）
- **python-coding-style.md**：Python 编码风格规范（DRY/KISS/YAGNI、命名规范、文件格式）
- **python-testing.md**：pytest 测试规范（AAA 模式、覆盖率 >85%）
- **python-test-review.md**：Python 测试代码质量检查清单（断言质量、Mock 使用、FIRST 原则）

**项目特定规范：**

- **pyinstaller-packaging.md**：PyInstaller 打包最佳实践（GUI/CLI 应用打包规范）

### 代码思维协议

项目遵循深度技术分析框架（见 [src/.cursorrules](src/.cursorrules)），在修改代码前进行系统性技术分析。

**重要提醒**：遵循 [src/.cursorrules](src/.cursorrules) 中定义的代码思维协议，确保代码质量和架构一致性。

### 规则应用机制

Claude Code 根据文件扩展名自动应用相应规则：

- `**/*.py` → 应用 python-code-review.md 和 python-coding-style.md
- `**/test_*.py`、`**/*_test.py`、`**/tests/**/*.py` → 应用 python-testing.md 和 python-test-review.md
- `build*.py`、`*.spec`、`setup.py`、`pyproject.toml` → 应用 pyinstaller-packaging.md

## Cursor 规则迁移说明

原 `.cursor/rules/` 和 `.windsurf/rules/` 中的规范已迁移至 `.claude/rules/` 系统：

- `code_review.mdc` → `.claude/rules/python-code-review.md`
- `testing.mdc` → `.claude/rules/python-testing.md`
- `code_test_review.mdc` → `.claude/rules/python-test-review.md`
- `packaging-pyinstaller.mdc` → `.claude/rules/pyinstaller-packaging.md`
- `coding-style.md` → `.claude/rules/python-coding-style.md`

## 常见任务

### 扩展数据类型

在 `src/yaml_field_parser.py` 中：

1. 在 `_build_type_parsers()` 添加类型定义
2. 实现对应的 `_parse_xxx()` 方法
3. 在 `src/yaml_config.py` 的 `TypeDef` 中添加类型验证逻辑
4. 在 YAML 配置的 `types` 中使用

### 调试解析问题

1. 使用 `--validate` 检查配置
2. 检查日志文件格式（时间戳 + 十六进制数据）
3. 在 `yaml_unified_protocol.py` 中查看性能统计（解析完成后自动输出）
4. 使用 `python src/validate_configs.py <config>` 单独验证配置文件

### GUI 开发

- **依赖安装**: `pip install -r requirements-gui.txt`
- **主题定制**: 在 `gui/themes.py` 中修改颜色方案
- **组件扩展**: 自定义控件放在 `gui/widgets/` 目录
- **打包测试**: 使用 `python build_gui.py --debug` 先测试控制台版本

### 性能优化

- YAML 配置会自动缓存
- 字段解析器使用预编译类型映射
- 支持大文件流式处理

## 设计原则

### 以配置为中心

- **新协议只需要 YAML 配置，不需要修改代码**
- 配置验证工具确保配置正确性
- 自动发现机制简化协议管理
- 保持零代码扩展特性

### 可扩展性

- 类型系统可扩展（添加新类型解析器）
- 支持复杂的循环结构和嵌套
- 丰富的过滤器系统
- 支持条件字段和动态解析

### 用户友好

- 清晰的错误提示
- 自动创建空日志文件
- 按协议+时间戳命名输出文件
- 双入口设计（CLI + GUI）

### 代码质量

- 所有代码使用中文注释
- 保持单文件不超过 600 行
- 遵循 PEP 8 规范
- 使用类型注解提高可维护性
