# src/xiaoju_protocol.py

from src.base_protocol import BaseProtocol, ProtocolConfig
from src.field_parser import *
from typing import Any, Dict, List
import src.cmdformat as cmdformat
import sys
from src.console_log import ConsoleLog
from src.logger_instance import log
from collections import namedtuple

class XiaojuProtocol(BaseProtocol):
    def __init__(self, log_file_name: str, format_file_path: str, config: ProtocolConfig):
        super().__init__(log_file_name, format_file_path, config)

    def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从结构化的数据中，提取出起始域、长度域、版本域、序列号域、命令代码等信息
        并且把数据字符串转化为列表。只处理valid_cmds中包含的cmd码。
        """
        log.i_print("提取结构化数据，得到起始域、长度域、版本域、序列号域、命令代码等信息")
        valid_cmd = cmdformat.load_filter()
        if valid_cmd is None:
            log.e_print("valid_cmd is None")
            return []
        
        filtered_data_groups = []
        for group in data_groups:
            data_bytes = group["data"].strip().split()
            if len(data_bytes) >= self.config.head_len:
                # 提取起始域，前2字节
                start_field = int(data_bytes[0] + data_bytes[1], 16)
                if start_field != 0x7dd0:
                    continue  # 如果起始域不正确，跳过这条数据
                
                # 提取长度域，第3,4字节，小端格式
                length = int(data_bytes[2], 16) + (int(data_bytes[3], 16) << 8)
                
                # 提取版本域，第5-8字节
                version = ''.join(data_bytes[4:8])
                
                # 提取序列号域，第9-12字节，小端格式
                sequence = int(data_bytes[8], 16) + (int(data_bytes[9], 16) << 8) + \
                           (int(data_bytes[10], 16) << 16) + (int(data_bytes[11], 16) << 24)
                
                # 提取命令代码，第13,14字节，小端格式
                cmd = int(data_bytes[12], 16) + (int(data_bytes[13], 16) << 8)
                
                if len(valid_cmd) > 0 and cmd not in valid_cmd:
                    continue
                
                group["startField"] = start_field
                group["length"] = length
                group["version"] = version
                group["sequence"] = sequence
                group["cmd"] = cmd
                filtered_data_groups.append(group)
        
        return filtered_data_groups

    def run(self):
        """
        运行XIAOJU协议解析
        """
        log.i_print("开始解析XIAOJU协议")
        self.custom_stdout = ConsoleLog(stream=sys.stdout)
        sys.stdout = self.custom_stdout
        g_net_info_list = self.load_file_format(self.log_file_name)
        self.screen_parse_data(g_net_info_list)
        sys.stdout = sys.stdout
