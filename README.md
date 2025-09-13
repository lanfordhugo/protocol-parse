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
- **⏰ 时间筛选**: 支持按时间范围筛选日志数据
- **🔍 命令过滤**: 支持按命令码过滤特定类型的报文
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
| V8 | AA F5 | 11字节 | 2字节 | ✅ `configs/v8/protocol.yaml` | 🟢 完整支持 | `v8_com.log` |
| 小桔(XIAOJU) | 7D D0 | 14字节 | 1字节 | ✅ `configs/xiaoju/protocol.yaml` | 🟢 完整支持 | `xiaoju.log` |
| 运维(YUNWEI) | AA F5 | 11字节 | 2字节 | ✅ `configs/yunwei/protocol.yaml` | 🟢 完整支持 | `yunwei.log` |
| Sinexcel | AA F5 | 8字节 | 1字节 | ✅ `configs/sinexcel/protocol.yaml` | 🟢 完整支持 | `sincexcel.log` |

## 📁 项目结构

```text
v8parse/
├── main.py                    # 🚀 主程序入口（YAML配置驱动）
├── configs/                   # 🚀 YAML协议配置目录
│   ├── v8/protocol.yaml       # V8协议YAML配置
│   ├── xiaoju/protocol.yaml   # 小桔协议YAML配置
│   ├── yunwei/protocol.yaml   # 运维协议YAML配置
│   └── sinexcel/protocol.yaml # Sinexcel协议YAML配置
├── src/                       # 📦 核心源码目录
│   ├── yaml_config.py         # YAML配置加载器
│   ├── yaml_unified_protocol.py # YAML统一协议解析器
│   ├── yaml_field_parser.py   # YAML字段解析器
│   ├── yaml_cmdformat.py      # YAML命令格式管理器
│   ├── validate_configs.py    # YAML配置验证工具
│   ├── logger_instance.py     # 📊 日志实例管理
│   └── m_print.py             # 🖨️ 打印工具

├── tools/                     # 🔧 其他辅助工具目录
├── input_logs/                # 📥 输入日志文件目录
│   ├── v8.log                  # V8协议日志文件
│   ├── xiaoju.log             # 小桔协议日志文件
│   ├── yunwei.log             # 运维协议日志文件
│   └── sinexcel.log            # Sinexcel协议日志文件
├── parsed_log/                # 📤 解析结果输出目录（按协议+时间戳）
├── protocol_template.yaml     # 📋 协议配置模板文件
├── README.md                  # 📖 项目说明文档
├── .gitignore                 # 🔧 版本控制忽略文件
└── v8协议解析.code-workspace   # 💻 VS Code工作区配置
```

### 🎯 架构亮点

- **🆕 YAML配置**: 每个协议只需一个`protocol.yaml`文件，包含所有配置
- **🚀 零代码扩展**: 添加新协议只需创建YAML配置，无需修改任何Python代码
- **🔧 自动发现**: `main.py`自动发现`configs/`目录下的协议配置
- **🛡️ 配置验证**: `tools/validate_configs.py`提供完整的配置验证
- **📊 智能日志**: 按协议名+时间戳生成解析结果文件，不创建系统日志

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
python main.py v8        # 解析V8协议
python main.py xiaoju    # 解析小桔协议
python main.py yunwei    # 解析运维协议
python main.py sinexcel  # 解析Sinexcel协议

# 列出所有可用协议
python main.py --list

# 验证所有配置
python main.py --validate
```

### 4. 日志文件准备

将需要解析的日志文件复制到 `input_logs/` 目录，并根据协议类型重命名：

| 协议类型 | 文件路径 | 格式 |
|---------|----------|------|
| V8 | `input_logs/v8.log` | 文本格式，时间戳 + 十六进制数据 |
| 小桔 | `input_logs/xiaoju.log` | 文本格式，时间戳 + 十六进制数据 |
| 运维 | `input_logs/yunwei.log` | 文本格式，时间戳 + 十六进制数据 |
| Sinexcel | `input_logs/sinexcel.log` | 文本格式，时间戳 + 十六进制数据 |

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

## 📜 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 技术支持

- 📖 **文档**: 查看本README文档
- 🐛 **问题反馈**: 提交 GitHub Issues
- 💬 **技术交流**: 联系开发团队

---

**V8Parse** - 现代化的多协议通信报文解析工具 🚀

*最后更新时间: 2025-09-13*