from src import cmdformat
from typing import List, Dict, Any, Tuple


# Define lists for different types of keys
bcd_keys = ["桩编号", "账号或者物理卡号", "逻辑卡号", "物理卡号", "并充序号"]
time_keys = ["交易日期", "开始时间", "结束时间"]
ascii_keys = [
    "电动汽车唯一标识",
    "VIN",
    "交易流水号",
    "充电流水号",
    "订单号",
    "订单编号",
    "升级文件路径",
    "升级文件名",
    "日志上传文件路径",
    "终端桩编码",
    "充电桩编码",
    "充电桩Mac地址或者IMEI码",
    "事件参数",
    "BRM-车辆识别码vin",
    "字符串参数值",
]
eight_binary_keys = [
    "A接触器驱动反馈测试结果正",
    "A接触器驱动反馈测试结果负",
    "B接触器驱动反馈测试结果正",
    "B接触器驱动反馈测试结果负",
    "模块地址测试结果",
    "A面接触器驱动位置测试结果",
    "B面接触器驱动位置测试结果",
    "A面控制信号",
    "A面反馈信号+",
    "A面反馈信号-",
    "B面控制信号",
    "B面反馈信号+",
    "B面反馈信号-",
    "BST报文",
    "BEM报文",
]
four_binary_keys = [
    "枪故障状态",
    "A模块通讯状态",
    "B模块通讯状态",
    "线缆测试结果",
    "M2全自动工装结果",
    "主机系统告警",
    "充电桩软件版本",
]
three_binary_keys = [
    "BRM-BMS通讯协议版本号",
]
two_binary_keys = [
    "终端系统状态",
    "终端充电状态(发给主机)",
    "工装使能",
    "终端通讯状态",
    "BST中止充电故障原因",
    "BCS-最高单体电压及其组号",
    
    
]
binary_keys = [
    "模块状态码",
    "驱动板通讯状态",
    "枪状态",
    "BST充电机中止原因",
    "BST中止充电错误原因",
    "主枪地址"  ,
    "副枪1地址"
]


def get_bit_val(byte, index):
    """
    获取字节中指定位的值
    :param byte: 要检查的字节
    :param index: 要检查的位索引（0-7）
    :return: 如果指定位为1则返回1，否则返回0
    """
    if index > 7:
        return None
    if byte & (1 << index):
        return 1
    else:
        return 0


def set_bit_val(byte, index, val):
    """
    设置字节中指定位的值
    :param byte: 要修改的字节
    :param index: 要设置的位索引
    :param val: 要设置的值（True或False）
    :return: 修改后的字节
    """
    if val:
        return byte | (1 << index)
    else:
        return byte & ~(1 << index)


# 按二进制打印，0x1122334455667788 打印为大端顺序
def get_eight_binary_str(num):
    """
    将8字节整数转换为格式化的二进制字符串
    :param num: 8字节整数
    :return: 格式化的二进制字符串，包括二进制表示和十六进制表示
    """
    if num is None:
        return "None"
    binary_str = bin(num)[2:].zfill(64)  # 64位，即8字节
    formatted_str = " : ".join(
        [
            binary_str[:8],
            binary_str[8:16],
            binary_str[16:24],
            binary_str[24:32],
            binary_str[32:40],
            binary_str[40:48],
            binary_str[48:56],
            binary_str[56:],
        ]
    )
    char_str = " ".join(
        [f"0x{int(binary_str[i : i + 8], 2):02X}" for i in range(0, 32, 8)]
    )
    return f"{formatted_str} | {char_str}"


# 按二进制打印，0x11223344 打印为大端顺序 10101011 : 01000001 : 00110000
def get_four_binary_str(num):
    """
    将4字节整数转换为格式化的二进制字符串
    :param num: 4字节整数
    :return: 格式化的二进制字符串，包括二进制表示和十六进制表示
    """
    if num is None:
        return "None"
    binary_str = bin(num)[2:].zfill(32)  # 32位，即4字节
    formatted_str = " : ".join(
        [binary_str[:8], binary_str[8:16], binary_str[16:24], binary_str[24:]]
    )
    char_str = ":".join(
        [f"0x{int(binary_str[i : i + 8], 2):02X}" for i in range(0, 32, 8)]
    )
    return f"{formatted_str} | {char_str}"


def get_three_binary_str(num):
    """
    将3字节整数转换为格式化的二进制字符串
    :param num: 3字节整数
    :return: 格式化的二进制字符串，包括二进制表示和十六进制表示
    """
    if num is None:
        return "None"
    binary_str = bin(num)[2:].zfill(24)  # 24位，即3字节
    formatted_str = " : ".join([binary_str[:8], binary_str[8:16], binary_str[16:]])
    char_str = ":".join(
        [f"0x{int(binary_str[i : i + 8], 2):02X}" for i in range(0, 24, 8)]
    )
    return f"{formatted_str} | {char_str}"


# 按二进制打印 0x0301 打印为大端顺序 0 0 0 0 0 0 1 1 : 0 0 0 0 0 0 1 1
def get_two_binary_str(num):
    """
    将2字节整数转换为格式化的二进制字符串
    :param num: 2字节整数
    :return: 格式化的二进制字符串，包括二进制表示和十六进制表示
    """
    if num is None:
        return "None"
    binary_str = bin(num)[2:].zfill(16)  # 16位，即2字节
    formatted_str = " : ".join([binary_str[:8], binary_str[8:]])
    char_str = ":".join(
        [f"0x{int(binary_str[i : i + 8], 2):02X}" for i in range(0, 16, 8)]
    )
    return f"{formatted_str} | {char_str}"


#  打印一个字节的二进制字符串
def get_binary_str(num):
    """
    将1字节整数转换为格式化的二进制字符串
    :param num: 1字节整数
    :return: 格式化的二进制字符串，包括二进制表示和十六进制表示
    """
    if num is None:
        return "None"
    binary_str = bin(num)[2:].zfill(8)  # 8位，即1字节
    return f"{binary_str} | 0x{num:02x}"


def data_byte_merge(data):
    """
    将字节列表按小端格式合并为有符号整数
    :param data: 字节列表
    :return: 合并后的有符号整数值
    """
    if not data:
        return None
    result = 0
    for i in range(len(data) - 1, -1, -1):
        result = (data[i] << 8 * i) + result
    return result


def get_ascii_data(data_list):
    """
    将字节列表转换为ASCII字符串
    :param data_list: 字节列表
    :return: ASCII字符串
    """
    if not data_list:
        return ""
    code_str = ""
    for data in data_list:
        if not data:
            code_str = code_str + "*"
        else:
            code_str = code_str + chr(data)
    return code_str


def get_bcd_data(data_list):
    """
    将字节列表转换为BCD编码的字符串
    :param data_list: 字节列表
    :return: BCD编码的字符串
    """
    if not data_list:
        return ""
    code_str = ""
    for data in data_list:
        data = str(hex(data)).replace("0x", "")
        if len(data) == 1:
            data = "0" + data
        code_str = code_str + data
    return code_str


def get_date_time(bytes_list):
    """
    将字节列表转换为格式化的日期时间字符串
    :param bytes_list: 包含日期时间信息的字节列表
    :return: 格式化的日期时间字符串
    """
    datetime = ""
    date_format = ["", "", "-", "-", " ", ":", ":"]
    for index, date in enumerate(bytes_list[:-1]):
        if date < 10:
            date = "0{:x}".format(date)
            datetime = datetime + ("{}{}".format(date_format[index], date))
        else:
            datetime = datetime + ("{}{:x}".format(date_format[index], date))

    return datetime  # 2018-5-23 13:32:9


def get_time_from_cp56time2a(timebuff):
    """
    从CP56Time2a格式的时间缓冲区获取时间
    :param timebuff: 7字节CP56Time2a时间缓冲区
    :return: 格式化的时间字符串
    """
    tm_year = (timebuff[6] & 0x7F) + 2000
    tm_mon = (timebuff[5] & 0x0F) - 1
    tm_mday = timebuff[4] & 0x1F
    tm_hour = timebuff[3] & 0x1F
    tm_min = timebuff[2] & 0x3F
    msec = (timebuff[1] << 8) | timebuff[0]

    tm_sec = (msec + 500) // 1000

    time_str = "{}-{}-{} {}:{}:{}".format(
        tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec
    )

    return time_str


def get_alarm_list(bytes_list):
    """
    从告警字段中提取告警位信息
    :param bytes_list: 32字节的告警字段列表
    :return: 告警列表，包含激活的告警描述
    """
    alarm_bit_list = []
    for index, byte in enumerate(bytes_list):
        if index > 19:  # 协议中只定义到了20字节
            break
        #     遍历一个字节的故障bit是否是1，是1，添加汉字说明的故障到列表中
        for i, alarm_byte_format in enumerate(cmdformat.get_alarm_bit_list()[index]):
            if get_bit_val(byte, i):
                alarm_bit_list.append(alarm_byte_format)
            else:
                continue
    return alarm_bit_list


def get_stop_reason(stop_code):
    """
    根据停止原因代码获取停止原因名称
    :param stop_code: 停止原因代码（整数）
    :return: 停止原因名称
    """
    alarm_dict, stop_dict = cmdformat.get_alarm_stop_dict()
    return stop_dict.get(str(stop_code), "未知原因")


def get_multi_bit_val(byte: int, start: int, bit_number: int) -> int:
    """
    获取多个bit位数据大小
    """
    return (byte >> start) & (0xFF >> (8 - bit_number))


def parse_multi_bit_date(data_list: List[int], format_: List[Any]) -> Dict[str, Any]:
    """
    解析报文中的数据，支持按位划分和按字节划分的混合格式，也兼容普通报文

    参数:
    data_list: 有效的数据列表
    format_: 数据格式和键名格式

    返回:
    Dict[str, Any]: 解析后的数据字典

    功能:
    1. 根据协议类型和命令码获取数据格式
    2. 逐字段解析数据，支持按位和按字节两种方式
    3. 处理异常情况并返回解析结果
    """
    try:
        data_format, key_format, loop_info = format_
    except Exception as err:
        print(f"-------------数据格式错误: {err}-------------")
        return {}

    parsed_dict = {}
    bit_count = 0
    cur_parse_index = 0
    bit_data_format = []
    bit_key_format = []

    for index, data in enumerate(data_format):
        if isinstance(data, str):
            # 按位解析
            # 获取当前字段的位长度
            bit_length = int(data[:1])
            # 累加当前字段的位长度到总位长度
            bit_count += bit_length
            # 将当前字段的位长度添加到位长度列表中
            bit_data_format.append(bit_length)
            # 将当前字段的键名添加到键名列表中
            bit_key_format.append(key_format[index])

            # 检查是否已处理完一个完整字节或是最后一个不完整字节
            if bit_count == 8 or (index == len(data_format) - 1 and 0 < bit_count < 8):
                # 处理完整字节或最后一个不完整字节
                # 调用parsed_one_byte_data函数解析一个字节的数据
                one_byte_dict = parsed_one_byte_data(
                    data_list[cur_parse_index], bit_data_format, bit_key_format
                )
                parsed_dict.update(one_byte_dict)
                # 更新当前解析的索引，指向下一个字节
                cur_parse_index += 1
                # 重置位计数器
                bit_count = 0
                # 清空位长度列表
                bit_data_format.clear()
                # 清空键名列表
                bit_key_format.clear()
        else:
            # 按字节解析
            # 调用parse_byte_data函数解析按字节处理的数据
            parse_byte_data(
                data_list, cur_parse_index, data, key_format[index], parsed_dict
            )
            # 更新当前解析的索引，指向下一个字段
            cur_parse_index += data

    return parsed_dict


def parsed_one_byte_data(
    byte: int, bit_data_format: List[int], bit_key_format: List[str]
) -> Dict[str, int]:
    """
    针对一个字节的报文，按bit处理的报文

    参数:
    byte: 待解析的字节数据
    bit_data_format: 每个字段的位长度列表
    bit_key_format: 每个字段的键名列表

    返回:
    Dict[str, int]: 解析后的字典，��为字段名，值为对应的数据

    功能:
    1. 遍历bit_data_format列表，逐个解析字节中的位字段
    2. 使用get_multi_bit_val函数提取指定位的值
    3. 将解析结果存入字典，键名来自bit_key_format
    """
    bit_parsed_dict = {}
    cur_bit_index = 0
    for index, one_field_len in enumerate(bit_data_format):
        # 从当前位置开始，提取指定长度的位值
        data_ = get_multi_bit_val(byte, cur_bit_index, one_field_len)
        # 将提取的值存入字典，使用对应的键名
        bit_parsed_dict[bit_key_format[index]] = data_
        # 更新当前位索引
        cur_bit_index += one_field_len
    return bit_parsed_dict


def parse_byte_data(
    data_list: List[int],
    start_index: int,
    length: int,
    key: str,
    parsed_dict: Dict[str, Any],
):
    """
    解析按字节处理的报文

    参数:
    data_list: 包含所有数据的列表
    start_index: 当前字段在data_list中的起始索引
    length: 当前字段的长度（字节数）
    key: 当前字段的键名
    parsed_dict: 用于存储解析结果的字典

    功能:
    根据字段类型选择适当的解析方法，并将解析结果存入parsed_dict
    """
    # 提取当前字段的数据
    data = data_list[start_index : start_index + length]

    # 移除键名中的数字，以便于匹配预定义的键类型
    format_key = key.strip("1234567890")

    # 根据字段类型选择相应的解析方法
    if format_key in bcd_keys:
        parsed_dict[key] = get_bcd_data(data)  # BCD编码数据解析
    elif format_key in time_keys:
        parsed_dict[key] = get_time_from_cp56time2a(
            data
        )  # 时间数据解析（CP56Time2a格式）
    elif format_key in ascii_keys:
        parsed_dict[key] = get_ascii_data(data)  # ASCII编码数据解析
    elif format_key in eight_binary_keys:
        parsed_dict[key] = get_eight_binary_str(
            data_byte_merge(data)
        )  # 8位二进制字符串解析
    elif format_key in four_binary_keys:
        parsed_dict[key] = get_four_binary_str(
            data_byte_merge(data)
        )  # 4位二进制字符串解析
    elif format_key in three_binary_keys:
        parsed_dict[key] = get_three_binary_str(
            data_byte_merge(data)
        )  # 3位二进制字符串解析
    elif format_key in two_binary_keys:
        parsed_dict[key] = get_two_binary_str(
            data_byte_merge(data)
        )  # 2位二进制字符串解析
    elif format_key in binary_keys:
        parsed_dict[key] = get_binary_str(data_byte_merge(data))  # 普通二进制字符串解析
    else:
        # 对于未定义的类型，直接合并字节数据
        parsed_dict[key] = data_byte_merge(data)


class LoopFieldParser:
    """变长循环字段解析器"""
    
    def __init__(self, data_list: List[int], start_pos: int):
        """
        初始化解析器
        :param data_list: 完整的数据字节列表
        :param start_pos: 循环字段的起始位置
        """
        self.data_list = data_list
        self.current_pos = start_pos
        
    def parse_loop_fields(self, count: int, field_formats: List[Dict[str, Any]]) -> tuple[Dict[str, Any], int]:
        """
        解析循环字段组
        :param count: 循环次数
        :param field_formats: 字段格式列表 [{"length": int, "name": str}, ...]
        :return: (解析结果字典, 结束位置)
        """
        result = {}
        for i in range(count):
            field_group = {}
            for field in field_formats:
                length = field["length"]
                name = field["name"]
                value = self._parse_field(length)
                field_group[name] = value
            result[f"组{i+1}"] = field_group
        
        return result, self.current_pos
    
    def _parse_field(self, length: int) -> int:
        """
        解析单个字段
        :param length: 字段长度
        :return: 解析后的值
        """
        value = 0
        for i in range(length):
            if self.current_pos + i < len(self.data_list):
                value = (value << 8) | self.data_list[self.current_pos + i]
        self.current_pos += length
        return value
