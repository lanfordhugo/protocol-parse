#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8协议配置与文档对比分析工具
自动对比YAML配置文件和协议文档，找出字段差异、缺失和不一致
支持通用参数输入，可对比任意协议配置和文档
"""

import yaml
import re
import os
import sys
import argparse
from typing import Dict, List, Set, Tuple, Optional

def load_yaml_config(config_path: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return {}

def parse_protocol_doc(doc_path: str) -> Dict[int, Dict]:
    """解析协议文档，提取CMD定义"""
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取协议文档失败: {e}")
        return {}
    
    protocol_cmds = {}
    
    # 分段处理，每个段落分别解析
    lines = content.split('\n')
    
    # 方法1：查找所有CMD标题行，优先使用正文中的定义（有表格）
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
    
    # 方法2：处理每个CMD段落，按优先级排序（优先级高的在前）
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
            
            fields.append({
                'seq': seq_num,
                'name': field_name.strip(),
                'length': length,
                'description': description.strip()
            })
        except ValueError:
            continue
    
    return fields

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
    
    # 解析YAML字段
    yaml_fields = []
    if isinstance(yaml_cmd, list):
        for field in yaml_cmd:
            if isinstance(field, dict) and 'name' in field:
                yaml_fields.append({
                    'name': field.get('name', ''),
                    'length': field.get('len', 0),
                    'type': field.get('type', ''),
                    'scale': field.get('scale'),
                    'enum': field.get('enum'),
                    'notes': field.get('notes')
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
    
    # 对比字段长度
    for yaml_field in yaml_fields:
        for protocol_field in protocol_def.get('fields', []):
            if yaml_field['name'] == protocol_field['name']:
                if yaml_field['length'] != protocol_field['length']:
                    result['length_mismatches'].append({
                        'field': yaml_field['name'],
                        'yaml_length': yaml_field['length'],
                        'protocol_length': protocol_field['length']
                    })
                    result['issues'].append(
                        f"字段长度不匹配 '{yaml_field['name']}': "
                        f"配置={yaml_field['length']}, 协议={protocol_field['length']}"
                    )
    
    if result['issues']:
        result['status'] = 'MISMATCH'
    
    return result

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
    for cmd_num in sorted(protocol_cmds_set):
        result = compare_cmd_config(cmd_num, yaml_config, protocol_cmds[cmd_num])
        results[cmd_num] = result
        
        if result['status'] == 'MISMATCH':
            mismatch_count += 1
    
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
    
    if not missing_cmds and not extra_cmds and mismatch_count == 0:
        print("✅ 配置与协议文档完全一致！")
    
    return results

def create_argument_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='协议配置与文档对比分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 对比V8协议配置与文档
  python cmd_analysis.py -c configs/v8/protocol.yaml -d protocoltxt/充电桩系统MCU-CCU-M2以太网通信协议11-10.txt
  
  # 只分析CMD 1-100范围
  python cmd_analysis.py -c configs/v8/protocol.yaml -d protocoltxt/v8_protocol.txt --cmd-range 1-100
  
  # 分析多个范围（3000以内和3000-4000）
  python cmd_analysis.py -c configs/yunwei/protocol.yaml -d protocoltxt/yunwei_protocol.txt --cmd-range 1-3000,3000-4000
  
  # 分析特定CMD列表
  python cmd_analysis.py -c configs/v8/protocol.yaml -d protocoltxt/v8_protocol.txt --cmd-range 1,2,104,122
  
  # 显示详细输出
  python cmd_analysis.py -c configs/v8/protocol.yaml -d protocoltxt/v8_protocol.txt -v
  
  # 显示帮助信息
  python cmd_analysis.py -h
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
        version='协议对比分析工具 v1.0'
    )
    
    return parser

def validate_files(config_path: str, doc_path: str) -> bool:
    """验证输入文件是否存在和有效"""
    errors = []
    
    # 检查配置文件
    if not os.path.exists(config_path):
        errors.append(f"❌ 配置文件不存在: {config_path}")
    elif not config_path.lower().endswith(('.yaml', '.yml')):
        errors.append(f"⚠️  配置文件不是YAML格式: {config_path}")
    
    # 检查协议文档
    if not os.path.exists(doc_path):
        errors.append(f"❌ 协议文档不存在: {doc_path}")
    elif not doc_path.lower().endswith(('.txt', '.md', '.doc', '.docx')):
        errors.append(f"⚠️  协议文档格式可能不支持: {doc_path}")
    
    # 输出错误信息
    if errors:
        print("文件验证失败:")
        for error in errors:
            print(f"  {error}")
        return False
    
    return True

if __name__ == "__main__":
    # 解析命令行参数
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 验证输入文件
    if not validate_files(args.config, args.doc):
        sys.exit(1)
    
    try:
        # 执行分析
        results = analyze_protocol_config(args.config, args.doc, args.cmd_range)
        
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
