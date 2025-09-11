# protocol_configs.py
"""
=============================================================================
🚀 协议配置文件 - 添加新协议就在这里改！
=============================================================================

这个文件是整个系统的"配置中心"，所有支持的协议都在这里定义。
如果您是运维人员想要添加新协议支持，只需要修改这个文件即可，
不需要懂编程，按照下面的说明填写配置就行了。

📖 使用指南：
1. 如果要添加新协议，直接复制一个现有协议的配置，然后修改参数
2. 如果要修改现有协议，找到对应的协议名称，修改里面的参数
3. 修改完保存文件即可，程序会自动识别新配置

=============================================================================
📋 配置参数详细说明（给不懂编程的人看）
=============================================================================

🔸 协议基本信息：
   - protocol_name: 协议的名字（比如"v8"、"xiaoju"）
   - log_file: 要解析的日志文件名（比如"v8_com.log"）
   - format_file: 数据格式定义文件位置（在resources文件夹里）
   - config: 协议解析的详细配置（见下面说明）

🔸 协议解析配置（ProtocolConfigNew）：
   - head_len: 数据包头部有多少个字节（比如11表示头部11个字节）
   - tail_len: 数据包尾部有多少个字节（比如2表示尾部2个字节）
   - frame_head: 数据包的识别标志（比如"AA F5"表示以AA F5开头的包）
   - head_fields: 头部各个字段的详细配置（见下面说明）
   - time_regex: 时间格式的匹配规则（一般不用改）
   - cmd_aliases: 命令代码的别名映射（可选，一般不用）

🔸 头部字段配置（HeaderField）：
每个字段都有以下参数，按顺序填写：
   - name: 字段的名字（比如"cmd"表示命令字段，"addr"表示地址字段）
   - offset: 这个字段在第几个字节开始（从0开始数，0表示第1个字节）
   - length: 这个字段占几个字节（比如2表示占2个字节）
   - endian: 字节排列方式（"little"=小端，"big"=大端，不懂就用"little"）
   - type: 字段类型（"uint"=数字，"const"=固定值，"ascii"=文本，"hex"=十六进制）
   - const_value: 当type="const"时，期望的固定值（用于验证数据包是否正确）
   - required: 是否必须匹配（True=必须，False=可选，一般都用True）

💡 简单例子：
HeaderField("cmd", 4, 2, "little", "uint")
解释：名为"cmd"的字段，从第5个字节开始（offset=4），长度2字节，小端模式，数字类型

HeaderField("startField", 0, 2, "big", "const", const_value=0x7dd0)
解释：名为"startField"的字段，从第1个字节开始，长度2字节，大端模式，固定值类型，
     值必须是0x7dd0，用来验证数据包是否是正确的协议

=============================================================================
"""

from typing import Dict, NamedTuple
from src.base_protocol import HeaderField, ProtocolConfigNew


class ProtocolInfo(NamedTuple):
    """协议信息结构"""
    protocol_name: str
    log_file: str
    format_file: str
    config: ProtocolConfigNew


# 所有协议配置已集中到下面的 PROTOCOL_CONFIGS 中，无需单独的配置函数


# =============================================================================
# 🚀 协议配置区域 - 添加/修改协议就在这里
# =============================================================================
# 重要提示：每个协议的配置格式都是一样的，复制粘贴后修改参数即可

PROTOCOL_CONFIGS: Dict[str, ProtocolInfo] = {
    
    # -----------------------------------------------------------------------------
    # V8协议配置 - 用于解析V8设备的通信数据
    # -----------------------------------------------------------------------------
    "v8": ProtocolInfo(
        protocol_name="v8",                                    # 协议名字
        log_file="v8_com.log",                                # 日志文件名
        format_file="./resources/format_mcu_ccu.txt",         # 数据格式定义文件
        config=ProtocolConfigNew(
            head_len=11,                                       # 数据包头部占11个字节
            tail_len=2,                                        # 数据包尾部占2个字节
            frame_head=r"AA F5",                              # 识别标志：以"AA F5"开头
            head_fields=[                                      # 头部各字段配置：
                HeaderField("cmd", 4, 2, "little", "uint"),          # 命令字段：第5-6字节，数字类型
                HeaderField("index", 6, 2, "little", "uint"),        # 序号字段：第7-8字节，数字类型
                HeaderField("deviceType", 8, 1, "little", "uint"),   # 设备类型：第9字节，数字类型
                HeaderField("addr", 9, 1, "little", "uint"),         # 地址字段：第10字节，数字类型
                HeaderField("gunNum", 10, 1, "little", "uint"),      # 枪号字段：第11字节，数字类型
            ]
        )
    ),
    
    # -----------------------------------------------------------------------------
    # 小桔协议配置 - 用于解析小桔充电设备的通信数据
    # -----------------------------------------------------------------------------
    "xiaoju": ProtocolInfo(
        protocol_name="xiaoju",                                # 协议名字
        log_file="xiaoju.log",                                # 日志文件名
        format_file="./resources/format_xiaoju.txt",          # 数据格式定义文件
        config=ProtocolConfigNew(
            head_len=14,                                       # 数据包头部占14个字节
            tail_len=1,                                        # 数据包尾部占1个字节
            frame_head=r"7D D0",                              # 识别标志：以"7D D0"开头
            head_fields=[                                      # 头部各字段配置：
                HeaderField("startField", 0, 2, "big", "const", const_value=0x7dd0),    # 起始验证字段：第1-2字节，固定值0x7dd0
                HeaderField("length", 2, 2, "little", "uint"),                         # 长度字段：第3-4字节，数字类型
                HeaderField("version", 4, 4, "big", "hex"),                            # 版本字段：第5-8字节，十六进制类型
                HeaderField("sequence", 8, 4, "little", "uint"),                       # 序列号字段：第9-12字节，数字类型
                HeaderField("cmd", 12, 2, "little", "uint"),                          # 命令字段：第13-14字节，数字类型
            ]
        )
    ),
    
    # -----------------------------------------------------------------------------
    # Sinexcel协议配置 - 用于解析Sinexcel设备的通信数据
    # -----------------------------------------------------------------------------
    "sinexcel": ProtocolInfo(
        protocol_name="sinexcel",                              # 协议名字
        log_file="sincexcel.log",                             # 日志文件名
        format_file="./resources/format_sinexcel.txt",        # 数据格式定义文件
        config=ProtocolConfigNew(
            head_len=8,                                        # 数据包头部占8个字节
            tail_len=1,                                        # 数据包尾部占1个字节
            frame_head=r"AA F5",                              # 识别标志：以"DD E8"开头
            head_fields=[                                      # 头部各字段配置：
                HeaderField("cmd", 6, 2, "little", "uint"),                            # 命令字段：第7-8字节，数字类型
            ],
            cmd_aliases={1103: 1102, 1108: 1105}              # 命令别名：1103当作1102处理，1108当作1105处理
        )
    ),
    
    # -----------------------------------------------------------------------------
    # 运维协议配置 - 用于解析运维设备的通信数据（与V8协议使用相同帧头）
    # -----------------------------------------------------------------------------
    "yunwei": ProtocolInfo(
        protocol_name="yunwei",                                # 协议名字
        log_file="yunwei.log",                                # 日志文件名
        format_file="./resources/format_yunwei.txt",          # 数据格式定义文件
        config=ProtocolConfigNew(
            head_len=11,                                       # 数据包头部占11个字节（与V8相同）
            tail_len=2,                                        # 数据包尾部占2个字节（与V8相同）
            frame_head=r"AA F5",                              # 识别标志：以"AA F5"开头（与V8相同）
            head_fields=[                                      # 头部各字段配置：
                HeaderField("cmd", 6, 2, "little", "uint"),                            # 命令字段：第7-8字节，数字类型
                HeaderField("deviceType", 4, 1, "little", "uint"),                     # 设备类型：第5字节
                HeaderField("addr", 8, 1, "little", "uint"),                          # 地址字段：第9字节
                HeaderField("gunNum", 9, 1, "little", "uint"),                        # 枪号字段：第10字节
            ]
        )
    ),
    
    # =============================================================================
    # 🚀 新增协议模板 - 要添加新协议就复制下面这段，去掉注释符号#，然后修改参数
    # =============================================================================
    # "new_protocol": ProtocolInfo(                            # ← 改成你的协议名字
    #     protocol_name="new_protocol",                         # ← 改成你的协议名字（和上面一行一样）
    #     log_file="new_protocol.log",                          # ← 改成你的日志文件名
    #     format_file="./resources/format_new_protocol.txt",    # ← 改成你的格式文件名（记得在resources文件夹里创建）
    #     config=ProtocolConfigNew(
    #         head_len=10,                                      # ← 改成你的数据包头部字节数
    #         tail_len=2,                                       # ← 改成你的数据包尾部字节数
    #         frame_head=r"AA BB",                             # ← 改成你的识别标志（数据包开头的特征）
    #         head_fields=[                                     # ← 配置你的头部字段（看上面例子照着写）
    #             HeaderField("cmd", 4, 2, "little", "uint"),  # ← 这是一个示例字段，按你的协议修改
    #         ]
    #     )
    # ),
}

# =============================================================================
# 以下是程序内部使用的函数，不需要修改
# =============================================================================

def get_protocol_info(protocol_name: str) -> ProtocolInfo:
    """根据协议名称获取完整协议信息"""
    if protocol_name not in PROTOCOL_CONFIGS:
        raise ValueError(f"Unsupported protocol: {protocol_name}")
    return PROTOCOL_CONFIGS[protocol_name]


def get_protocol_config(protocol_name: str) -> ProtocolConfigNew:
    """根据协议名称获取协议配置（保持向后兼容）"""
    return get_protocol_info(protocol_name).config


def get_supported_protocols() -> list:
    """获取所有支持的协议列表"""
    return list(PROTOCOL_CONFIGS.keys())

# =============================================================================
# 📝 添加新协议的完整步骤（给不懂编程的人看）
# =============================================================================
# 
# 第1步：准备工作
#   1. 找到你要解析的日志文件，放到项目根目录
#   2. 在resources文件夹里创建对应的格式定义文件（参考现有的txt文件）
#
# 第2步：添加协议配置
#   1. 复制上面的"新增协议模板"
#   2. 删除每行开头的#号
#   3. 修改协议名字、文件名等参数
#   4. 配置head_fields（这是最重要的部分，决定如何解析数据包头部）
#
# 第3步：测试
#   1. 保存文件
#   2. 运行：python main.py 你的协议名字
#   3. 检查输出是否正确
#
# 💡 头部字段配置技巧：
#   - 如果不知道怎么配置，先用十六进制编辑器打开日志文件
#   - 找到数据包的开头（frame_head），然后数字节确定各字段位置
#   - offset是从0开始数的，0表示第1个字节，1表示第2个字节，以此类推
#   - 如果字段是固定值（比如协议版本），用type="const"并设置const_value
#   - 如果字段是变化的数字，用type="uint"
#   - 如果不确定用"little"还是"big"，先试"little"，不行再改"big"
#
# =============================================================================