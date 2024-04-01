import logging as log
import os
# 停止原因编码
alarm_dict = {}
stop_dict = {}


def get_format(cmd):
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
    with open('./resources/format.txt', 'r', encoding='utf-8') as file:
        format_lines = file.readlines()

    for index, format in enumerate(format_lines):
        if cmd_code == format.strip():
            cmd_start = index + 1
        elif cmd_code_end == format.strip():
            cmd_end = index
    cmd_lines = format_lines[cmd_start:cmd_end]

    for one_line in cmd_lines:
        if one_line.split()[0][-1:] == 'b':
            format_list[0].append(one_line.split()[0])
        # 4:4N:
        elif one_line.split()[0][-1:] == 'N':
            format_list[0].append(eval(one_line.strip().split()[0].strip()))    
        else:
            format_list[0].append(eval(one_line.strip().split()[0].strip()))
        format_list[1].append(one_line.strip().split()[1].strip())


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
