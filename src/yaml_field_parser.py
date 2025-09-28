"""
基于YAML配置的字段解析器
统一处理各种数据类型的解析和转换
"""

import struct
import logging
from typing import Dict, Any, List, Union, Optional
from datetime import datetime
import binascii

from src.yaml_config import ProtocolConfig, Field, Group, TypeDef

logger = logging.getLogger(__name__)


class YamlFieldParser:
    """基于YAML配置的字段解析器"""
    
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.type_parsers = self._build_type_parsers()
    
    def _build_type_parsers(self) -> Dict[str, callable]:
        """构建类型解析器映射"""
        return {
            'uint': self._parse_uint,
            'int': self._parse_int,
            'str': self._parse_str,
            'hex': self._parse_hex,
            'bcd': self._parse_bcd,
            'time.cp56time2a': self._parse_cp56time2a,
            'binary_str': self._parse_binary_str,
            'bitset': self._parse_bitset,
            'bitfield': self._parse_bitfield,
        }
    
    def parse_fields(self, data: bytes, fields: List[Union[Field, Group]], 
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """解析字段列表"""
        if context is None:
            context = {}
        
        result = {}
        offset = 0
        
        for field_item in fields:
            if isinstance(field_item, Field):
                # 解析普通字段
                field_result, consumed = self._parse_field(data[offset:], field_item, context)
                
                # 检查是否需要展平bitfield结果
                if hasattr(field_item, 'flatten') and field_item.flatten and isinstance(field_result, dict):
                    result.update(field_result)
                else:
                    result[field_item.name] = field_result
                
                # 保存字段值到上下文（如果有ID）
                if field_item.id:
                    context[field_item.id] = field_result
                
                offset += consumed
                
            elif isinstance(field_item, Group):
                # 解析字段组（循环）
                group_result, consumed = self._parse_group(data[offset:], field_item, context)
                result.update(group_result)
                offset += consumed
        
        return result
    
    def _parse_field(self, data: bytes, field: Field, context: Dict[str, Any]) -> tuple:
        """解析单个字段"""
        if len(data) < field.len:
            raise ValueError(f"Not enough data for field '{field.name}', need {field.len} bytes, got {len(data)}")
        
        # 获取类型定义
        if field.type not in self.config.types:
            raise ValueError(f"Unknown type '{field.type}' for field '{field.name}'")
        
        type_def = self.config.types[field.type]
        field_data = data[:field.len]
        
        # 解析基础值
        try:
            raw_value = self._parse_by_type(field_data, type_def, field)
            # 应用后处理（缩放、枚举映射等）
            processed_value = self._post_process_value(raw_value, field)
            return processed_value, field.len
        except Exception as e:
            logger.warning(f"Failed to parse field '{field.name}': {e}")
            return field_data.hex().upper(), field.len
    
    def _parse_group(self, data: bytes, group: Group, context: Dict[str, Any]) -> tuple:
        """解析字段组（循环）"""
        result = {}
        offset = 0
        
        # 确定循环次数
        if group.repeat_by:
            if group.repeat_by not in context:
                raise ValueError(f"Repeat count field '{group.repeat_by}' not found in context")
            repeat_count = context[group.repeat_by]
        elif group.repeat_const:
            repeat_count = group.repeat_const
        else:
            raise ValueError("Group must specify either repeat_by or repeat_const")
        
        # 循环解析
        group_items = []
        for i in range(repeat_count):
            item_result = self.parse_fields(data[offset:], group.fields, context.copy())
            group_items.append(item_result)
            
            # 计算这一轮消耗的字节数
            item_size = sum(self._calculate_field_size(f, context) for f in group.fields)
            offset += item_size
        
        # 生成组结果键名（基于第一个字段名）
        if group.fields:
            first_field_name = self._get_first_field_name(group.fields[0])
            if repeat_count == 1:
                # 单个项目，直接合并到结果中
                result.update(group_items[0])
            else:
                # 多个项目，创建数组
                result[f"{first_field_name}_list"] = group_items
        
        return result, offset
    
    def _get_first_field_name(self, field_item: Union[Field, Group]) -> str:
        """获取第一个字段的名称"""
        if isinstance(field_item, Field):
            return field_item.name
        elif isinstance(field_item, Group) and field_item.fields:
            return self._get_first_field_name(field_item.fields[0])
        else:
            return "unknown"
    
    def _calculate_field_size(self, field_item: Union[Field, Group], context: Dict[str, Any]) -> int:
        """计算字段或组的大小"""
        if isinstance(field_item, Field):
            return field_item.len
        elif isinstance(field_item, Group):
            # 计算组内所有字段的大小
            item_size = sum(self._calculate_field_size(f, context) for f in field_item.fields)
            
            # 乘以循环次数
            if field_item.repeat_by:
                repeat_count = context.get(field_item.repeat_by, 1)
            else:
                repeat_count = field_item.repeat_const or 1
            
            return item_size * repeat_count
        else:
            return 0
    
    def _parse_by_type(self, data: bytes, type_def: TypeDef, field: Field) -> Any:
        """根据类型定义解析数据"""
        parser = self.type_parsers.get(type_def.base)
        if not parser:
            raise ValueError(f"Unsupported type base: {type_def.base}")
        
        return parser(data, type_def, field)
    
    def _parse_uint(self, data: bytes, type_def: TypeDef, field: Field) -> int:
        """解析无符号整数"""
        endian = field.endian or self.config.meta.default_endian
        fmt = '<' if endian == 'LE' else '>'
        
        if len(data) == 1:
            fmt += 'B'
        elif len(data) == 2:
            fmt += 'H'
        elif len(data) == 4:
            fmt += 'L'
        elif len(data) == 8:
            fmt += 'Q'
        else:
            raise ValueError(f"Unsupported uint size: {len(data)} bytes")
        
        return struct.unpack(fmt, data)[0]
    
    def _parse_int(self, data: bytes, type_def: TypeDef, field: Field) -> int:
        """解析有符号整数"""
        endian = field.endian or self.config.meta.default_endian
        fmt = '<' if endian == 'LE' else '>'
        
        if len(data) == 1:
            fmt += 'b'
        elif len(data) == 2:
            fmt += 'h'
        elif len(data) == 4:
            fmt += 'l'
        elif len(data) == 8:
            fmt += 'q'
        else:
            raise ValueError(f"Unsupported int size: {len(data)} bytes")
        
        return struct.unpack(fmt, data)[0]
    
    def _parse_str(self, data: bytes, type_def: TypeDef, field: Field) -> str:
        """解析字符串"""
        encoding = type_def.encoding or 'ASCII'
        try:
            # 移除末尾的空字节
            clean_data = data.rstrip(b'\x00')
            return clean_data.decode(encoding)
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode string field '{field.name}' with {encoding}, using hex")
            return binascii.hexlify(data).decode('ascii')
    
    def _parse_hex(self, data: bytes, type_def: TypeDef, field: Field) -> str:
        """解析十六进制字符串"""
        return binascii.hexlify(data).decode('ascii').upper()
    
    def _parse_bcd(self, data: bytes, type_def: TypeDef, field: Field) -> str:
        """解析BCD码"""
        result = ""
        for byte in data:
            high = (byte >> 4) & 0x0F
            low = byte & 0x0F
            if high <= 9:
                result += str(high)
            if low <= 9:
                result += str(low)
        return result
    
    def _parse_cp56time2a(self, data: bytes, type_def: TypeDef, field: Field) -> str:
        """解析CP56Time2a时间格式"""
        if len(data) != 7:
            raise ValueError("CP56Time2a requires exactly 7 bytes")
        
        try:
            # CP56Time2a格式：毫秒(2) + 分钟(1) + 小时(1) + 日(1) + 月(1) + 年(1)
            ms = struct.unpack('<H', data[0:2])[0]
            minute = data[2] & 0x3F  # 低6位
            hour = data[3] & 0x1F   # 低5位
            day = data[4] & 0x1F    # 低5位
            month = data[5] & 0x0F  # 低4位
            year = data[6] & 0x7F   # 低7位 (相对于2000年)
            
            # 构造时间
            actual_year = 2000 + year
            second = ms // 1000
            millisecond = ms % 1000
            
            dt = datetime(actual_year, month, day, hour, minute, second, millisecond * 1000)
            return dt.isoformat()
            
        except (ValueError, OverflowError) as e:
            logger.warning(f"Failed to parse CP56Time2a: {e}, returning hex")
            return binascii.hexlify(data).decode('ascii').upper()
    
    def _parse_binary_str(self, data: bytes, type_def: TypeDef, field: Field) -> str:
        """解析二进制字符串（作为十六进制显示）"""
        return binascii.hexlify(data).decode('ascii').upper()
    
    def _parse_bitset(self, data: bytes, type_def: TypeDef, field: Field) -> Dict[str, bool]:
        """解析位段"""
        if not type_def.bits:
            return {"raw": binascii.hexlify(data).decode('ascii').upper()}
        
        # 将字节转换为整数
        if len(data) == 1:
            value = struct.unpack('B', data)[0]
        elif len(data) == 2:
            endian = field.endian or self.config.meta.default_endian
            fmt = '<H' if endian == 'LE' else '>H'
            value = struct.unpack(fmt, data)[0]
        else:
            # 对于更大的位段，当作十六进制处理
            return {"raw": binascii.hexlify(data).decode('ascii').upper()}
        
        result = {}
        for i, bit_def in enumerate(type_def.bits):
            if i < len(data) * 8:  # 确保不超出数据范围
                bit_value = (value >> i) & 1
                result[bit_def['name']] = bool(bit_value)
        
        return result
    
    def _parse_bitfield(self, data: bytes, type_def: TypeDef, field: Field) -> Dict[str, Any]:
        """解析位段字段"""
        # 优先使用字段级位段定义，回退到类型级定义（向后兼容）
        groups = field.get_bitfield_groups() if field.bit_groups else type_def.get_bitfield_groups()
        
        if not groups:
            return {"raw": binascii.hexlify(data).decode('ascii').upper()}
        
        # 将字节数据转换为整数（支持多字节）
        endian = field.endian or self.config.meta.default_endian
        value = self._bytes_to_int(data, endian)
        
        result = {}
        
        # 获取位序信息（优先从type_def，默认lsb0）
        bit_order = getattr(type_def, 'order', 'lsb0')
        
        for group in groups:
            # 提取位段值
            if bit_order == "msb0":
                # MSB0: 最高位为第0位
                total_bits = len(data) * 8
                actual_start = total_bits - group.start_bit - group.width
            else:
                # LSB0: 最低位为第0位 (默认)
                actual_start = group.start_bit
            
            # 创建掩码并提取值
            mask = (1 << group.width) - 1
            group_value = (value >> actual_start) & mask
            
            # 应用枚举映射
            if group.enum and group.enum in self.config.enums:
                enum_def = self.config.enums[group.enum]
                if group_value in enum_def.values:
                    result[group.name] = enum_def.values[group_value]
                else:
                    result[group.name] = f"Unknown({group_value})"
            else:
                result[group.name] = group_value
        
        return result
    
    def _bytes_to_int(self, data: bytes, endian: str) -> int:
        """将字节数据转换为整数"""
        if endian == 'LE':
            # 小端序
            value = 0
            for i, byte in enumerate(data):
                value |= byte << (i * 8)
        else:
            # 大端序
            value = 0
            for byte in data:
                value = (value << 8) | byte
        return value
    
    def _post_process_value(self, raw_value: Any, field: Field) -> Any:
        """后处理字段值（缩放、枚举映射等）"""
        processed_value = raw_value
        
        # 应用缩放因子
        if field.scale is not None and isinstance(raw_value, (int, float)):
            processed_value = raw_value * field.scale
        
        # 应用枚举映射
        if field.enum and field.enum in self.config.enums:
            enum_def = self.config.enums[field.enum]
            if raw_value in enum_def.values:
                processed_value = {
                    'value': raw_value,
                    'name': enum_def.values[raw_value]
                }
        
        return processed_value
