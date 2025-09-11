# 运维协议解析问题修复记录

## 问题描述
运维协议解析失败，显示 `data_groups is empty`，无法找到匹配的数据。

## 根本原因分析
1. **错误的帧头配置**: 配置中设置为"CC D7"，但实际日志数据以"AA F5"开头
2. **错误的数据包结构**: 
   - 原配置: head_len=8, tail_len=1
   - 实际应为: head_len=11, tail_len=2 (与V8协议相同)
3. **错误的命令字偏移**: 
   - 原配置: 偏移6-7
   - 实际应为: 偏移6-7 (经过调试确认)

## 数据包结构分析
运维日志数据: `AA F5 1D 00 10 FB B9 0B 02 00 37 3F...`
- `AA F5` - 帧头 (偏移0-1)
- `1D 00` - 长度 (偏移2-3)
- `10` - 设备类型 (偏移4)
- `FB` - 未知字段 (偏移5)
- `B9 0B` - 命令字 (偏移6-7) = 0x0BB9 = 3001 ✓
- `02 00` - 地址等信息 (偏移8-9)

## 修复方案
更新 `src/protocol_configs.py` 中运维协议配置:
```python
"yunwei": ProtocolInfo(
    protocol_name="yunwei",
    log_file="yunwei.log", 
    format_file="./resources/format_yunwei.txt",
    config=ProtocolConfigNew(
        head_len=11,                    # 修改为11字节
        tail_len=2,                     # 修改为2字节  
        frame_head=r"AA F5",           # 修改为AA F5
        head_fields=[
            HeaderField("cmd", 6, 2, "little", "uint"),        # 命令字段
            HeaderField("deviceType", 4, 1, "little", "uint"), # 设备类型
            HeaderField("addr", 8, 1, "little", "uint"),       # 地址
            HeaderField("gunNum", 9, 1, "little", "uint"),     # 枪号
        ]
    )
)
```

## 修复结果
✅ 成功解析运维协议数据
✅ 正确提取cmd=3001
✅ 正确解析各种运维数据字段

## 经验总结
1. 协议配置必须与实际数据包格式严格匹配
2. 通过日志中的cmd信息可以反推命令字段的正确位置
3. 运维协议实际上与V8协议使用相同的帧头和基本结构