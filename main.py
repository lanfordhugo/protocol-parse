# main.py

from enum import Enum
from typing import Type
from src.v8_protocol2 import V8Protocol
from src.xiaoju_protocol import XiaojuProtocol
from src.base_protocol import BaseProtocol, ProtocolConfig


class ProtocolType(Enum):
    """·
    协议类型枚举
    # 协议类型枚举包含以下参数：
    # protocol_name: str - 协议名称
    # file_name: str - 日志文件名
    # file_path: str - 协议格式文件路径
    # head_len: int - 协议头长度
    #tail_len: int - 协议尾长度
    """

    V8 = ("v8", "v8_com.log", "./resources/format_mcu_ccu.txt", ProtocolConfig(11, 2, r"AA F5"))
    YUNWEI = ("yunwei", "yunwei.log", "./resources/format_yunwei.txt", ProtocolConfig(8, 1, r"CC D7"))
    SINCEXCEL = ("sincexcel", "sincexcel.csv", "./resources/format_sinexcel.txt", ProtocolConfig(8, 1, r"DD E8"))
    XIAOJU = ("xiaoju", "xiaoju.log", "./resources/format_xiaoju.txt", ProtocolConfig(14, 1, r"7D D0"))

    def __init__(
        self, protocol_name: str, file_name: str, format_file_path: str, config: ProtocolConfig
    ):
        self.protocol_name = protocol_name
        self.file_name = file_name
        self.format_file_path = format_file_path
        self.config = config

    # 协议类型
    @property
    def protocol_type(self) -> str:
        return self.protocol_name

    # 日志文件名
    @property
    def log_file_name(self) -> str:
        return self.file_name

    # 协议格式文件路径
    @property
    def protocol_format_file_path(self) -> str:
        return self.format_file_path

    # 头长度
    @property
    def protocol_head_len(self) -> int:
        return self.config.head_len

    # 尾长度
    @property
    def protocol_tail_len(self) -> int:
        return self.config.tail_len

    # 协议配置
    @property
    def protocol_config(self) -> ProtocolConfig:
        return self.config


def get_protocol_class(protocol_type: ProtocolType) -> Type[BaseProtocol]:
    """
    根据协议类型获取对应的协议类

    :param protocol_type: 协议类型枚举
    :return: 对应的协议类
    :raises ValueError: 如果协议类型不支持
    """
    protocol_map = {
        ProtocolType.V8: V8Protocol,
        ProtocolType.XIAOJU: XiaojuProtocol,
        # 添加其他协议类型映射
        # ProtocolType.YUNWEI: YunweiProtocol,
        # ProtocolType.SINCEXCEL: SincexcelProtocol,
    }

    protocol_class = protocol_map.get(protocol_type)
    if protocol_class is None:
        raise ValueError(f"不支持的协议类型: {protocol_type}")

    return protocol_class


def run_protocol(protocol_type: ProtocolType):
    """
    运行指定的协议

    :param protocol_type: 协议类型枚举
    """
    protocol_class = get_protocol_class(protocol_type)
    
    # 构造参数
    log_file_name = protocol_type.log_file_name
    format_file_path = protocol_type.protocol_format_file_path
    config = protocol_type.protocol_config
    
    # 创建协议实例
    protocol = protocol_class(log_file_name, format_file_path, config)
    
    # 运行协议
    protocol.run()


if __name__ == "__main__":
    # 可以从配置文件或命令行参数中读取PROTOCOL_TYPE
    PROTOCOL_TYPE = ProtocolType.XIAOJU
    # PROTOCOL_TYPE = ProtocolType.V8
    run_protocol(PROTOCOL_TYPE)
    
    
# 如果要指定某个字段使用什么方式解析，在field_parser.py中指定
