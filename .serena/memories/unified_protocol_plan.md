# 统一协议解析方案

## 1. 配置驱动的头部解析架构

### 扩展ProtocolConfig
```python
@dataclass
class ProtocolConfig:
    # 基础配置
    head_len: int
    tail_len: int
    frame_head: str
    
    # 头部字段配置
    head_fields: List[HeaderField]
    
    # 可选配置
    time_regex: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{3}"
    cmd_aliases: Dict[int, int] = field(default_factory=dict)

@dataclass
class HeaderField:
    name: str           # 字段名称，如"cmd", "index", "addr"
    offset: int         # 字节偏移(0-based)
    length: int         # 字段长度(字节数)
    endian: str         # "little" 或 "big"
    type: str           # "uint", "const", "ascii", "hex"
    const_value: Optional[int] = None  # 当type="const"时的期望值
    required: bool = True  # 是否必须匹配(用于const验证)
```

## 2. 各协议配置定义

### V8协议配置
```python
V8_CONFIG = ProtocolConfig(
    head_len=11,
    tail_len=2,
    frame_head=r"AA F5",
    head_fields=[
        HeaderField("cmd", 4, 2, "little", "uint"),
        HeaderField("index", 6, 2, "little", "uint"),
        HeaderField("deviceType", 8, 1, "little", "uint"),
        HeaderField("addr", 9, 1, "little", "uint"),
        HeaderField("gunNum", 10, 1, "little", "uint"),
    ]
)
```

### 小桔协议配置
```python
XIAOJU_CONFIG = ProtocolConfig(
    head_len=14,
    tail_len=1,
    frame_head=r"7D D0",
    head_fields=[
        HeaderField("startField", 0, 2, "big", "const", const_value=0x7dd0),
        HeaderField("length", 2, 2, "little", "uint"),
        HeaderField("version", 4, 4, "big", "hex"),
        HeaderField("sequence", 8, 4, "little", "uint"),
        HeaderField("cmd", 12, 2, "little", "uint"),
    ]
)
```

### Sinexcel/运维协议配置
```python
SINEXCEL_CONFIG = ProtocolConfig(
    head_len=8,
    tail_len=1,
    frame_head=r"DD E8",
    head_fields=[
        HeaderField("cmd", 6, 2, "little", "uint"),
    ],
    cmd_aliases={1103: 1102, 1108: 1105}  # Sinexcel特有的cmd映射
)
```

## 3. BaseProtocol增强

### 统一parse_data_content实现
```python
def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """统一的头部字段解析实现"""
    valid_cmd = cmdformat.load_filter()
    filtered_data_groups = []
    
    for group in data_groups:
        data_bytes = group["data"].strip().split()
        if len(data_bytes) < self.config.head_len:
            continue
            
        # 解析所有头部字段
        parsed_fields = {}
        skip_group = False
        
        for field in self.config.head_fields:
            value = self._extract_field_value(data_bytes, field)
            
            # 常量验证
            if field.type == "const" and field.required:
                if value != field.const_value:
                    skip_group = True
                    break
            
            parsed_fields[field.name] = value
        
        if skip_group:
            continue
            
        # 应用cmd别名
        if "cmd" in parsed_fields:
            cmd = parsed_fields["cmd"]
            cmd = self.config.cmd_aliases.get(cmd, cmd)
            parsed_fields["cmd"] = cmd
            
            # 应用过滤
            if valid_cmd and cmd not in valid_cmd:
                continue
        
        # 更新group
        group.update(parsed_fields)
        filtered_data_groups.append(group)
    
    return filtered_data_groups

def _extract_field_value(self, data_bytes: List[str], field: HeaderField) -> Any:
    """根据字段配置提取值"""
    # 实现字段值提取逻辑
    pass
```

## 4. 实施步骤

1. **扩展ProtocolConfig**: 添加HeaderField和相关配置
2. **实现字段解析器**: _extract_field_value方法
3. **创建协议配置**: 为每个协议定义配置
4. **更新BaseProtocol**: 实现统一的parse_data_content
5. **简化协议类**: 移除重复的头部解析逻辑
6. **测试验证**: 确保所有协议正常工作

## 5. 预期收益

- **零代码新增协议**: 只需定义配置即可
- **统一维护**: 所有头部解析逻辑集中在BaseProtocol
- **配置化验证**: 支持常量字段验证和cmd别名映射
- **向后兼容**: 现有协议无需修改，逐步迁移