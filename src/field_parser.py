from src import cmdformat

# Define lists for different types of keys
bcd_keys = ["桩编号", "账号或者物理卡号", "逻辑卡号", "物理卡号", "并充序号"]
time_keys = ["交易日期", "开始时间", "结束时间"]
ascii_keys = [
    "电动汽车唯一标识",
    "VIN",
    "交易流水号",
    '充电流水号',
    "升级文件路径",
    "升级文件名",
    "日志上传文件路径",
    "终端桩编码",
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
    "BSD报文",
    "BEM报文",
]
four_binary_keys = [
    "枪故障状态",
    "A模块通讯状态",
    "B模块通讯状态",
    "线缆测试结果",
    "M2全自动工装结果",
    '主机系统告警',
]
two_binary_keys = [
    "终端系统状态",
    "终端充电状态(发给主机)",
    "工装使能",
    "终端通讯状态",
]
binary_keys = ["模块状态码", "驱动板通讯状态", "枪状态",]


def get_bit_val(byte, index):
    """
    获取索引bit是否是1
    :param byte: 字节
    :param index: 索引位置0-7
    :return: 是否是1
    """
    if index > 7:
        return None
    if byte & (1 << index):
        return 1
    else:
        return 0


def set_bit_val(byte, index, val):
    if val:
        return byte | (1 << index)
    else:
        return byte & ~(1 << index)


# 按二进制打印，0x1122334455667788 打印为大端顺序
def get_eight_binary_str(num):
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


# 按二进制打印 0x0301 打印为大端顺序 0 0 0 0 0 0 1 1 : 0 0 0 0 0 0 1 1
def get_two_binary_str(num):
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
    if num is None:
        return "None"
    binary_str = bin(num)[2:].zfill(8)  # 8位，即1字节
    return f"{binary_str} | 0x{num:02x}"


def data_byte_merge(data):
    """
    传入一个字段的数据列表，按小端格式合并数据，返回整数值
    :param data: 一个字段的数据列表
    :return: 整数实际值
    """
    if not data:
        return None
    result = 0
    for i in range(len(data) - 1, -1, -1):
        result = (data[i] << 8 * i) + result
    return result


def get_ascii_data(data_list):
    # 可能需要反转列表，则用下面语句
    # gun_number.reverse()
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
    # 可能需要反转列表，则用下面语句
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
    格式化日期信息
    :param bytes_list:
    :return:
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
    获取cp56time2a时间
    :param timebuff: 7字节cp65时间
    :return: time_t
    """ ""

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
    从告警字段（32字节）中提取告警位信息
    :param bytes_list: 32字节列表
    :return: 告警列表
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
    根据停止原因代码(整数)，返回停止原因名称
    :param stop_code: 停止原因代码(整数)
    :return: 停止原因名称
    """
    alarm_dict, stop_dict = cmdformat.get_alarm_stop_dict()
    return stop_dict[str(stop_code)]
