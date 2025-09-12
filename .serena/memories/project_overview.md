# V8Parse 项目概览

## 项目简介
V8Parse是一个专业的多协议通信报文解析工具，专门用于解析和分析各种通信协议的日志数据。该工具采用面向对象的模块化设计，基于抽象基类和策略模式，支持多种协议格式。

## 核心特性
- 🔌 多协议支持：V8、小桔(XIAOJU)、运维(YUNWEI)、Sinexcel等协议
- 🚀 配置驱动架构：零代码添加新协议支持
- 📋 灵活的报文格式：支持固定长度、循环字段、变长字段等
- 🧠 智能数据解析：BCD码、ASCII码、二进制等多种数据格式
- ⏰ 时间筛选和命令过滤功能
- 📊 结构化输出，便于分析

## 技术栈
- **语言**: Python 3.7+ (当前运行环境: Python 3.11.11)
- **依赖**: 仅使用Python标准库，无第三方依赖
- **架构模式**: 配置驱动模式、抽象工厂模式、策略模式、模板方法模式
- **操作系统**: Windows/Linux/macOS (当前: Windows)

## 支持协议
| 协议名称 | 协议头标识 | 头长度 | 尾长度 | 格式文件 | 配置驱动 |
|---------|-----------|--------|--------|----------|---------|
| V8 | AA F5 | 11字节 | 2字节 | format_mcu_ccu.txt | ✅ |
| 小桔(XIAOJU) | 7D D0 | 14字节 | 1字节 | format_xiaoju.txt | ✅ |
| 运维(YUNWEI) | AA F5 | 11字节 | 2字节 | format_yunwei.txt | ✅ |
| Sinexcel | AA F5 | 8字节 | 1字节 | format_sinexcel.txt | ✅ |

## 项目结构
```
v8parse/
├── main.py                    # 主程序入口，配置驱动协议解析框架
├── protocol_configs.py        # 协议配置文件（顶层目录，易于配置）
├── src/                       # 核心源码目录
│   ├── unified_protocol.py    # 统一协议类（配置驱动）
│   ├── base_protocol.py       # 基础协议抽象类
│   ├── field_parser.py        # 字段解析器
│   ├── cmdformat.py           # 命令格式解析器
│   └── 其他工具模块...
├── resources/                 # 资源文件目录
│   ├── format_*.txt           # 协议格式定义文件
│   └── filter.txt             # 命令过滤配置
├── input_logs/                # 输入日志文件目录
└── parsed_log/                # 解析结果输出目录
```

## 核心模块
- **UnifiedProtocol**: 统一协议解析器，使用配置驱动的头部解析
- **BaseProtocol**: 抽象基类，定义协议解析的通用接口和流程
- **protocol_configs.py**: 协议配置中心，零代码添加新协议支持
- **FieldParser**: 字段解析引擎，支持多种数据格式
- **CmdFormat**: 命令格式管理器，处理协议格式定义文件