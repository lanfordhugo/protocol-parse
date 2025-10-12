#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
协议配置与文档对比分析工具 v2.0
=================================

功能描述:
    自动对比YAML配置文件和协议文档，找出字段差异、缺失和不一致
    支持多种协议格式：V8、盛弘、云快充等
    智能处理Windows中文文件名编码问题

支持的协议格式:
    - V8协议: 基于MD锚点格式 <a id="cmd-xxx"></a>
    - 盛弘协议: 传统章节格式 ### x.x.x (CMD=xxx)
    - 云快充协议: 帧类型码格式 | 帧类型码 | 0xXX |

编码问题解决方案:
    本工具已内置Windows中文文件名编码问题的解决方案：
    
    1. 智能路径规范化: 自动处理编码转换问题
    2. 通配符匹配支持: 避免直接传递中文文件名
    3. 多重容错机制: 处理各种编码异常情况
    
    推荐用法（避免编码问题）:
    ✅ python cmd_analysis.py -c config.yaml -d "protocoltxt/*MCU*.md" --cmd-range 1-100
    ❌ python cmd_analysis.py -c config.yaml -d "protocoltxt/充电桩系统.md" --cmd-range 1-100

使用示例:
    # 分析V8协议CMD 20-37范围
    python cmd_analysis.py -c configs/v8/protocol.yaml -d "protocoltxt/*MCU-CCU-M2*.md" --cmd-range 20-37
    
    # 分析盛弘协议特定CMD
    python cmd_analysis.py -c configs/shenghong/protocol.yaml -d "protocoltxt/*盛弘*.md" --cmd-range 1,5,10-20
    
    # 分析云快充协议完整范围
    python cmd_analysis.py -c configs/yunkuaichong/protocol.yaml -d "protocoltxt/*云快充*.md"
    
    # 显示详细输出
    python cmd_analysis.py -c config.yaml -d "protocoltxt/*.md" --cmd-range 1-100 -v

CMD范围格式说明:
    - 单个范围: 1-100
    - 多个范围: 1-100,200-300  
    - 具体CMD: 1,2,104,122
    - 混合格式: 1-100,104,200-300

注意事项:
    1. Windows环境建议使用通配符匹配文件名，避免中文编码问题
    2. 协议文档需要是Markdown格式(.md)或文本格式(.txt)
    3. YAML配置文件必须符合项目的协议配置规范
    4. 大型协议建议使用--cmd-range参数限制分析范围，提高性能

技术实现:
    - 自动检测协议文档格式类型
    - 支持变长字段和重复结构解析
    - 智能字段名归一化处理
    - 完整的错误处理和用户友好的输出

作者: AI Assistant
版本: 2.0
更新: 2024-12 - 增加编码问题解决方案和智能路径处理
"""

import yaml
import re
import os
import sys
import argparse
from typing import Dict, List, Set, Tuple, Optional

# 设置输出编码和文件系统编码处理
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    # 设置环境变量以支持UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def normalize_file_path(file_path: str) -> str:
    """规范化文件路径，处理编码问题"""
    if not file_path:
        return file_path
    
    # 如果路径包含通配符，尝试glob匹配
    if '*' in file_path or '?' in file_path:
        import glob
        matches = glob.glob(file_path, recursive=True)
        if matches:
            return matches[0]
    
    # 检查文件是否存在
    if os.path.exists(file_path):
        return file_path
    
    # 如果文件不存在，尝试在目录中查找相似文件
    dir_path = os.path.dirname(file_path) or '.'
    filename = os.path.basename(file_path)
    
    if os.path.exists(dir_path):
        try:
            for existing_file in os.listdir(dir_path):
                # 检查是否包含关键词（处理编码问题）
                try:
                    # 尝试多种编码匹配
                    keywords = ['MCU-CCU-M2', 'protocol', '协议', '充电桩', '通信协议']
                    if any(keyword in existing_file for keyword in keywords):
                        return os.path.join(dir_path, existing_file)
                    
                    # 如果原文件名包含中文，尝试匹配包含关键词的文件
                    if any(ord(c) > 127 for c in filename):  # 包含非ASCII字符
                        # 优先匹配MCU-CCU-M2文件（V8协议）
                        if 'MCU-CCU-M2' in existing_file and existing_file.endswith('.md'):
                            return os.path.join(dir_path, existing_file)
                        # 如果原文件名包含"充电桩"和"MCU"，也匹配MCU-CCU-M2文件
                        if ('充电桩' in filename or 'MCU' in filename) and 'MCU-CCU-M2' in existing_file:
                            return os.path.join(dir_path, existing_file)
                            
                except (UnicodeDecodeError, UnicodeEncodeError):
                    # 编码问题时，使用更宽松的匹配
                    if 'MCU-CCU-M2' in existing_file:
                        return os.path.join(dir_path, existing_file)
                    
        except (OSError, UnicodeDecodeError):
            pass
    
    return file_path

def load_yaml_config(config_path: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return {}

def detect_document_format(content: str) -> str:
    """检测文档格式类型"""
    # 检查是否为云快充格式（使用帧类型码）
    if re.search(r'\|\s*帧类型码\s*\|\s*0x[0-9A-Fa-f]+', content):
        return 'yunkuaichong'
    # 检查是否有MD锚点格式的CMD定义
    elif re.search(r'<a id="cmd-\d+"></a>', content):
        # 进一步区分盛弘和V8格式
        if re.search(r'### \d+\.\d+.*\(cmd=\d+\)', content, re.IGNORECASE):
            return 'shenghong'
        elif re.search(r'### [^(]+\(cmd=\d+\)', content, re.IGNORECASE):
            return 'v8'
        else:
            return 'anchor_based'
    # 传统盛弘格式（无锚点）
    elif re.search(r'### \d+\.\d+.*\(CMD=\d+\)', content, re.IGNORECASE):
        return 'shenghong_legacy'
    else:
        return 'unknown'

def parse_protocol_doc(doc_path: str) -> Dict[int, Dict]:
    """解析协议文档，提取CMD定义 - 支持多种格式"""
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取协议文档失败: {e}")
        return {}
    
    # 检测文档格式
    doc_format = detect_document_format(content)
    print(f"🔍 检测到文档格式: {doc_format}")
    
    # 根据格式选择解析方法
    if doc_format == 'yunkuaichong':
        return parse_yunkuaichong_protocol(content)
    elif doc_format in ['shenghong', 'v8', 'anchor_based']:
        return parse_anchor_based_protocol(content, doc_format)
    elif doc_format == 'shenghong_legacy':
        return parse_shenghong_legacy_protocol(content)
    else:
        print(f"⚠️  未知文档格式，尝试使用传统解析方法")
        return parse_shenghong_legacy_protocol(content)

def parse_anchor_based_protocol(content: str, doc_format: str) -> Dict[int, Dict]:
    """解析基于MD锚点的协议文档（盛弘和V8）"""
    protocol_cmds = {}
    lines = content.split('\n')
    
    # 查找所有带有 <a id="cmd-数字"></a> 锚点的CMD定义
    cmd_anchors = []
    
    for i, line in enumerate(lines):
        # 匹配锚点格式：<a id="cmd-001"></a> 或 <a id="cmd-1"></a>
        anchor_match = re.search(r'<a id="cmd-(\d+)"></a>', line)
        if anchor_match:
            cmd_num_str = anchor_match.group(1)
            cmd_num = int(cmd_num_str.lstrip('0') or '0')  # 处理前导零
            
            # 查找紧接着的标题行
            title_line_idx = i + 1
            if title_line_idx < len(lines):
                title_line = lines[title_line_idx]
                
                # 根据文档格式匹配不同的标题模式
                if doc_format == 'shenghong':
                    # 盛弘格式：### 3.1.1  (cmd=1)后台服务器下发充电桩整形工作参数
                    title_match = re.match(r'^\s*### .*\(cmd=\d+\)', title_line, re.IGNORECASE)
                elif doc_format == 'v8':
                    # V8格式：### 注册帧(cmd=1) [cmd=001]
                    title_match = re.match(r'^\s*### .*\(cmd=\d+\)', title_line, re.IGNORECASE)
                else:
                    # 通用锚点格式
                    title_match = re.match(r'^\s*#{1,4}', title_line)
                
                if title_match:
                    cmd_anchors.append((i, cmd_num, title_line.strip(), title_line_idx))
    
    print(f"🔍 通过锚点找到 {len(cmd_anchors)} 个CMD定义")
    
    # 处理每个CMD段落
    for i, (anchor_idx, cmd_num, title, title_idx) in enumerate(cmd_anchors):
        # 确定段落结束位置 - 查找下一个锚点或主要章节
        end_line_idx = len(lines)
        
        # 查找下一个CMD锚点
        if i + 1 < len(cmd_anchors):
            next_anchor_idx = cmd_anchors[i + 1][0]
            end_line_idx = next_anchor_idx
            # 在当前标题与下一个锚点之间查找新的标题，提前截断
            for j in range(title_idx + 1, next_anchor_idx):
                line = lines[j].strip()
                if (
                    re.match(r'^\s*#{1,2}\s+\d+\.\d+', line)
                    or (re.match(r'^\s*#{2,4}\s+.+', line) and j != title_idx)
                ):
                    end_line_idx = j
                    break
        else:
            # 如果是最后一个，查找下一个主要章节
            for j in range(title_idx + 1, len(lines)):
                line = lines[j].strip()
                # 主要章节标题或新的锚点
                if (
                    re.match(r'^\s*#{1,2}\s+\d+\.\d+', line)
                    or re.search(r'<a id="[^"]*"></a>', line)
                    # 普通的markdown标题（如### 标题），遇到下一个标题也结束
                    or (re.match(r'^\s*#{2,4}\s+.+', line) and j != title_idx)
                ):
                    end_line_idx = j
                    break
        
        
        # 提取段落内容
        cmd_lines = lines[anchor_idx:end_line_idx]
        cmd_content = '\n'.join(cmd_lines)
        
        # 提取字段定义表格
        fields = extract_fields_from_table(cmd_content)
        
        protocol_cmds[cmd_num] = {
            'name': extract_cmd_name_from_title(title, doc_format),
            'fields': fields,
            'raw_content': cmd_content[:200] + '...' if len(cmd_content) > 200 else cmd_content
        }
    
    return protocol_cmds

def parse_yunkuaichong_protocol(content: str) -> Dict[int, Dict]:
    """解析云快充协议文档（基于帧类型码）"""
    protocol_cmds = {}
    lines = content.split('\n')
    
    # 查找所有帧类型码定义
    frame_type_sections = []
    
    for i, line in enumerate(lines):
        # 匹配表格中的帧类型码行：| 帧类型码      | 0x01                          |
        frame_match = re.search(r'\|\s*帧类型码\s*\|\s*0x([0-9A-Fa-f]+)', line)
        if frame_match:
            hex_str = frame_match.group(1)
            cmd_num = int(hex_str, 16)  # 十六进制转十进制
            
            # 向前查找章节标题
            section_title = "未知功能"
            for j in range(max(0, i - 10), i):
                title_line = lines[j].strip()
                if re.match(r'^\s*#{1,3}\s+.+', title_line):
                    # 提取标题内容
                    title_match = re.search(r'#{1,3}\s+(.+)', title_line)
                    if title_match:
                        section_title = title_match.group(1).strip()
                        break
            
            frame_type_sections.append((i, cmd_num, section_title, hex_str))
    
    print(f"🔍 通过帧类型码找到 {len(frame_type_sections)} 个CMD定义")
    
    # 处理每个帧类型码段落
    for i, (line_idx, cmd_num, title, hex_str) in enumerate(frame_type_sections):
        # 确定段落结束位置
        end_line_idx = len(lines)
        
        # 查找下一个帧类型码或主要章节
        if i + 1 < len(frame_type_sections):
            next_line_idx = frame_type_sections[i + 1][0]
            end_line_idx = next_line_idx - 10  # 留一些缓冲
        else:
            # 查找下一个主要章节
            for j in range(line_idx + 1, len(lines)):
                line = lines[j].strip()
                if re.match(r'^\s*#{1,2}\s+.+', line):
                    end_line_idx = j
                    break
        
        # 提取段落内容
        start_idx = max(0, line_idx - 20)  # 向前扩展以包含完整表格
        cmd_lines = lines[start_idx:end_line_idx]
        cmd_content = '\n'.join(cmd_lines)
        
        # 提取字段定义表格
        fields = extract_yunkuaichong_fields(cmd_content)
        
        protocol_cmds[cmd_num] = {
            'name': title,
            'fields': fields,
            'raw_content': cmd_content[:200] + '...' if len(cmd_content) > 200 else cmd_content
        }
    
    return protocol_cmds

def parse_shenghong_legacy_protocol(content: str) -> Dict[int, Dict]:
    """解析传统盛弘协议文档（原有解析逻辑）"""
    protocol_cmds = {}
    lines = content.split('\n')
    
    # 原有的解析逻辑 - 查找所有CMD标题行
    cmd_headers = []
    found_cmds = set()  # 用于去重，避免解析重复的CMD
    
    for i, line in enumerate(lines):
        # 匹配多种CMD定义格式：
        # 1. ### 3.2.14  (CMD=123)充电桩具体告警信息上报
        # 2. 3.1.1  (CMD=1)后台服务器下发充电桩整形工作参数
        # 3. #### 3.1.1  (CMD=1)后台服务器下发充电桩整形工作参数
        cmd_pattern = r'^\s*(#{0,4})\s*(\d+\.\d+(?:\.\d+)*)\s*\(CMD=(\d+)\)'
        match = re.match(cmd_pattern, line, re.IGNORECASE)
        if match:
            hash_prefix, section_num, cmd_num_str = match.groups()
            cmd_num = int(cmd_num_str)
            
            # 优先选择有###前缀的定义（正文），如果已存在则跳过目录中的重复定义
            priority = len(hash_prefix)  # ###的数量，越多优先级越高
            
            if cmd_num not in found_cmds or priority > 0:
                if cmd_num in found_cmds:
                    # 如果已存在但当前有更高优先级，替换之前的
                    cmd_headers = [h for h in cmd_headers if h[1] != cmd_num]
                
                found_cmds.add(cmd_num)
                cmd_headers.append((i, cmd_num, line.strip(), priority))
    
    # 处理每个CMD段落，按优先级排序（优先级高的在前）
    cmd_headers.sort(key=lambda x: (x[1], -x[3]))  # 按CMD号排序，然后按优先级降序
    
    for i, (line_idx, cmd_num, header, priority) in enumerate(cmd_headers):
        # 确定段落结束位置 - 查找下一个主要章节
        end_line_idx = len(lines)
        
        # 向后搜索，找到下一个主要章节或下一个CMD定义
        for j in range(line_idx + 1, len(lines)):
            line = lines[j].strip()
            # 主要章节（如 3.3  充电信息数据）
            if re.match(r'^\s*\d+\.\d+\s+\w+', line) and not line.startswith('#'):
                end_line_idx = j
                break
            # 下一个CMD定义（任何格式）
            elif re.match(r'^\s*#{0,4}\s*\d+\.\d+(?:\.\d+)*\s*\(CMD=\d+\)', line, re.IGNORECASE):
                end_line_idx = j
                break
        
        # 提取段落内容
        cmd_lines = lines[line_idx:end_line_idx]
        cmd_content = '\n'.join(cmd_lines)
        
        # 提取字段定义表格
        fields = extract_fields_from_table(cmd_content)
        
        protocol_cmds[cmd_num] = {
            'name': extract_cmd_name(cmd_content),
            'fields': fields,
            'raw_content': cmd_content[:200] + '...' if len(cmd_content) > 200 else cmd_content
        }
    
    return protocol_cmds

def extract_cmd_name(content: str) -> str:
    """从内容中提取命令名称"""
    lines = content.split('\n')[:10]  # 只看前10行
    for line in lines:
        if '###' in line and ('cmd=' in line.lower() or 'CMD=' in line):
            # 提取命令名称
            name_match = re.search(r'###\s*([^(（]+)', line)
            if name_match:
                return name_match.group(1).strip()
    return "未知命令"

def extract_cmd_name_from_title(title: str, doc_format: str) -> str:
    """从标题行中提取命令名称"""
    if doc_format == 'shenghong':
        # 盛弘格式：### 3.1.1  (cmd=1)后台服务器下发充电桩整形工作参数
        match = re.search(r'### \d+\.\d+(?:\.\d+)?\s*\(cmd=\d+\)\s*(.+)', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # 备选模式：提取括号后的内容
        match = re.search(r'\(cmd=\d+\)\s*(.+)', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    elif doc_format == 'v8':
        # V8格式：### 注册帧(cmd=1) [cmd=001]
        match = re.search(r'###\s*([^(]+)\(cmd=\d+\)', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    else:
        # 通用格式：尝试提取###后的内容
        match = re.search(r'#{1,4}\s*(.+)', title)
        if match:
            # 去除括号内容
            name = re.sub(r'\([^)]*\)', '', match.group(1)).strip()
            return name if name else "未知命令"
    
    return "未知命令"

def extract_yunkuaichong_fields(content: str) -> List[Dict]:
    """提取云快充协议的字段定义"""
    fields = []
    
    # 云快充使用不同的表格格式，查找参数定义表格
    # 格式：| 序号 | 参数名称 | 数据类型 | 长度(Byte) | 备注 |
    table_pattern = r'\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|'
    matches = re.findall(table_pattern, content)
    
    for match in matches:
        seq_num_str, field_name, data_type, length_str, description = match
        try:
            seq_num = int(seq_num_str)
            
            # 处理长度字段
            length_str = length_str.strip()
            if length_str.isdigit():
                length = int(length_str)
            else:
                # 尝试从字符串中提取数字
                length_match = re.search(r'(\d+)', length_str)
                if length_match:
                    length = int(length_match.group(1))
                else:
                    length = -1  # 未知长度
            
            fields.append({
                'seq': seq_num,
                'name': field_name.strip(),
                'length': length,
                'data_type': data_type.strip(),
                'description': description.strip()
            })
        except ValueError:
            continue
    
    return fields

def parse_cmd_range(cmd_range_str: str) -> Set[int]:
    """解析CMD范围字符串，返回CMD号码集合
    
    支持的格式：
    - 单个范围: "1-100"
    - 多个范围: "1-100,200-300"  
    - 具体CMD: "1,2,104,122"
    - 混合格式: "1-100,104,200-300"
    """
    if not cmd_range_str:
        return set()
    
    cmd_set = set()
    
    # 分割逗号分隔的部分
    parts = [part.strip() for part in cmd_range_str.split(',')]
    
    for part in parts:
        if '-' in part and not part.startswith('-'):
            # 范围格式：start-end
            try:
                start, end = part.split('-', 1)
                start_num = int(start.strip())
                end_num = int(end.strip())
                
                if start_num <= end_num:
                    cmd_set.update(range(start_num, end_num + 1))
                else:
                    print(f"⚠️  警告：无效范围 '{part}'，起始值大于结束值")
            except ValueError:
                print(f"⚠️  警告：无法解析范围 '{part}'")
        else:
            # 单个CMD号码
            try:
                cmd_num = int(part.strip())
                cmd_set.add(cmd_num)
            except ValueError:
                print(f"⚠️  警告：无法解析CMD号码 '{part}'")
    
    return cmd_set

def normalize_repeated_field_name(field_name: str) -> str:
    """归一化重复字段名称：将'开始时间1'、'开始时间n'等归一化为'开始时间'
    但保留独立字段如'停止参数1-8'等不应该被归一化的字段"""
    
    # 定义不应该被归一化的字段模式（独立字段）
    INDEPENDENT_FIELD_PATTERNS = [
        r'停止参数\d+',      # 停止参数1-8
        r'传感器\d+',        # 传感器1-N
        r'通道\d+',          # 通道1-N
        r'模块\d+',          # 模块1-N
        r'路\d+',           # 1路、2路等
        r'枪\d+',           # 枪1、枪2等
        r'相\d+',           # A相、B相等（虽然不是数字，但相关）
        r'温度\d+',         # 温度1-N
        r'电压\d+',         # 电压1-N
        r'电流\d+',         # 电流1-N
        r'功率\d+',         # 功率1-N
    ]
    
    # 检查是否匹配独立字段模式
    for pattern in INDEPENDENT_FIELD_PATTERNS:
        if re.match(pattern, field_name):
            # 这是独立字段，不应该归一化
            return field_name
    
    # 对于其他字段，进行归一化处理
    # 只归一化明确的重复模式：如"开始时间1"、"开始时间n"等
    # 但要更保守，只处理明确的重复结构标记
    if re.search(r'[1-9n]$', field_name):
        # 检查是否是真正的重复结构（通常在描述中会有提示）
        # 如果字段名本身就是独特的，不要归一化
        base_name = re.sub(r'[1-9n]$', '', field_name)
        
        # 如果去掉数字后的基础名称太短，可能不是重复结构
        if len(base_name) < 2:
            return field_name
            
        # 更保守的归一化：只对明确的时间、地址等重复结构进行归一化
        if any(keyword in base_name for keyword in ['时间', '地址', '参数地址', '数据', '电费', '服务费']):
            return base_name
    
    return field_name

def extract_fields_from_table(content: str) -> List[Dict]:
    """从协议文档表格中提取字段定义"""
    fields = []
    
    # 查找表格行，支持多种格式：
    # 1. 带星号的序号（如 4*、5*）
    # 2. 长度可以是数字或字母（如 1、2、N）
    # 3. 支持不同的表格分隔符
    table_pattern = r'\|\s*(\d+\*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|'
    matches = re.findall(table_pattern, content)
    
    for match in matches:
        seq_num_str, field_name, length_str, description = match
        try:
            # 提取数字部分，忽略星号
            seq_num = int(seq_num_str.rstrip('*'))
            
            # 处理长度字段，支持数字和字母
            length_str = length_str.strip()
            if length_str.isdigit():
                length = int(length_str)
            elif length_str.upper() == 'N':
                # N表示可变长度，设为特殊值
                length = -1
            else:
                # 尝试从字符串中提取数字
                length_match = re.search(r'\d+', length_str)
                if length_match:
                    length = int(length_match.group())
                else:
                    # 无法解析长度，跳过
                    continue
            
            # 归一化字段名（处理重复结构）
            normalized_name = normalize_repeated_field_name(field_name.strip())
            
            fields.append({
                'seq': seq_num,
                'name': normalized_name,
                'length': length,
                'description': description.strip()
            })
        except ValueError:
            continue
    
    # 去重：如果有多个相同的归一化字段名，只保留第一个（重复结构的模板）
    seen_names = set()
    unique_fields = []
    for field in fields:
        if field['name'] not in seen_names:
            seen_names.add(field['name'])
            unique_fields.append(field)
    
    return unique_fields

def compare_cmd_config(cmd_num: int, yaml_config: Dict, protocol_def: Dict) -> Dict:
    """对比单个CMD的配置与协议定义"""
    result = {
        'cmd': cmd_num,
        'status': 'OK',
        'issues': [],
        'yaml_fields': [],
        'protocol_fields': protocol_def.get('fields', []),
        'missing_fields': [],
        'extra_fields': [],
        'length_mismatches': []
    }
    
    if cmd_num not in yaml_config.get('cmds', {}):
        result['status'] = 'MISSING'
        result['issues'].append(f"CMD {cmd_num} 在配置中完全缺失")
        return result
    
    yaml_cmd = yaml_config['cmds'][cmd_num]
    
    # 解析YAML字段 - 增强版，支持repeat_by和变长字段
    yaml_fields = []
    if isinstance(yaml_cmd, list):
        for field in yaml_cmd:
            if isinstance(field, dict):
                if 'name' in field:
                    # 处理普通字段
                    yaml_fields.append({
                        'name': field.get('name', ''),
                        'length': field.get('len', 0),
                        'type': field.get('type', ''),
                        'scale': field.get('scale'),
                        'enum': field.get('enum'),
                        'notes': field.get('notes')
                    })
                elif 'repeat_by' in field and 'fields' in field:
                    # 处理repeat_by结构中的字段
                    for repeat_field in field['fields']:
                        if isinstance(repeat_field, dict) and 'name' in repeat_field:
                            notes = repeat_field.get('notes', '')
                            if notes:
                                notes = notes + ' '
                            notes += '[重复结构]'
                            yaml_fields.append({
                                'name': repeat_field.get('name', ''),
                                'length': repeat_field.get('len', 0),
                                'type': repeat_field.get('type', ''),
                                'scale': repeat_field.get('scale'),
                                'enum': repeat_field.get('enum'),
                                'notes': notes
                            })
                elif 'repeat_const' in field and 'fields' in field:
                    for repeat_field in field['fields']:
                        if isinstance(repeat_field, dict) and 'name' in repeat_field:
                            notes = repeat_field.get('notes', '')
                            if notes:
                                notes = notes + ' '
                            notes += '[重复结构]'
                            yaml_fields.append({
                                'name': repeat_field.get('name', ''),
                                'length': repeat_field.get('len', 0),
                                'type': repeat_field.get('type', ''),
                                'scale': repeat_field.get('scale'),
                                'enum': repeat_field.get('enum'),
                                'notes': notes
                            })
    
    result['yaml_fields'] = yaml_fields
    
    # 对比字段
    protocol_field_names = {f['name'] for f in protocol_def.get('fields', [])}
    yaml_field_names = {f['name'] for f in yaml_fields}
    
    # 查找缺失字段 - 按协议定义顺序排序
    missing = protocol_field_names - yaml_field_names
    if missing:
        # 按协议定义的序号顺序排序
        protocol_fields_ordered = sorted(protocol_def.get('fields', []), key=lambda x: x.get('seq', 999))
        missing_ordered = []
        for field in protocol_fields_ordered:
            if field['name'] in missing:
                missing_ordered.append(field['name'])
        
        result['missing_fields'] = missing_ordered
        # 构建缺失字段的清晰显示
        missing_display = '\n      '.join(['- ' + field for field in missing_ordered])
        result['issues'].append(f"缺失字段:\n      {missing_display}")
    
    # 查找多余字段 - 按YAML配置顺序排序（保持配置文件的顺序）
    extra = yaml_field_names - protocol_field_names
    if extra:
        # 按YAML配置中的顺序排序
        extra_ordered = []
        for field in yaml_fields:
            if field['name'] in extra:
                extra_ordered.append(field['name'])
        
        result['extra_fields'] = extra_ordered
        # 构建多余字段的清晰显示
        extra_display = '\n      '.join(['- ' + field for field in extra_ordered])
        result['issues'].append(f"多余字段:\n      {extra_display}")
    
    # 对比字段长度 - 增强版，支持变长字段
    for yaml_field in yaml_fields:
        for protocol_field in protocol_def.get('fields', []):
            if yaml_field['name'] == protocol_field['name']:
                yaml_len = yaml_field['length']
                protocol_len = protocol_field['length']
                
                # 处理变长字段：如果协议长度为-1（变长）而配置使用变长标识符，则认为匹配
                is_varlen_match = (protocol_len == -1 and 
                                 isinstance(yaml_len, str) and 
                                 yaml_len not in ['0', '1', '2', '4', '8'])
                
                if yaml_len != protocol_len and not is_varlen_match:
                    result['length_mismatches'].append({
                        'field': yaml_field['name'],
                        'yaml_length': yaml_len,
                        'protocol_length': protocol_len
                    })
                    result['issues'].append(
                        f"字段长度不匹配 '{yaml_field['name']}': "
                        f"配置={yaml_len}, 协议={protocol_len}"
                    )
    
    if result['issues']:
        result['status'] = 'MISMATCH'

    # 检测是否属于位域拆分等需人工核查的场景
    manual_review_message = detect_manual_review_case(result)
    if manual_review_message:
        result['status'] = 'MANUAL_REVIEW'
        result['issues'].append(manual_review_message)
    
    return result


def detect_manual_review_case(result: Dict) -> Optional[str]:
    """识别无法由自动比对覆盖的特殊场景，提示人工核查。

    当前支持的识别场景：
    - 协议字段为汇总位图，但配置里拆解成大量单独位字段
    """

    missing_fields = result.get('missing_fields', []) or []
    extra_fields = result.get('extra_fields', []) or []
    yaml_fields = result.get('yaml_fields', []) or []

    if missing_fields and extra_fields:
        # 统计额外字段中可能代表单个位或拆分字段的类型
        extra_field_details = [field for field in yaml_fields if field['name'] in extra_fields]
        if extra_field_details:
            bitfield_like = [
                field for field in extra_field_details
                if (
                    isinstance(field.get('type'), str) and 'bitfield' in field['type']
                )
                or (
                    isinstance(field.get('length'), int)
                    and field['length'] == 1
                    and field.get('type') in {'uint8', 'hex', 'binary_str_1byte'}
                )
            ]

            # 如果大多数多余字段是位字段，且缺失字段疑似汇总字段，则提示人工处理
            if bitfield_like and len(bitfield_like) >= max(4, int(len(extra_field_details) * 0.6)):
                if any(re.search(r'(状态|反馈|告警|位|位图)', name) for name in missing_fields):
                    base_names = {
                        re.sub(r'[0-9一二三四五六七八九十]+$', '', name).strip()
                        for name in missing_fields
                    }
                    base_names = {name for name in base_names if name}

                    if not base_names:
                        base_summary = '协议字段'
                    else:
                        base_summary = '、'.join(sorted(base_names))

                    return (
                        f"检测到{base_summary}等协议字段在配置中被拆分为多个位/子字段，"
                        f"自动比对无法准确匹配，请参考协议附录人工核对对应位定义。"
                    )

    # 处理协议按编号展开而配置使用重复结构的场景
    repeat_fields = [
        field for field in yaml_fields
        if isinstance(field.get('notes'), str) and '重复结构' in field['notes']
    ]

    if repeat_fields and missing_fields:
        numeric_missing = [name for name in missing_fields if re.search(r'\d', name)]
        if numeric_missing:
            sample_missing = '、'.join(numeric_missing[:3])
            repeat_names = sorted({field['name'] for field in repeat_fields})
            sample_repeat = '、'.join(repeat_names[:3]) if repeat_names else '循环字段'

            return (
                f"检测到协议按编号列出字段（如 {sample_missing}），"
                f"而配置使用循环结构字段（{sample_repeat} 等）。"
                f"自动比对无法直接映射，请人工核对循环项字段含义与顺序。"
            )

    return None

def analyze_protocol_config(config_path: str, doc_path: str, cmd_range: Optional[str] = None) -> Dict:
    """分析协议配置与文档的一致性"""
    
    print("🔍 协议配置与文档对比分析")
    print("=" * 60)
    print(f"📄 配置文件: {config_path}")
    print(f"📄 协议文档: {doc_path}")
    if cmd_range:
        print(f"🎯 CMD范围: {cmd_range}")
    print("=" * 60)
    
    # 加载配置文件
    print(f"📖 加载配置文件: {config_path}")
    yaml_config = load_yaml_config(config_path)
    if not yaml_config:
        return {}
    
    # 解析协议文档
    print(f"📖 解析协议文档: {doc_path}")
    protocol_cmds = parse_protocol_doc(doc_path)
    if not protocol_cmds:
        return {}
    
    # 解析CMD范围过滤
    allowed_cmds = None
    if cmd_range:
        allowed_cmds = parse_cmd_range(cmd_range)
        if allowed_cmds:
            sorted_cmds = sorted(allowed_cmds)
            if len(sorted_cmds) <= 20:
                print(f"🎯 解析CMD范围: {sorted_cmds} (共{len(sorted_cmds)}个)")
            else:
                print(f"🎯 解析CMD范围: {sorted_cmds[:10]}...{sorted_cmds[-10:]} (共{len(sorted_cmds)}个)")
                print(f"   范围概要: {min(sorted_cmds)}-{max(sorted_cmds)}")
            
            # 过滤协议CMD
            original_protocol_count = len(protocol_cmds)
            protocol_cmds = {k: v for k, v in protocol_cmds.items() if k in allowed_cmds}
            
            # 过滤配置CMD（仅用于统计）
            original_yaml_count = len(yaml_config.get('cmds', {}))
            filtered_yaml_cmds = {k: v for k, v in yaml_config.get('cmds', {}).items() if k in allowed_cmds}
            
            print(f"📊 范围过滤结果:")
            print(f"   协议文档: {original_protocol_count} -> {len(protocol_cmds)} 个CMD")
            print(f"   配置文件: {original_yaml_count} -> {len(filtered_yaml_cmds)} 个CMD")
        else:
            print(f"⚠️  警告：CMD范围解析失败或为空，将分析所有CMD")
    
    print(f"✅ 协议文档中找到 {len(protocol_cmds)} 个CMD定义")
    print(f"✅ 配置文件中找到 {len(yaml_config.get('cmds', {}))} 个CMD配置")
    print()
    
    # 对比分析
    results = {}
    yaml_cmds = set(yaml_config.get('cmds', {}).keys())
    protocol_cmds_set = set(protocol_cmds.keys())
    
    # 应用CMD范围过滤
    if allowed_cmds:
        yaml_cmds = yaml_cmds & allowed_cmds
        protocol_cmds_set = protocol_cmds_set & allowed_cmds
    
    # 统计信息
    missing_cmds = protocol_cmds_set - yaml_cmds
    extra_cmds = yaml_cmds - protocol_cmds_set
    common_cmds = yaml_cmds & protocol_cmds_set
    
    print(f"📊 统计信息:")
    print(f"   协议文档CMD数量: {len(protocol_cmds_set)}")
    print(f"   配置文件CMD数量: {len(yaml_cmds)}")
    print(f"   共同CMD数量: {len(common_cmds)}")
    print(f"   缺失CMD数量: {len(missing_cmds)}")
    print(f"   多余CMD数量: {len(extra_cmds)}")
    print(f"   覆盖率: {len(common_cmds)/len(protocol_cmds_set)*100:.1f}%")
    print()
    
    # 详细对比每个CMD
    mismatch_count = 0
    manual_review_cmds = []
    for cmd_num in sorted(protocol_cmds_set):
        result = compare_cmd_config(cmd_num, yaml_config, protocol_cmds[cmd_num])
        results[cmd_num] = result
        
        if result['status'] == 'MISMATCH':
            mismatch_count += 1
        elif result['status'] == 'MANUAL_REVIEW':
            manual_review_cmds.append(cmd_num)
    
    # 输出问题汇总
    print("🚨 问题汇总:")
    print("-" * 30)
    
    if missing_cmds:
        print(f"❌ 完全缺失的CMD ({len(missing_cmds)}个): {sorted(missing_cmds)}")
    
    if extra_cmds:
        print(f"⚠️  协议中不存在的CMD ({len(extra_cmds)}个): {sorted(extra_cmds)}")
    
    if mismatch_count > 0:
        print(f"⚠️  字段不匹配的CMD ({mismatch_count}个):")
        for cmd_num, result in results.items():
            if result['status'] == 'MISMATCH':
                print(f"   CMD {cmd_num}:")
                for issue in result['issues']:
                    print(f"     {issue}")
                print()  # 添加空行分隔不同CMD
    if manual_review_cmds:
        print(f"📝  需人工核查的CMD ({len(manual_review_cmds)}个):")
        for cmd_num in manual_review_cmds:
            result = results[cmd_num]
            print(f"   CMD {cmd_num}:")
            for issue in result['issues']:
                print(f"     {issue}")
            print()
    
    if not missing_cmds and not extra_cmds and mismatch_count == 0:
        print("✅ 配置与协议文档完全一致！")
    
    return results

def create_argument_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='协议配置与文档对比分析工具 v2.0 - 支持多种协议格式，智能处理编码问题',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:

🔥 推荐用法（避免中文编码问题）:
  # V8协议分析 - 使用通配符匹配
  python cmd_analysis.py -c configs/v8/protocol.yaml -d "protocoltxt/*MCU-CCU-M2*.md" --cmd-range 20-37
  
  # 盛弘协议分析 - 使用通配符匹配  
  python cmd_analysis.py -c configs/shenghong/protocol.yaml -d "protocoltxt/*盛弘*.md" --cmd-range 1-100
  
  # 云快充协议分析 - 使用通配符匹配
  python cmd_analysis.py -c configs/yunkuaichong/protocol.yaml -d "protocoltxt/*云快充*.md"

📋 CMD范围格式:
  --cmd-range 1-100           # 单个范围
  --cmd-range 1-100,200-300   # 多个范围  
  --cmd-range 1,2,104,122     # 具体CMD列表
  --cmd-range 1-50,104,200-300 # 混合格式

🛠️ 高级用法:
  # 显示详细分析信息
  python cmd_analysis.py -c config.yaml -d "protocoltxt/*.md" --cmd-range 1-100 -v
  
  # 分析大型协议的特定范围（提高性能）
  python cmd_analysis.py -c config.yaml -d "protocoltxt/*.md" --cmd-range 3000-4000

⚠️ 编码问题说明:
  Windows环境下，建议使用通配符匹配文件名（如 "*MCU*.md"）而不是直接使用中文文件名。
  本工具已内置智能路径处理，会自动匹配正确的协议文档文件。
  
  ✅ 推荐: -d "protocoltxt/*MCU*.md"
  ❌ 避免: -d "protocoltxt/充电桩系统MCU-CCU-M2以太网通信协议11-10.md"

📖 支持的协议格式:
  - V8协议: MD锚点格式 <a id="cmd-xxx"></a>
  - 盛弘协议: 章节格式 ### x.x.x (CMD=xxx)  
  - 云快充协议: 帧类型码格式 | 帧类型码 | 0xXX |
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        required=True,
        help='YAML协议配置文件路径'
    )
    
    parser.add_argument(
        '-d', '--doc',
        type=str,
        required=True,
        help='协议文档文件路径'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细输出信息'
    )
    
    parser.add_argument(
        '--cmd-range',
        type=str,
        help='指定要分析的CMD范围，支持多种格式：\n'
             '  单个范围: 1-100\n'
             '  多个范围: 1-100,200-300\n'
             '  具体CMD: 1,2,104,122\n'
             '  混合格式: 1-100,104,200-300'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='协议对比分析工具 v2.0 - 智能编码处理版本'
    )
    
    return parser

def validate_files(config_path: str, doc_path: str) -> Tuple[bool, str, str]:
    """验证输入文件是否存在和有效，返回(是否有效, 规范化配置路径, 规范化文档路径)"""
    errors = []
    
    # 规范化路径
    normalized_config = normalize_file_path(config_path)
    normalized_doc = normalize_file_path(doc_path)
    
    # 检查配置文件
    if not os.path.exists(normalized_config):
        errors.append(f"❌ 配置文件不存在: {config_path}")
        if normalized_config != config_path:
            errors.append(f"   尝试规范化为: {normalized_config}")
    elif not normalized_config.lower().endswith(('.yaml', '.yml')):
        errors.append(f"⚠️  配置文件不是YAML格式: {normalized_config}")
    
    # 检查协议文档
    if not os.path.exists(normalized_doc):
        errors.append(f"❌ 协议文档不存在: {doc_path}")
        if normalized_doc != doc_path:
            errors.append(f"   尝试规范化为: {normalized_doc}")
    elif not normalized_doc.lower().endswith(('.txt', '.md', '.doc', '.docx')):
        errors.append(f"⚠️  协议文档格式可能不支持: {normalized_doc}")
    
    # 输出错误信息或成功信息
    if errors:
        print("文件验证失败:")
        for error in errors:
            print(f"  {error}")
        return False, config_path, doc_path
    else:
        # 如果路径被规范化了，显示信息
        if normalized_config != config_path:
            print(f"📁 配置文件路径已规范化: {normalized_config}")
        if normalized_doc != doc_path:
            print(f"📁 协议文档路径已规范化: {normalized_doc}")
        return True, normalized_config, normalized_doc

if __name__ == "__main__":
    # 解析命令行参数
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 验证输入文件
    is_valid, config_path, doc_path = validate_files(args.config, args.doc)
    if not is_valid:
        sys.exit(1)
    
    try:
        # 执行分析
        results = analyze_protocol_config(config_path, doc_path, args.cmd_range)
        
        if args.verbose:
            print(f"\n🔧 详细分析结果已保存到内存，可进一步处理")
            
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 分析过程中出现错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
