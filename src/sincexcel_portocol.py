"""
每个报文解析函数的框架类似，只需修改数据区格式，添加解析规则
普通报文参考106，变长度报文参考3和4
"""

import sys
import time
import re
from src.console_log import ConsoleLog
from src.field_parser import *
from src.m_print import MyLogger
from typing import Any, Dict, List


# 日志模块配置，使用print print 等打印信息
# # 使控制台输出同时保存到文件
stand_stdout = sys.stdout
custom_stdout = ConsoleLog(stream=sys.stdout)

# 是否打印外围附加信息
print_more_info = False
# 附加信息长度
other_info_len = 9

PROTOCOL_TYPE = "sinexcel"

log = MyLogger(0)


def common_fun(data_format, message):
    """
    分离出来的公共处理子程序
    :param data_format: 需要解析的样式
    :param message: 报文字符串，每个字节用空格分隔    例： 13 34 45 56
    :return:每个字段结束位置索引列表，只包含数据域的字节列表，解析了包头和包尾的字典，此时数据域为空，外部填充
    """
    # 数据格式数量的依次求和列表[2,4,36......],目的是求出每个字段的开始index
    field_index_list = []
    for i in range(1, len(data_format) + 1):
        field_index_list.append(sum(data_format[:i]))

    # 将字符报文序列转化为数字格式的字节列表
    message_list_hex = str_seq_to_hexlist(message)
    data_count = len(message_list_hex) - other_info_len  # 统计数据区域长度

    # 对外围信息和数据区做分离
    parsed_dict, data_list = split_message(message_list_hex, data_count)

    # 对报文和协议不匹配的情况进行处理,差多少补多少0
    diff = sum(data_format) - data_count
    data_list.extend([0 for _ in range(diff)])
    if diff:
        if diff > 0:
            print(
                "报文有效数据长度{},需要格式化的长度{},报文少{}字节".format(
                    data_count, sum(data_format), diff
                )
            )
            print("报文协议版本比解析器老")
        else:
            print(
                "报文有效数据长度{},需要格式化的长度{},报文多{}字节".format(
                    data_count, sum(data_format), abs(diff)
                )
            )
            print("报文协议版本比解析器新")

    return field_index_list, data_list, parsed_dict


def str_seq_to_hexlist(message):
    """
    字符串的列表转化为16进制的列表，['15','14'] to [0x15,0x14]
    """
    message_list_str = message.split()
    message_list_hex = []
    for i in message_list_str:
        message_list_hex.append(eval("0x" + i))
    return message_list_hex


def split_message(message_list_hex, data_area_len):
    """
    解析包头和包尾，拆分出数据域，将报文按格式化到字典
    :param message: 报文字符串
    :param data_format: 数据域格式
    :return: 解析后的字典，数据域列表
    """
    message_format = [2, 2, 1, 1, 2, data_area_len, 1]
    # 解析报文其他部分
    # 分离出数据，列表存储
    split_message_dict = {}
    count = 0
    for number in message_format:
        bytes_list = []
        for byte in message_list_hex[count : count + number]:
            count += 1
            bytes_list.append(byte)
        if count == 2:
            split_message_dict.update({"start_area": bytes_list})
        elif count == 4:
            if bytes_list[1] == 0:
                split_message_dict.update({"len": bytes_list[0]})
            else:
                split_message_dict.update({"len": data_byte_merge(bytes_list)})
        elif count == 5:
            split_message_dict.update({"info": bytes_list[0]})
        elif count == 6:
            split_message_dict.update({"serial": bytes_list[0]})
        elif count == 8:
            if bytes_list[1] == 0:
                split_message_dict.update({"cmd": bytes_list[0]})
            else:
                split_message_dict.update({"cmd": data_byte_merge(bytes_list)})
        elif count == 8 + number:
            data_list = bytes_list
        else:
            split_message_dict.update({"check": bytes_list[0]})

    if print_more_info:
        print(
            "起始域：{:x}{:x}".format(
                split_message_dict["start_area"][0], split_message_dict["start_area"][1]
            )
        )
        print("长度域：{}".format(split_message_dict["len"]))
        print("信息域：{}".format(split_message_dict["info"]))
        print("序列号：{}".format(split_message_dict["serial"]))
        print("命令代号：{}".format(split_message_dict["cmd"]))
        print("校验和：{}".format(split_message_dict["check"]))

    split_message_dict.update(
        ({"data": {}})
    )  # 最后添加数据区域的空字段，数据域由外部填充

    return split_message_dict, data_list


def parser_1(message, format_):
    # --------数据区分配格式，与协议定义格式相关------
    data_format = format_[0]
    key_format = format_[1]
    str_parameter_format = cmdformat.get_format(PROTOCOL_TYPE, "整形参数设置表")
    # ---------------------------
    # 根据设置参数数量不同，重新设置报文格式，便于使用通用方式解析
    field_index_list, data_list, parsed_dict = common_fun(data_format, message)
    # print('field_index_list:', field_index_list)
    # print('data_list', data_list)

    # 获取设置参数的起始地址和参数的总字节数，参数的起始地址从1开始
    set_para_start_address = data_byte_merge(data_list[5:9])
    set_para_count = data_byte_merge(data_list[9:10])
    set_byte_number = data_byte_merge(data_list[10:12])

    # 根据设置参数的开始字节地址和设置字节数量重新设置数据格式
    for i in range(set_para_count):
        data_format.append(
            4
        )  # 所有参数长度都是4，设置几个参数就添加几个4字节宽度的解析域
        key_format.append(str_parameter_format[1][set_para_start_address - 1 + i])
    field_index_list, data_list, parsed_dict = common_fun(data_format, message)

    # 循环解析-------------------
    count = 0
    for i in range(1, len(data_format) + 1):
        field_index_list.append(sum(data_format[:i]))
    for index, number in enumerate(data_format):
        bytes_list = []
        for byte in data_list[count : count + number]:
            count += 1
            bytes_list.append(byte)
        # --------------------------------数据区解析规则-------------------------------
        for sum_index, sum_ in enumerate(field_index_list):
            if count == sum_:
                parsed_dict["data"].update(
                    {key_format[index]: data_byte_merge(bytes_list)}
                )
                break
    return parsed_dict


def parser_2(message, format_):
    print("未解析cmd=2")
    return None


# 3,4报文可以合并
def parser_3(message, format_):
    # --------数据区分配格式，与协议定义格式相关------
    data_format = format_[0]
    key_format = format_[1]
    str_parameter_format = cmdformat.get_format(PROTOCOL_TYPE, "字符参数设置表")
    # ---------------------------
    # 根据设置参数数量不同，重新设置报文格式，便于使用通用方式解析
    field_index_list, data_list, parsed_dict = common_fun(data_format, message)

    # 获取设置参数的起始地址和参数的总字节数，参数的起始地址从1开始
    set_para_start_address = data_byte_merge(data_list[5:9])
    set_byte_number = data_byte_merge(data_list[9:11])

    # 根据设置参数的开始字节地址和设置字节数量重新设置数据格式
    data_format.append(set_byte_number)
    key_format.append(str_parameter_format[1][set_para_start_address - 1])
    field_index_list, data_list, parsed_dict = common_fun(data_format, message)
    # 循环解析-------------------
    count = 0
    for i in range(1, len(data_format) + 1):
        field_index_list.append(sum(data_format[:i]))
    for index, number in enumerate(data_format):
        bytes_list = []
        for byte in data_list[count : count + number]:
            count += 1
            bytes_list.append(byte)
        # --------------------------------数据区解析规则-------------------------------
        for sum_index, sum_ in enumerate(field_index_list):
            if count == sum_:
                # 对特殊格式进行解析
                if key_format[index] == "标准时钟时间":
                    parsed_dict["data"].update(
                        {key_format[index]: get_date_time(bytes_list)}
                    )
                    break
                if index > 4:  # 对于字符串设置参数使用ascii解析
                    parsed_dict["data"].update(
                        {key_format[index]: get_ascii_data(bytes_list)}
                    )
                    break
                parsed_dict["data"].update(
                    {key_format[index]: data_byte_merge(bytes_list)}
                )
                break
    return parsed_dict


def parser_4(message, format_):
    # --------数据区分配格式，与协议定义格式相关------
    data_format = format_[0]
    key_format = format_[1]
    str_parameter_format = cmdformat.get_format(PROTOCOL_TYPE, "字符参数设置表")
    # ---------------------------
    # 根据设置参数数量不同，重新设置报文格式，便于使用通用方式解析
    field_index_list, data_list, parsed_dict = common_fun(data_format, message)
    # 获取设置参数的起始地址和参数的总字节数，参数的起始地址从1开始
    set_para_start_address = data_byte_merge(data_list[37:40])
    # 根据设置参数的开始字节地址和设置字节数量重新设置数据格式
    data_format.append((len(message) + 1) // 3 - len(data_list) - 9)
    key_format.append(str_parameter_format[1][set_para_start_address - 1])
    field_index_list, data_list, parsed_message = common_fun(data_format, message)
    # 循环解析-------------------
    count = 0
    for i in range(1, len(data_format) + 1):
        field_index_list.append(sum(data_format[:i]))
    for index, number in enumerate(data_format):
        bytes_list = []
        for byte in data_list[count : count + number]:
            count += 1
            bytes_list.append(byte)
        # --------------------------------数据区解析规则-------------------------------
        for sum_index, sum_ in enumerate(field_index_list):
            if count == sum_:
                # 对特殊格式进行解析
                if key_format[index] == "标准时钟时间":
                    parsed_message["data"].update(
                        {key_format[index]: get_date_time(bytes_list)}
                    )
                    break
                if key_format[index] == "充电桩编码":
                    parsed_message["data"].update(
                        {key_format[index]: get_ascii_data(bytes_list)}
                    )
                    break
                if index > 5:  # 对于字符串设置参数使用ascii解析
                    parsed_message["data"].update(
                        {key_format[index]: get_ascii_data(bytes_list)}
                    )
                    break
                parsed_message["data"].update(
                    {key_format[index]: data_byte_merge(bytes_list)}
                )
                break
    return parsed_message


def parser_common(message, format_):
    """
    定长报文公共解析函数
    :param message: 报文字符串数据
    :return: 解析后的报文字典
    """
    # --------数据区分配格式------
    data_format = format_[0]
    key_format = format_[1]
    # ---------------------------

    cur_index = 0  # 目前解析到的位置索引
    field_index_list, data_list, parsed_dict = common_fun(data_format, message)

    # 遍历数据帧格式，即每个字段几个字节，field_num为第几个字段
    for field_num, number in enumerate(data_format):
        one_field_data = []
        # 按字节数从数据列表中取出一个字段的数据到one_field_data
        for byte in data_list[cur_index : cur_index + number]:
            cur_index += 1
            one_field_data.append(byte)
        # --------------------------------数据区解析规则-------------------------------
        # 根据数据定义格式解析每个字段的报文数据,并填充解析后的字典
        # 创建一个字典，将每个条件映射到相应的函数
        key_format_func_mapping = {
            "充电桩编码": get_ascii_data,
            "充电桩资产码": get_ascii_data,
            "查询参数信息": get_ascii_data,
            "ICCID": get_ascii_data,
            "IMEI": get_ascii_data,
            "4G模块版本": get_ascii_data,
            "注册运营商": get_ascii_data,
            "主机资产码": get_ascii_data,
            "卡号/用户id":get_ascii_data,
            "BRM-车辆识别码VIN": get_ascii_data,
            "AES秘钥": get_ascii_data,
            "设备名称": get_ascii_data,
            "FTP服务器IP地址或者域名": get_ascii_data,
            "FTP下载路径": get_ascii_data,
            "FTP用户名": get_ascii_data,
            "FTP密码": get_ascii_data,
            "FTP存放日志路径": get_ascii_data,
            "映射远程服务器IP或域名": get_ascii_data,
            "当前充电桩系统时间": get_date_time,
            "平台标准BCD时间": get_date_time,
            "充电开始时间": get_date_time,
            "充电结束时间": get_date_time,
            "充电流水号": get_ascii_data,
            "预约/开始充电开始时间": get_date_time,
            "预约/定时启动时间": get_date_time,
            "充电卡号": get_ascii_data,
            "用户充电卡密码": get_ascii_data,
            "车辆VIN码": get_ascii_data,
            "BRM-车辆识别码vin": get_ascii_data,
            "告警位信息": get_alarm_list,
            "充电结束原因": get_stop_reason,
            "车辆VIN绑定账号": get_ascii_data,
        }

        for i, field_index in enumerate(field_index_list):
            if cur_index == field_index:
                # 对特殊格式进行解析
                func = key_format_func_mapping.get(key_format[field_num], data_byte_merge)
                if func == get_stop_reason:
                    one_field_data = data_byte_merge(one_field_data)
                parsed_dict["data"].update(
                    {key_format[field_num]: func(one_field_data)}
                )
                break

    return parsed_dict


def message_parser(cmd, message):
    """
     提供报文号和数据，解析数据
    :param message: 报文的字符串数据
    :param cmd: 报文代号 int
    :return: 解析的数据
    """
    if cmd == 1103:  # 两个报文解析模板用一样的
        cmd = 1102
    # if cmd == 201:
    #     cmd = 221
    if cmd == 1108:
        cmd = 1105

    if cmd == 3:
        parsed_dict = parser_3(message, cmdformat.get_format(PROTOCOL_TYPE, cmd))
    # elif cmd == 4:
    #     parsed_dict = parser_4(message, cmdformat.get_format(PROTOCOL_TYPE, cmd))
    elif cmd == 1:
        parsed_dict = parser_1(message, cmdformat.get_format(PROTOCOL_TYPE, cmd))
    # elif cmd == 2:
    #     parsed_dict = parser_2(message, cmdformat.get_format(PROTOCOL_TYPE, cmd))
    else:
        parsed_dict = parser_common(message, cmdformat.get_format(PROTOCOL_TYPE, cmd))

    return parsed_dict


def extract_data_from_file(file_path):
    """
    从数据行中匹配到数据，返回结构化数据，主要获取的是数据产生时间和数据内容本身
    """
    # 正则表达式以匹配两种时间格式2024-03-26 18:54:05:200 或者 2024-03-28 19:27:38.079
    # ms 时间同时匹配 . 和 : 两种分隔符
    info_line_re = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{2,3}")
    # 这里不再需要特别匹配AA F5开始的数据行，因为我们会连续读取数据直到下一个信息行
    data_line_start_re = re.compile(r"AA F5")

    data_groups = []
    current_group = None
    is_collecting_data = False  # 标记是否正在收集多行数据

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line == "" or "//" in line:
                continue

            info_line_match = info_line_re.search(line)
            if info_line_match:
                # 遇到新的信息行，如果之前有在收集数据，则先结束当前数据的收集
                if current_group:
                    data_groups.append(current_group)
                    is_collecting_data = False
                current_group = {"time": info_line_match.group(), "data": ""}

                continue

            # 如果行以AA F5开始，标记为开始收集数据
            if data_line_start_re.search(line):
                is_collecting_data = True
            # 如果正在收集数据，则将行添加到数据中
            if is_collecting_data and current_group is not None:
                current_group["data"] += line + " "

        # 不要忘记将最后一个数据组添加到列表中
        if current_group and current_group["data"]:
            data_groups.append(current_group)

    return data_groups


def parse_data_content(data_groups:List[Dict[str, str]], valid_cmds: List[int]):
    """
    从结构化的数据中，提取出cmd码，报文序号，设备类型，设备地址，设备枪号等信息
    并且把数据字符串转化为列表。只处理valid_cmds中包含的cmd码。
    """
    filtered_data_groups = []
    for group in data_groups:
        # 将数据字符串分割成列表，每个元素代表一字节的数据
        data_bytes = group["data"].strip().split()

        # 确保数据长度足够
        if len(data_bytes) >= cmdformat.get_head_len(PROTOCOL_TYPE):
            # 提取cmd码，第5,6字节，小端格式
            cmd = int(data_bytes[6], 16) + (int(data_bytes[7], 16) << 8)
             # 如果cmd不在valid_cmds列表中，跳过当前循环，如果valid_cmds为空，则不跳过
            if cmd not in valid_cmds:
                continue
            group["cmd"] = cmd
            
             # 将处理过的group添加到filtered_data_groups列表中
            filtered_data_groups.append(group)

    return filtered_data_groups


def load_file_format(file_path):
    """
    加载文件并格式化，格式为列表加字典的形式，字典内容包含time，tx_rx,len，cmd，四项参数
    :param file_path:日志文件的路径
    :return:加载文件的列表
    """

    vaild_cmd = cmdformat.load_filter()
    data_groups = extract_data_from_file(file_path)
    data_groups = parse_data_content(data_groups, vaild_cmd)

    return data_groups


def screen_parse_data(net_info_list):
    """
    筛选解析报文并打印
    :param net_info_list:原始网络数据列表
    :return:None
    """

    # 解析并打印过滤后的报文
    for net_info in net_info_list:
        byte_data_str = net_info["data"]
        cmd = net_info["cmd"]
        net_info_time = net_info["time"]
        try:
            can_read_data = message_parser(cmd, byte_data_str)
            net_info["data"] = can_read_data
        except Exception as err:
            can_read_data = None
            log.e_print("-------------数据解析错误{}-------------".format(err))
            net_info["data"] = "-------------数据解析错误{}-------------".format(err)
        if can_read_data:
            print("[{}] cmd={}".format(net_info["time"], can_read_data["cmd"]))

            for key, value in can_read_data["data"].items():
                try:
                    print("'{}': {}".format(key, value))
                except Exception as err:
                    log.e_print("-----数据打印错误-----", err)
            print()
        else:
            log.e_print("cmd={} time={}报文数据未解析\n".format(cmd, net_info_time))

    return net_info_list


# 定义枚举类型 运营， 运维
class RunType:
    OPERATE = 1
    MAINTAIN = 2


def main(run_type=RunType.OPERATE):
    global PROTOCOL_TYPE
    # 加载网络日志文件
    if run_type == RunType.OPERATE:
        net_file_path = "client_tcu_net.log"
        PROTOCOL_TYPE = "sinexcel"
    elif run_type == RunType.MAINTAIN:
        net_file_path = "yunwei_tcu_net.log"
        PROTOCOL_TYPE = "yunwei"
    g_net_info_list = load_file_format(net_file_path)

    # 筛选解析报文并打印
    screen_parse_data(g_net_info_list)


def run(run_type=RunType.OPERATE):
    sys.stdout = custom_stdout
    main(run_type)
    sys.stdout = stand_stdout
    input("回车结束程序")
