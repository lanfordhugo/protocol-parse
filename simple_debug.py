#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from tools.cmd_analysis import parse_protocol_doc

# 简单测试
result = parse_protocol_doc('protocoltxt/盛弘充电桩与运维平台通迅协议V3.0A03-20250702.txt')

print(f"总共解析出 {len(result)} 个CMD")

for cmd_num in [1, 104]:
    if cmd_num in result:
        fields = result[cmd_num].get('fields', [])
        print(f"\nCMD {cmd_num}: {len(fields)} 个字段")
        for field in sorted(fields, key=lambda x: x['seq']):
            print(f"  {field['seq']}. {field['name']} (长度: {field['length']})")
    else:
        print(f"\nCMD {cmd_num}: 未找到")
