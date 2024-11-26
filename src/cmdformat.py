import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# 现在可以导入src模块了
from src.logger_instance import log
import ast
from typing import List, Any, Dict, Any

# 停止原因编码
alarm_dict = {}
stop_dict = {}

def _find_cmd_lines(format_lines: List[str], cmd: int) -> tuple[int, int]:
    """
    在格式文件中查找指定命令的起始和结束行
    """
    cmd_code = f"cmd{cmd}"
    cmd_code_end = f"end{cmd}"
    cmd_start = cmd_end = -1
    
    for index, line in enumerate(format_lines):
        if cmd_code == line.strip():
            cmd_start = index + 1
        elif cmd_code_end == line.strip():
            cmd_end = index
            break
    
    if cmd_start == -1:
        raise ValueError(f"未找到命令 {cmd_code} 的开始标记")
    if cmd_end == -1:
        raise ValueError(f"未找到命令 {cmd_code} 的结束标记 {cmd_code_end}")
        
    return cmd_start, cmd_end

def _parse_loop_field(one_format: List[str], loop_format: dict) -> dict:
    """
    解析循环字段内的数据
    """
    try:
        length = eval(one_format[0].strip())
        name = one_format[1].strip()
    except (IndexError, SyntaxError) as e:
        raise ValueError(f"循环字段格式错误: {one_format}, 原因: {str(e)}")
        
    return {
        "length": length,
        "name": name
    }

def _parse_single_field(one_format: List[str]) -> tuple[Any, str]:
    """
    解析单个字段
    """
    try:
        length = eval(one_format[0].strip())
        name = one_format[1].strip()
    except (IndexError, SyntaxError) as e:
        raise ValueError(f"字段格式错误: {one_format}, 原因: {str(e)}")
        
    return length, name

def _parse_repeat_field(one_format: List[str]) -> tuple[List[int], List[str]]:
    """
    解析重复字段 (4:4n 格式)
    """
    try:
        count_str = one_format[0].split(":")[1]
        count = int("".join([i for i in count_str if i.isdigit()]))
        length = eval(one_format[0].split(":")[0])
        base_name = one_format[1].strip()
    except (IndexError, ValueError) as e:
        raise ValueError(f"重复字段格式错误: {one_format}, 原因: {str(e)}")
        
    lengths = [length] * count
    names = [f"{base_name}{i+1}" for i in range(count)]
    return lengths, names

def get_format(file_path: str, cmd: int) -> List[Any]:
    """
    通用获取报文格式的函数，支持四种格式：
    1. 固定长度格式
       直接指定字节长度和字段名
       格式示例：
       4           命令序号
       1           结果
       返回格式：format_list[0]=[4,1], format_list[1]=["命令序号","结果"]
    
    2. 单字段循环格式
       使用 "长度:Nn" 表示字段重复N次
       格式示例：
       4:4n        参数      # 重复4次,每次4字节
       返回格式：format_list[0]=[4,4,4,4], format_list[1]=["参数1","参数2","参数3","参数4"]
    
    3. 多字段循环格式
       使用 startfor:N 和 endfor 包围需要重复的字段组
       格式示例：
       startfor:2          # 重复2次
       1        状态
       2        电压
       endfor
       返回格式：format_list[0]=[1,2,1,2], format_list[1]=["1状态","1电压","2状态","2电压"]
    
    4. 变长字段循环格式
       使用 startloop:计数字段 和 endloop 包围变长字段组
       格式示例：
       1           数量
       startloop:数量
       2           时间
       4           数值
       endloop
       返回格式：format_list[0]=[1], format_list[1]=["数量"], 
                format_list[2]=[{"count_field":"数量", 
                                "fields":[{"length":2,"name":"时间"},
                                         {"length":4,"name":"数值"}]}]
    
    :param file_path: 格式文件路径
    :param cmd: 报文命令号
    :return: 格式列表 [长度列表, 名称列表, 循环信息列表]
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            format_lines = file.readlines()
    except IOError as e:
        raise IOError(f"无法读取格式文件 {file_path}: {str(e)}")

    try:
        cmd_start, cmd_end = _find_cmd_lines(format_lines, cmd)
        cmd_lines = format_lines[cmd_start:cmd_end]
        
        format_list = [[], [], []]  # [lengths, names, loop_info]
        is_for_n = False  # 当前命令是否为for循环插入格式
        for_count = 0  # for循环计数
        for_data_format = [[], []]  # 需要循环添加的格式
        
        # 变长报文相关变量
        is_in_loop = False
        loop_format = {"count_field": "", "fields": []}

        for line_num, one_line in enumerate(cmd_lines, start=cmd_start):
            try:
                one_format = one_line.strip().split()
                if not one_format:  # 跳过空行
                    continue
                    
                # 处理变长报文循环
                if "startloop" in one_format[0]:
                    if is_in_loop:
                        raise ValueError("循环嵌套错误：已在一个循环内")
                    is_in_loop = True
                    loop_format["count_field"] = one_format[0].split(":")[1]
                    continue
                    
                elif "endloop" in one_format[0]:
                    if not is_in_loop:
                        raise ValueError("发现endloop但未找到对应的startloop")
                    is_in_loop = False
                    format_list[2].append(loop_format)
                    loop_format = {"count_field": "", "fields": []}
                    continue
                    
                if is_in_loop:
                    field = _parse_loop_field(one_format, loop_format)
                    loop_format["fields"].append(field)
                    continue
                    
                # 处理其他格式
                if one_format[0][-1:] == "b":  # bit格式
                    format_list[0].append(one_format[0])
                    format_list[1].append(one_format[1].strip())
                    
                elif "startfor" in one_format[0]:  # for循环开始
                    if is_for_n:
                        raise ValueError("for循环嵌套错误：已在一个for循环内")
                    for_count = int(one_format[0].split(":")[1])
                    is_for_n = True
                    
                elif "endfor" in one_format[0]:  # for循环结束
                    if not is_for_n:
                        raise ValueError("发现endfor但未找到对应的startfor")
                    for i in range(for_count):
                        format_list[0].extend(for_data_format[0])
                        for j in range(len(for_data_format[1])):
                            format_list[1].append(f"{i+1}{for_data_format[1][j]}")
                    for_count = 0
                    is_for_n = False
                    for_data_format = [[], []]
                    
                elif ("n" in one_format[0] or "N" in one_format[0]) and ":" in one_format[0]:
                    lengths, names = _parse_repeat_field(one_format)
                    format_list[0].extend(lengths)
                    format_list[1].extend(names)
                    
                else:  # 普通字段
                    if is_for_n:
                        length, name = _parse_single_field(one_format)
                        for_data_format[0].append(length)
                        for_data_format[1].append(name)
                    else:
                        length, name = _parse_single_field(one_format)
                        format_list[0].append(length)
                        format_list[1].append(name)
                        
            except Exception as e:
                raise ValueError(f"解析错误 在第{line_num}行 '{one_line.strip()}': {str(e)}")
                
        # 检查循环是否都正确结束
        if is_in_loop:
            raise ValueError("循环未正确结束：缺少endloop")
        if is_for_n:
            raise ValueError("for循环未正确结束：缺少endfor")
            
        return format_list
        
    except Exception as e:
        log.e_print(f"解析命令{cmd}格式时发生错误: {str(e)}")
        raise


def strlist_to_hexlist(message):
    """
    字符串的列表转化为16进制的列表，['15','14'] to [0x15,0x14]
    """
    message_list_str = message.split()
    message_list_hex = []
    for i in message_list_str:
        message_list_hex.append(eval("0x" + i))
    # print('输入字节：', message_list_hex)
    return message_list_hex


def get_alarm_bit_list():
    """
    获取系统告警位定义表
    :param cmd: 报文代号
    :return: 报文格式
    """
    cmd_code = "cmd系统告警位定义表"
    cmd_code_end = "end系统告警位定义表"
    byte_alarm = []
    with open("./resources/format.txt", "r", encoding="utf-8") as file:
        format_lines = file.readlines()
    for index, format in enumerate(format_lines):
        if cmd_code in format:
            cmd_start = index + 1
        elif cmd_code_end in format:
            cmd_end = index
    cmd_lines = format_lines[cmd_start:cmd_end]
    for bit_index, bit in enumerate(cmd_lines):
        if "byte" in bit:
            temp_list = cmd_lines[bit_index + 1 : bit_index + 9]
            for i in temp_list:
                byte_alarm.append(i.strip())
    alarm_bit_list = [byte_alarm[i : i + 8] for i in range(0, len(byte_alarm), 8)]
    return alarm_bit_list


def get_alarm_stop_dict():
    """
    从文件获取告警和停止原因的字典
    :return: 告警和停止原因的字典,两个字典
    """
    with open("./resources/alarm.conf", "r", encoding="gb2312") as file:
        code_lines = file.readlines()

    for index, one_line in enumerate(code_lines):
        if "[告警信息列表]" == one_line.strip():
            alarm_reason_start = index + 2
        if "[充电停止原因列表]" == one_line.strip():
            stop_reason_start = index + 2

    for index, one_line in enumerate(code_lines[alarm_reason_start:]):
        if "\n" == one_line:
            alarm_reason_end = index + alarm_reason_start
            break
    for index, one_line in enumerate(code_lines[stop_reason_start:]):
        if "\n" == one_line:
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


def load_filter():
    """
    加载过滤参数
    """
    # 从文件./resources/filter.txt中读取过滤参数,cmd=[609,610,611,612]
    with open("./resources/filter.txt", "r", encoding="utf-8") as file:
        filter_lines = file.readlines()
        for one_line in filter_lines:
            if "cmd" in one_line:
                cmd = one_line.split("=")[1].strip()
                try:
                    # 使用 ast.literal_eval 安全地评估字符串，避免代码注入风险
                    cmd_list = ast.literal_eval(cmd)
                    if isinstance(cmd_list, list):
                        return cmd_list
                except (ValueError, SyntaxError):
                    # 如果解析失败，返回空列表
                    return []
    # 如果没有找到 "cmd" 行，返回空列表
    return []

if __name__ == "__main__":
    import os
    import sys
    
    # 测试所有类型的报文格式
    test_format = """
# 1. 固定长度格式测试
cmd101
4           命令序号
1           结果
end101

# 2. 单字段循环格式测试
cmd102
4           命令序号
4:4n        参数值      # 4字节参数重复4次
end102

# 3. 多字段循环格式测试
cmd103
4           命令序号
startfor:2
1           状态
2           电压
2           电流
endfor
end103

# 4. 变长字段循环格式测试
cmd701
4           命令序号
1           时段数量
startloop:时段数量
2           开始时间
2           结束时间
4           电费
4           服务费
1           尖峰平谷标志段
endloop
end701
"""
    
    # 创建临时测试文件
    test_file = "test_format.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_format)
        
    try:
        # 1. 测试固定长度格式
        print("\n1. 固定长度格式测试:")
        format_list = get_format(test_file, 101)
        print("长度列表:", format_list[0])
        print("名称列表:", format_list[1])
        print("循环信息:", format_list[2])
        
        # 2. 测试单字段循环格式
        print("\n2. 单字段循环格式测试:")
        format_list = get_format(test_file, 102)
        print("长度列表:", format_list[0])
        print("名称列表:", format_list[1])
        print("循环信息:", format_list[2])
        
        # 3. 测试多字段循环格式
        print("\n3. 多字段循环格式测试:")
        format_list = get_format(test_file, 103)
        print("长度列表:", format_list[0])
        print("名称列表:", format_list[1])
        print("循环信息:", format_list[2])
        
        # 4. 测试变长字段循环格式
        print("\n4. 变长字段循环格式测试:")
        format_list = get_format(test_file, 701)
        print("长度列表:", format_list[0])
        print("名称列表:", format_list[1])
        print("循环信息:", format_list[2])
        
        # 测试字符串转16进制功能
        print("\n5. 字符串转16进制列表测试:")
        test_str = "15 14 AA BB"
        hex_list = strlist_to_hexlist(test_str)
        print(f"输入: {test_str}")
        print(f"输出: {hex_list}")
        
    finally:
        # 清理临时文件
        if os.path.exists(test_file):
            os.remove(test_file)
