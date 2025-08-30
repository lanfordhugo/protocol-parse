# V8Parse - 多协议通信报文解析工具

## 项目简介

V8Parse是一个专业的多协议通信报文解析工具，主要用于解析和分析各种通信协议的日志数据。该工具采用模块化设计，支持多种协议格式，能够高效地从原始日志文件中提取、解析和格式化通信数据。

## 核心特性

- **多协议支持**: 支持V8、小桔、运维、Sinexcel等多种通信协议
- **灵活的报文格式**: 支持固定长度、循环字段、变长字段等多种报文格式
- **智能数据解析**: 自动识别和解析BCD码、ASCII码、二进制等多种数据格式
- **时间筛选**: 支持按时间范围筛选日志数据
- **命令过滤**: 支持按命令码过滤特定类型的报文
- **结构化输出**: 解析结果以结构化格式输出，便于分析

## 支持的协议类型

| 协议名称 | 协议头标识 | 头长度 | 尾长度 | 格式文件 |
|---------|-----------|--------|--------|----------|
| V8 | AA F5 | 11字节 | 2字节 | format_mcu_ccu.txt |
| 小桔(XIAOJU) | 7D D0 | 14字节 | 1字节 | format_xiaoju.txt |
| 运维(YUNWEI) | CC D7 | 8字节 | 1字节 | format_yunwei.txt |
| Sinexcel | DD E8 | 8字节 | 1字节 | format_sinexcel.txt |

## 项目结构

```text
v8parse/
├── main.py                 # 主程序入口，统一的协议解析框架
├── v8_run.py              # V8协议专用运行脚本
├── sinexcel_run.py        # Sinexcel协议专用运行脚本
├── yunwei_run.py          # 运维协议专用运行脚本
├── src/                   # 核心源码目录
│   ├── base_protocol.py   # 基础协议抽象类
│   ├── v8_protocol.py     # V8协议实现
│   ├── xiaoju_protocol.py # 小桔协议实现
│   ├── sincexcel_portocol.py # Sinexcel协议实现
│   ├── yunwei_portocol.py # 运维协议实现
│   ├── field_parser.py    # 字段解析器
│   ├── cmdformat.py       # 命令格式解析
│   ├── console_log.py     # 控制台日志输出
│   ├── logger_instance.py # 日志实例
│   └── m_print.py         # 打印工具
├── resources/             # 资源文件目录
│   ├── format_mcu_ccu.txt # V8协议格式定义
│   ├── format_xiaoju.txt  # 小桔协议格式定义
│   ├── format_yunwei.txt  # 运维协议格式定义
│   ├── format_sinexcel.txt # Sinexcel协议格式定义
│   ├── filter.txt         # 命令过滤配置
│   └── alarm.conf         # 告警配置
├── parsed_log/            # 解析结果输出目录
├── log/                   # 日志文件目录
└── 使用说明.txt           # 详细使用说明
```

## 快速开始

### 1. 环境要求

- Python 3.7+
- 无需额外依赖包

### 2. 基本使用方法

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

### 4. 数据筛选配置

在日志文件前三行添加筛选条件（可选）：

```text
start:2021-06-04 18:13:23
end:2021-06-04 19:13:25
cmd:[104,106]
```

- `start`: 开始时间
- `end`: 结束时间
- `cmd`: 需要解析的命令码列表

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

## 扩展开发

### 添加新协议

1. 在 `ProtocolType` 枚举中添加新协议定义
2. 创建新的协议类继承 `BaseProtocol`
3. 实现 `parse_data_content()` 和 `run()` 方法
4. 在 `get_protocol_class()` 中添加映射关系
5. 创建对应的格式定义文件

### 自定义字段解析

在 `field_parser.py` 中添加新的解析规则：

```python
# 添加到对应的字段类型列表
custom_keys = ["自定义字段名"]

# 实现解析函数
def parse_custom_field(data_list, start_index, length):
    # 自定义解析逻辑
    return parsed_value, next_index
```

## 更新日志

- **v1.5**: 重构为统一的多协议框架，支持配置化协议管理
- **v1.0**: 初始版本，支持V8协议解析

## 技术支持

如有问题或建议，请查看项目中的 `使用说明.txt` 文件或联系开发团队。

---

**最后更新时间: 2025-08-30**