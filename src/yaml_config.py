"""
YAML配置加载器和数据模型
统一管理所有协议配置，取代原有的format.txt、field_types.ini、filter.txt
"""

import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Meta:
    """协议元数据"""
    protocol: str
    version: int = 1
    default_endian: str = "LE"  # LE/BE
    notes: Optional[str] = None


@dataclass
class TypeDef:
    """类型定义"""
    base: str  # uint, int, str, hex, bcd, time.cp56time2a, bitset
    bytes: Optional[int] = None  # 字节长度
    signed: Optional[bool] = None  # 是否有符号
    encoding: Optional[str] = None  # 字符编码
    bits: Optional[List[Dict[str, str]]] = None  # 位段定义
    
    def __post_init__(self):
        """类型定义后处理"""
        if self.base in ['uint', 'int'] and self.bytes is None:
            raise ValueError(f"Type {self.base} requires 'bytes' parameter")
        if self.base == 'bitset' and self.bits is None:
            raise ValueError("Bitset type requires 'bits' parameter")


@dataclass
class EnumDef:
    """枚举定义"""
    values: Dict[int, str]


@dataclass
class Field:
    """字段定义"""
    len: int  # 字段长度（字节）
    name: str  # 字段名称
    type: str  # 类型名称
    id: Optional[str] = None  # 字段ID，用于引用
    scale: Optional[float] = None  # 缩放因子
    endian: Optional[str] = None  # 端序，覆盖默认值
    enum: Optional[str] = None  # 枚举名称
    when: Optional[str] = None  # 条件表达式
    len_by: Optional[str] = None  # 按字段值确定长度
    size_by: Optional[str] = None  # 按字段值确定大小
    notes: Optional[str] = None  # 备注信息


@dataclass
class Group:
    """字段组（循环）"""
    repeat_by: Optional[str] = None  # 按字段值循环
    repeat_const: Optional[int] = None  # 固定次数循环
    fields: List[Union[Field, 'Group']] = field(default_factory=list)
    
    def __post_init__(self):
        """组定义后处理"""
        if self.repeat_by is None and self.repeat_const is None:
            raise ValueError("Group must specify either repeat_by or repeat_const")
        if self.repeat_by is not None and self.repeat_const is not None:
            raise ValueError("Group cannot specify both repeat_by and repeat_const")


@dataclass
class ProtocolConfig:
    """完整的协议配置"""
    meta: Meta
    types: Dict[str, TypeDef]
    enums: Dict[str, EnumDef]
    cmds: Dict[int, List[Union[Field, Group]]]
    
    # 原协议配置兼容字段
    head_len: int
    tail_len: int
    frame_head: str
    head_fields: List[Dict[str, Any]]


class YamlConfigLoader:
    """YAML配置加载器"""
    
    def __init__(self):
        self._cache: Dict[str, ProtocolConfig] = {}
    
    def load_protocol_config(self, config_path: Union[str, Path]) -> ProtocolConfig:
        """加载协议配置"""
        config_path = Path(config_path)
        
        if str(config_path) in self._cache:
            return self._cache[str(config_path)]
        
        if not config_path.exists():
            raise FileNotFoundError(f"Protocol config file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            config = self._parse_config(data)
            self._cache[str(config_path)] = config
            
            logger.info(f"Loaded protocol config: {config.meta.protocol}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load protocol config {config_path}: {e}")
            raise
    
    def _parse_config(self, data: Dict[str, Any]) -> ProtocolConfig:
        """解析配置数据"""
        # 解析元数据
        meta_data = data.get('meta', {})
        meta = Meta(
            protocol=meta_data.get('protocol', ''),
            version=meta_data.get('version', 1),
            default_endian=meta_data.get('default_endian', 'LE'),
            notes=meta_data.get('notes')
        )
        
        # 解析类型定义
        types = {}
        for type_name, type_data in data.get('types', {}).items():
            if isinstance(type_data, dict):
                types[type_name] = TypeDef(**type_data)
            else:
                # 简单类型定义，如 uint8: { base: uint, bytes: 1 }
                types[type_name] = TypeDef(base=str(type_data))
        
        # 解析枚举定义
        enums = {}
        for enum_name, enum_data in data.get('enums', {}).items():
            if isinstance(enum_data, dict):
                enums[enum_name] = EnumDef(values=enum_data)
        
        # 解析命令定义
        cmds = {}
        for cmd_id, cmd_fields in data.get('cmds', {}).items():
            cmds[int(cmd_id)] = self._parse_fields(cmd_fields)
        
        
        # 兼容性字段（从原protocol_configs.py迁移）
        compat_data = data.get('compatibility', {})
        head_len = compat_data.get('head_len', 11)
        tail_len = compat_data.get('tail_len', 2)
        frame_head = compat_data.get('frame_head', 'AA F5')
        head_fields = compat_data.get('head_fields', [])
        
        return ProtocolConfig(
            meta=meta,
            types=types,
            enums=enums,
            cmds=cmds,
            head_len=head_len,
            tail_len=tail_len,
            frame_head=frame_head,
            head_fields=head_fields
        )
    
    def _parse_fields(self, fields_data: List[Dict[str, Any]]) -> List[Union[Field, Group]]:
        """解析字段列表"""
        fields = []
        
        for field_data in fields_data:
            if 'group' in field_data or 'repeat_by' in field_data or 'repeat_const' in field_data:
                # 这是一个组
                if 'group' in field_data:
                    # 新格式：group字段包含fields
                    group_data = field_data['group']
                    group = Group(
                        repeat_by=field_data.get('repeat_by'),
                        repeat_const=field_data.get('repeat_const'),
                        fields=self._parse_fields(group_data.get('fields', []))
                    )
                else:
                    # 兼容格式：直接在字段数据中指定repeat_by/repeat_const
                    group = Group(
                        repeat_by=field_data.get('repeat_by'),
                        repeat_const=field_data.get('repeat_const'),
                        fields=self._parse_fields(field_data.get('fields', []))
                    )
                fields.append(group)
            else:
                # 这是一个普通字段
                field_obj = Field(**field_data)
                fields.append(field_obj)
        
        return fields
    
    def get_cmd_layout(self, config: ProtocolConfig, cmd_id: int) -> List[Union[Field, Group]]:
        """获取命令的字段布局"""
        if cmd_id not in config.cmds:
            raise ValueError(f"Command {cmd_id} not found in protocol {config.meta.protocol}")
        
        return config.cmds[cmd_id]
    
    def validate_config(self, config: ProtocolConfig) -> List[str]:
        """验证配置的完整性和正确性"""
        errors = []
        
        # 验证基本字段
        if not config.meta.protocol:
            errors.append("Protocol name is required")
        
        # 验证类型定义
        for type_name, type_def in config.types.items():
            try:
                # TypeDef的__post_init__会进行验证
                pass
            except ValueError as e:
                errors.append(f"Invalid type definition '{type_name}': {e}")
        
        # 验证命令定义
        for cmd_id, fields in config.cmds.items():
            cmd_errors = self._validate_fields(fields, config, f"cmd{cmd_id}")
            errors.extend(cmd_errors)
        
        return errors
    
    def _validate_fields(self, fields: List[Union[Field, Group]], 
                        config: ProtocolConfig, context: str) -> List[str]:
        """验证字段列表"""
        errors = []
        field_ids = set()
        
        for field_item in fields:
            if isinstance(field_item, Field):
                # 验证字段
                if field_item.type not in config.types:
                    errors.append(f"{context}: Unknown type '{field_item.type}' in field '{field_item.name}'")
                
                if field_item.enum and field_item.enum not in config.enums:
                    errors.append(f"{context}: Unknown enum '{field_item.enum}' in field '{field_item.name}'")
                
                if field_item.id:
                    if field_item.id in field_ids:
                        errors.append(f"{context}: Duplicate field ID '{field_item.id}'")
                    field_ids.add(field_item.id)
                    
            elif isinstance(field_item, Group):
                # 验证组
                if field_item.repeat_by and field_item.repeat_by not in field_ids:
                    errors.append(f"{context}: repeat_by references unknown field '{field_item.repeat_by}'")
                
                # 递归验证组内字段
                group_errors = self._validate_fields(field_item.fields, config, f"{context}.group")
                errors.extend(group_errors)
        
        return errors


# 全局加载器实例
yaml_loader = YamlConfigLoader()
