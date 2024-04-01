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


log = MyLogger(1)

# 日志模块配置，使用print print 等打印信息
# LOG_FORMAT = "[%(levelname)s %(asctime)s] %(message)s [%(funcName)s() %(module)s:%(lineno)d] "
# log.basicConfig(level=print, format=LOG_FORMAT, filename='log.txt')
# # 使控制台输出同时保存到文件
stand_stdout = sys.stdout
custom_stdout = ConsoleLog(stream=sys.stdout)

# 数据域起始地址
DATA_START_ADDR = 11

def str_seq_to_hexlist(message):
    """
    字符串的列表转化为16进制的列表，['15','14'] to [0x15,0x14]
    """
    message_list_str = message.split()
    message_list_hex = []
    for i in message_list_str:
        message_list_hex.append(eval('0x' + i))
    return message_list_hex


def get_multi_bit_val(byte, start, bit_number):
    """
    获取多个bit位数据大小
    """
    return (byte >> start) & (0xff >> (8 - bit_number))


def parsed_one_byte_data(byte, bit_data_format, bit_key_format):
    bit_parsed_dict = {}

    cur_bit_index = 0  # 记录当前处理在一个字节的第几位
    for index, one_field_len in enumerate(bit_data_format):
        # 根据此字段占bit数据分别处理
        data_ = get_multi_bit_val(byte, cur_bit_index, one_field_len)
        bit_parsed_dict.update({bit_key_format[index]: data_})
        cur_bit_index = cur_bit_index + one_field_len
    return bit_parsed_dict


def parse_multi_bit_date(message, cmd):
    """
    解析报文中的数据不是完全按字节划分，而是按部分按bit划分的,其实也可以兼容普通报文
    :param message:报文的字符串
    :param pf: pf号
    :return:解析后的字典
    """
    # 将字符报文转化为数字格式
    data_list = cmdformat.strlist_to_hexlist(message)
    data_list = data_list[DATA_START_ADDR:-2]
    parsed_dict = {}

    # 获取格式解析所需格式信息
    format_ = cmdformat.get_format(cmd)
    data_format = format_[0]
    key_format = format_[1]



    # 循环解析，根据是否是bit分别处理
    bit_count = 0  # 用于bitt计数，满一个字节就去解析
    cur_parse_index = 0  # 记录当前处理数据列表的第几个字节
    bit_data_format = []  # 用于解析一个字节多bit数据时用
    bit_key_format = []  # 用于解析一个字节多bit数据时用
    for index, data in enumerate(data_format):
        # 处理按bit分的数据
        if isinstance(data, str):
            bit_count = bit_count + int(data[:1])
            bit_data_format.append(int(data[:1]))
            bit_key_format.append(key_format[index])
            if bit_count == 8:
                bit_count = 0
                one_byte_dict = parsed_one_byte_data(data_list[cur_parse_index], bit_data_format, bit_key_format)
                parsed_dict.update(one_byte_dict)
                cur_parse_index = cur_parse_index + 1
                bit_data_format.clear()
                bit_key_format.clear()
                # 对剩余未占满一个字节的数据进行处理
            if index == len(data_format) - 1 and 0 < bit_count < 8:
                one_byte_dict = parsed_one_byte_data(data_list[cur_parse_index], bit_data_format, bit_key_format)
                parsed_dict.update(one_byte_dict)
        else:  # 处理按byte分的数据
            one_field_data = data_list[cur_parse_index:cur_parse_index + data]
            # print(one_field_data)

            if key_format[index] == '桩编号':
                parsed_dict.update({key_format[index]: get_bcd_data(one_field_data)})
            elif key_format[index] == '交易流水号':
                parsed_dict.update({key_format[index]: get_bcd_data(one_field_data)})
            elif key_format[index] == '交易日期':
                parsed_dict.update({key_format[index]: get_time_from_cp56time2a(one_field_data)})
            elif key_format[index] == '开始时间':
                parsed_dict.update({key_format[index]: get_time_from_cp56time2a(one_field_data)})
            elif key_format[index] == '结束时间':
                parsed_dict.update({key_format[index]: get_time_from_cp56time2a(one_field_data)})
            elif key_format[index] == '电动汽车唯一标识':
                parsed_dict.update({key_format[index]: get_ascii_data(one_field_data)})
            elif key_format[index] == '账号或者物理卡号':
                parsed_dict.update({key_format[index]: get_bcd_data(one_field_data)})
            elif key_format[index] == '逻辑卡号':
                parsed_dict.update({key_format[index]: get_bcd_data(one_field_data)})
            elif key_format[index] == '物理卡号':
                parsed_dict.update({key_format[index]: get_bcd_data(one_field_data)})
            elif key_format[index] == 'VIN':
                parsed_dict.update({key_format[index]: get_ascii_data(one_field_data)})
            elif key_format[index] == '并充序号':
                parsed_dict.update({key_format[index]: get_bcd_data(one_field_data)})
            elif key_format[index] == '终端系统状态':
                parsed_dict.update({key_format[index]: get_two_binary_str(data_byte_merge(one_field_data))})
            else:
                parsed_dict.update({key_format[index]: data_byte_merge(one_field_data)})

            cur_parse_index = cur_parse_index + data
    return parsed_dict


def message_parser(cmd, message):
    """
     提供报文号和数据，解析数据
    :param message: 报文的字符串数据
    :param cmd: 报文代号 int
    :return: 解析的数据
    """

    parsed_dict = parse_multi_bit_date(message, cmd)


    return parsed_dict


def extract_data_from_file(file_path):
    # 正则表达式以匹配两种时间格式2024-03-26 18:54:05:200 或者 2024-03-28 19:27:38.079
    # ms 时间同时匹配 . 和 : 两种分隔符
    info_line_re = re.compile( r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{3}')
    # 这里不再需要特别匹配AA F5开始的数据行，因为我们会连续读取数据直到下一个信息行
    data_line_start_re = re.compile(r'AA F5')
    
    data_groups = []
    current_group = None
    is_collecting_data = False  # 标记是否正在收集多行数据
    
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line == "":
                continue
            
            # print(line)
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
def parse_data_content(data_groups):
    for group in data_groups:
        # 将数据字符串分割成列表，每个元素代表一字节的数据
        data_bytes = group["data"].strip().split()

        # 确保数据长度足够
        if len(data_bytes) >= 11:
            # 提取cmd码，第5,6字节，小端格式
            cmd = int(data_bytes[4], 16) + (int(data_bytes[5], 16) << 8)
            group["cmd"] = cmd
            
            # 提取报文序号，第7,8字节，小端格式
            index = int(data_bytes[6], 16) + (int(data_bytes[7], 16) << 8)
            group["index"] = index
            
            # 提取设备类型，第9字节
            device_type = int(data_bytes[8], 16)
            group["deviceType"] = device_type
            
            # 提取设备地址，第10字节
            addr = int(data_bytes[9], 16)
            group["addr"] = addr
            
            # 提取设备枪号，第11字节
            gunNum = int(data_bytes[10], 16)
            group["gunNum"] = gunNum

    return data_groups
def load_file_format(file_path):
    """
    加载文件并格式化，格式为列表加字典的形式，字典内容包含time，tx_rx,len，cmd，四项参数
    :param file_path:日志文件的路径
    :return:加载文件的列表
    """

    data_groups = extract_data_from_file(file_path)
    data_groups = parse_data_content(data_groups)
    
    return data_groups

def screen_parse_data(net_info_list):
    """
    筛选解析报文并打印
    :param net_info_list:原始网络数据列表
    :return:None
    """

    # 解析并打印过滤后的报文
    for net_info in net_info_list:
        byte_data_str = net_info['data']
        cmd = net_info['cmd']
        net_info_time = net_info['time']
        try:
            can_read_data = message_parser(cmd, byte_data_str)
            net_info['data'] = can_read_data
        except Exception as err:
            can_read_data = None
            log.e_print('-------------数据解析错误{}-------------'.format(err))
            net_info['data'] = '-------------数据解析错误{}-------------'.format(err)
        if can_read_data:
            print('[{}] cmd={} port:{}-{}'.format(net_info['time'], cmd, net_info['addr'], net_info['gunNum']))

            for key, value in can_read_data.items():
                try:
                    print("'{}': {}".format(key, value))
                except Exception as err:
                    log.e_print('-----数据打印错误-----', err)
            print()
        else:
            log.d_print('cmd={} time={}报文数据未解析\n'.format(cmd, net_info_time))

    return net_info_list




def load_config(file_path):
    """
    从日志文件中加载
    :return:
    """
    top_three_lines = []
    cmd_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for i in range(3):
            top_three_lines.append(file.readline().strip())

    try:
        start_time = top_three_lines[0][6:25]
        end_time = top_three_lines[1][4:23]
        start_time_stamp = time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
        end_time_stamp = time.mktime(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
    except Exception as err:
        print('没有开始或结束时间，默认不限制时间{}'.format(err))
        start_time = '2020-01-01 00:00:00'
        end_time = '2030-01-01 00:00:00'
        start_time_stamp = time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
        end_time_stamp = time.mktime(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))

    # 默认配置
    for line in top_three_lines:
        if line[:3] == 'cmd':
            cmd_list = eval(line[4:])

    if len(cmd_list) == 0:
        print('沒有cmd列表，不过滤cmd')
    print('开始时间：{}，结束时间：{}，cmd列表：{}\n'.format(start_time, end_time, cmd_list))
    return start_time_stamp, end_time_stamp, cmd_list


def main():
    # 加载网络日志文件
    net_file_path = 'v8com.log'
    g_net_info_list = load_file_format(net_file_path)

    # 筛选解析报文并打印
    screen_parse_data(g_net_info_list)


def run():
    sys.stdout = custom_stdout
    main()
    sys.stdout = stand_stdout
    input('回车结束程序')
