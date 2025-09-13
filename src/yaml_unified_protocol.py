"""
基于YAML配置的统一协议实现
完全使用YAML配置驱动，取代原有的unified_protocol.py
"""

from typing import Any, Dict, List, Optional
import logging
from pathlib import Path

from src.base_protocol import BaseProtocol
from src.yaml_cmdformat import YamlCmdFormat
from src.yaml_field_parser import YamlFieldParser
from src.console_log import ConsoleLog
from src.logger_instance import log

logger = logging.getLogger(__name__)


class YamlUnifiedProtocol(BaseProtocol):
    """基于YAML配置的统一协议类"""

    def __init__(self, log_file_name: str, protocol_yaml_path: str):
        # 加载YAML配置
        self.yaml_format = YamlCmdFormat(protocol_yaml_path)
        self.yaml_config = self.yaml_format.config
        
        # 创建兼容的旧配置格式给父类
        from collections import namedtuple
        LegacyConfig = namedtuple('ProtocolConfig', ['head_len', 'tail_len', 'frame_head'])
        legacy_config = LegacyConfig(
            self.yaml_config.head_len, 
            self.yaml_config.tail_len, 
            self.yaml_config.frame_head
        )
        
        # 初始化父类（传入dummy format_file_path）
        super().__init__(log_file_name, "", legacy_config)
        
        self.field_parser = YamlFieldParser(self.yaml_format.config)
        
        logger.info(f"Initialized YAML protocol: {self.yaml_config.meta.protocol}")

    def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用YAML配置解析数据内容"""
        filtered_data_groups = []
        
        for group in data_groups:
            try:
                # 解析数据字节
                data_bytes = group["data"].strip().split()
                if len(data_bytes) < self.yaml_config.head_len:
                    log.d_print(f"数据长度不足，跳过: {len(data_bytes)} < {self.yaml_config.head_len}")
                    continue
                
                # 转换为字节数组
                byte_data = bytes([int(b, 16) for b in data_bytes])
                
                # 解析头部字段
                header_info = self._parse_header(byte_data[:self.yaml_config.head_len])
                if not header_info:
                    continue
                
                cmd_id = header_info.get('cmd')
                if cmd_id is None:
                    log.d_print("未找到命令ID，跳过")
                    continue
                
                # 检查命令过滤
                if not self.yaml_format.should_include_cmd(cmd_id):
                    continue
                
                # 检查是否支持该命令
                if not self.yaml_format.has_cmd(cmd_id):
                    log.d_print(f"不支持的命令: {cmd_id}")
                    continue
                
                # 解析数据内容（跳过头部和尾部）
                content_data = byte_data[self.yaml_config.head_len:-self.yaml_config.tail_len if self.yaml_config.tail_len > 0 else None]
                
                try:
                    parsed_content = self.yaml_format.parse_cmd_data(cmd_id, content_data)
                    
                    # 构建结果
                    result = {
                        'timestamp': group.get('time', ''),  # 使用'time'而不是'timestamp'
                        'direction': group.get('direction', ''),
                        'raw_data': group.get('data', ''),
                        'header': header_info,
                        'cmd': cmd_id,
                        'content': parsed_content
                    }
                    
                    filtered_data_groups.append(result)
                    
                except Exception as e:
                    log.d_print(f"解析命令{cmd_id}数据失败: {e}")
                    # 添加原始数据作为备用
                    result = {
                        'timestamp': group.get('time', ''),  # 使用'time'而不是'timestamp'
                        'direction': group.get('direction', ''),
                        'raw_data': group.get('data', ''),
                        'header': header_info,
                        'cmd': cmd_id,
                        'content': {'raw': content_data.hex().upper()},
                        'parse_error': str(e)
                    }
                    filtered_data_groups.append(result)
                    
            except Exception as e:
                log.e_print(f"处理数据组失败: {e}")
                continue
        
        return filtered_data_groups

    def _parse_header(self, header_data: bytes) -> Optional[Dict[str, Any]]:
        """解析数据包头部"""
        try:
            header_fields = self.yaml_format.get_head_fields()
            header_info = {}
            
            for field_config in header_fields:
                name = field_config['name']
                offset = field_config['offset']
                length = field_config['length']
                endian = field_config['endian']
                field_type = field_config['type']
                
                if offset + length > len(header_data):
                    log.d_print(f"头部字段{name}超出数据范围")
                    continue
                
                field_data = header_data[offset:offset + length]
                
                # 解析字段值
                if field_type == 'uint':
                    value = self._parse_uint_field(field_data, endian)
                elif field_type == 'const':
                    value = self._parse_uint_field(field_data, endian)
                    # 检查常量值
                    expected = field_config.get('const_value')
                    if expected is not None and value != expected:
                        if field_config.get('required', True):
                            log.d_print(f"头部字段{name}常量检查失败: {value} != {expected}")
                            return None
                elif field_type == 'hex':
                    value = field_data.hex().upper()
                elif field_type == 'ascii':
                    value = field_data.decode('ascii', errors='ignore').rstrip('\x00')
                else:
                    value = field_data.hex().upper()
                
                header_info[name] = value
            
            return header_info
            
        except Exception as e:
            log.d_print(f"解析头部失败: {e}")
            return None

    def _parse_uint_field(self, data: bytes, endian: str) -> int:
        """解析无符号整数字段"""
        import struct
        
        fmt = '<' if endian == 'little' else '>'
        
        if len(data) == 1:
            return struct.unpack('B', data)[0]
        elif len(data) == 2:
            return struct.unpack(fmt + 'H', data)[0]
        elif len(data) == 4:
            return struct.unpack(fmt + 'L', data)[0]
        elif len(data) == 8:
            return struct.unpack(fmt + 'Q', data)[0]
        else:
            raise ValueError(f"Unsupported uint size: {len(data)}")

    def screen_parse_data(self, parse_data: List[Dict[str, Any]]):
        """筛选并打印解析结果，同时输出到特定的解析文件"""
        # 记录日志信息（带时间戳）
        log.i_print("筛选解析报文并打印")
        
        if not parse_data:
            log.printf("没有解析到有效数据")
            return
        
        # 创建解析结果输出文件
        protocol_info = self.yaml_format.get_protocol_info()
        protocol_name = protocol_info['protocol']
        
        import datetime
        import os
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        output_filename = f"parsed_{protocol_name}_log_{timestamp}.txt"
        output_path = os.path.join("parsed_log", output_filename)
        
        # 确保输出目录存在
        os.makedirs("parsed_log", exist_ok=True)
        
        # 准备输出内容
        output_lines = []
        
        # 协议信息
        output_lines.append(f"成功解析 {len(parse_data)} 条数据")
        output_lines.append(f"协议: {protocol_name} v{protocol_info['version']}")
        output_lines.append(f"支持命令: {len(protocol_info['supported_cmds'])} 个")
        
        # 统计命令频次
        cmd_stats = {}
        for item in parse_data:
            cmd = item.get('cmd')
            if cmd:
                cmd_stats[cmd] = cmd_stats.get(cmd, 0) + 1
        
        output_lines.append("命令统计:")
        for cmd, count in sorted(cmd_stats.items()):
            output_lines.append(f"  cmd{cmd}: {count} 条")
        
        # 详细输出所有数据
        for i, item in enumerate(parse_data):
            output_lines.append(f"\n=== 数据项 {i+1} ===")
            output_lines.append(f"时间: {item.get('timestamp', 'N/A')}")
            output_lines.append(f"方向: {item.get('direction', 'N/A')}")
            output_lines.append(f"命令: cmd{item.get('cmd', 'N/A')}")
            
            # 打印解析内容
            content = item.get('content', {})
            if content:
                output_lines.append("解析内容:")
                self._collect_content_lines(content, output_lines, indent=2)
            
            if 'parse_error' in item:
                output_lines.append(f"解析错误: {item['parse_error']}")
        
        # 同时输出到控制台和文件
        for line in output_lines:
            log.printf(line)
        
        # 写入解析结果文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in output_lines:
                    f.write(line + '\n')
            log.i_print(f"解析结果已保存到: {output_path}")
        except Exception as e:
            log.e_print(f"保存解析结果失败: {e}")

    def _print_content(self, content: Dict[str, Any], indent: int = 0):
        """递归打印内容"""
        prefix = "  " * indent
        
        for key, value in content.items():
            if isinstance(value, dict):
                if 'value' in value and 'name' in value:
                    # 枚举值
                    log.printf(f"{prefix}{key}: {value['value']} ({value['name']})")
                else:
                    # 嵌套字典
                    log.printf(f"{prefix}{key}:")
                    self._print_content(value, indent + 1)
            elif isinstance(value, list):
                log.printf(f"{prefix}{key}: [{len(value)} 项]")
                for i, item in enumerate(value[:3]):  # 只显示前3项
                    if isinstance(item, dict):
                        log.printf(f"{prefix}  [{i}]:")
                        self._print_content(item, indent + 2)
                    else:
                        log.printf(f"{prefix}  [{i}]: {item}")
                if len(value) > 3:
                    log.printf(f"{prefix}  ... 还有 {len(value) - 3} 项")
            else:
                log.printf(f"{prefix}{key}: {value}")

    def _collect_content_lines(self, content: Dict[str, Any], output_lines: List[str], indent: int = 0):
        """递归收集内容行到列表中"""
        prefix = "  " * indent
        
        for key, value in content.items():
            if isinstance(value, dict):
                if 'value' in value and 'name' in value:
                    # 枚举值
                    output_lines.append(f"{prefix}{key}: {value['value']} ({value['name']})")
                else:
                    # 嵌套字典
                    output_lines.append(f"{prefix}{key}:")
                    self._collect_content_lines(value, output_lines, indent + 1)
            elif isinstance(value, list):
                output_lines.append(f"{prefix}{key}: [{len(value)} 项]")
                for i, item in enumerate(value[:3]):  # 只显示前3项
                    if isinstance(item, dict):
                        output_lines.append(f"{prefix}  [{i}]:")
                        self._collect_content_lines(item, output_lines, indent + 2)
                    else:
                        output_lines.append(f"{prefix}  [{i}]: {item}")
                if len(value) > 3:
                    output_lines.append(f"{prefix}  ... 还有 {len(value) - 3} 项")
            else:
                output_lines.append(f"{prefix}{key}: {value}")

    def extract_data_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        从文件中提取数据，增强版本支持提取方向信息
        
        :param file_path: 文件路径
        :return: 提取的数据列表
        """
        import re
        
        info_line_re = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{3}")
        byte_sequence_re = re.compile(self.yaml_config.frame_head)
        direction_re = re.compile(r"(Send|Recv)")  # 提取发送/接收方向

        data_groups = []
        current_group = None
        is_collecting_data = False

        try:
            with open(file_path, "r", encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line == "":
                        continue

                    info_line_match = info_line_re.search(line)
                    if info_line_match:
                        if current_group:
                            data_groups.append(current_group)
                            is_collecting_data = False
                        
                        # 提取时间
                        time_str = info_line_match.group()
                        
                        # 提取方向
                        direction_match = direction_re.search(line)
                        direction = direction_match.group() if direction_match else ""
                        
                        current_group = {
                            "time": time_str,
                            "direction": direction,
                            "data": ""
                        }
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

    def run(self):
        """运行协议解析"""
        try:
            # 提取数据
            data_groups = self.extract_data_from_file(self.log_file_name)
            if not data_groups:
                log.d_print("没有提取到数据")
                return
            
            log.i_print(f"提取到 {len(data_groups)} 组数据")
            
            # 解析数据
            parsed_data = self.parse_data_content(data_groups)
            
            # 筛选并打印结果
            self.screen_parse_data(parsed_data)
            
        except Exception as e:
            log.e_print(f"协议解析失败: {e}")
            raise
