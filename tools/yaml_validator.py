#!/usr/bin/env python3
"""
文件名称: yaml_validator.py
内容摘要: YAML协议配置独立验证器，用于验证configs目录下协议配置文件的规范性
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24

本脚本是独立的验证工具，不依赖项目其他模块，可作为配置文件的第一道验证关卡。
"""

import sys
import yaml
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from enum import Enum


class ErrorLevel(Enum):
    """错误级别"""
    ERROR = "ERROR"      # 致命错误，必须修复
    WARNING = "WARNING"  # 警告，建议修复
    INFO = "INFO"        # 提示信息


@dataclass
class ValidationIssue:
    """验证问题"""
    level: ErrorLevel
    location: str       # 错误位置，如 "cmds.104.fields[2].电压值"
    message: str        # 错误原因
    suggestion: str     # 修改意见
    
    def __str__(self) -> str:
        return f"[{self.level.value}] {self.location}\n  原因: {self.message}\n  建议: {self.suggestion}"


@dataclass
class ValidationResult:
    """验证结果"""
    file_path: Path
    issues: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return any(i.level == ErrorLevel.ERROR for i in self.issues)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == ErrorLevel.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == ErrorLevel.WARNING)
    
    def add_error(self, location: str, message: str, suggestion: str):
        """添加错误"""
        self.issues.append(ValidationIssue(ErrorLevel.ERROR, location, message, suggestion))
    
    def add_warning(self, location: str, message: str, suggestion: str):
        """添加警告"""
        self.issues.append(ValidationIssue(ErrorLevel.WARNING, location, message, suggestion))
    
    def add_info(self, location: str, message: str, suggestion: str):
        """添加提示"""
        self.issues.append(ValidationIssue(ErrorLevel.INFO, location, message, suggestion))


class YamlConfigValidator:
    """YAML配置验证器"""
    
    # 支持的base类型
    VALID_BASE_TYPES = {
        'uint', 'int', 'str', 'hex', 'bcd', 'bitset', 'bitfield',
        'binary_str', 'time.cp56time2a', 'float'
    }
    
    # 需要bytes参数的base类型
    TYPES_REQUIRING_BYTES = {'uint', 'int', 'bitfield', 'binary_str', 'bcd', 'float'}
    
    # 有效的端序值
    VALID_ENDIAN = {'LE', 'BE', 'little', 'big'}
    
    # 有效的位序
    VALID_BIT_ORDER = {'lsb0', 'msb0'}
    
    def __init__(self):
        self.result: Optional[ValidationResult] = None
        self.config_data: Dict[str, Any] = {}
        self.defined_types: Set[str] = set()
        self.defined_enums: Set[str] = set()
        self.used_types: Set[str] = set()
        self.used_enums: Set[str] = set()
    
    def validate_file(self, file_path: Path) -> ValidationResult:
        """验证单个配置文件"""
        self.result = ValidationResult(file_path=file_path)
        self.config_data = {}
        self.defined_types = set()
        self.defined_enums = set()
        self.used_types = set()
        self.used_enums = set()
        
        # 1. 验证文件可读性和YAML语法
        if not self._validate_yaml_syntax(file_path):
            return self.result
        
        # 2. 验证顶级结构
        self._validate_top_level_structure()
        
        # 3. 验证meta部分
        self._validate_meta()
        
        # 4. 验证compatibility部分
        self._validate_compatibility()
        
        # 5. 验证types部分
        self._validate_types()
        
        # 6. 验证enums部分
        self._validate_enums()
        
        # 7. 验证cmds部分
        self._validate_cmds()
        
        # 8. 验证引用一致性
        self._validate_references()
        
        # 9. 最佳实践检查
        self._check_best_practices()
        
        return self.result
    
    def _validate_yaml_syntax(self, file_path: Path) -> bool:
        """验证YAML语法"""
        if not file_path.exists():
            self.result.add_error(
                location="文件",
                message=f"文件不存在: {file_path}",
                suggestion="检查文件路径是否正确"
            )
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
        except UnicodeDecodeError as e:
            self.result.add_error(
                location="文件编码",
                message=f"文件编码错误: {e}",
                suggestion="请确保文件使用UTF-8编码保存"
            )
            return False
        except yaml.YAMLError as e:
            # 解析YAML错误，提取行号信息
            error_msg = str(e)
            if hasattr(e, 'problem_mark') and e.problem_mark:
                mark = e.problem_mark
                self.result.add_error(
                    location=f"第 {mark.line + 1} 行, 第 {mark.column + 1} 列",
                    message=f"YAML语法错误: {e.problem if hasattr(e, 'problem') else error_msg}",
                    suggestion="检查该位置的缩进、冒号、引号等YAML语法"
                )
            else:
                self.result.add_error(
                    location="YAML语法",
                    message=f"YAML解析失败: {error_msg}",
                    suggestion="使用YAML在线验证工具检查语法"
                )
            return False
        
        if self.config_data is None:
            self.result.add_error(
                location="文件内容",
                message="配置文件为空",
                suggestion="请添加必要的配置内容"
            )
            return False
        
        if not isinstance(self.config_data, dict):
            self.result.add_error(
                location="文件结构",
                message=f"配置文件顶层应为字典类型，实际为: {type(self.config_data).__name__}",
                suggestion="确保配置文件以 'meta:', 'types:', 'cmds:' 等键值对开始"
            )
            return False
        
        return True
    
    def _validate_top_level_structure(self):
        """验证顶级结构"""
        required_sections = ['meta', 'types', 'cmds']
        optional_sections = ['compatibility', 'enums', 'filters']
        valid_sections = set(required_sections + optional_sections)
        
        # 检查必需部分
        for section in required_sections:
            if section not in self.config_data:
                self.result.add_error(
                    location=f"顶级结构",
                    message=f"缺少必需的配置部分: '{section}'",
                    suggestion=f"请添加 '{section}:' 配置部分"
                )
        
        # 检查未知部分（警告）
        for section in self.config_data.keys():
            if section not in valid_sections:
                self.result.add_warning(
                    location=f"顶级结构.{section}",
                    message=f"未知的配置部分: '{section}'",
                    suggestion=f"有效的配置部分包括: {', '.join(valid_sections)}"
                )
    
    def _validate_meta(self):
        """验证meta部分"""
        meta = self.config_data.get('meta', {})
        if not isinstance(meta, dict):
            self.result.add_error(
                location="meta",
                message=f"meta应为字典类型，实际为: {type(meta).__name__}",
                suggestion="格式: meta:\n  protocol: 协议名\n  version: 1"
            )
            return
        
        # 必需字段
        if 'protocol' not in meta:
            self.result.add_error(
                location="meta.protocol",
                message="缺少必需字段: protocol",
                suggestion="添加 protocol: 协议名称"
            )
        elif not isinstance(meta['protocol'], str) or not meta['protocol'].strip():
            self.result.add_error(
                location="meta.protocol",
                message="protocol必须是非空字符串",
                suggestion="设置有效的协议名称，如 protocol: v8"
            )
        
        # 可选字段验证
        if 'default_endian' in meta:
            endian = meta['default_endian']
            if endian not in self.VALID_ENDIAN:
                self.result.add_error(
                    location="meta.default_endian",
                    message=f"无效的端序值: '{endian}'",
                    suggestion=f"有效值: {', '.join(self.VALID_ENDIAN)}"
                )
        
        if 'version' in meta:
            version = meta['version']
            if not isinstance(version, (int, float, str)):
                self.result.add_warning(
                    location="meta.version",
                    message=f"version类型异常: {type(version).__name__}",
                    suggestion="建议使用整数或字符串，如 version: 1 或 version: '3.0A03'"
                )
    
    def _validate_compatibility(self):
        """验证compatibility部分"""
        compat = self.config_data.get('compatibility', {})
        if not compat:
            return  # compatibility是可选的
        
        if not isinstance(compat, dict):
            self.result.add_error(
                location="compatibility",
                message=f"compatibility应为字典类型，实际为: {type(compat).__name__}",
                suggestion="格式: compatibility:\n  head_len: 11\n  tail_len: 2"
            )
            return
        
        # 验证head_len
        if 'head_len' in compat:
            head_len = compat['head_len']
            if not isinstance(head_len, int) or head_len < 0:
                self.result.add_error(
                    location="compatibility.head_len",
                    message=f"head_len必须是非负整数，实际值: {head_len}",
                    suggestion="设置正确的报文头长度，如 head_len: 11"
                )
        
        # 验证tail_len
        if 'tail_len' in compat:
            tail_len = compat['tail_len']
            if not isinstance(tail_len, int) or tail_len < 0:
                self.result.add_error(
                    location="compatibility.tail_len",
                    message=f"tail_len必须是非负整数，实际值: {tail_len}",
                    suggestion="设置正确的报文尾长度，如 tail_len: 2"
                )
        
        # 验证frame_head
        if 'frame_head' in compat:
            frame_head = compat['frame_head']
            if not isinstance(frame_head, str):
                self.result.add_error(
                    location="compatibility.frame_head",
                    message=f"frame_head必须是字符串，实际类型: {type(frame_head).__name__}",
                    suggestion="格式: frame_head: 'AA F5'"
                )
            else:
                # 验证16进制格式
                parts = frame_head.replace(',', ' ').split()
                for part in parts:
                    try:
                        int(part, 16)
                    except ValueError:
                        self.result.add_error(
                            location="compatibility.frame_head",
                            message=f"无效的16进制值: '{part}'",
                            suggestion="使用空格分隔的16进制字符串，如 'AA F5'"
                        )
                        break
        
        # 验证head_fields
        if 'head_fields' in compat:
            head_fields = compat['head_fields']
            if not isinstance(head_fields, list):
                self.result.add_error(
                    location="compatibility.head_fields",
                    message=f"head_fields必须是列表，实际类型: {type(head_fields).__name__}",
                    suggestion="格式: head_fields:\n  - {name: cmd, offset: 4, length: 2}"
                )
            else:
                self._validate_head_fields(head_fields)
    
    def _validate_head_fields(self, head_fields: List):
        """验证head_fields列表"""
        for idx, field_def in enumerate(head_fields):
            loc = f"compatibility.head_fields[{idx}]"
            
            if not isinstance(field_def, dict):
                self.result.add_error(
                    location=loc,
                    message=f"head_field定义必须是字典，实际类型: {type(field_def).__name__}",
                    suggestion="格式: {name: cmd, offset: 4, length: 2, type: uint}"
                )
                continue
            
            # 必需字段
            required = ['name', 'offset', 'length']
            for req in required:
                if req not in field_def:
                    self.result.add_error(
                        location=f"{loc}.{req}",
                        message=f"缺少必需字段: {req}",
                        suggestion=f"添加 {req} 字段"
                    )
            
            # 验证offset和length类型
            if 'offset' in field_def and not isinstance(field_def['offset'], int):
                self.result.add_error(
                    location=f"{loc}.offset",
                    message=f"offset必须是整数，实际值: {field_def['offset']}",
                    suggestion="设置整数偏移量"
                )
            
            if 'length' in field_def and not isinstance(field_def['length'], int):
                self.result.add_error(
                    location=f"{loc}.length",
                    message=f"length必须是整数，实际值: {field_def['length']}",
                    suggestion="设置整数长度"
                )
    
    def _validate_types(self):
        """验证types部分"""
        types = self.config_data.get('types', {})
        if not isinstance(types, dict):
            self.result.add_error(
                location="types",
                message=f"types应为字典类型，实际为: {type(types).__name__}",
                suggestion="格式: types:\n  uint8: {base: uint, bytes: 1}"
            )
            return
        
        for type_name, type_def in types.items():
            self.defined_types.add(type_name)
            self._validate_single_type(type_name, type_def)
    
    def _validate_single_type(self, type_name: str, type_def: Any):
        """验证单个类型定义"""
        loc = f"types.{type_name}"
        
        if not isinstance(type_def, dict):
            self.result.add_error(
                location=loc,
                message=f"类型定义必须是字典，实际类型: {type(type_def).__name__}",
                suggestion="格式: {base: uint, bytes: 1}"
            )
            return
        
        # 验证base字段
        if 'base' not in type_def:
            self.result.add_error(
                location=f"{loc}.base",
                message="缺少必需字段: base",
                suggestion=f"添加 base 字段，有效值: {', '.join(self.VALID_BASE_TYPES)}"
            )
            return
        
        base = type_def['base']
        if base not in self.VALID_BASE_TYPES:
            self.result.add_error(
                location=f"{loc}.base",
                message=f"无效的base类型: '{base}'",
                suggestion=f"有效的base类型: {', '.join(self.VALID_BASE_TYPES)}"
            )
            return
        
        # 验证需要bytes参数的类型
        if base in self.TYPES_REQUIRING_BYTES:
            if 'bytes' not in type_def:
                self.result.add_error(
                    location=f"{loc}.bytes",
                    message=f"类型 '{base}' 需要指定 bytes 参数",
                    suggestion=f"添加 bytes 参数，如 bytes: 1"
                )
            elif not isinstance(type_def['bytes'], int) or type_def['bytes'] <= 0:
                self.result.add_error(
                    location=f"{loc}.bytes",
                    message=f"bytes必须是正整数，实际值: {type_def['bytes']}",
                    suggestion="设置正确的字节数"
                )
        
        # 验证bitset类型
        if base == 'bitset':
            if 'bits' not in type_def:
                self.result.add_error(
                    location=f"{loc}.bits",
                    message="bitset类型需要指定 bits 参数",
                    suggestion="添加 bits 列表定义各位含义"
                )
            elif not isinstance(type_def['bits'], list):
                self.result.add_error(
                    location=f"{loc}.bits",
                    message=f"bits必须是列表，实际类型: {type(type_def['bits']).__name__}",
                    suggestion="格式: bits:\n  - {name: 状态位0}\n  - {name: 状态位1}"
                )
            else:
                self._validate_bitset_bits(loc, type_def['bits'])
        
        # 验证bitfield类型的groups（如果有）
        if base == 'bitfield' and 'groups' in type_def:
            self._validate_bitfield_groups(loc, type_def['groups'], type_def.get('bytes', 1))
        
        # 验证order字段
        if 'order' in type_def:
            order = type_def['order']
            if order not in self.VALID_BIT_ORDER:
                self.result.add_error(
                    location=f"{loc}.order",
                    message=f"无效的位序值: '{order}'",
                    suggestion=f"有效值: {', '.join(self.VALID_BIT_ORDER)}"
                )
    
    def _validate_bitset_bits(self, loc: str, bits: List):
        """验证bitset的bits定义"""
        for idx, bit_def in enumerate(bits):
            bit_loc = f"{loc}.bits[{idx}]"
            
            if not isinstance(bit_def, dict):
                self.result.add_error(
                    location=bit_loc,
                    message=f"位定义必须是字典，实际类型: {type(bit_def).__name__}",
                    suggestion="格式: {name: 状态位名称}"
                )
                continue
            
            if 'name' not in bit_def:
                self.result.add_error(
                    location=f"{bit_loc}.name",
                    message="位定义缺少 name 字段",
                    suggestion="添加 name 字段描述该位含义"
                )
    
    def _validate_bitfield_groups(self, loc: str, groups: Any, total_bytes: int):
        """验证bitfield的groups定义"""
        if not isinstance(groups, list):
            self.result.add_error(
                location=f"{loc}.groups",
                message=f"groups必须是列表，实际类型: {type(groups).__name__}",
                suggestion="格式: groups:\n  - {name: 字段名, start_bit: 0, width: 1}"
            )
            return
        
        total_bits = total_bytes * 8
        used_bits: Set[int] = set()
        
        for idx, group in enumerate(groups):
            group_loc = f"{loc}.groups[{idx}]"
            
            if not isinstance(group, dict):
                self.result.add_error(
                    location=group_loc,
                    message=f"group定义必须是字典，实际类型: {type(group).__name__}",
                    suggestion="格式: {name: 字段名, start_bit: 0, width: 1}"
                )
                continue
            
            # 必需字段
            for req in ['name', 'start_bit', 'width']:
                if req not in group:
                    self.result.add_error(
                        location=f"{group_loc}.{req}",
                        message=f"缺少必需字段: {req}",
                        suggestion=f"添加 {req} 字段"
                    )
            
            if 'start_bit' in group and 'width' in group:
                start_bit = group['start_bit']
                width = group['width']
                
                # 验证类型
                if not isinstance(start_bit, int) or start_bit < 0:
                    self.result.add_error(
                        location=f"{group_loc}.start_bit",
                        message=f"start_bit必须是非负整数，实际值: {start_bit}",
                        suggestion="设置正确的起始位"
                    )
                    continue
                
                if not isinstance(width, int) or width <= 0:
                    self.result.add_error(
                        location=f"{group_loc}.width",
                        message=f"width必须是正整数，实际值: {width}",
                        suggestion="设置正确的位宽"
                    )
                    continue
                
                # 验证范围
                if start_bit + width > total_bits:
                    self.result.add_error(
                        location=group_loc,
                        message=f"位段范围 [{start_bit}, {start_bit + width - 1}] 超出总位数 {total_bits}",
                        suggestion=f"调整 start_bit 或 width，确保不超过 {total_bits} 位"
                    )
                    continue
                
                # 检查重叠
                group_bits = set(range(start_bit, start_bit + width))
                overlap = used_bits & group_bits
                if overlap:
                    self.result.add_error(
                        location=group_loc,
                        message=f"位段与之前定义的位段重叠，重叠位: {sorted(overlap)}",
                        suggestion="调整 start_bit 或 width 避免重叠"
                    )
                used_bits.update(group_bits)
    
    def _validate_enums(self):
        """验证enums部分"""
        enums = self.config_data.get('enums', {})
        if not enums:
            return  # enums是可选的
        
        if not isinstance(enums, dict):
            self.result.add_error(
                location="enums",
                message=f"enums应为字典类型，实际为: {type(enums).__name__}",
                suggestion="格式: enums:\n  status:\n    0: 空闲\n    1: 工作"
            )
            return
        
        for enum_name, enum_def in enums.items():
            self.defined_enums.add(enum_name)
            self._validate_single_enum(enum_name, enum_def)
    
    def _validate_single_enum(self, enum_name: str, enum_def: Any):
        """验证单个枚举定义"""
        loc = f"enums.{enum_name}"
        
        if not isinstance(enum_def, dict):
            self.result.add_error(
                location=loc,
                message=f"枚举定义必须是字典，实际类型: {type(enum_def).__name__}",
                suggestion="格式: 0: 含义1\n  1: 含义2"
            )
            return
        
        if not enum_def:
            self.result.add_warning(
                location=loc,
                message="枚举定义为空",
                suggestion="添加枚举值定义"
            )
            return
        
        # 验证枚举键值
        for key, value in enum_def.items():
            if not isinstance(key, (int, str)):
                self.result.add_warning(
                    location=f"{loc}.{key}",
                    message=f"枚举键类型异常: {type(key).__name__}",
                    suggestion="建议使用整数作为枚举键"
                )
            
            if not isinstance(value, str):
                self.result.add_warning(
                    location=f"{loc}.{key}",
                    message=f"枚举值应为字符串，实际类型: {type(value).__name__}",
                    suggestion="设置字符串描述"
                )
    
    def _validate_cmds(self):
        """验证cmds部分"""
        cmds = self.config_data.get('cmds', {})
        if not isinstance(cmds, dict):
            self.result.add_error(
                location="cmds",
                message=f"cmds应为字典类型，实际为: {type(cmds).__name__}",
                suggestion="格式: cmds:\n  1:\n    - {len: 1, name: 字段名, type: uint8}"
            )
            return
        
        if not cmds:
            self.result.add_warning(
                location="cmds",
                message="未定义任何命令",
                suggestion="添加命令定义"
            )
            return
        
        for cmd_id, cmd_fields in cmds.items():
            self._validate_single_cmd(cmd_id, cmd_fields)
    
    def _validate_single_cmd(self, cmd_id: Any, cmd_fields: Any):
        """验证单个命令定义"""
        # 验证命令ID
        try:
            cmd_id_int = int(cmd_id)
        except (ValueError, TypeError):
            self.result.add_error(
                location=f"cmds.{cmd_id}",
                message=f"命令ID必须是整数，实际值: {cmd_id}",
                suggestion="使用整数作为命令ID"
            )
            return
        
        loc = f"cmds.{cmd_id_int}"
        
        if not isinstance(cmd_fields, list):
            self.result.add_error(
                location=loc,
                message=f"命令字段必须是列表，实际类型: {type(cmd_fields).__name__}",
                suggestion="格式:\n  - {len: 1, name: 字段名, type: uint8}"
            )
            return
        
        if not cmd_fields:
            self.result.add_warning(
                location=loc,
                message="命令未定义任何字段",
                suggestion="添加字段定义"
            )
            return
        
        # 验证字段列表，收集字段ID
        field_ids: Set[str] = set()
        self._validate_fields(loc, cmd_fields, field_ids)
    
    def _validate_fields(self, loc: str, fields: List, field_ids: Set[str], depth: int = 0):
        """递归验证字段列表"""
        if depth > 10:
            self.result.add_error(
                location=loc,
                message="字段嵌套层级过深（超过10层）",
                suggestion="简化字段结构，减少嵌套层级"
            )
            return
        
        for idx, field_def in enumerate(fields):
            field_loc = f"{loc}.fields[{idx}]"
            
            if not isinstance(field_def, dict):
                self.result.add_error(
                    location=field_loc,
                    message=f"字段定义必须是字典，实际类型: {type(field_def).__name__}",
                    suggestion="格式: {len: 1, name: 字段名, type: uint8}"
                )
                continue
            
            # 判断是普通字段还是循环组
            if 'repeat_by' in field_def or 'repeat_const' in field_def:
                self._validate_group(field_loc, field_def, field_ids, depth)
            else:
                self._validate_single_field(field_loc, field_def, field_ids)
    
    def _validate_group(self, loc: str, group_def: Dict, field_ids: Set[str], depth: int):
        """验证循环组定义"""
        has_repeat_by = 'repeat_by' in group_def
        has_repeat_const = 'repeat_const' in group_def
        
        if has_repeat_by and has_repeat_const:
            self.result.add_error(
                location=loc,
                message="不能同时指定 repeat_by 和 repeat_const",
                suggestion="只保留一个循环控制方式"
            )
        
        if has_repeat_by:
            ref_id = group_def['repeat_by']
            if not isinstance(ref_id, str):
                self.result.add_error(
                    location=f"{loc}.repeat_by",
                    message=f"repeat_by必须是字符串引用，实际类型: {type(ref_id).__name__}",
                    suggestion="设置引用的字段ID，如 repeat_by: count"
                )
            elif ref_id not in field_ids:
                self.result.add_error(
                    location=f"{loc}.repeat_by",
                    message=f"引用的字段ID '{ref_id}' 未定义或定义在当前位置之后",
                    suggestion=f"确保在使用前定义字段ID，如 {{len: 1, name: 数量, type: uint8, id: {ref_id}}}"
                )
        
        if has_repeat_const:
            repeat_const = group_def['repeat_const']
            if not isinstance(repeat_const, int) or repeat_const <= 0:
                self.result.add_error(
                    location=f"{loc}.repeat_const",
                    message=f"repeat_const必须是正整数，实际值: {repeat_const}",
                    suggestion="设置正确的循环次数"
                )
        
        # 验证fields
        if 'fields' not in group_def:
            self.result.add_error(
                location=f"{loc}.fields",
                message="循环组缺少 fields 定义",
                suggestion="添加 fields 列表定义循环内的字段"
            )
        elif not isinstance(group_def['fields'], list):
            self.result.add_error(
                location=f"{loc}.fields",
                message=f"fields必须是列表，实际类型: {type(group_def['fields']).__name__}",
                suggestion="格式: fields:\n  - {len: 1, name: 字段名, type: uint8}"
            )
        else:
            # 递归验证组内字段
            self._validate_fields(loc, group_def['fields'], field_ids, depth + 1)
    
    def _validate_single_field(self, loc: str, field_def: Dict, field_ids: Set[str]):
        """验证单个字段定义"""
        field_name = field_def.get('name', '<未命名>')
        
        # 必需字段检查
        if 'name' not in field_def:
            self.result.add_error(
                location=f"{loc}.name",
                message="字段缺少 name 属性",
                suggestion="添加 name 属性描述字段名称"
            )
        elif not isinstance(field_def['name'], str) or not field_def['name'].strip():
            self.result.add_error(
                location=f"{loc}.name",
                message="name必须是非空字符串",
                suggestion="设置有效的字段名称"
            )
        
        if 'type' not in field_def:
            self.result.add_error(
                location=f"{loc}.type",
                message=f"字段 '{field_name}' 缺少 type 属性",
                suggestion="添加 type 属性指定数据类型"
            )
        else:
            type_name = field_def['type']
            self.used_types.add(type_name)
            
            # 类型引用检查
            if type_name not in self.defined_types:
                self.result.add_error(
                    location=f"{loc}.type",
                    message=f"字段 '{field_name}' 引用了未定义的类型: '{type_name}'",
                    suggestion=f"在 types 部分定义类型 '{type_name}'，或使用已定义的类型"
                )
        
        # len字段验证
        if 'len' not in field_def:
            self.result.add_error(
                location=f"{loc}.len",
                message=f"字段 '{field_name}' 缺少 len 属性",
                suggestion="添加 len 属性指定字段字节长度"
            )
        else:
            len_val = field_def['len']
            has_len_by = 'len_by' in field_def
            has_len_to_end = field_def.get('len_to_end', False)
            has_size_by = 'size_by' in field_def
            
            if isinstance(len_val, int):
                if len_val == 0:
                    # len: 0 必须配合 len_by, len_to_end 或 size_by 使用
                    if not (has_len_by or has_len_to_end or has_size_by):
                        self.result.add_error(
                            location=f"{loc}.len",
                            message=f"字段 '{field_name}' 的 len 为 0，但未指定变长控制方式",
                            suggestion="len: 0 必须配合 len_by、len_to_end: true 或 size_by 使用"
                        )
                elif len_val < 0:
                    self.result.add_error(
                        location=f"{loc}.len",
                        message=f"字段 '{field_name}' 的 len 不能为负数，实际值: {len_val}",
                        suggestion="设置正确的字节长度"
                    )
            elif isinstance(len_val, str):
                # 变长字段，引用其他字段
                if len_val not in field_ids:
                    self.result.add_error(
                        location=f"{loc}.len",
                        message=f"字段 '{field_name}' 的 len 引用了未定义的字段ID: '{len_val}'",
                        suggestion=f"确保在使用前定义字段ID '{len_val}'"
                    )
            else:
                self.result.add_error(
                    location=f"{loc}.len",
                    message=f"字段 '{field_name}' 的 len 类型无效: {type(len_val).__name__}",
                    suggestion="len应为整数或字段ID引用"
                )
        
        # 验证 len_by 引用
        if 'len_by' in field_def:
            len_by = field_def['len_by']
            if not isinstance(len_by, str):
                self.result.add_error(
                    location=f"{loc}.len_by",
                    message=f"字段 '{field_name}' 的 len_by 必须是字符串引用",
                    suggestion="设置引用的字段ID"
                )
            elif len_by not in field_ids:
                self.result.add_error(
                    location=f"{loc}.len_by",
                    message=f"字段 '{field_name}' 的 len_by 引用了未定义的字段ID: '{len_by}'",
                    suggestion=f"确保在使用前定义字段ID '{len_by}'"
                )
        
        # 验证 size_by 引用
        if 'size_by' in field_def:
            size_by = field_def['size_by']
            if not isinstance(size_by, str):
                self.result.add_error(
                    location=f"{loc}.size_by",
                    message=f"字段 '{field_name}' 的 size_by 必须是字符串引用",
                    suggestion="设置引用的字段ID"
                )
            elif size_by not in field_ids:
                self.result.add_error(
                    location=f"{loc}.size_by",
                    message=f"字段 '{field_name}' 的 size_by 引用了未定义的字段ID: '{size_by}'",
                    suggestion=f"确保在使用前定义字段ID '{size_by}'"
                )
        
        # id字段验证
        if 'id' in field_def:
            field_id = field_def['id']
            if not isinstance(field_id, str):
                self.result.add_error(
                    location=f"{loc}.id",
                    message=f"字段 '{field_name}' 的 id 必须是字符串，实际类型: {type(field_id).__name__}",
                    suggestion="设置字符串类型的字段ID"
                )
            elif field_id in field_ids:
                self.result.add_error(
                    location=f"{loc}.id",
                    message=f"字段ID '{field_id}' 重复定义",
                    suggestion="使用唯一的字段ID"
                )
            else:
                field_ids.add(field_id)
        
        # enum字段验证
        if 'enum' in field_def:
            enum_name = field_def['enum']
            self.used_enums.add(enum_name)
            
            if enum_name not in self.defined_enums:
                self.result.add_error(
                    location=f"{loc}.enum",
                    message=f"字段 '{field_name}' 引用了未定义的枚举: '{enum_name}'",
                    suggestion=f"在 enums 部分定义枚举 '{enum_name}'，或移除 enum 属性"
                )
        
        # scale字段验证
        if 'scale' in field_def:
            scale = field_def['scale']
            if not isinstance(scale, (int, float)):
                self.result.add_error(
                    location=f"{loc}.scale",
                    message=f"字段 '{field_name}' 的 scale 必须是数值，实际类型: {type(scale).__name__}",
                    suggestion="设置数值类型的缩放因子，如 scale: 0.1"
                )
            elif scale == 0:
                self.result.add_error(
                    location=f"{loc}.scale",
                    message=f"字段 '{field_name}' 的 scale 不能为0",
                    suggestion="设置非零的缩放因子"
                )
        
        # bit_groups字段验证（bitfield类型专用）
        if 'bit_groups' in field_def:
            bit_groups = field_def['bit_groups']
            if 'len' in field_def and isinstance(field_def['len'], int):
                self._validate_bitfield_groups(loc, bit_groups, field_def['len'])
        
        # endian字段验证
        if 'endian' in field_def:
            endian = field_def['endian']
            if endian not in self.VALID_ENDIAN:
                self.result.add_error(
                    location=f"{loc}.endian",
                    message=f"字段 '{field_name}' 的 endian 无效: '{endian}'",
                    suggestion=f"有效值: {', '.join(self.VALID_ENDIAN)}"
                )
        
        # when字段验证（条件表达式）
        if 'when' in field_def:
            when = field_def['when']
            if not isinstance(when, str):
                self.result.add_error(
                    location=f"{loc}.when",
                    message=f"字段 '{field_name}' 的 when 必须是字符串表达式",
                    suggestion="格式: when: 'field_id == 1'"
                )
        
        # 类型与长度一致性检查
        self._validate_type_length_consistency(loc, field_def, field_name)
    
    def _validate_type_length_consistency(self, loc: str, field_def: Dict, field_name: str):
        """验证类型与长度的一致性"""
        if 'type' not in field_def or 'len' not in field_def:
            return
        
        type_name = field_def['type']
        field_len = field_def['len']
        
        if not isinstance(field_len, int):
            return  # 变长字段不检查
        
        if type_name not in self.defined_types:
            return  # 类型未定义，已在其他地方报错
        
        type_def = self.config_data.get('types', {}).get(type_name, {})
        if not isinstance(type_def, dict):
            return
        
        type_bytes = type_def.get('bytes')
        if type_bytes is not None and isinstance(type_bytes, int):
            if field_len != type_bytes:
                self.result.add_warning(
                    location=f"{loc}.len",
                    message=f"字段 '{field_name}' 长度 ({field_len}) 与类型 '{type_name}' 定义的长度 ({type_bytes}) 不一致",
                    suggestion=f"将 len 修改为 {type_bytes}，或检查类型定义是否正确"
                )
    
    def _validate_references(self):
        """验证引用一致性"""
        # 此方法在字段验证时已内联检查，保留作为扩展点
        pass
    
    def _check_best_practices(self):
        """检查最佳实践（警告级别）"""
        # 检查未使用的类型
        unused_types = self.defined_types - self.used_types
        if unused_types:
            self.result.add_warning(
                location="types",
                message=f"以下类型已定义但未使用: {', '.join(sorted(unused_types))}",
                suggestion="移除未使用的类型定义，或在命令字段中使用它们"
            )
        
        # 检查未使用的枚举
        unused_enums = self.defined_enums - self.used_enums
        if unused_enums:
            self.result.add_warning(
                location="enums",
                message=f"以下枚举已定义但未使用: {', '.join(sorted(unused_enums))}",
                suggestion="移除未使用的枚举定义，或在命令字段中使用它们"
            )
        
        # 检查命令ID范围
        cmds = self.config_data.get('cmds', {})
        for cmd_id in cmds.keys():
            try:
                cmd_id_int = int(cmd_id)
                if cmd_id_int < 0:
                    self.result.add_warning(
                        location=f"cmds.{cmd_id}",
                        message=f"命令ID为负数: {cmd_id_int}",
                        suggestion="通常命令ID应为正整数"
                    )
                elif cmd_id_int > 65535:
                    self.result.add_warning(
                        location=f"cmds.{cmd_id}",
                        message=f"命令ID超出常规范围 (0-65535): {cmd_id_int}",
                        suggestion="检查命令ID是否正确"
                    )
            except (ValueError, TypeError):
                pass  # 已在其他地方报错


def print_result(result: ValidationResult):
    """打印验证结果"""
    print(f"\n{'='*70}")
    print(f"验证文件: {result.file_path}")
    print('='*70)
    
    if not result.issues:
        print("\n✅ 配置文件验证通过，未发现问题！")
        return
    
    # 按级别分组打印
    errors = [i for i in result.issues if i.level == ErrorLevel.ERROR]
    warnings = [i for i in result.issues if i.level == ErrorLevel.WARNING]
    infos = [i for i in result.issues if i.level == ErrorLevel.INFO]
    
    if errors:
        print(f"\n❌ 错误 ({len(errors)} 个):")
        print('-'*50)
        for issue in errors:
            print(f"\n{issue}")
    
    if warnings:
        print(f"\n⚠️ 警告 ({len(warnings)} 个):")
        print('-'*50)
        for issue in warnings:
            print(f"\n{issue}")
    
    if infos:
        print(f"\nℹ️ 提示 ({len(infos)} 个):")
        print('-'*50)
        for issue in infos:
            print(f"\n{issue}")
    
    print(f"\n{'='*70}")
    if result.has_errors:
        print(f"❌ 验证失败: {result.error_count} 个错误, {result.warning_count} 个警告")
    else:
        print(f"⚠️ 验证通过（有警告）: {result.warning_count} 个警告")
    print('='*70)


def validate_all_configs(configs_dir: Path) -> bool:
    """验证所有协议配置"""
    validator = YamlConfigValidator()
    all_valid = True
    
    yaml_files = list(configs_dir.glob("*/protocol.yaml"))
    
    if not yaml_files:
        print(f"未找到配置文件: {configs_dir}/*/protocol.yaml")
        return False
    
    print(f"发现 {len(yaml_files)} 个协议配置文件")
    
    for config_file in yaml_files:
        result = validator.validate_file(config_file)
        print_result(result)
        
        if result.has_errors:
            all_valid = False
    
    print(f"\n{'#'*70}")
    if all_valid:
        print("✅ 所有配置文件验证通过！")
    else:
        print("❌ 部分配置文件存在错误，请修复后重新验证")
    print('#'*70)
    
    return all_valid


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="YAML协议配置验证器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python yaml_validator.py                          # 验证所有配置
  python yaml_validator.py --all                    # 验证所有配置
  python yaml_validator.py configs/v8/protocol.yaml # 验证单个配置
        """
    )
    parser.add_argument(
        "config_path",
        nargs="?",
        help="要验证的配置文件路径（不指定则验证所有配置）"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="验证configs/目录下的所有协议配置"
    )
    
    args = parser.parse_args()
    
    # 确定项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if args.all or not args.config_path:
        # 验证所有配置
        configs_dir = project_root / "configs"
        if not configs_dir.exists():
            print(f"错误: 配置目录不存在: {configs_dir}")
            sys.exit(1)
        
        success = validate_all_configs(configs_dir)
        sys.exit(0 if success else 1)
    else:
        # 验证单个配置
        config_path = Path(args.config_path)
        if not config_path.is_absolute():
            config_path = Path.cwd() / config_path
        
        if not config_path.exists():
            print(f"错误: 配置文件不存在: {config_path}")
            sys.exit(1)
        
        validator = YamlConfigValidator()
        result = validator.validate_file(config_path)
        print_result(result)
        
        sys.exit(0 if not result.has_errors else 1)


if __name__ == "__main__":
    main()
