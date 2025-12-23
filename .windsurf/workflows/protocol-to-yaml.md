---
description: 协议文档到YAML配置的AI编辑工作流，逐CMD配置，避免上下文溢出
---

# 协议到YAML配置工作流

本工作流用于将协议文档转换为V8Parse的YAML配置文件。采用**分阶段、逐CMD**的方式，确保每个CMD配置前都重新读取对应文档位置，避免上下文溢出导致的记忆不准确问题。

---

## 阶段一：准备工作

### 1.1 确认协议文档位置

用户需提供协议文档路径，通常位于 `protocoltxt/` 目录下。

### 1.2 创建协议配置目录

// turbo

```bash
# 在 configs/ 下创建协议目录（如果不存在）
mkdir -p configs/<protocol_name>
```

### 1.3 读取配置模板

读取 `configs/protocol_template.yaml` 了解完整的配置规范，特别关注：

- **meta**: 协议元信息
- **compatibility**: 兼容性配置（帧头、头部字段）
- **types**: 数据类型定义
- **enums**: 枚举定义
- **cmds**: 命令定义
- **filters**: 过滤器配置

---

## 阶段二：文档分析（必须先完成）

### 2.1 读取协议文档目录结构

**首先读取协议文档的前200行**，获取目录和CMD分布概览：

```
读取文件: protocoltxt/<协议文档>.md，行范围: 1-200
```

### 2.2 提取CMD索引表

从目录中提取所有CMD及其在文档中的位置，创建索引表：

| CMD编号 | 命令名称 | 文档行号范围 | 配置状态 |
|---------|----------|--------------|----------|
| 1       | xxx      | 100-150      | 待配置   |
| 2       | xxx      | 151-200      | 待配置   |
| 99      | xxx      | 500-550      | TODO     |
| ...     | ...      | ...          | ...      |

配置状态说明：
- **待配置**：尚未处理
- **已配置**：配置完成
- **TODO**：无法配置，需要人工处理或等待模板支持

### 2.3 分析协议基本信息

从文档中提取：

- 帧头格式（frame_head）
- 报文头长度（head_len）
- 报文尾长度（tail_len）
- 头部字段定义（head_fields）
- 默认字节序（default_endian）

---

## 阶段三：初始化YAML配置

### 3.1 创建基础配置结构

基于阶段二的分析，创建 `configs/<protocol_name>/protocol.yaml` 的基础结构：

```yaml
meta:
  protocol: <protocol_name>
  version: 1
  default_endian: LE  # 或 BE
  notes: <协议说明>

compatibility:
  head_len: <头部长度>
  tail_len: <尾部长度>
  frame_head: "<帧头十六进制>"
  head_fields:
    - {name: "cmd", offset: <偏移>, length: <长度>, endian: "little", type: "uint"}
    # 其他头部字段...

types:
  # 基础类型（从模板复制）
  uint8:   { base: uint, bytes: 1, signed: false }
  uint16:  { base: uint, bytes: 2, signed: false }
  uint32:  { base: uint, bytes: 4, signed: false }
  # 根据协议需要添加更多类型...

enums:
  # 根据协议定义枚举...

cmds:
  # 逐个添加CMD配置...

filters:
  include_cmds: []
  exclude_cmds: []
```

---

## 阶段四：逐CMD配置（核心阶段）

### ⚠️ 重要原则

1. **每次只配置一个CMD**
2. **配置前必须重新读取该CMD对应的文档位置**
3. **配置完成后立即验证**
4. **记录配置进度**

### 4.1 CMD配置循环

对于每个待配置的CMD，执行以下步骤：

#### 步骤A：读取CMD文档

```
读取文件: protocoltxt/<协议文档>.md
行范围: <该CMD的起始行>-<该CMD的结束行>
```

#### 步骤B：分析字段结构

从文档中提取：

- 字段名称
- 字段长度（字节数）
- 数据类型
- 是否有枚举映射
- 是否有缩放因子
- 是否有条件字段
- 是否有循环结构

#### 步骤B.1：判断是否可配置

**如果遇到以下情况，该CMD标记为TODO，不进行配置**：

1. **文档描述不完整**：字段长度、类型等关键信息缺失
2. **复杂的动态结构**：无法用现有repeat_by/when等机制表达
3. **特殊编码格式**：模板不支持的数据格式（如自定义压缩、加密）
4. **依赖外部状态**：字段解析依赖于其他报文或运行时状态
5. **文档与实际不符**：有示例报文但与文档描述矛盾

**TODO标记格式**：

```yaml
cmds:
  # TODO: CMD 99 - 无法配置
  # 原因：[具体原因描述]
  # 文档位置：第XXX-XXX行
  # 待解决：[需要什么信息或支持才能配置]
  # 99:
  #   - {len: 0, name: 待实现, type: hex, len_to_end: true}
```

#### 步骤C：编写CMD配置

根据分析结果，编写该CMD的YAML配置：

```yaml
cmds:
  <cmd_id>:
    - {len: <长度>, name: <字段名>, type: <类型>}
    - {len: <长度>, name: <字段名>, type: <类型>, enum: <枚举名>}
    - {len: <长度>, name: <字段名>, type: <类型>, scale: <缩放因子>, unit: <单位>}
    # 循环结构示例
    - {len: 1, name: 数量, type: uint8, id: count}
    - repeat_by: count
      fields:
        - {len: 2, name: 数据项, type: uint16}
```

#### 步骤D：添加所需枚举

如果该CMD使用了新的枚举，在 `enums` 部分添加：

```yaml
enums:
  <enum_name>:
    0: <值0含义>
    1: <值1含义>
    # ...
```

#### 步骤E：添加所需类型

如果该CMD使用了新的数据类型，在 `types` 部分添加。

#### 步骤F：更新配置进度

在索引表中标记该CMD为"已配置"。

### 4.2 配置检查点

每配置5个CMD后，执行一次配置验证：
// turbo

```bash
python main.py --validate
```

---

## 阶段五：验证与测试

### 5.1 完整配置验证

// turbo

```bash
python main.py --validate
```

### 5.2 解析测试

如果有测试日志文件：

```bash
python main.py <protocol_name>
```

### 5.3 检查输出

查看 `parsed_log/` 目录下的解析结果，确认：

- 所有CMD都能正确识别
- 字段解析结果符合预期
- 枚举映射正确
- 缩放因子计算正确

---

## 配置规范速查

### 字段属性

| 属性 | 必填 | 说明 |
|------|------|------|
| len | 是 | 字段长度（字节），0表示变长 |
| name | 是 | 字段显示名称（建议中文） |
| type | 是 | 数据类型（必须在types中定义） |
| scale | 否 | 缩放因子，实际值 = 原始值 × scale |
| offset | 否 | 偏移量，实际值 = 原始值 + offset |
| unit | 否 | 单位（仅显示用） |
| enum | 否 | 枚举名称 |
| id | 否 | 字段标识符（用于repeat_by/len_by引用） |
| when | 否 | 条件表达式 |
| notes | 否 | 备注信息 |
| endian | 否 | 字节序（big/little） |
| len_by | 否 | 长度来源字段id |
| len_to_end | 否 | true表示读取到报文末尾 |
| bit_groups | 否 | 位段定义（仅用于bitfield类型） |

### types支持的base类型

| base类型 | 说明 | 必需属性 | 示例 |
|----------|------|----------|------|
| uint | 无符号整数 | bytes, signed:false | `{base: uint, bytes: 2, signed: false}` |
| int | 有符号整数 | bytes, signed:true | `{base: int, bytes: 2, signed: true}` |
| str | 字符串 | encoding | `{base: str, encoding: ASCII}` 或 `{base: str, encoding: UTF8}` |
| hex | 十六进制原始数据 | 无 | `{base: hex}` |
| bcd | BCD码 | bytes | `{base: bcd, bytes: 4}` |
| time.cp56time2a | IEC104时间格式 | bytes:7 | `{base: time.cp56time2a, bytes: 7}` |
| binary_str | 二进制字符串显示 | bytes | `{base: binary_str, bytes: 2}` |
| bitset | 位集合（每位独立命名） | bits列表 | 见下方示例 |
| bitfield | 位段（可定义多位组） | bytes, order | `{base: bitfield, bytes: 2, order: lsb0}` |

### 常用类型定义参考

```yaml
types:
  # 基础整数类型
  uint8:   { base: uint, bytes: 1, signed: false }    # 0-255
  uint16:  { base: uint, bytes: 2, signed: false }    # 0-65535
  uint32:  { base: uint, bytes: 4, signed: false }    # 0-4294967295
  int8:    { base: int,  bytes: 1, signed: true }     # -128到27
  int16:   { base: int,  bytes: 2, signed: true }     # -32768到32767
  int32:   { base: int,  bytes: 4, signed: true }
  
  # 字符串类型
  ascii:   { base: str,  encoding: ASCII }
  utf8:    { base: str,  encoding: UTF8 }
  
  # 特殊显示类型
  hex:     { base: hex }                              # 16进制显示
  
  # BCD码类型（根据协议需要选择）
  bcd1:    { base: bcd, bytes: 1 }                   # 最多2位十进制
  bcd2:    { base: bcd, bytes: 2 }                   # 最多4位十进制
  bcd3:    { base: bcd, bytes: 3 }                   # 最多6位十进制
  bcd4:    { base: bcd, bytes: 4 }                   # 最多8位十进制
  bcd6:    { base: bcd, bytes: 6 }                   # 最多12位十进制
  bcd7:    { base: bcd, bytes: 7 }                   # 最多14位（常用于桩编码）
  bcd10:   { base: bcd, bytes: 10 }                  # 最多20位（常用于SIM卡号）
  bcd16:   { base: bcd, bytes: 16 }                  # 最多32位（常用于交易流水号）
  
  # 时间类型
  cp56time2a: { base: time.cp56time2a, bytes: 7 }    # IEC104标准时间格式
  # IEC104时间格式说明：
  # 字节0-1: 毫秒 (0-59999)
  # 字节2: 分钟 (0-59)
  # 字节3: 小时 (0-23)
  # 字节4: 日 (1-31)
  # 字节5: 月 (1-12)
  # 字节6: 年 (相对于2000年)
  
  # 二进制字符串类型
  binary_str_1byte:  { base: binary_str, bytes: 1 }
  binary_str_2bytes: { base: binary_str, bytes: 2 }
  binary_str_4bytes: { base: binary_str, bytes: 4 }
  binary_str_8bytes: { base: binary_str, bytes: 8 }
  
  # 位字段类型
  bitfield8:  { base: bitfield, bytes: 1, order: lsb0 }
  bitfield16: { base: bitfield, bytes: 2, order: lsb0 }
  bitfield32: { base: bitfield, bytes: 4, order: lsb0 }
  bitfield64: { base: bitfield, bytes: 8, order: lsb0 }  # 用于64个设备状态位
```

### bitset类型定义（每位独立命名）

```yaml
types:
  # 8位状态位示例
  device_status_bits:
    base: bitset
    bits:
      - {name: "设备在线状态"}      # 位0：0=离线，1=在线
      - {name: "充电状态"}         # 位1：0=未充电，1=正在充电
      - {name: "故障状态"}         # 位2：0=正常，1=故障
      - {name: "门锁状态"}         # 位3：0=未锁，1=已锁
      - {name: "急停状态"}         # 位4：0=正常，1=急停
      - {name: "预留位5"}          # 位5：预留
      - {name: "预留位6"}          # 位6：预留
      - {name: "预留位7"}          # 位7：预留
  
  # 16位告警状态示例
  alarm_status_bits:
    base: bitset
    bits:
      - {name: "过压告警"}         # 位0
      - {name: "欠压告警"}         # 位1
      - {name: "过流告警"}         # 位2
      - {name: "过温告警"}         # 位3
      - {name: "通信故障"}         # 位4
      - {name: "接触器故障"}       # 位5
      - {name: "绝缘故障"}         # 位6
      - {name: "漏电故障"}         # 位7
      - {name: "风扇故障"}         # 位8
      - {name: "输入故障"}         # 位9
      - {name: "预留位10"}         # 位10
      - {name: "预留位11"}         # 位11
      - {name: "预留位12"}         # 位12
      - {name: "预留位13"}         # 位13
      - {name: "预留位14"}         # 位14
      - {name: "预留位15"}         # 位15
```

**bitset vs bitfield 区别**：
- **bitset**: 每个位独立解析，适用于开关状态（如：开/关、正常/故障）
- **bitfield**: 支持多位组合，适用于数值、枚举、复杂状态

### bitfield order说明

- `lsb0`: 最低有效位为bit0（常用）
- `msb0`: 最高有效位为bit0

### 循环结构

```yaml
# 变长循环（次数由字段值决定）
- {len: 1, name: 数量, type: uint8, id: count}
- repeat_by: count
  fields:
    - {len: 2, name: 数据, type: uint16}

# 固定循环
- repeat_const: 8
  fields:
    - {len: 2, name: 通道值, type: uint16}
    - {len: 1, name: 通道状态, type: uint8}
```

### 完整字段属性汇总

| 属性 | 必填 | 说明 |
|------|------|------|
| len | 是 | 字段长度（字节），0表示变长 |
| name | 是 | 字段显示名称（建议中文） |
| type | 是 | 数据类型（必须在types中定义） |
| scale | 否 | 缩放因子，实际值 = 原始值 × scale |
| offset | 否 | 偏移量，实际值 = 原始值 + offset（如温度-40） |
| unit | 否 | 单位（仅显示用），如 V、A、kWh、℃ |
| enum | 否 | 枚举名称 |
| id | 否 | 字段标识符（用于repeat_by/len_by/when引用） |
| when | 否 | 条件表达式，支持 ==, !=, >, <, >=, <= |
| notes | 否 | 备注信息 |
| endian | 否 | 字节序（big/little），覆盖默认值 |
| len_by | 否 | 长度来源字段id |
| len_to_end | 否 | true表示读取到报文末尾 |
| bit_groups | 否 | 位段定义（仅用于bitfield类型） |
| flatten | 否 | 扁平化输出（仅用于bitfield类型） |

### 条件字段

```yaml
- {len: 1, name: 类型, type: uint8, id: data_type}
- {len: 4, name: 扩展数据, type: uint32, when: "data_type == 1"}
- {len: 2, name: 简化数据, type: uint16, when: "data_type == 2"}
```

when支持的比较运算符：`==`, `!=`, `>`, `<`, `>=`, `<=`

### 变长字段（len_by）

```yaml
# 长度由其他字段决定
- {len: 2, name: 数据字节数, type: uint16, id: data_len}
- {len: 0, name: 变长数据, type: hex, len_by: data_len}

# len_by与when组合使用
- {len: 1, name: 操作类型, type: uint8, id: op_type}
- {len: 2, name: 设置参数字节数, type: uint16, id: param_len}
- {len: 0, name: 设置数据, type: hex, len_by: param_len, when: "op_type == 1"}
```

### 读取剩余数据（len_to_end）

```yaml
# 读取从当前位置到报文末尾的所有数据
- {len: 1, name: 操作类型, type: uint8, id: op_type}
- {len: 1, name: 操作结果, type: uint8}
- {len: 0, name: 查询参数信息, type: hex, len_to_end: true, when: "op_type == 0"}
```

### 位字段（带bit_groups的字段定义）

```yaml
# 简单位字段
- len: 2
  name: 状态字
  type: bitfield16
  bit_groups:
    - {name: "状态1", start_bit: 0, width: 1}
    - {name: "模式", start_bit: 1, width: 2, enum: mode_enum}

# 复杂位字段示例（实际配置参考）
- len: 2
  name: 终端充电状态
  type: bitfield16
  bit_groups:
    - {name: 插枪信号, start_bit: 0, width: 1}
    - {name: 系统启动状态, start_bit: 1, width: 1}
    - {name: 模块启动状态, start_bit: 2, width: 1}
    - {name: 模块挡位, start_bit: 3, width: 1}
    - {name: 预留1, start_bit: 4, width: 1}
    - {name: 双枪单枪, start_bit: 5, width: 1}
    - {name: 风扇状态, start_bit: 6, width: 1}
    - {name: 并充状态, start_bit: 7, width: 1}
    - {name: 预留2, start_bit: 8, width: 1}
    - {name: 超充机型, start_bit: 9, width: 1}
    - {name: 绝缘状态, start_bit: 10, width: 1}
    - {name: 中间接触器状态, start_bit: 11, width: 1}
    - {name: 预充信号, start_bit: 12, width: 1}

# 行内简写格式（适用于简单情况）
- {len: 2, name: 接触器状态, type: bitfield16, bit_groups: [{name: 存在, start_bit: 0, width: 1}, {name: 控制闭合, start_bit: 1, width: 1}, {name: 拒动, start_bit: 2, width: 1}]}
```

bit_groups属性说明：

| 属性 | 必填 | 说明 |
|------|------|------|
| name | 是 | 位段名称 |
| start_bit | 是 | 起始位（从0开始） |
| width | 是 | 位宽度 |
| enum | 否 | 枚举映射 |

bitfield字段级别属性：

| 属性 | 必填 | 说明 |
|------|------|------|
| flatten | 否 | true表示扁平化输出，将位组直接作为独立字段 |
| notes | 否 | 备注信息，如"Bit0~Bit63分别表示64个模块的状态" |

### bitfield扁平化输出示例

```yaml
# 不扁平化（默认）：输出嵌套结构
# "双泵控制状态" -> {"泵1状态": "工作模式", "泵2状态": "待机模式"}

# 扁平化（flatten: true）：输出独立字段
# "泵1状态": "工作模式", "泵2状态": "待机模式"
- len: 2
  name: 双泵控制状态
  type: bitfield16
  flatten: true
  bit_groups:
    - {name: 泵1状态, start_bit: 0, width: 4, enum: device_mode}
    - {name: 泵2状态, start_bit: 4, width: 4, enum: device_mode}
    - {name: 泵1转速, start_bit: 8, width: 4}
    - {name: 泵2转速, start_bit: 12, width: 4}
```

### 64位位字段示例（大量设备状态）

```yaml
# 用于64个模块的在线状态
- len: 8
  name: 模块在线状态
  type: bitfield64
  notes: "Bit0~Bit63分别表示1~64号模块的在线状态，0=离线，1=在线"
```

### head_fields头部字段定义

```yaml
compatibility:
  head_len: 11                   # 报文头长度
  tail_len: 2                    # 报文尾长度
  frame_head: "AA F5"           # 帧头标识（16进制字符串，空格分隔）
  head_fields:                   # 头部字段定义列表
    - {name: "cmd", offset: 4, length: 2, endian: "little", type: "uint"}
    - {name: "index", offset: 6, length: 2, endian: "little", type: "uint"}
    - {name: "deviceType", offset: 8, length: 1, endian: "little", type: "uint"}
    - {name: "addr", offset: 9, length: 1, endian: "little", type: "uint"}
    - {name: "gunNum", offset: 10, length: 1, endian: "little", type: "uint"}
```

head_fields各项属性：

| 属性 | 必填 | 说明 |
|------|------|------|
| name | 是 | 字段名称（cmd为必需字段） |
| offset | 是 | 在报文头中的偏移量（字节） |
| length | 是 | 字段长度（字节） |
| endian | 是 | 字节序："little" 或 "big" |
| type | 是 | 类型："uint"、"hex"、"const" |
| const_value | 否 | 当type="const"时必填，用于校验帧头固定值 |

**帧头常量校验示例**：

```yaml
head_fields:
  - {name: "startField", offset: 0, length: 2, endian: "big", type: "const", const_value: 0x7dd0}
  - {name: "cmd", offset: 4, length: 2, endian: "little", type: "uint"}
```

### 枚举定义规范

```yaml
enums:
  # 简单枚举
  login_result:
    0: 失败
    1: 成功
  
  # 多值枚举
  work_status:
    0: 空闲
    1: 握手阶段
    2: 配置阶段
    3: 充电中
    4: 充电结束阶段
    5: 故障
    6: 副枪并充状态
    7: 维护模式
    8: 作为副枪并充中
```

### 嵌套循环结构

```yaml
# 两层嵌套循环
- {len: 1, name: 组数, type: uint8, id: group_count}
- repeat_by: group_count
  fields:
    - {len: 1, name: 组ID, type: uint8}
    - {len: 1, name: 项目数, type: uint8, id: item_count}
    - repeat_by: item_count
      fields:
        - {len: 2, name: 项目值, type: uint16}
        - {len: 1, name: 项目状态, type: uint8}

# 三层嵌套循环（复杂场景）
- {len: 1, name: 站点数量, type: uint8, id: site_count}
- repeat_by: site_count
  fields:
    - {len: 2, name: 站点ID, type: uint16}
    - {len: 1, name: 充电桩数量, type: uint8, id: charger_count}
    - repeat_by: charger_count
      fields:
        - {len: 1, name: 充电桩编号, type: uint8}
        - {len: 1, name: 枪数量, type: uint8, id: gun_count_inner}
        - repeat_by: gun_count_inner
          fields:
            - {len: 1, name: 枪编号, type: uint8}
            - {len: 4, name: 累计充电量, type: uint32, scale: 0.01}
```

**repeat_by支持中文字段名**：

```yaml
# 可以直接使用中文字段名作为循环次数
- {len: 1, name: 最大模块数量, type: uint8}
- repeat_by: 最大模块数量
  fields:
    - {len: 2, name: 模块电压, type: uint16, scale: 0.1}
    - {len: 2, name: 模块电流, type: uint16, scale: 0.1}
```

### filters过滤器配置

```yaml
filters:
  include_cmds: []              # 包含的命令列表，空表示包含所有
  exclude_cmds: [255]           # 排除的命令列表
```

**过滤器使用说明**：
- `include_cmds` 和 `exclude_cmds` 不能同时使用
- 如果两个都为空，则解析所有命令
- `include_cmds` 优先级更高，如果设置了include_cmds，exclude_cmds会被忽略

---

## 常见问题处理

### Q1: 文档中字段描述不清晰

- 查看是否有示例报文
- 参考类似协议的配置
- 在notes中标注不确定的地方

### Q2: 遇到复杂的嵌套结构

- 使用多层repeat_by
- 每层循环使用不同的id

### Q3: 字段长度可变

- 使用len_by指定长度来源
- 或使用len_to_end读取剩余数据

### Q4: 需要跳过某些字节

- 使用hex类型读取原始数据
- 或使用预留字段名称

### Q5: 如何处理大端字节序？

在字段级别设置endian：
```yaml
- {len: 2, name: 大端数据, type: uint16, endian: big}
```

### Q6: 如何处理浮点数？

使用整数类型 + 缩放因子：
```yaml
- {len: 4, name: 温度值, type: uint32, scale: 0.001, unit: ℃}
```

### Q7: 如何处理不同版本的协议？

使用版本字段 + 条件字段：
```yaml
- {len: 1, name: 协议版本, type: uint8, id: version}
- {len: 4, name: V1字段, type: uint32, when: "version == 1"}
- {len: 8, name: V2字段, type: hex, when: "version == 2"}
```

### Q8: 如何处理变长字符串？

使用长度字段 + len_by：
```yaml
- {len: 1, name: 字符串长度, type: uint8, id: str_len}
- {len: 0, name: 字符串内容, type: ascii, len_by: str_len}
```

---

## 进度跟踪模板

```markdown
## 配置进度

- [x] 阶段一：准备工作
- [x] 阶段二：文档分析
- [x] 阶段三：初始化配置
- [ ] 阶段四：CMD配置
  - [x] CMD 1: xxx - 已配置
  - [x] CMD 2: xxx - 已配置
  - [ ] CMD 3: xxx - 待配置
  - [!] CMD 99: xxx - TODO（原因：文档描述不完整）
  - ...
- [ ] 阶段五：验证测试

## TODO清单（无法配置的CMD）

| CMD | 命令名称 | 原因 | 待解决 |
|-----|----------|------|--------|
| 99  | xxx      | 文档描述不完整 | 需要补充字段长度信息 |
| 100 | xxx      | 特殊编码格式 | 需要模板支持自定义解码 |
```
