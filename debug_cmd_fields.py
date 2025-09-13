#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试CMD字段解析问题
"""

import sys
sys.path.append('.')
from tools.cmd_analysis import parse_protocol_doc, load_yaml_config

def debug_cmd_fields(cmd_nums, config_path, doc_path):
    """调试指定CMD的字段解析"""
    
    # 解析协议文档
    print(f"📖 解析协议文档...")
    protocol_cmds = parse_protocol_doc(doc_path)
    
    # 加载配置文件
    print(f"📖 加载配置文件...")
    yaml_config = load_yaml_config(config_path)
    
    for cmd_num in cmd_nums:
        print(f"\n🔍 分析 CMD {cmd_num}:")
        print("=" * 50)
        
        # 协议文档中的字段
        if cmd_num in protocol_cmds:
            protocol_fields = protocol_cmds[cmd_num].get('fields', [])
            print(f"📋 协议文档中的字段 ({len(protocol_fields)}个):")
            for field in sorted(protocol_fields, key=lambda x: x['seq']):
                print(f"  {field['seq']:2d}. {field['name']} (长度: {field['length']})")
        else:
            print(f"❌ 协议文档中未找到 CMD {cmd_num}")
            protocol_fields = []
        
        # 配置文件中的字段
        if cmd_num in yaml_config.get('cmds', {}):
            yaml_cmd = yaml_config['cmds'][cmd_num]
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
            
            print(f"\n📋 配置文件中的字段 ({len(yaml_fields)}个):")
            for i, field in enumerate(yaml_fields, 1):
                print(f"  {i:2d}. {field['name']} (长度: {field['length']})")
        else:
            print(f"❌ 配置文件中未找到 CMD {cmd_num}")
            yaml_fields = []
        
        # 字段名称对比
        if protocol_fields and yaml_fields:
            protocol_names = {f['name'] for f in protocol_fields}
            yaml_names = {f['name'] for f in yaml_fields}
            
            missing = protocol_names - yaml_names
            extra = yaml_names - protocol_names
            
            print(f"\n🔍 字段对比结果:")
            print(f"  相同字段: {len(protocol_names & yaml_names)}个")
            print(f"  缺失字段: {len(missing)}个")
            print(f"  多余字段: {len(extra)}个")
            
            if missing:
                print(f"\n❌ 缺失字段:")
                for field in sorted(missing):
                    print(f"    - {field}")
            
            if extra:
                print(f"\n⚠️  多余字段:")
                for field in sorted(extra):
                    print(f"    - {field}")

if __name__ == "__main__":
    # 调试CMD 1和CMD 104
    debug_cmd_fields(
        [1, 104], 
        'configs/yunwei/protocol.yaml',
        'protocoltxt/盛弘充电桩与运维平台通迅协议V3.0A03-20250702.txt'
    )
