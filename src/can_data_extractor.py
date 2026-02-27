"""
文件名称: can_data_extractor.py
内容摘要: CAN总线数据提取器 - 从TCU日志或CSV文件中提取并结构化CAN帧数据
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
"""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# MCU板地址阈值
MCU_ADDR_THRESHOLD = 0x64
# 广播地址
BROADCAST_ADDR = 0x40


@dataclass
class CanFrame:
    """CAN帧数据结构"""

    time: str
    direction: str
    frame_id: str
    tx_board: str
    rx_board: str
    pf: int
    long_frame: bool
    data: str


@dataclass
class CanDataGroup:
    """CAN数据组（长帧合并后的最终数据单元）"""

    time: str
    direction: str
    frame_id: str
    tx_board: str
    rx_board: str
    cmd: int  # PF码，等价于cmd_id
    data: str  # 空格分隔的十六进制字符串


class CanDataExtractor:
    """
    CAN总线数据提取器

    支持两种输入格式：
    1. TCU日志: [timestamp] TX/RX:0xFrameID,DataLen,HexData
    2. CSV: 序号,方向,时间,名称,帧ID,帧格式,帧类型,数据长度,数据(HEX)

    职责：
    - 逐行解析CAN帧
    - 从帧ID解码PF码、源板、目标板
    - 处理长帧合并
    - 输出统一的 CanDataGroup 列表
    """

    # TCU日志行正则：[2021-07-02 11:11:50.392] TX:0x10106401,8,30 01 00 00 ...
    # 兼容格式：] ,RX: 和 ] RX:（逗号可选）
    _LOG_PATTERN = re.compile(
        r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'  # 时间戳（不含毫秒）
        r'[^\]]*\]\s*,?\s*'                              # 毫秒部分、右括号、可选逗号
        r'(TX|RX):'                                      # 方向
        r'(0x[0-9A-Fa-f]+),'                             # 帧ID
        r'(\d+),'                                        # 数据长度
        r'(.+)'                                          # 数据
    )

    def __init__(self) -> None:
        self._progress_callback: Optional[Callable[[int, int], None]] = None

    def set_progress_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        """设置进度回调"""
        self._progress_callback = callback

    def extract(
        self, file_path: str, is_csv: bool = False
    ) -> List[CanDataGroup]:
        """
        从文件提取CAN数据组

        Args:
            file_path: 日志文件路径
            is_csv: 是否为CSV格式

        Returns:
            合并长帧后的CAN数据组列表
        """
        logger.info(f"开始提取CAN数据: {file_path} (CSV={is_csv})")

        if is_csv:
            frames = self._load_csv_file(file_path)
        else:
            frames = self._load_log_file(file_path)

        logger.info(f"提取到 {len(frames)} 个CAN帧")

        # 合并长帧
        merged = self._merge_long_frames(frames)
        logger.info(f"长帧合并后剩余 {len(merged)} 个数据组")

        return merged

    def detect_file_format(self, file_path: str) -> bool:
        """
        自动检测文件格式

        Args:
            file_path: 文件路径

        Returns:
            True=CSV格式, False=TCU日志格式
        """
        path = Path(file_path)
        suffix = path.suffix.upper()
        if suffix == '.CSV':
            return True

        # 读取前几行判断
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for _ in range(5):
                    line = f.readline().strip()
                    if not line:
                        continue
                    # CSV首行通常包含"序号"
                    if '序号' in line and ',' in line:
                        return True
                    # TCU日志以 [ 开头
                    if line.startswith('['):
                        return False
        except Exception:
            pass

        return suffix == '.CSV'

    # ============== 内部方法 ==============

    def _load_log_file(self, file_path: str) -> List[CanFrame]:
        """
        解析TCU日志文件

        格式: [2021-07-02 11:11:50.392] TX:0x10106401,8,30 01 00 00 ...
        """
        frames: List[CanFrame] = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                lines = f.readlines()

        total = len(lines)
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 跳过非日志行（不以 [19 或 [20 开头）
            if len(line) < 3 or line[:3] not in ('[19', '[20'):
                continue

            # 跳过MCU已解析的行
            if 'LRX' in line:
                continue

            frame = self._parse_log_line(line)
            if frame:
                frames.append(frame)

            if self._progress_callback and i % 1000 == 0:
                self._progress_callback(i, total)

        return frames

    def _parse_log_line(self, line: str) -> Optional[CanFrame]:
        """解析单行TCU日志"""
        match = self._LOG_PATTERN.match(line)
        if not match:
            return None

        time_str = match.group(1)
        direction = match.group(2)
        frame_id_str = match.group(3)
        data_len = int(match.group(4))
        data_str = match.group(5).strip()

        # 截取实际数据长度（每字节占3个字符：两位hex + 空格）
        data_str = data_str[:data_len * 3 - 1]

        frame_id = int(frame_id_str, 16)
        pf, tx_board, rx_board, long_frame = self._decode_frame_id(frame_id)

        return CanFrame(
            time=time_str,
            direction=direction,
            frame_id=frame_id_str,
            tx_board=tx_board,
            rx_board=rx_board,
            pf=pf,
            long_frame=long_frame,
            data=data_str,
        )

    def _load_csv_file(self, file_path: str) -> List[CanFrame]:
        """
        解析CSV文件

        格式: 序号,方向,时间,名称,帧ID,帧格式,帧类型,数据长度,数据(HEX)
        """
        frames: List[CanFrame] = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                lines = f.readlines()

        total = len(lines)
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')

            # 跳过表头和配置行
            if (
                len(parts) < 9
                or parts[0] == '序号'
                or line.startswith('start')
                or line.startswith('end')
                or line.startswith('pf')
            ):
                continue

            frame = self._parse_csv_line(parts)
            if frame:
                frames.append(frame)

            if self._progress_callback and i % 1000 == 0:
                self._progress_callback(i, total)

        return frames

    def _parse_csv_line(self, parts: List[str]) -> Optional[CanFrame]:
        """解析单行CSV"""
        try:
            direction = parts[1].strip()
            # CSV时间只有时分秒，补充当天日期
            time_str = (
                time.strftime("%Y-%m-%d") + ' ' + parts[2].strip()[:8]
            )
            frame_id_str = parts[4].strip()
            data_str = parts[8].strip()

            frame_id = int(frame_id_str, 16)
            pf, tx_board, rx_board, long_frame = self._decode_frame_id(
                frame_id
            )

            return CanFrame(
                time=time_str,
                direction=direction,
                frame_id=frame_id_str,
                tx_board=tx_board,
                rx_board=rx_board,
                pf=pf,
                long_frame=long_frame,
                data=data_str,
            )
        except (ValueError, IndexError) as e:
            logger.debug(f"CSV行解析失败: {e}")
            return None

    @staticmethod
    def _decode_frame_id(
        frame_id: int,
    ) -> Tuple[int, str, str, bool]:
        """
        解码CAN帧ID

        帧ID结构（32位）:
        - bit16-23: PF码（bit7为长帧标志）
        - bit8-15: 目标板地址
        - bit0-7: 源板地址

        Args:
            frame_id: 32位帧ID整数

        Returns:
            (pf码, 源板名称, 目标板名称, 是否长帧)
        """
        pf = (frame_id >> 16) & 0xFF
        rx_addr = (frame_id >> 8) & 0xFF
        tx_addr = frame_id & 0xFF

        # 长帧检测：PF码的bit7
        long_frame = bool(pf & 0x80)
        if long_frame:
            pf = pf & 0x7F  # 清除bit7

        tx_board = CanDataExtractor._addr_to_name(tx_addr)
        rx_board = CanDataExtractor._addr_to_name(rx_addr)

        return pf, tx_board, rx_board, long_frame

    @staticmethod
    def _addr_to_name(addr: int) -> str:
        """
        板地址转名称

        规则:
        - >= 0x64: MCU
        - == 0x40: 广播
        - 其他: N号CCU
        """
        if addr >= MCU_ADDR_THRESHOLD:
            return "MCU"
        elif addr == BROADCAST_ADDR:
            return "广播"
        else:
            return f"{addr:x}号CCU"

    @staticmethod
    def _merge_long_frames(
        frames: List[CanFrame],
    ) -> List[CanDataGroup]:
        """
        合并长帧并转换为数据组

        长帧合并规则：
        - 长帧的data第一个字节表示总帧数
        - 从第2帧开始拼接data（跳过每帧的第一个字节序号）
        - 当收集到足够帧数时完成合并
        - 合并后数据跳过前9字节的附加信息
        """
        result: List[CanDataGroup] = []
        long_frame_buffer: str = ''
        long_frame_count: int = 0
        long_frame_ref: Optional[CanFrame] = None

        for frame in frames:
            if not frame.long_frame:
                # 普通帧直接转换
                result.append(CanDataGroup(
                    time=frame.time,
                    direction=frame.direction,
                    frame_id=frame.frame_id,
                    tx_board=frame.tx_board,
                    rx_board=frame.rx_board,
                    cmd=frame.pf,
                    data=frame.data,
                ))
                continue

            # 长帧处理
            long_frame_count += 1
            # 跳过第一个字节（序号），拼接剩余数据
            parts = frame.data.split(' ', 1)
            if len(parts) > 1:
                long_frame_buffer += parts[1] + ' '

            if not long_frame_ref:
                long_frame_ref = frame

            # 检查是否收集完毕
            if long_frame_buffer.strip():
                hex_parts = long_frame_buffer.strip().split()
                if hex_parts:
                    try:
                        total_frames = int(hex_parts[0], 16)
                        if long_frame_count >= total_frames:
                            # 合并完成，跳过前3字节的长帧头信息
                            # 与V6源码 real_data_str[9:] 等价（9字符=3字节）
                            all_bytes = long_frame_buffer.strip().split()
                            if len(all_bytes) > 3:
                                effective_data = ' '.join(all_bytes[3:])
                            else:
                                effective_data = ' '.join(all_bytes)

                            result.append(CanDataGroup(
                                time=long_frame_ref.time,
                                direction=long_frame_ref.direction,
                                frame_id=long_frame_ref.frame_id,
                                tx_board=long_frame_ref.tx_board,
                                rx_board=long_frame_ref.rx_board,
                                cmd=long_frame_ref.pf,
                                data=effective_data,
                            ))

                            # 重置缓冲区
                            long_frame_buffer = ''
                            long_frame_count = 0
                            long_frame_ref = None
                    except ValueError:
                        pass

        return result
