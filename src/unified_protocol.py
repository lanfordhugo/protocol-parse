# unified_protocol.py
"""
统一协议实现类
使用配置驱动的头部解析，替代各个协议的特定实现
"""

from src.base_protocol import BaseProtocol, ProtocolConfigNew
from src.field_parser import *
from typing import Any, Dict, List
import src.cmdformat as cmdformat
import sys
from src.console_log import ConsoleLog
from src.logger_instance import log


class UnifiedProtocol(BaseProtocol):
    """统一协议类，使用配置驱动的头部解析"""

    def __init__(self, log_file_name: str, format_file_path: str, config: ProtocolConfigNew):
        # 为了兼容性，我们需要创建一个兼容的config对象传给父类
        # 但是保存新的配置用于我们的解析
        self.new_config = config
        
        # 创建兼容的旧配置格式给父类
        from collections import namedtuple
        LegacyConfig = namedtuple('ProtocolConfig', ['head_len', 'tail_len', 'frame_head'])
        legacy_config = LegacyConfig(config.head_len, config.tail_len, config.frame_head)
        
        super().__init__(log_file_name, format_file_path, legacy_config)

    def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用配置驱动的头部字段解析"""
        valid_cmd = cmdformat.load_filter()
        if valid_cmd is None:
            log.e_print("valid_cmd is None")
            return []
            
        log.d_print(f"valid_cmd: {valid_cmd}")
        filtered_data_groups = []
        
        for group in data_groups:
            data_bytes = group["data"].strip().split()
            if len(data_bytes) < self.new_config.head_len:
                continue
                
            # 解析所有头部字段
            parsed_fields = {}
            skip_group = False
            
            for field in self.new_config.head_fields:
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
                cmd = self.new_config.cmd_aliases.get(cmd, cmd)
                parsed_fields["cmd"] = cmd
                
                # 应用过滤
                if len(valid_cmd) > 0 and cmd not in valid_cmd:
                    continue
            
            # 更新group
            group.update(parsed_fields)
            filtered_data_groups.append(group)
        
        return filtered_data_groups

    def _extract_field_value(self, data_bytes: List[str], field) -> Any:
        """根据字段配置提取值"""
        if field.offset + field.length > len(data_bytes):
            return None
            
        end_offset = field.offset + field.length
        field_bytes = data_bytes[field.offset:end_offset]
        
        if field.type == "uint" or field.type == "const":
            if field.endian == "little":
                # 小端序：低字节在前
                value = sum(int(b, 16) << (8*i) for i, b in enumerate(field_bytes))
            else:  # big endian
                # 大端序：高字节在前
                value = sum(int(b, 16) << (8*(field.length-1-i)) for i, b in enumerate(field_bytes))
            return value
        elif field.type == "hex":
            return ''.join(field_bytes)
        elif field.type == "ascii":
            return ''.join(chr(int(b, 16)) for b in field_bytes if int(b, 16) != 0)
        else:
            # 默认按uint处理
            if field.endian == "little":
                return sum(int(b, 16) << (8*i) for i, b in enumerate(field_bytes))
            else:
                return sum(int(b, 16) << (8*(field.length-1-i)) for i, b in enumerate(field_bytes))

    def run(self):
        """运行协议解析"""
        log.i_print(f"开始解析统一协议")
        self.custom_stdout = ConsoleLog(stream=sys.stdout)
        sys.stdout = self.custom_stdout
        g_net_info_list = self.load_file_format(self.log_file_name)
        self.screen_parse_data(g_net_info_list)
        sys.stdout = sys.stdout