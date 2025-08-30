# V8Parse - 多协议通信报文解析工具

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 项目简介

V8Parse是一个专业的多协议通信报文解析工具，专门用于解析和分析各种通信协议的日志数据。该工具采用面向对象的模块化设计，基于抽象基类和策略模式，支持多种协议格式，能够高效地从原始日志文件中提取、解析和格式化通信数据。

## 核心特性

- **🔌 多协议支持**: 支持V8、小桔、运维、Sinexcel等多种通信协议，易于扩展
- **📋 灵活的报文格式**: 支持固定长度、循环字段、变长字段等多种报文格式
- **🧠 智能数据解析**: 自动识别和解析BCD码、ASCII码、二进制等多种数据格式
- **⏰ 时间筛选**: 支持按时间范围筛选日志数据
- **🔍 命令过滤**: 支持按命令码过滤特定类型的报文
- **📊 结构化输出**: 解析结果以结构化格式输出，便于分析和后续处理
- **🏗️ 可扩展架构**: 基于抽象基类设计，新增协议只需继承BaseProtocol类

## 技术架构

### 设计模式
- **抽象工厂模式**: 通过ProtocolType枚举和工厂方法创建不同协议实例
- **策略模式**: 每种协议实现不同的解析策略
- **模板方法模式**: BaseProtocol定义通用解析流程，子类实现具体细节

### 核心组件
- **BaseProtocol**: 抽象基类，定义协议解析的通用接口和流程
- **ProtocolConfig**: 协议配置数据类，包含头长度、尾长度、帧头标识
- **FieldParser**: 字段解析器，支持多种数据格式解析
- **CmdFormat**: 命令格式管理器，处理协议格式定义文件

## 支持的协议类型

| 协议名称 | 协议头标识 | 头长度 | 尾长度 | 格式文件 | 状态 |
|---------|-----------|--------|--------|----------|------|
| V8 | AA F5 | 11字节 | 2字节 | format_mcu_ccu.txt | ✅ 完整支持 |
| 小桔(XIAOJU) | 7D D0 | 14字节 | 1字节 | format_xiaoju.txt | ✅ 完整支持 |
| 运维(YUNWEI) | CC D7 | 8字节 | 1字节 | format_yunwei.txt | 🚧 部分支持 |
| Sinexcel | DD E8 | 8字节 | 1字节 | format_sinexcel.txt | 🚧 部分支持 |

## 项目结构

```text
v8parse/
├── main.py                    # 🚀 主程序入口，统一的协议解析框架
├── v8_run.py                  # V8协议专用运行脚本（兼容性保留）
├── sinexcel_run.py            # Sinexcel协议专用运行脚本
├── yunwei_run.py              # 运维协议专用运行脚本
├── src/                       # 📦 核心源码目录
│   ├── base_protocol.py       # 🏗️ 基础协议抽象类（核心架构）
│   ├── v8_protocol.py         # V8协议具体实现
│   ├── xiaoju_protocol.py     # 小桔协议具体实现
│   ├── sincexcel_portocol.py  # Sinexcel协议具体实现
│   ├── yunwei_portocol.py     # 运维协议具体实现
│   ├── field_parser.py        # 🔧 字段解析器（支持多种数据格式）
│   ├── cmdformat.py           # 📋 命令格式解析器
│   ├── console_log.py         # 📝 控制台日志输出管理
│   ├── logger_instance.py     # 📊 日志实例管理
│   ├── m_print.py             # 🖨️ 打印工具
│   └── test.py                # 🧪 测试文件
├── resources/                 # 📁 资源文件目录
│   ├── format_mcu_ccu.txt     # V8协议格式定义文件
│   ├── format_xiaoju.txt      # 小桔协议格式定义文件
│   ├── format_yunwei.txt      # 运维协议格式定义文件
│   ├── format_sinexcel.txt    # Sinexcel协议格式定义文件
│   ├── filter.txt             # 命令过滤配置文件
│   └── alarm.conf             # 告警配置文件
├── parsed_log/                # 📤 解析结果输出目录
├── log/                       # 📥 原始日志文件目录
├── .cursor/                   # 🔧 开发工具配置
│   └── rules/                 # 代码规范配置
├── README.md                  # 📖 项目说明文档
└── 使用说明.txt               # 📋 详细使用说明（中文）
```

### 核心模块说明

| 模块 | 功能描述 | 关键特性 |
|------|----------|----------|
| `BaseProtocol` | 协议解析基类 | 定义通用解析流程，抽象方法规范 |
| `ProtocolType` | 协议类型枚举 | 配置化协议管理，工厂模式实现 |
| `FieldParser` | 字段解析引擎 | 支持BCD、ASCII、二进制等多种格式 |
| `CmdFormat` | 格式定义管理 | 解析协议格式文件，支持循环和变长字段 |

## 快速开始

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

# 运行测试（可选）
python -m pytest src/test.py
```

### 3. 基本使用方法

#### 方法一：使用统一框架（推荐）

```python
# 修改main.py中的协议类型
PROTOCOL_TYPE = ProtocolType.V8  # 可选: V8, XIAOJU, YUNWEI, SINCEXCEL

# 运行解析
python main.py
```

#### 方法二：使用专用脚本

```bash
# V8协议解析
python v8_run.py

# Sinexcel协议解析
python sinexcel_run.py

# 运维协议解析
python yunwei_run.py
```

### 3. 日志文件准备

1. 将需要解析的日志文件复制到项目根目录
2. 根据协议类型重命名文件：
   - V8协议: `v8_com.log`
   - 小桔协议: `xiaoju.log`
   - 运维协议: `yunwei.log`
   - Sinexcel协议: `sincexcel.csv`

### 4. 日志文件配置

#### 4.1 文件命名规范

根据协议类型将日志文件重命名并放置在项目根目录：

| 协议类型 | 文件名 | 格式 | 示例 |
|---------|--------|------|------|
| V8 | `v8_com.log` | 文本格式 | 时间戳 + 十六进制数据 |
| 小桔 | `xiaoju.log` | 文本格式 | 时间戳 + 十六进制数据 |
| 运维 | `yunwei.log` | 文本格式 | 时间戳 + 十六进制数据 |
| Sinexcel | `sincexcel.csv` | CSV格式 | 结构化数据 |

#### 4.2 数据筛选配置

在日志文件前三行添加筛选条件（可选）：

```text
start:2021-06-04 18:13:23
end:2021-06-04 19:13:25
cmd:[104,106]
```

**配置参数说明：**
- `start`: 开始时间（格式：YYYY-MM-DD HH:MM:SS）
- `end`: 结束时间（格式：YYYY-MM-DD HH:MM:SS）
- `cmd`: 需要解析的命令码列表（JSON数组格式）

#### 4.3 过滤器配置

编辑 `resources/filter.txt` 文件设置全局命令过滤：

```text
[104, 106, 108, 110]
```

## 报文格式定义

项目支持四种报文格式定义方式：

### 1. 固定长度格式

```text
4           命令序号
1           结果
```

### 2. 单字段循环格式

```text
4:4n        参数值      # 4字节参数重复4次
```

### 3. 多字段循环格式

```text
startfor:2
1           状态
2           电压
endfor
```

### 4. 变长字段循环格式

```text
1           时段数量
startloop:时段数量
2           开始时间
2           结束时间
endloop
```

## 字段解析类型

系统支持多种字段解析类型：

- **BCD码字段**: 桩编号、账号、物理卡号等
- **ASCII字段**: VIN码、交易流水号、订单号等
- **二进制字段**: 状态位、控制信号等
- **时间字段**: CP时间格式
- **数值字段**: 电压、电流、功率等

## 输出结果

解析结果保存在 `parsed_log/` 目录下，文件名格式为：

```text
parsed_net_log_YYYY-MM-DD HH-MM-SS.txt
```

输出内容包括：

- 时间戳
- 命令码
- 设备地址和枪号
- 解析后的结构化数据

## 开发指南

### 添加新协议

#### 步骤1: 定义协议类型

在 `main.py` 的 `ProtocolType` 枚举中添加新协议：

```python
class ProtocolType(Enum):
    # 现有协议...
    NEW_PROTOCOL = ("new_protocol", "new_protocol.log",
                   "./resources/format_new_protocol.txt",
                   ProtocolConfig(head_len=8, tail_len=1, frame_head=r"FF AA"))
```

#### 步骤2: 创建协议实现类

```python
# src/new_protocol.py
from src.base_protocol import BaseProtocol, ProtocolConfig
from typing import Any, Dict, List

class NewProtocol(BaseProtocol):
    def __init__(self, log_file_name: str, format_file_path: str, config: ProtocolConfig):
        super().__init__(log_file_name, format_file_path, config)

    def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """实现具体的数据内容解析逻辑"""
        # 自定义解析逻辑
        pass

    def run(self):
        """实现协议运行逻辑"""
        # 自定义运行逻辑
        pass
```

#### 步骤3: 注册协议类

在 `main.py` 的 `get_protocol_class()` 函数中添加映射：

```python
protocol_map = {
    ProtocolType.V8: V8Protocol,
    ProtocolType.XIAOJU: XiaojuProtocol,
    ProtocolType.NEW_PROTOCOL: NewProtocol,  # 新增
}
```

#### 步骤4: 创建格式定义文件

在 `resources/` 目录下创建 `format_new_protocol.txt`，定义字段格式。

### 自定义字段解析

#### 添加新的字段类型

在 `field_parser.py` 中扩展字段解析：

```python
# 1. 添加到对应的字段类型列表
custom_keys = ["自定义字段名", "特殊数据类型"]

# 2. 在 parse_byte_data 函数中添加解析逻辑
elif format_key in custom_keys:
    parsed_dict[key] = parse_custom_field(data)

# 3. 实现自定义解析函数
def parse_custom_field(data_list: List[int]) -> Any:
    """
    自定义字段解析函数

    Args:
        data_list: 字节数据列表

    Returns:
        解析后的数据
    """
    # 实现自定义解析逻辑
    return parsed_value
```

### 测试开发

#### 单元测试

```python
# tests/test_new_protocol.py
import unittest
from src.new_protocol import NewProtocol
from src.base_protocol import ProtocolConfig

class TestNewProtocol(unittest.TestCase):
    def setUp(self):
        self.config = ProtocolConfig(8, 1, r"FF AA")
        self.protocol = NewProtocol("test.log", "test_format.txt", self.config)

    def test_parse_data_content(self):
        # 测试数据内容解析
        pass

    def test_message_parsing(self):
        # 测试消息解析
        pass
```

## 性能优化

### 大文件处理

- **流式处理**: 支持大文件分块读取，避免内存溢出
- **并发解析**: 可配置多线程解析提升处理速度
- **缓存机制**: 格式定义文件缓存，减少重复解析

### 内存管理

- **数据清理**: 及时释放已处理的数据对象
- **垃圾回收**: 合理使用Python垃圾回收机制
- **内存监控**: 提供内存使用情况监控

## 故障排除

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 文件读取失败 | 文件路径错误或权限不足 | 检查文件路径和读取权限 |
| 解析结果为空 | 协议头标识不匹配 | 确认日志文件格式和协议类型 |
| 内存不足 | 文件过大 | 分批处理或增加系统内存 |
| 格式解析错误 | 格式定义文件语法错误 | 检查格式文件语法 |

### 调试模式

启用详细日志输出：

```python
# 在代码中设置日志级别
from src.logger_instance import log
log.set_debug_mode(True)
```

## 更新日志

### v1.5.0 (2025-08-30)
- 🏗️ 重构为统一的多协议框架
- 📦 支持配置化协议管理
- 🔧 优化字段解析器性能
- 📝 完善文档和代码注释
- 🧪 添加单元测试支持

### v1.0.0 (初始版本)
- ✨ 支持V8协议解析
- 📋 基础报文格式解析
- 🔍 命令过滤功能

## 贡献指南

### 代码规范

- 遵循PEP 8 Python编码规范
- 使用类型注解提高代码可读性
- 编写完整的文档字符串
- 保持单一职责原则

### 提交规范

```bash
# 功能开发
git commit -m "feat: 添加新协议支持"

# 问题修复
git commit -m "fix: 修复字段解析错误"

# 文档更新
git commit -m "docs: 更新README文档"
```

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 技术支持

- 📖 **文档**: 查看项目中的 `使用说明.txt` 文件
- 🐛 **问题反馈**: 提交 GitHub Issues
- 💬 **技术交流**: 联系开发团队
- 📧 **邮件支持**: [support@example.com](mailto:support@example.com)

---

## 最后更新时间

2025-08-30