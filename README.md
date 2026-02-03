# V8Parse - 多协议通信报文解析工具

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Architecture](https://img.shields.io/badge/architecture-YAML%20Config-brightgreen.svg)](#yaml配置架构)

## 🚀 项目简介

V8Parse是一个专业的多协议通信报文解析工具，采用现代化的YAML配置驱动架构。专门用于解析和分析各种通信协议的日志数据，支持零代码扩展新协议，能够高效地从原始日志文件中提取、解析和格式化通信数据。

### ✨ 核心特性

- **🔧 YAML配置驱动**: 每个协议只需一个`protocol.yaml`文件，包含所有配置信息
- **⚡ 零代码扩展**: 新协议无需修改Python代码，只需创建YAML配置
- **🛡️ 完整验证**: 语法检查、语义检查、类型一致性验证
- **🔍 自动发现**: 自动扫描`configs/`目录发现协议配置
- **🎨 丰富类型系统**: 支持uint、ascii、bcd、cp56time2a、binary_str、bitset等类型
- **🔄 循环结构**: 支持固定次数和按字段值的循环解析
- **📊 枚举映射**: 支持数值到名称的自动映射
- **⏰ 时间筛选**: 支持按时间范围筛选日志数据（绝对时间和相对时间）
- **🔍 命令过滤**: 支持按命令码过滤特定类型的报文
- **📊 日志统计**: 自动分析日志文件的时间范围、大小、行数等统计信息
- **🆔 终端ID显示**: 解析并显示通信终端的设备ID
- **📊 结构化输出**: 解析结果以结构化格式输出，便于分析和后续处理

## 🏗️ 技术架构

### YAML配置驱动架构

采用现代化的配置驱动模式：

- **yaml_unified_protocol.py**: YAML驱动的统一协议解析器
- **yaml_config.py**: YAML配置加载器和验证器  
- **yaml_field_parser.py**: YAML驱动的字段解析器
- **yaml_cmdformat.py**: YAML驱动的命令格式管理器

### 设计模式

- **🚀 YAML配置驱动**: 通过YAML文件定义协议的完整配置，包括类型、字段、枚举、过滤器
- **抽象工厂模式**: 通过协议名称创建对应的解析器实例
- **策略模式**: 每种协议实现不同的解析策略
- **模板方法模式**: 定义通用解析流程，具体实现由配置驱动

## 🔌 支持的协议类型

| 协议名称 | 协议头标识 | 头长度 | 尾长度 | YAML配置 | 状态 | 日志文件 |
|---------|-----------|--------|--------|----------|------|----------|
| V8 | AA F5 | 11字节 | 2字节 | ✅ `configs/v8/protocol.yaml` | 🟢 完整支持 | `v8.log` |
| 小桔(XIAOJU) | 7D D0 | 14字节 | 1字节 | ✅ `configs/xiaoju/protocol.yaml` | 🟢 完整支持 | `xiaoju.log` |
| 运维(YUNWEI) | AA F5 | 11字节 | 2字节 | ✅ `configs/yunwei/protocol.yaml` | 🟢 完整支持 | `yunwei.log` |
| Sinexcel | AA F5 | 8字节 | 1字节 | ✅ `configs/sinexcel/protocol.yaml` | 🟢 完整支持 | `sinexcel.log` |
| 云快充(Yunkuaichong) | 68 | 6字节 | 2字节 | ✅ `configs/yunkuaichong/protocol.yaml` | 🟢 完整支持 | `yunkuaichong.log` |
| 北京三友(BeijingSanyou) | AA F5 | 11字节 | 2字节 | ✅ `configs/beijingSanyou/protocol.yaml` | 🟢 完整支持 | `beijingSanyou.log` |

## 📁 项目结构

```text
v8parse/
├── main.py                    # 🚀 主程序入口（CLI版本，YAML配置驱动）
├── main_gui.py                # 🖥️ GUI应用主入口
├── build_gui.py               # 📦 GUI打包脚本
├── configs/                   # 🚀 YAML协议配置目录
│   ├── v8/protocol.yaml       # V8协议YAML配置
│   ├── xiaoju/protocol.yaml   # 小桔协议YAML配置
│   ├── yunwei/protocol.yaml   # 运维协议YAML配置
│   ├── sinexcel/protocol.yaml # Sinexcel协议YAML配置
│   ├── yunkuaichong/protocol.yaml # 云快充协议YAML配置
│   └── beijingSanyou/protocol.yaml # 北京三友协议YAML配置
├── src/                       # 📦 核心源码目录
│   ├── yaml_config.py         # YAML配置加载器
│   ├── yaml_unified_protocol.py # YAML统一协议解析器
│   ├── yaml_field_parser.py   # YAML字段解析器
│   ├── yaml_cmdformat.py      # YAML命令格式管理器
│   ├── validate_configs.py    # YAML配置验证工具
│   ├── time_parser.py         # ⏰ 时间范围解析器
│   ├── log_scanner.py         # 📊 日志文件扫描器
│   ├── logger_instance.py     # 📊 日志实例管理
│   └── m_print.py             # 🖨️ 打印工具
├── gui/                       # 🖥️ GUI应用模块（模块化架构）
│   ├── unified_main_window.py # 统一主窗口
│   ├── sidebar.py             # 侧边栏导航
│   ├── normal_parse_page.py   # 普通解析页面
│   ├── protocol_panel.py      # 协议选择面板
│   ├── detail_panel.py        # 详情面板
│   ├── log_panel.py           # 日志输出面板
│   ├── themes.py              # 主题配置
│   ├── shared/                # 共享模块
│   │   └── ...                # 共享工具类
│   ├── workers/               # 工作线程
│   │   └── ...                # 后台任务线程
│   └── widgets/               # 自定义控件
│       ├── searchable_list.py # 可搜索列表
│       ├── multi_select_combo.py # 多选下拉框
│       └── datetime_picker.py # 日期时间选择器
├── tcp_log/                   # 🔌 TCP日志工具模块(测试组件)
│   ├── tcp_client.py          # TCP客户端核心实现
│   ├── tcp_server.py          # TCP服务端核心实现
│   ├── sender_gui.py          # 发送端GUI应用
│   ├── server_panel.py        # 服务端面板（集成到主GUI）
│   ├── log_entry_parser.py    # 日志条目解析器
│   ├── themes.py              # 主题配置
│   └── test/                  # 测试工具目录
│       ├── run_sender.py      # 发送端启动脚本
│       └── run_server.py      # 接收端启动脚本
├── .claude/                   # 🤖 Claude Code 配置
│   ├── skills/                # Skills 技能系统
│   │   ├── *.md               # 各种开发和测试技能
│   │   └── ...                # 更多技能文件
│   └── rules/                 # 代码质量规则
│       ├── python-*.md        # Python 编码规范
│       └── ...                # 更多规则文件
├── input_logs/                # 📥 输入日志文件目录
│   ├── v8.log                 # V8协议日志文件
│   ├── xiaoju.log             # 小桔协议日志文件
│   ├── yunwei.log             # 运维协议日志文件
│   ├── sinexcel.log           # Sinexcel协议日志文件
│   ├── yunkuaichong.log       # 云快充协议日志文件
│   └── beijingSanyou.log      # 北京三友协议日志文件
├── parsed_log/                # 📤 解析结果输出目录（按协议+时间戳）
├── protocol_template.yaml     # 📋 协议配置模板文件
├── CLAUDE.md                  # 📖 Claude Code 工作指南
├── README.md                  # 📖 项目说明文档
├── .gitignore                 # 🔧 版本控制忽略文件
├── requirements-gui.txt       # 📦 GUI依赖列表
└── v8协议解析.code-workspace  # 💻 VS Code工作区配置
```

### 🎯 架构亮点

- **🆕 YAML配置**: 每个协议只需一个`protocol.yaml`文件，包含所有配置
- **🚀 零代码扩展**: 添加新协议只需创建YAML配置，无需修改任何Python代码
- **🔧 自动发现**: `main.py`自动发现`configs/`目录下的协议配置
- **🛡️ 配置验证**: `src/validate_configs.py`提供完整的配置验证
- **📊 智能日志**: 按协议名+时间戳生成解析结果文件，不创建系统日志
- **🤖 AI赋能**: 集成Claude Code Skills系统，提供代码质量和测试规范
- **🖥️ 模块化GUI**: 统一侧边栏导航，可扩展页面架构

## 🚀 快速开始

### 1. 环境要求

- **Python版本**: Python 3.7+ (推荐Python 3.8+)
- **操作系统**: Windows/Linux/macOS
- **依赖**: 仅使用Python标准库，无需额外第三方依赖
- **内存**: 建议至少512MB可用内存用于大文件解析

### 2. 安装部署

```bash
# 克隆项目
git clone <repository-url>
cd v8parse

# 验证Python版本
python --version

# 验证配置文件（可选）
python src/validate_configs.py --all
```

### 3. 基本使用

```bash
# 解析指定协议
python main.py v8              # 解析V8协议
python main.py xiaoju          # 解析小桔协议
python main.py yunwei          # 解析运维协议
python main.py sinexcel        # 解析Sinexcel协议
python main.py yunkuaichong    # 解析云快充协议
python main.py beijingSanyou   # 解析北京三友协议

# 列出所有可用协议
python main.py --list
python main.py -l

# 验证所有配置
python main.py --validate
python main.py -v
```

### 4. 测试

项目采用 pytest 测试框架，拥有完整的单元测试和集成测试套件。

#### 4.1 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_yaml_field_parser.py

# 运行特定测试类
pytest tests/test_yaml_field_parser.py::TestBasicTypes

# 运行特定测试用例
pytest tests/test_yaml_field_parser.py::TestBasicTypes::test_uint8_le

# 显示详细输出
pytest -v

# 显示打印输出
pytest -s

# 遇到第一个失败就停止
pytest -x

# 只运行失败的测试
pytest --lf
```

#### 4.2 生成覆盖率报告

```bash
# 终端覆盖率报告
pytest --cov=src --cov-report=term-missing

# HTML覆盖率报告
pytest --cov=src --cov-report=html

# 查看HTML覆盖率报告（Windows）
start htmlcov/index.html

# 查看HTML覆盖率报告（Linux/macOS）
open htmlcov/index.html
```

#### 4.3 测试覆盖率

**当前整体测试覆盖率：90%**

核心模块覆盖率：

| 模块 | 语句数 | 覆盖率 | 状态 |
|------|--------|--------|------|
| yaml_cmdformat.py | 47 | 100% | ✅ |
| protocol_data_extractor.py | 61 | 100% | ✅ |
| logger_instance.py | 2 | 100% | ✅ |
| validate_configs.py | 132 | 92% | ✅ |
| yaml_field_parser.py | 314 | 92% | ✅ |
| yaml_unified_protocol.py | 87 | 92% | ✅ |
| protocol_output_formatter.py | 109 | 94% | ✅ |
| time_parser.py | 108 | 94% | ✅ |
| log_scanner.py | 177 | 92% | ✅ |
| m_print.py | 291 | 82% | ✅ |
| protocol_parser.py | 122 | 89% | ✅ |
| yaml_config.py | 195 | 90% | ✅ |

#### 4.4 测试结构

```
tests/
├── conftest.py                          # 共享 fixtures
├── helpers/                             # 测试辅助工具
│   └── byte_data_builder.py             # 字节数据构建器
├── test_yaml_field_parser.py            # 字段解析器测试（172个测试）
├── test_yaml_cmdformat.py               # 命令格式管理器测试（50个测试）
├── test_yaml_config.py                  # YAML配置加载器测试
├── test_protocol_data_extractor.py      # 数据提取器测试（16个测试）
├── test_protocol_parser.py              # 协议解析器测试（40个测试）
├── test_protocol_output_formatter.py    # 输出格式化器测试（15个测试）
├── test_yaml_unified_protocol_integration.py  # 集成测试（16个测试）
└── test_validate_configs.py             # 配置验证测试
```

**测试统计**：
- 总测试用例数：408个
- 测试文件数：13个
- 测试代码行数：约6200行

#### 4.5 测试规范

项目遵循以下测试规范：

- **AAA模式**：所有测试用例遵循 Arrange-Act-Assert 模式
- **中文注释**：测试代码使用中文注释说明测试意图
- **覆盖率要求**：核心模块覆盖率 >90%，整体覆盖率 >85%
- **独立性**：每个测试用例独立运行，不依赖其他测试
- **快速反馈**：单元测试快速运行，集成测试可以较慢

详细的测试指南请参考 [tests/README.md](tests/README.md)

### 5. 高级功能

#### 5.1 时间范围过滤

CLI 版本支持强大的时间过滤功能，可以快速定位特定时间段的日志数据：

```bash
# 绝对时间过滤
python main.py v8 --time-start "2024-01-01 00:00:00" --time-end "2024-01-31 23:59:59"
python main.py v8 --time-start "2024-01-01" --time-end "2024-01-31"
python main.py v8 --time-start "2024-01-01 00:00"

# 相对时间过滤（最近 N 时间单位）
python main.py v8 --time-last "1h"      # 最近1小时
python main.py v8 --time-last "24h"     # 最近24小时
python main.py v8 --time-last "7d"      # 最近7天
python main.py v8 --time-last "30d"     # 最近30天
python main.py v8 --time-last "1h 30m"  # 语法错误：时间last只支持单个单位
```

**支持的时间单位：**
- `s` - 秒
- `m` - 分钟
- `h` - 小时
- `d` - 天

#### 5.2 命令过滤

可以通过命令ID过滤特定类型的报文：

```bash
# 只解析特定命令
python main.py v8 --include-cmds "2,3,5"

# 排除特定命令
python main.py v8 --exclude-cmds "1,99"

# 组合过滤（时间 + 命令）
python main.py v8 --time-last "1h" --include-cmds "2,3"
```

#### 5.3 日志统计

查看日志文件的统计信息（时间范围、文件大小、总行数等）：

```bash
# 显示日志统计信息
python main.py v8 --stats

# 统计信息包括：
# - 文件路径和大小
# - 总行数和扫描耗时
# - 时间范围（最早/最晚时间戳）
# - 时间跨度（秒/分钟/小时/天）
```

#### 5.4 自定义日志文件

使用自定义日志文件路径：

```bash
# 使用自定义日志文件
python main.py v8 --log-file "/path/to/custom.log"
```

### 6. 日志文件准备

将需要解析的日志文件复制到 `input_logs/` 目录，并根据协议类型重命名：

| 协议类型 | 文件路径 | 格式 |
|---------|----------|------|
| V8 | `input_logs/v8.log` | 文本格式，时间戳 + 十六进制数据 |
| 小桔 | `input_logs/xiaoju.log` | 文本格式，时间戳 + 十六进制数据 |
| 运维 | `input_logs/yunwei.log` | 文本格式，时间戳 + 十六进制数据 |
| Sinexcel | `input_logs/sinexcel.log` | 文本格式，时间戳 + 十六进制数据 |
| 云快充 | `input_logs/yunkuaichong.log` | 文本格式，时间戳 + 十六进制数据 |
| 北京三友 | `input_logs/beijingSanyou.log` | 文本格式，时间戳 + 十六进制数据 |

### 7. GUI 应用

项目提供统一的 GUI 应用，集成普通解析和 TCP 实时解析功能。

#### 功能特性

- **📋 普通解析**: 批量解析日志文件，支持协议选择、命令过滤、时间范围过滤
- **🌐 TCP 服务端**: 实时接收 TCP 连接并解析报文（集成在统一 GUI 中）
- **🎨 统一界面**: 侧边栏导航的多页面架构，操作更直观
- **🌓 主题支持**: 内置亮色/暗色主题切换
- **⚙️ 灵活配置**: 支持自定义过滤条件、解析参数等
- **📅 可视化时间选择**: 直观的时间范围选择器，支持快捷选择
- **🔄 实时进度**: 后台线程处理，实时显示解析进度和统计

#### 启动方式

```bash
# 启动 GUI 应用
python main_gui.py
```

#### 依赖安装

GUI 应用需要额外的依赖:

```bash
pip install -r requirements-gui.txt
```

#### 打包发布

```bash
# 打包为独立可执行文件（自动清理 build 目录）
python build_gui.py            # 标准打包（自动清理 build/）
python build_gui.py --clean    # 清理后打包
python build_gui.py --debug    # 调试模式（显示控制台）
python build_gui.py --clean-only  # 仅清理不打包
```

#### 界面说明

- **普通解析页面**: 选择协议 → 配置过滤 → 开始解析 → 查看结果
- **TCP 服务端页面**: 启动服务器 → 等待连接 → 实时解析报文
- **快捷键**: `Ctrl+1` 切换到普通解析，`Ctrl+2` 切换到 TCP 服务端

### 8. TCP 日志工具模块（测试组件）

项目包含一个完整的 TCP 日志收发测试工具，位于 `tcp_log/` 目录，用于模拟设备通信、日志采集和协议测试。

#### 功能特性

- **🔄 实时收发**: 支持 TCP 客户端/服务端双向通信
- **📋 日志解析**: 自动解析 V8Parse 格式的日志文件
- **⚙️ 灵活配置**: 支持自定义 IP、端口、发送间隔等参数
- **📊 进度显示**: 实时显示发送进度和统计信息
- **🌓 主题支持**: 内置亮色/暗色主题切换

#### 启动方式

```bash
# 启动 TCP 服务端(接收端)
python tcp_log/test/run_server.py

# 启动 TCP 客户端(发送端)
python tcp_log/test/run_sender.py
```

#### 依赖安装

TCP 日志工具需要额外的 GUI 依赖:

```bash
pip install -r requirements-gui.txt
```

#### 使用场景

1. **协议开发测试**: 在开发新协议配置时,模拟设备通信验证解析结果
2. **日志回放**: 将历史日志文件通过 TCP 发送,测试解析器性能
3. **设备模拟**: 模拟充电桩等设备的行为,测试监控系统
4. **压力测试**: 批量发送报文,测试系统稳定性

#### 注意事项

- TCP 日志工具是**测试组件**,仅用于开发和调试环境
- 不建议在生产环境中使用,主要用于协议开发和验证
- 默认监听端口: 服务端 `8888`,客户端可配置目标地址
- 测试工具位于 `tcp_log/test/` 目录,与核心实现分离

## 💡 添加新协议（零代码）

只需2步即可添加新协议支持：

### 步骤1：创建YAML配置

```bash
# 创建协议配置目录
mkdir configs/new_protocol
```

```yaml
# configs/new_protocol/protocol.yaml
meta:
  protocol: new_protocol
  version: 1
  default_endian: LE
  notes: 新协议配置示例

types:
  uint8:  { base: uint, bytes: 1, signed: false }
  uint16: { base: uint, bytes: 2, signed: false }
  uint32: { base: uint, bytes: 4, signed: false }
  ascii:  { base: str,  encoding: ASCII }
  bcd2:   { base: bcd, bytes: 2 }

enums:
  device_status:
    0: 离线
    1: 在线
    2: 故障

cmds:
  1:
    - {len: 1, name: 设备状态, type: uint8, enum: device_status}
    - {len: 32, name: 设备编码, type: ascii}
    - {len: 4, name: 电压值, type: uint32, scale: 0.1, unit: V}

filters:
  include_cmds: []
  exclude_cmds: []
```

### 步骤2：放置日志文件

```bash
# 将日志文件放到指定位置
cp your_protocol.log input_logs/new_protocol.log

# 运行解析
python main.py new_protocol
```

**就这样！零代码添加新协议！**

## 🎯 YAML配置详解

### 基本配置结构

```yaml
meta:                          # 协议元数据
  protocol: v8                 # 协议名称
  version: 1                   # 配置版本
  default_endian: LE           # 默认字节序 (LE/BE)
  notes: 可选说明

types:                         # 类型定义
  uint8:   { base: uint, bytes: 1, signed: false }
  uint16:  { base: uint, bytes: 2, signed: false }
  ascii:   { base: str,  encoding: ASCII }
  bcd2:    { base: bcd, bytes: 2 }
  
enums:                         # 枚举定义
  status:
    0: 离线
    1: 在线

cmds:                          # 命令定义
  1:                           # 命令ID
    - {len: 1, name: 状态, type: uint8, enum: status}
    - {len: 4, name: 电压, type: uint32, scale: 0.1, unit: V}

filters:                       # 过滤器
  include_cmds: [1, 2, 3]      # 包含的命令
  exclude_cmds: []             # 排除的命令
```

### 支持的数据类型

| 类型 | 说明 | 示例配置 |
|------|------|----------|
| uint | 无符号整数 | `{base: uint, bytes: 2, signed: false}` |
| int | 有符号整数 | `{base: int, bytes: 2, signed: true}` |
| str | 字符串 | `{base: str, encoding: ASCII}` |
| hex | 十六进制 | `{base: hex}` |
| bcd | BCD码 | `{base: bcd, bytes: 2}` |
| cp56time2a | IEC时间 | `{base: time.cp56time2a, bytes: 7}` |
| binary_str | 二进制串 | `{base: binary_str, bytes: 4}` |
| bitset | 位段 | `{base: bitset, bits: [{name: "bit0"}]}` |

### 条件字段支持

```yaml
# 基础字段
- {len: 1, name: 数据类型, type: uint8, id: data_type}
- {len: 2, name: 基础数据, type: uint16}

# 条件字段（仅当条件满足时解析）
- {len: 4, name: 扩展数据, type: uint32, when: "data_type == 1"}
- {len: 8, name: 额外信息, type: uint64, when: "data_type > 1"}
```

**条件表达式支持:**

- 相等比较: `field == value`
- 不等比较: `field != value`
- 大于小于: `field > value`, `field < value`
- 逻辑运算: `field1 == 1 and field2 == 2`
- 复杂条件: `(field1 == 1 or field2 == 2) and field3 == 3`

### 循环结构支持

```yaml
# 固定次数循环
- repeat_const: 28
  fields:
    - {len: 1, name: 枪状态, type: uint8}
    - {len: 2, name: 枪电压, type: uint16}

# 按字段值循环
- {len: 1, name: 时段数量, type: uint8, id: period_count}
- repeat_by: period_count
  fields:
    - {len: 2, name: 开始时间, type: uint16}
    - {len: 2, name: 结束时间, type: uint16}
```

### 数值处理

```yaml
# 缩放和单位
- {len: 4, name: 电压, type: uint32, scale: 0.1, unit: V}
- {len: 2, name: 电流, type: uint16, scale: 0.01, unit: A}

# 枚举映射
- {len: 1, name: 状态, type: uint8, enum: device_status}
```

## 🛠️ 配置验证

使用内置的配置验证工具：

```bash
# 验证单个配置
python src/validate_configs.py configs/v8/protocol.yaml

# 验证所有配置
python src/validate_configs.py --all

# 集成到主程序
python main.py --validate
```

验证内容包括：

- ✅ YAML语法检查
- ✅ 配置结构验证
- ✅ 类型定义一致性
- ✅ 字段引用正确性
- ✅ 循环结构闭合性

## 📊 输出结果

解析结果保存在 `parsed_log/` 目录下，文件名格式为：

```text
parsed_<protocol>_log_YYYY-MM-DD HH-MM-SS.txt
```

输出内容包括：

- 时间戳和方向（Send/Recv）
- 命令码和设备信息
- 解析后的结构化数据
- 枚举值的名称映射
- 带单位的数值显示

## 🤖 Claude Code Skills 系统

项目集成了 Claude Code Skills 技能系统,提供AI辅助的代码质量和测试规范。

### 核心技能

**代码质量保障:**

- **代码审查**: 系统化代码检查清单,确保代码质量
- **编码规范**: Python编码风格规范(PEP 8、DRY/KISS/YAGNI原则)
- **测试规范**: pytest测试规范(AAA模式、覆盖率要求)
- **测试审查**: 测试代码质量检查(断言质量、FIRST原则)

**开发流程:**

- **需求澄清**: 快速实现小需求的技术方案设计
- **架构设计**: 系统架构设计专家,提供可扩展方案
- **模块设计**: 模块逻辑文档规范,确保文档一致性
- **问题分析**: 通用问题分析与技术方案文档化

**调试与验证:**

- **Bug排查**: 系统性分析和解决软件问题
- **系统化调试**: 遇到bug时的标准调试流程
- **验证前置**: 完成工作前的验证检查清单

### 规则系统

项目根据文件类型自动应用相应规则:

- `**/*.py` → Python代码质量和编码风格规范
- `**/test_*.py` → Python测试规范和测试代码审查
- `build*.py`, `*.spec` → PyInstaller打包规范

### 使用方式

Claude Code 会自动加载相关技能和规则,无需手动配置。详见 [`.claude/`](.claude/) 目录。

## 🔧 开发指南

### 扩展类型系统

要添加新的数据类型，只需在`src/yaml_field_parser.py`中：

1. 在`_build_type_parsers()`中添加解析器
2. 实现对应的`_parse_xxx()`方法

### 扩展验证规则

在`tools/validate_configs.py`中添加新的验证规则。

### 性能优化

- YAML配置在首次加载后会缓存
- 字段解析器使用预编译的类型映射
- 支持大文件的流式处理

## 🎉 项目优势

### 相比传统架构的改进

- **配置简化**: 多个文件 → 1个YAML文件
- **扩展简化**: 修改代码 → 零代码配置  
- **类型安全**: 硬编码 → 完整类型系统
- **工具完备**: 无验证 → 语法语义检查
- **架构现代**: 硬编码 → 配置驱动

### 技术特点

- ✅ **生产就绪**：核心功能稳定可靠
- ✅ **零技术债务**：全新架构，代码简洁
- ✅ **高扩展性**：新协议添加极其简单
- ✅ **类型安全**：完整的类型检查和验证
- ✅ **工具齐全**：配置验证、自动发现等

## 📋 更新日志

### v3.6.0 (2025-01-28) 🚀 CLI 增强功能

- ⏰ **时间过滤**: CLI 版本新增强大的时间范围过滤功能
  - 支持绝对时间过滤（`--time-start`、`--time-end`）
  - 支持相对时间过滤（`--time-last`：1h、24h、7d 等）
  - 智能时间格式化显示
- 📊 **日志统计**: 新增日志文件统计分析功能（`--stats`）
  - 文件大小和总行数统计
  - 自动检测时间范围（最早/最晚时间戳）
  - 时间跨度智能格式化（秒/分钟/小时/天）
  - 大文件采样优化（>1MB）
- 🆔 **终端ID显示**: 解析并显示通信终端的设备ID
- 🔧 **多编码支持**: 日志扫描器支持 UTF-8/GBK/Latin-1 多编码自动检测
- ⚡ **性能优化**: 大文件采用采样策略，提升扫描速度
- 📦 **命令过滤**: 增强 `--include-cmds` 和 `--exclude-cmds` 参数
- 📖 **自定义日志**: 支持 `--log-file` 参数使用自定义日志文件路径

### v3.5.0 (2025-01-24) 🎨 GUI 模块化重构

- 🎨 **GUI模块化**: 提取共享模块和工作线程到独立目录
- 📅 **可视化时间选择**: 添加直观的日期时间选择器控件
- 🔄 **智能时间格式化**: 实现人类可读的时间显示（今天、昨天等）
- 🤖 **Claude Code集成**: 添加Skills系统和代码质量规则
- 📦 **北京三友协议**: 新增北京三友充电桩协议支持

### v3.0.0 (2025-09-13) 🚀 全面YAML重构

- 🚀 **完全重构**: 基于YAML配置的现代化架构
- 🔧 **零代码扩展**: 新协议只需YAML配置，无需修改Python代码
- 🛡️ **配置验证**: 完整的语法和语义检查工具
- 📊 **智能日志**: 优化日志系统，按协议+时间戳输出
- 🧹 **代码清理**: 移除所有旧格式文件和代码
- 📖 **文档更新**: 完整更新README和使用说明

### v2.0.0 (2025-09-11) 配置驱动架构

- 🚀 **配置驱动**: 引入配置驱动的协议解析架构
- 📦 **统一解析**: 所有协议使用同一套解析逻辑
- ✅ **头部配置化**: 支持字段级配置

### v1.0.0 (初始版本)

- ✨ 支持基础协议解析
- 📋 基础报文格式解析
- 🔍 命令过滤功能

## ❓ 常见问题 (FAQ)

### 解析相关

**Q: 如何添加新协议支持？**

A: 只需创建 YAML 配置文件，无需修改代码：

1. 在 `configs/` 下创建协议目录
2. 创建 `protocol.yaml` 配置文件
3. 将日志文件放到 `input_logs/<protocol_name>.log`
4. 运行 `python main.py <protocol_name>`

详细步骤见 [添加新协议](#添加新协议) 章节。

**Q: 解析结果保存在哪里？**

A: 解析结果保存在 `parsed_log/` 目录，文件名格式：
```
parsed_<protocol>_log_YYYY-MM-DD HH-MM-SS.txt
```

**Q: 如何只解析特定命令？**

A: 使用命令过滤器：

```python
from src.yaml_unified_protocol import YamlUnifiedProtocol

parser = YamlUnifiedProtocol("your_protocol")
parser.set_include_cmds([0x01, 0x02])  # 只解析命令 0x01 和 0x02
parser.run()
```

**Q: 如何按时间范围筛选日志？**

A: 使用时间筛选：

```python
parser.set_time_range(
    start_time="2024-01-01 00:00:00",
    end_time="2024-01-31 23:59:59"
)
```

或使用相对时间：

```python
parser.set_time_range(
    start_time="-1h",  # 最近1小时
    end_time="now"      # 到现在
)
```

### 配置相关

**Q: YAML 配置文件结构是什么？**

A: `protocol.yaml` 包含以下主要部分：

- `meta`: 协议元数据（名称、版本、字节序）
- `types`: 类型定义（uint、ascii、bcd 等）
- `enums`: 枚举映射
- `cmds`: 命令格式定义
- `filters`: 过滤器配置

详见 [YAML配置详解](#yaml配置详解) 章节。

**Q: 如何验证配置文件是否正确？**

A: 运行配置验证：

```bash
python main.py --validate
# 或
python src/validate_configs.py configs/your_protocol/protocol.yaml
```

**Q: 支持哪些数据类型？**

A: 支持以下类型：

- `uint/int`: 整数类型（可指定字节长度）
- `str`: 字符串类型（支持多种编码）
- `hex`: 十六进制字符串
- `bcd`: BCD 编码
- `time.*`: 时间格式（cp56time2a、bcd_time、unix_time 等）
- `binary_str`: 二进制字符串
- `bitset`: 位集合
- `bitfield`: 位字段

### GUI 相关

**Q: 如何启动 GUI 版本？**

A: 运行：

```bash
python main_gui.py
```

**Q: GUI 和 CLI 版本有什么区别？**

A:

- **CLI 版本**: 适合批量处理和自动化脚本
- **GUI 版本**: 提供可视化界面，支持实时 TCP 监控

**Q: 如何打包 GUI 应用？**

A: 运行打包脚本：

```bash
python build_gui.py
```

打包后的应用在 `dist/` 目录。

### 错误排查

**Q: 提示 "协议配置不存在" 怎么办？**

A: 检查以下几点：

1. `configs/<protocol_name>/protocol.yaml` 是否存在
2. `input_logs/<protocol_name>.log` 是否存在
3. 配置文件格式是否正确（运行 `--validate` 检查）

**Q: 解析结果为空或数据不完整？**

A: 可能的原因：

1. 日志文件格式不正确（应为：时间戳 + 十六进制数据）
2. 协议头/尾配置不匹配
3. 字段长度定义错误
4. 字节序配置错误

建议使用 `--validate` 检查配置。

**Q: 测试失败怎么办？**

A: 运行测试并查看详细输出：

```bash
python -m pytest tests/ -v --tb=short
```

查看具体失败的测试用例和错误信息。

### 性能相关

**Q: 如何提高解析速度？**

A:

1. 使用 `pytest-xdist` 并行运行测试
2. 减少不必要的日志输出
3. 使用命令过滤减少解析数据量
4. 优化 YAML 配置，减少复杂嵌套

**Q: 大文件解析很慢？**

A: 尝试：

1. 使用时间筛选减少数据量
2. 使用命令过滤只解析需要的命令
3. 增加日志文件轮换大小

## 📜 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 技术支持

- 📖 **文档**: 查看本README文档
- 🐛 **问题反馈**: 提交 GitHub Issues
- 💬 **技术交流**: 联系开发团队

---

**V8Parse** - 现代化的多协议通信报文解析工具 🚀

*最后更新时间: 2025-02-02*
