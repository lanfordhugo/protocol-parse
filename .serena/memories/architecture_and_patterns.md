# 架构设计和设计模式

## 系统架构概览

V8Parse采用配置驱动的多层架构设计，支持多协议解析：

```
┌─────────────────────────────────────────────┐
│              配置驱动层                      │
│         protocol_configs.py                │
│    (零代码添加新协议支持)                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              统一解析层                      │
│         unified_protocol.py                │
│     (配置驱动的通用解析逻辑)                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              抽象基类层                      │
│          base_protocol.py                  │
│    (定义通用接口和解析流程)                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│            字段解析引擎层                    │
│         field_parser.py                    │
│   (支持BCD、ASCII、Binary等格式)            │
└─────────────────────────────────────────────┘
```

## 核心设计模式

### 1. 配置驱动模式 (Configuration-Driven)
**位置**: `protocol_configs.py`
**目的**: 零代码添加新协议支持
```python
# 只需配置即可添加新协议
PROTOCOL_CONFIGS = {
    "new_protocol": ProtocolInfo(
        protocol_name="new_protocol",
        log_file="new_protocol.log",
        format_file="./resources/format_new.txt",
        config=ProtocolConfigNew(...)
    )
}
```

### 2. 模板方法模式 (Template Method)
**位置**: `BaseProtocol`类
**目的**: 定义解析流程骨架，子类实现具体细节
```python
def run(self):  # 模板方法
    # 1. 加载文件
    # 2. 解析数据
    # 3. 筛选和输出
    # 具体实现由子类完成
```

### 3. 策略模式 (Strategy)
**位置**: 不同协议的字段解析策略
**目的**: 根据字段类型选择不同的解析策略
```python
if field.type == "uint":
    # 数值解析策略
elif field.type == "ascii":
    # ASCII解析策略
elif field.type == "const":
    # 常量验证策略
```

### 4. 抽象工厂模式 (Abstract Factory)
**位置**: `main.py`中的协议创建
**目的**: 根据协议名称创建对应的解析器实例
```python
def run_protocol(protocol_name: str):
    protocol_info = get_protocol_info(protocol_name)
    protocol = UnifiedProtocol(...)  # 工厂创建
```

### 5. 单一职责原则 (SRP)
每个模块都有明确的单一职责：
- `protocol_configs.py`: 协议配置管理
- `unified_protocol.py`: 统一解析逻辑
- `field_parser.py`: 字段解析
- `cmdformat.py`: 格式文件解析
- `base_protocol.py`: 抽象基类定义

## 关键设计决策

### 1. 配置外置化
- 协议配置放在顶层 `protocol_configs.py`
- 非开发人员可直接修改配置
- 支持字段级精细配置

### 2. 头部字段配置化
使用 `HeaderField` 定义每个字段的解析规则：
```python
HeaderField(
    name="cmd",           # 字段名称
    offset=4,             # 字节偏移
    length=2,             # 字段长度
    endian="little",      # 字节序
    type="uint",          # 数据类型
    const_value=None,     # 常量值（可选）
    required=True         # 是否必需
)
```

### 3. 类型安全
- 大量使用类型注解
- NamedTuple 定义数据结构
- 类型验证和边界检查

### 4. 错误处理策略
- 分层错误处理
- 详细的错误日志
- 优雅降级机制

## 扩展性设计

### 添加新协议的扩展点
1. **配置扩展**: 在 `PROTOCOL_CONFIGS` 中添加配置
2. **字段类型扩展**: 在 `_extract_field_value` 中添加新类型
3. **格式扩展**: 创建新的格式定义文件
4. **解析逻辑扩展**: 继承 `BaseProtocol` 实现特殊逻辑

### 向后兼容性
- 保持旧的 `ProtocolConfig` 接口
- 支持遗留协议实现
- 渐进式迁移到新架构

## 数据流设计

```
输入日志文件 → 协议头识别 → 字段解析 → 格式化输出
     ↓              ↓           ↓          ↓
  时间筛选 → 头部字段提取 → 内容解析 → 结构化数据
     ↓              ↓           ↓          ↓
  命令过滤 → 配置驱动解析 → 类型转换 → 文件输出
```

## 性能优化策略

1. **流式处理**: 避免加载大文件到内存
2. **缓存机制**: 格式文件解析结果缓存
3. **早期过滤**: 在头部解析阶段就过滤无效数据
4. **类型优化**: 使用高效的数据结构

## 可测试性设计

1. **依赖注入**: 配置和文件路径可注入
2. **纯函数**: 字段解析函数无副作用
3. **模块化**: 每个组件可独立测试
4. **Mock点**: 文件IO和外部依赖可Mock