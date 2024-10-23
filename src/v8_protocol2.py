# src/v8_protocol.py

from src.base_protocol import BaseProtocol, ProtocolConfig
from src.field_parser import *
from typing import Any, Dict, List
import src.cmdformat as cmdformat
import sys
from src.console_log import ConsoleLog
from src.logger_instance import log

class V8Protocol(BaseProtocol):
    def __init__(self, log_file_name: str, format_file_path: str, config: ProtocolConfig):
        super().__init__(log_file_name, format_file_path, config)

    # def parse_message(self, cmd: int, message: str) -> Dict[str, Any]:
    #     """
    #     解析V8协议的消息
        
    #     :param cmd: 命令代码
    #     :param message: 消息字符串
    #     :return: 解析后的消息字典
    #     """
    #     format_ = cmdformat.get_format(self.file_path, cmd)
    #     data_list = cmdformat.strlist_to_hexlist(message)
    #     data_start_index = self.head_len
    #     valid_data_list = data_list[data_start_index:-self.tail_len]
    #     return parse_multi_bit_date(valid_data_list, format_)

    def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从结构化的数据中，提取出cmd码，报文序号，设备类型，设备地址，设备枪号等信息
        并且把数据字符串转化为列表。只处理valid_cmds中包含的cmd码。
        """
        log.i_print("提取结构化数据，得到cmd码,报文序号,设备类型,设备地址,设备枪号等信息")
        valid_cmd = cmdformat.load_filter()
        if valid_cmd is None:
            log.e_print("valid_cmd is empty")
            return []
        
        log.d_print("valid_cmd:{}".format(valid_cmd))
        filtered_data_groups = []
        for group in data_groups:
            data_bytes = group["data"].strip().split()
            if len(data_bytes) >= self.config.head_len:
                # 提取cmd码，第5,6字节，小端格式
                cmd = int(data_bytes[4], 16) + (int(data_bytes[5], 16) << 8)
                if len(valid_cmd) > 0 and cmd not in valid_cmd:
                    continue
                group["cmd"] = cmd
                # 提取报文序号，第7,8字节，小端格式
                group["index"] = int(data_bytes[6], 16) + (int(data_bytes[7], 16) << 8)
                # 提取设备类型，第9字节
                group["deviceType"] = int(data_bytes[8], 16)
                # 提取设备地址，第10字节
                group["addr"] = int(data_bytes[9], 16)
                # 提取设备枪号，第11字节
                group["gunNum"] = int(data_bytes[10], 16)
                filtered_data_groups.append(group)
        return filtered_data_groups

    def run(self):
        """
        运行V8协议解析
        """
        log.i_print("开始解析V8协议")
        self.custom_stdout = ConsoleLog(stream=sys.stdout)
        sys.stdout = self.custom_stdout
        g_net_info_list = self.load_file_format(self.log_file_name)
        self.screen_parse_data(g_net_info_list)
        sys.stdout = sys.stdout
