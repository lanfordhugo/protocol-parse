"""
文件名称: generate_wave_test_log.py
内容摘要: 波形测试报文生成脚本 - 批量生产wave_test协议的spdlog格式日志文件
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-10

使用方法:
    python scripts/generate_wave_test_log.py
    python scripts/generate_wave_test_log.py --count 500 --interval 200
    python scripts/generate_wave_test_log.py --scenario sine
    python scripts/generate_wave_test_log.py --scenario all --count 300

生成文件:
    input_logs/wave_test.log
"""

import argparse
import math
import os
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple


# ============== 帧构造工具 ==============

# 帧头固定字节
FRAME_HEAD = bytes([0xAA, 0xF5])
# 帧头长度（AA F5 + len(2) + cmd(2) + index(2) + padding(3) = 11）
HEAD_LEN = 11
# 帧尾长度
TAIL_LEN = 2


def calc_checksum(data: bytes) -> bytes:
    """
    计算简单校验和（2字节，低位在前）

    Args:
        data: 待校验数据（不含校验位本身）

    Returns:
        2字节校验和(LE)
    """
    total = sum(data) & 0xFFFF
    return struct.pack("<H", total)


def build_frame(cmd_id: int, index: int, payload: bytes) -> bytes:
    """
    构造完整的协议帧

    帧结构: AA F5 + 长度(2B LE) + cmd(2B LE) + index(2B LE) + 填充(3B) + payload + 校验(2B)

    Args:
        cmd_id: 命令ID
        index: 帧序号
        payload: 数据段

    Returns:
        完整帧字节
    """
    total_len = HEAD_LEN + len(payload) + TAIL_LEN
    header = (
        FRAME_HEAD
        + struct.pack("<H", total_len)
        + struct.pack("<H", cmd_id)
        + struct.pack("<H", index)
        + bytes([0x01, 0x01, 0x01])  # 填充3字节（deviceType, addr, gunNum）
    )
    body = header + payload
    checksum = calc_checksum(body)
    return body + checksum


def bytes_to_hex_lines(data: bytes, bytes_per_line: int = 25) -> List[str]:
    """
    将字节数据格式化为十六进制行（与v8.log格式一致）

    Args:
        data: 字节数据
        bytes_per_line: 每行字节数

    Returns:
        格式化的十六进制行列表
    """
    hex_str = " ".join(f"{b:02X}" for b in data)
    lines = []
    tokens = hex_str.split(" ")
    for i in range(0, len(tokens), bytes_per_line):
        chunk = " ".join(tokens[i : i + bytes_per_line])
        lines.append(chunk + " ")
    return lines


def format_log_entry(
    timestamp: datetime,
    terminal_id: int,
    direction: str,
    cmd_id: int,
    frame_data: bytes,
) -> str:
    """
    格式化为spdlog日志条目

    格式: [timestamp] [terminal_id] ccucom: Direction N Bytes(cmd=X[0xHEX]) [source]
          hex_data_lines...

    Args:
        timestamp: 时间戳
        terminal_id: 终端ID
        direction: 方向 (Recv/Send)
        cmd_id: 命令ID
        frame_data: 完整帧数据

    Returns:
        格式化的日志文本
    """
    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.") + f"{timestamp.microsecond // 1000:03d}"
    byte_count = len(frame_data)
    cmd_hex = f"0X{cmd_id:04X}"

    header_line = (
        f"[{ts_str}] [{terminal_id}] ccucom: {direction} "
        f"{byte_count} Bytes(cmd={cmd_id}[{cmd_hex}]) "
        f"[waveTest.cpp:100 tid:1000]"
    )

    hex_lines = bytes_to_hex_lines(frame_data)
    return header_line + "\n" + "\n".join(hex_lines) + "\n"


# ============== CMD Payload 构造 ==============


def build_cmd1_payload(
    voltage: float,
    current: float,
    env_temp: int,
    gun_temp: int,
    energy: float,
    power: float,
) -> bytes:
    """
    CMD1 - 电气参数监控

    Args:
        voltage: 输出电压(V) → raw = voltage / 0.1
        current: 输出电流(A) → raw = current / 0.1
        env_temp: 环境温度(°C)
        gun_temp: 枪头温度(°C)
        energy: 累计电量(kWh) → raw = energy / 0.001
        power: 功率(kW) → raw = power / 0.1
    """
    return struct.pack(
        "<HHBBiH",
        int(voltage / 0.1),
        int(current / 0.1),
        env_temp,
        gun_temp,
        int(energy / 0.001),
        int(power / 0.1),
    )


def build_cmd2_payload(work_status: int, charge_mode: int, switch_state: int) -> bytes:
    """CMD2 - 状态监控（枚举型）"""
    return struct.pack("<BBB", work_status, charge_mode, switch_state)


def build_cmd3_payload(
    bms_voltage: float,
    bms_current: float,
    soc: int,
    work_status: int,
    demand_voltage: float,
    demand_current: float,
) -> bytes:
    """
    CMD3 - 混合型监控

    Args:
        bms_voltage: BMS电压(V)
        bms_current: BMS电流(A)，充电时为负值
        soc: SOC百分比
        work_status: 工作状态枚举值
        demand_voltage: 需求电压(V)
        demand_current: 需求电流(A)
    """
    return struct.pack(
        "<HhBBHh",
        int(bms_voltage / 0.1),
        int(bms_current / 0.1),
        soc,
        work_status,
        int(demand_voltage / 0.1),
        int(demand_current / 0.1),
    )


def build_cmd4_payload(ch1: float, ch2: float, ch3: float, ch4: float) -> bytes:
    """CMD4 - 多通道传感器（scale=0.01）"""
    return struct.pack(
        "<HHHH",
        int(ch1 / 0.01),
        int(ch2 / 0.01),
        int(ch3 / 0.01),
        int(ch4 / 0.01),
    )


# ============== 波形数据生成场景 ==============


def scenario_sine(count: int, interval_ms: int) -> List[str]:
    """
    正弦波场景（CMD1 + CMD4 交替）

    CMD1: 电压=350+50*sin, 电流=50+30*sin(偏移), 温度缓慢变化
    CMD4: 4通道不同频率正弦波
    """
    entries = []
    base_time = datetime(2024, 8, 29, 9, 0, 0)
    index = 0

    for i in range(count):
        t = i * interval_ms / 1000.0
        ts = base_time + timedelta(milliseconds=i * interval_ms)

        if i % 2 == 0:
            # CMD1 - 电气参数正弦波
            voltage = 350.0 + 50.0 * math.sin(t * 0.5)
            current = 50.0 + 30.0 * math.sin(t * 0.5 + math.pi / 4)
            env_temp = 25 + int(5 * math.sin(t * 0.1))
            gun_temp = 35 + int(10 * math.sin(t * 0.3))
            energy = max(0, t * 10)  # 随时间递增
            power = max(0, voltage * current / 1000)

            payload = build_cmd1_payload(voltage, current, env_temp, gun_temp, energy, power)
            frame = build_frame(1, index, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 1, frame))
        else:
            # CMD4 - 多通道正弦波
            ch1 = 50.0 + 30.0 * math.sin(t * 1.0)
            ch2 = 50.0 + 20.0 * math.sin(t * 2.0)
            ch3 = 50.0 + 10.0 * math.sin(t * 0.5)
            ch4 = 50.0 + 25.0 * math.sin(t * 3.0)

            payload = build_cmd4_payload(ch1, ch2, ch3, ch4)
            frame = build_frame(4, index, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 4, frame))

        index += 1

    return entries


def scenario_ramp(count: int, interval_ms: int) -> List[str]:
    """
    爬坡场景（CMD1 + CMD3）

    模拟充电从开始到满充的完整过程：
    - 电压从300V爬到400V
    - 电流从0A爬到100A再降到0A
    - SOC从10%升到90%
    """
    entries = []
    base_time = datetime(2024, 8, 29, 10, 0, 0)
    index = 0

    for i in range(count):
        t = i * interval_ms / 1000.0
        progress = i / max(count - 1, 1)
        ts = base_time + timedelta(milliseconds=i * interval_ms)

        if i % 3 != 2:
            # CMD1 - 电压电流爬坡
            voltage = 300.0 + 100.0 * progress
            # 电流先升后降（抛物线）
            current = 100.0 * 4 * progress * (1 - progress)
            env_temp = 25 + int(10 * progress)
            gun_temp = 30 + int(20 * progress)
            energy = 50.0 * progress
            power = max(0, voltage * current / 1000)

            payload = build_cmd1_payload(voltage, current, env_temp, gun_temp, energy, power)
            frame = build_frame(1, index, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 1, frame))
        else:
            # CMD3 - BMS数据
            bms_voltage = 300.0 + 100.0 * progress
            bms_current = -(100.0 * 4 * progress * (1 - progress))  # 负值=充入
            soc = int(10 + 80 * progress)
            status = 1 if progress < 0.95 else 0  # 运行中→空闲
            demand_v = 400.0
            demand_i = -80.0

            payload = build_cmd3_payload(bms_voltage, bms_current, soc, status, demand_v, demand_i)
            frame = build_frame(3, index, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 3, frame))

        index += 1

    return entries


def scenario_step(count: int, interval_ms: int) -> List[str]:
    """
    阶跃场景（CMD2 + CMD1）

    模拟状态突变和参数阶跃：
    - 工作状态周期性切换
    - 电压/电流在不同工位之间阶跃
    """
    entries = []
    base_time = datetime(2024, 8, 29, 11, 0, 0)
    index = 0

    # 预定义阶跃工位
    voltage_levels = [300.0, 350.0, 380.0, 400.0, 350.0, 300.0]
    current_levels = [0.0, 50.0, 80.0, 100.0, 60.0, 0.0]
    status_sequence = [0, 1, 1, 1, 1, 0]  # 空闲→运行→空闲
    mode_sequence = [1, 1, 2, 2, 1, 1]    # 恒压→恒流→恒压

    for i in range(count):
        ts = base_time + timedelta(milliseconds=i * interval_ms)
        # 每 count/6 条切换一个工位
        step_idx = min(int(i * len(voltage_levels) / count), len(voltage_levels) - 1)

        if i % 3 == 0:
            # CMD2 - 状态
            payload = build_cmd2_payload(
                status_sequence[step_idx],
                mode_sequence[step_idx],
                1 if status_sequence[step_idx] == 1 else 0,
            )
            frame = build_frame(2, index, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 2, frame))
        else:
            # CMD1 - 阶跃电压电流（加少量噪声使波形更真实）
            noise_v = 2.0 * math.sin(i * 0.7)
            noise_i = 1.0 * math.sin(i * 1.3)
            voltage = voltage_levels[step_idx] + noise_v
            current = current_levels[step_idx] + noise_i
            env_temp = 25
            gun_temp = 30 + int(current_levels[step_idx] / 5)
            energy = sum(current_levels[: step_idx + 1]) * 0.1
            power = max(0, voltage * current / 1000)

            payload = build_cmd1_payload(voltage, current, env_temp, gun_temp, energy, power)
            frame = build_frame(1, index, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 1, frame))

        index += 1

    return entries


def scenario_noise(count: int, interval_ms: int) -> List[str]:
    """
    噪声场景（CMD4 - 多通道随机噪声叠加正弦）

    模拟传感器采集的带噪声信号
    """
    import random

    random.seed(42)  # 固定种子保证可重复

    entries = []
    base_time = datetime(2024, 8, 29, 12, 0, 0)

    for i in range(count):
        t = i * interval_ms / 1000.0
        ts = base_time + timedelta(milliseconds=i * interval_ms)

        # 正弦基底 + 高斯噪声
        ch1 = 50.0 + 20.0 * math.sin(t * 1.0) + random.gauss(0, 3)
        ch2 = 30.0 + 15.0 * math.sin(t * 0.5) + random.gauss(0, 2)
        ch3 = 70.0 + 10.0 * math.sin(t * 2.0) + random.gauss(0, 5)
        ch4 = 40.0 + 25.0 * math.sin(t * 0.3) + random.gauss(0, 1)

        # 限制范围在0~100
        ch1 = max(0.01, min(99.99, ch1))
        ch2 = max(0.01, min(99.99, ch2))
        ch3 = max(0.01, min(99.99, ch3))
        ch4 = max(0.01, min(99.99, ch4))

        payload = build_cmd4_payload(ch1, ch2, ch3, ch4)
        frame = build_frame(4, i, payload)
        entries.append(format_log_entry(ts, 1, "Recv", 4, frame))

    return entries


def scenario_all(count: int, interval_ms: int) -> List[str]:
    """
    综合场景 - 所有CMD交替发送

    按 CMD1 → CMD2 → CMD3 → CMD4 循环，模拟真实数据流
    """
    entries = []
    base_time = datetime(2024, 8, 29, 14, 0, 0)

    for i in range(count):
        t = i * interval_ms / 1000.0
        progress = i / max(count - 1, 1)
        ts = base_time + timedelta(milliseconds=i * interval_ms)
        cmd_type = i % 4  # 0=CMD1, 1=CMD2, 2=CMD3, 3=CMD4

        if cmd_type == 0:
            # CMD1 - 正弦+爬坡混合
            voltage = 300.0 + 100.0 * progress + 20.0 * math.sin(t * 0.5)
            current = 80.0 * progress + 10.0 * math.sin(t * 0.7)
            current = max(0, current)
            env_temp = 25 + int(5 * progress)
            gun_temp = 30 + int(15 * progress)
            energy = 50.0 * progress
            power = max(0, voltage * current / 1000)

            payload = build_cmd1_payload(voltage, current, env_temp, gun_temp, energy, power)
            frame = build_frame(1, i, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 1, frame))

        elif cmd_type == 1:
            # CMD2 - 状态渐变
            if progress < 0.1:
                status, mode, switch = 0, 1, 0
            elif progress < 0.9:
                status, mode, switch = 1, 2 if progress > 0.5 else 1, 1
            else:
                status, mode, switch = 0, 1, 0

            payload = build_cmd2_payload(status, mode, switch)
            frame = build_frame(2, i, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 2, frame))

        elif cmd_type == 2:
            # CMD3 - BMS混合
            bms_v = 300.0 + 100.0 * progress
            bms_i = -(80.0 * 4 * progress * (1 - progress))
            soc = int(10 + 80 * progress)
            status = 1 if progress < 0.9 else 0

            payload = build_cmd3_payload(bms_v, bms_i, soc, status, 400.0, -80.0)
            frame = build_frame(3, i, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 3, frame))

        else:
            # CMD4 - 多通道正弦
            ch1 = 50.0 + 30.0 * math.sin(t * 1.0)
            ch2 = 50.0 + 20.0 * math.sin(t * 2.0)
            ch3 = 50.0 + 10.0 * math.sin(t * 0.5)
            ch4 = 50.0 + 25.0 * math.sin(t * 3.0)

            payload = build_cmd4_payload(ch1, ch2, ch3, ch4)
            frame = build_frame(4, i, payload)
            entries.append(format_log_entry(ts, 1, "Recv", 4, frame))

    return entries


# ============== 主程序 ==============

SCENARIOS = {
    "sine": ("正弦波（CMD1+CMD4交替）", scenario_sine),
    "ramp": ("充电爬坡（CMD1+CMD3）", scenario_ramp),
    "step": ("阶跃切换（CMD2+CMD1）", scenario_step),
    "noise": ("噪声信号（CMD4多通道）", scenario_noise),
    "all": ("综合场景（所有CMD交替）", scenario_all),
}


def main():
    parser = argparse.ArgumentParser(
        description="波形测试报文生成器 - 生成wave_test协议的spdlog格式日志",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="all",
        help="波形场景:\n"
        + "\n".join(f"  {k}: {v[0]}" for k, v in SCENARIOS.items()),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="生成报文条数（默认200）",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=500,
        help="报文间隔毫秒（默认500ms）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（默认 input_logs/wave_test.log）",
    )

    args = parser.parse_args()

    # 确定输出路径
    project_root = Path(__file__).parent.parent
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / "input_logs" / "wave_test.log"

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成报文
    desc, generator = SCENARIOS[args.scenario]
    print(f"场景: {desc}")
    print(f"条数: {args.count}")
    print(f"间隔: {args.interval}ms")

    entries = generator(args.count, args.interval)

    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        for entry_text in entries:
            f.write(entry_text)

    file_size = output_path.stat().st_size
    size_str = f"{file_size / 1024:.1f}KB" if file_size > 1024 else f"{file_size}B"
    print(f"输出: {output_path}")
    print(f"大小: {size_str}")
    print(f"完成: {len(entries)} 条报文已生成")


if __name__ == "__main__":
    main()
