import logging as log
import os
import pprint

#文件路径
mcu_cuu_format_path = './resources/format_mcu_ccu.txt'
sinexcel_format_path = './resources/format_sinexcel.txt'
yunwei_format_path = './resources/format_yunwei.txt'

# 帧头长度
MCU_CCU_DATA_START_ADDR = 11 # 数据域起始地址机柜内通信协议
SINEXCEL_DATA_START_ADDR = 8 #盛弘协议
YUNWEI_DATA_START_ADDR = 8 #运维协议

# 停止原因编码
alarm_dict = {}
stop_dict = {}

def get_head_len(type):
    if type == 'mcu_ccu':
        return MCU_CCU_DATA_START_ADDR
    elif type == 'sinexcel':
        return SINEXCEL_DATA_START_ADDR
    elif type == 'yunwei':
        return YUNWEI_DATA_START_ADDR

def get_file_path(type):
    """
    获取文件路径
    :return: 文件路径
    """
    if(type == 'mcu_ccu'):
        return mcu_cuu_format_path
    if(type == 'sinexcel'):
        return sinexcel_format_path
    if(type == 'yunwei'):
        return yunwei_format_path

def get_format(tpye, cmd):
    """
    通用获取报文格式的函数
    :param cmd: 报文代号
    :return: 报文格式   [[长度信息],[文本信息]]
    """
    cmd_code = 'cmd' + str(cmd)
    cmd_code_end = 'end' + str(cmd)
    format_list = [[], []]
    cmd_start = 0
    cmd_end = 0
    
    is_for_n = False # 当前命令是否为for循环插入格式
    for_count = 0 # for循环计数
    for_data_format = [[],[]] # 需要循环添加的格式
    with open(get_file_path(tpye), 'r', encoding='utf-8') as file:
        format_lines = file.readlines()

    for index, format in enumerate(format_lines):
        if cmd_code == format.strip():
            cmd_start = index + 1
        elif cmd_code_end == format.strip():
            cmd_end = index
    cmd_lines = format_lines[cmd_start:cmd_end]

    for one_line in cmd_lines:
        one_format = one_line.strip().split()
        # print(one_format)
        # 按bit处理的情况
        if one_format[0][-1:] == 'b':
            format_list[0].append(one_format[0])
            format_list[1].append(one_format[1].strip())
         # for 4n
        # 2        枪1输出电压
        # 2        枪1输出电流
        # 1        枪1当前实际占用模块个数
        # 1        枪1满足负载率最少模块个数
        # 1        枪1满足最大功率最少模块个数
        # endfor
        # 处理多个字段都需要重复添加的情况
        elif 'startfor' in one_format[0]:
            for_count = int(one_format[0].split(':')[1])
            is_for_n = True
            # print("开始for循环添加 for_count:",for_count)
        elif "endfor" in one_format[0]:
            pass
        # 4:4N:
        elif ('n' in one_format[0] or 'N' in one_format[0]) and ':' in one_format[0]:
            count_str = one_format[0].split(':')[1] # 当前字段需要重复几次
            s = ''.join([i for i in count_str if i.isdigit()])
            count = int(s)
            print("count:",count)
            for i in range(count):
                format_list[0].append(eval(one_format[0].split(":")[0]))
                format_list[1].append(one_format[1].strip()+str(i+1))
        else: # 按字节处理的情况
            if is_for_n:
                for_data_format[0].append(eval(one_format[0].strip()))
                for_data_format[1].append(one_format[1].strip())
                # print(f"for循环添加{for_data_format[0]}{for_data_format[1]}")
            else:
                format_list[0].append(eval(one_format[0].strip()))
                format_list[1].append(one_format[1].strip())
        
        # for循环添加到format_list中
        if 'endfor' in one_format[0] and is_for_n:
            # print("结束for循环添加 for_count:",for_count)
            for i in range(for_count):
               format_list[0].extend(for_data_format[0])
               for j in range(len(for_data_format[1])):
                   format_list[1].append(str(i+1) + for_data_format[1][j])
            
            # 结束for添加
            for_count = 0
            is_for_n = False

    # pprint.pprint(format_list)
    return format_list


def strlist_to_hexlist(message):
    """
    字符串的列表转化为16进制的列表，['15','14'] to [0x15,0x14]
    """
    message_list_str = message.split()
    message_list_hex = []
    for i in message_list_str:
        message_list_hex.append(eval('0x' + i))
    # print('输入字节：', message_list_hex)
    return message_list_hex


def get_alarm_bit_list():
    """
    获取系统告警位定义表
    :param cmd: 报文代号
    :return: 报文格式
    """
    cmd_code = 'cmd系统告警位定义表'
    cmd_code_end = 'end系统告警位定义表'
    byte_alarm = []
    with open('./resources/format.txt', 'r', encoding='utf-8') as file:
        format_lines = file.readlines()
    for index, format in enumerate(format_lines):
        if cmd_code in format:
            cmd_start = index + 1
        elif cmd_code_end in format:
            cmd_end = index
    cmd_lines = format_lines[cmd_start:cmd_end]
    for bit_index, bit in enumerate(cmd_lines):
        if 'byte' in bit:
            temp_list = cmd_lines[bit_index + 1:bit_index + 9]
            for i in temp_list:
                byte_alarm.append(i.strip())
    alarm_bit_list = [byte_alarm[i:i + 8] for i in range(0, len(byte_alarm), 8)]
    return alarm_bit_list


def get_alarm_stop_dict():
    """
    从文件获取告警和停止原因的字典
    :return: 告警和停止原因的字典,两个字典
    """
    with open('./resources/alarm.conf', 'r', encoding='gb2312') as file:
        code_lines = file.readlines()

    for index, one_line in enumerate(code_lines):
        if '[告警信息列表]' == one_line.strip():
            alarm_reason_start = index + 2
        if '[充电停止原因列表]' == one_line.strip():
            stop_reason_start = index + 2

    for index, one_line in enumerate(code_lines[alarm_reason_start:]):
        if '\n' == one_line:
            alarm_reason_end = index + alarm_reason_start
            break
    for index, one_line in enumerate(code_lines[stop_reason_start:]):
        if '\n' == one_line:
            stop_reason_end = index + stop_reason_start
            break

    alarm_lines = code_lines[alarm_reason_start:alarm_reason_end]
    stop_lines = code_lines[stop_reason_start:stop_reason_end]

    alarm_dict = {}
    stop_dict = {}
    for one_line in alarm_lines:
        alarm_code = one_line.split()[0]
        alarm_dict.update({alarm_code: one_line.split()[4]})

    for one_line in stop_lines:
        stop_code = one_line.split()[0]
        stop_dict.update({stop_code: one_line.split()[1]})
    return alarm_dict, stop_dict
