# base_protocol.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re
from src.console_log import ConsoleLog
import sys
from src.logger_instance import log
import src.cmdformat as cmdformat
from src.field_parser import parse_multi_bit_date
from collections import namedtuple

ProtocolConfig = namedtuple('ProtocolConfig', ['head_len', 'tail_len', 'frame_head'])

@dataclass
class HeaderField:
    """协议头部字段配置"""
    name: str                           # 字段名称，如"cmd", "index", "addr"
    offset: int                         # 字节偏移(0-based)
    length: int                         # 字段长度(字节数)
    endian: str                         # "little" 或 "big"
    type: str                           # "uint", "const", "ascii", "hex"
    const_value: Optional[int] = None   # 当type="const"时的期望值
    required: bool = True               # 是否必须匹配(用于const验证)


@dataclass
class ProtocolConfigNew:
    """协议配置"""
    # 基础配置
    head_len: int
    tail_len: int
    frame_head: str
    
    # 头部字段配置
    head_fields: List[HeaderField] = field(default_factory=list)
    
    # 可选配置
    time_regex: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{3}"
    cmd_aliases: Dict[int, int] = field(default_factory=dict)


# Legacy support - will be removed later
_LegacyProtocolConfig = namedtuple('_LegacyProtocolConfig', ['head_len', 'tail_len', 'frame_head'])

class BaseProtocol(ABC):
    """
    基础协议类,定义了所有协议共享的方法和属性
    """

    def __init__(self, log_file_name: str, format_file_path: str, config: ProtocolConfig):
        self.log = log
        self.log_file_name = log_file_name
        self.format_file_path = format_file_path
        self.config = config

    def parse_message(self, cmd: int, message: str) -> Dict[str, Any]:
        """
        解析消息
        
        :param cmd: 命令代码
        :param message: 消息字符串
        :return: 解析后的消息字典
        """
        format_ = cmdformat.get_format(self.format_file_path, cmd)
        data_list = cmdformat.strlist_to_hexlist(message)
        data_start_index = self.config.head_len
        valid_data_list = data_list[data_start_index:-self.config.tail_len]
        return parse_multi_bit_date(valid_data_list, format_)

    def extract_data_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        从文件中提取数据
        
        :param file_path: 文件路径
        :return: 提取的数据列表
        """
        info_line_re = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{3}")
        byte_sequence_re = re.compile(self.config.frame_head)

        data_groups = []
        current_group = None
        is_collecting_data = False

        try:
            with open(file_path, "r") as file:
                for line in file:
                    line = line.strip()
                    if line == "":
                        continue

                    info_line_match = info_line_re.search(line)
                    if info_line_match:
                        if current_group:
                            data_groups.append(current_group)
                            is_collecting_data = False
                        current_group = {"time": info_line_match.group(), "data": ""}
                        continue

                    # 检查行中是否包含特定字节序列
                    byte_sequence_match = byte_sequence_re.search(line)
                    if byte_sequence_match:
                        is_collecting_data = True
                        # 从匹配的字节序列开始收集数据
                        line = line[byte_sequence_match.start():]

                    if is_collecting_data and current_group is not None:
                        current_group["data"] += line + " "

                if current_group and current_group["data"]:
                    data_groups.append(current_group)

            return data_groups
        except IOError as e:
            log.e_print(f"无法打开文件 {file_path}: {str(e)}")
            raise IOError(f"无法打开文件 {file_path}: {str(e)}")

    def _extract_field_value(self, data_bytes: List[str], field: HeaderField) -> Any:
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

    def parse_data_content_unified(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """统一的头部字段解析实现"""
        if not hasattr(self.config, 'head_fields'):
            # 向后兼容：如果是旧配置，使用抽象方法
            return self.parse_data_content(data_groups)
            
        valid_cmd = cmdformat.load_filter()
        if valid_cmd is None:
            log.e_print("valid_cmd is None")
            return []
            
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
                if len(valid_cmd) > 0 and cmd not in valid_cmd:
                    continue
            
            # 更新group
            group.update(parsed_fields)
            filtered_data_groups.append(group)
        
        return filtered_data_groups

    @abstractmethod
    def parse_data_content(self, data_groups: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        解析数据内容
        
        :param data_groups: 数据组列表
        :return: 解析后的数据列表
        """
        pass

    def load_file_format(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载文件并格式化
        
        :param file_path: 文件路径
        :return: 格式化后的数据列表
        """
        log.i_print(f"加载解析格式文件:{file_path}")
        # 提取数据
        data_groups = self.extract_data_from_file(file_path)
        
        if len(data_groups) == 0:
            log.e_print(f"data_groups is empty")
            return []
        
        # 解析数据
        return self.parse_data_content(data_groups)

    def screen_parse_data(self, net_info_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        筛选解析报文并打印
        
        :param net_info_list: 网络信息列表
        :return: 解析后的数据列表
        """
        log.i_print("筛选解析报文并打印")
        for net_info in net_info_list:
            byte_data_str = net_info["data"]
            cmd = net_info["cmd"]
            net_info_time = net_info["time"]

            can_read_data = self.parse_message(cmd, byte_data_str)
            net_info['data'] = can_read_data

            if can_read_data:
                print(
                    "[{}] cmd={} port:{}-{}".format(
                        net_info["time"], cmd, net_info.get("addr", "N/A"), net_info.get("gunNum", "N/A")
                    )
                )

                for key, value in can_read_data.items():
                    try:
                        print("'{}': {}".format(key, value))
                    except Exception as err:
                        self.log.e_print("-----数据打印错误-----", err)
                print()
            else:
                self.log.d_print("cmd={} time={}报文数据未解析\n".format(cmd, net_info_time))

        return net_info_list

    @abstractmethod
    def run(self):
        """
        运行协议解析的抽象方法
        """
        
        log.e_print("run base protocol")
