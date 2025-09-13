"""
基于YAML配置的命令格式管理器
取代原有的cmdformat.py，使用YAML配置驱动
"""

from typing import Dict, List, Union, Optional, Any
from pathlib import Path
import logging

from src.yaml_config import yaml_loader, ProtocolConfig, Field, Group
from src.yaml_field_parser import YamlFieldParser

logger = logging.getLogger(__name__)


class YamlCmdFormat:
    """基于YAML配置的命令格式管理器"""
    
    def __init__(self, protocol_yaml_path: Union[str, Path]):
        self.config_path = Path(protocol_yaml_path)
        self.config = yaml_loader.load_protocol_config(self.config_path)
        self.field_parser = YamlFieldParser(self.config)
    
    def get_cmd_layout(self, cmd_id: int) -> List[Union[Field, Group]]:
        """获取命令的字段布局"""
        return yaml_loader.get_cmd_layout(self.config, cmd_id)
    
    def has_cmd(self, cmd_id: int) -> bool:
        """检查是否支持指定命令"""
        return cmd_id in self.config.cmds
    
    def parse_cmd_data(self, cmd_id: int, data: bytes) -> Dict[str, Any]:
        """解析命令数据"""
        if not self.has_cmd(cmd_id):
            raise ValueError(f"Unsupported command: {cmd_id}")
        
        fields = self.get_cmd_layout(cmd_id)
        return self.field_parser.parse_fields(data, fields)
    
    def get_supported_cmds(self) -> List[int]:
        """获取支持的命令列表"""
        return list(self.config.cmds.keys())
    
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """获取协议信息"""
        return {
            'protocol': self.config.meta.protocol,
            'version': self.config.meta.version,
            'default_endian': self.config.meta.default_endian,
            'notes': self.config.meta.notes,
            'supported_cmds': self.get_supported_cmds(),
            'head_len': self.config.head_len,
            'tail_len': self.config.tail_len,
            'frame_head': self.config.frame_head,
        }
    
    def get_head_fields(self) -> List[Dict[str, Any]]:
        """获取头部字段配置（兼容性）"""
        return self.config.head_fields
    
    def validate_config(self) -> List[str]:
        """验证配置"""
        return yaml_loader.validate_config(self.config)


# 兼容性函数，用于替换原有的cmdformat模块
def load_yaml_format(protocol_yaml_path: Union[str, Path]) -> YamlCmdFormat:
    """加载YAML格式配置"""
    return YamlCmdFormat(protocol_yaml_path)


def get_yaml_format(protocol_name: str) -> YamlCmdFormat:
    """根据协议名获取YAML格式配置"""
    config_path = Path(f"configs/{protocol_name}/protocol.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Protocol config not found: {config_path}")
    
    return load_yaml_format(config_path)


# 工具函数
def strlist_to_hexlist(str_list: List[str]) -> List[int]:
    """字符串列表转十六进制列表（保持兼容性）"""
    hex_list = []
    for s in str_list:
        try:
            # 移除空格并转换为十六进制
            hex_str = s.replace(' ', '')
            if len(hex_str) % 2 == 0:
                for i in range(0, len(hex_str), 2):
                    hex_list.append(int(hex_str[i:i+2], 16))
            else:
                logger.warning(f"Invalid hex string: {s}")
        except ValueError as e:
            logger.warning(f"Failed to convert hex string '{s}': {e}")
    
    return hex_list
