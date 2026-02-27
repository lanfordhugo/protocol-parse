"""
文件名称: can_protocol_parser.py
内容摘要: CAN协议解析器 - 使用YAML配置解析CAN数据组内容，支持过滤和特殊PF码处理
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-26
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from src.can_data_extractor import CanDataGroup
from src.yaml_cmdformat import YamlCmdFormat

logger = logging.getLogger(__name__)

# V6 CAN协议参数列表（用于PF 0x19/0x1C动态解析）
PARA_LIST = [
    "项目类型", "系统类型", "模块类型", "模块总数", "固定模块数",
    "模块负载率", "模块输出率", "降噪模式", "充电枪数", "充电枪类型",
    "BMS类型", "辅源类型", "电表类型", "预留IO", "并充类型",
    "电压校准", "电压校准2", "最大电压", "最大电流", "默认离线功率",
    "绝缘阻值", "最大允许SOC", "充电枪过温", "环境过温", "环境低温",
    "内部过温", "输出过压", "输出欠压", "输出过流", "输入过压",
    "输入欠压", "门禁检测", "输入断路器检测", "输入接触器检测",
    "车辆电池保护", "车辆状态保护", "测试模式", "工作模式", "负载类型",
    "充电输出电压", "充电输出电流", "解锁充电枪", "调试变量1", "调试变量2",
    "手动读取模块信息", "系统风扇调速", "模块风扇调速", "辅源自动恢复",
    "启动自动化测试", "VIN认证充电-后台结果", "取消升级指令", "CCU 复位",
    "实时限功率", "最高电池温度", "输出电压超限保护", "输出电流超限保护",
    "单体电压不变保护", "最高温度不变保护", "恒压停止保护", "需求小停止保护",
    "电压误差超限保护", "电流误差超限保护", "堆功率", "液冷状态",
    "放电最低允许SOC", "充电枪工作模式",
]

# 告警位定义表（20字节 × 8bit = 160个告警位）
ALARM_BIT_LIST = [
    # byte1
    ["急停故障", "输入断路器故障", "直流接触器故障", "输出熔断器故障",
     "充电枪锁故障", "风扇故障", "避雷器故障", "绝缘故障"],
    # byte2
    ["电池反接故障", "控制导引故障", "充电桩过温故障", "充电枪过温故障",
     "充电枪未归位---告警", "BMS通信故障", "输入过压故障", "输入欠压故障"],
    # byte3
    ["直流过压故障", "直流欠压故障", "直流过流故障", "模块故障",
     "模块输入故障---告警", "模块输入过压故障---告警", "模块输入欠压故障---告警", "模块输入缺相故障---告警"],
    # byte4
    ["模块输出短路故障---告警", "模块输出过流故障---告警", "模块输出过压故障---告警", "模块输出欠压故障---告警",
     "模块过温故障---告警", "模块通信故障---告警", "模块风扇故障---告警", "门禁故障"],
    # byte5
    ["绝缘监测告警---告警", "泄放回路故障", "充电桩过温告警---告警", "充电枪过温告警---告警",
     "输入接触器故障", "辅源故障", "中间接触器故障", "控制器复位"],
    # byte6
    ["直流接触器DC+拒动故障", "直流接触器DC+粘连故障", "直流接触器DC-拒动故障", "直流接触器DC-粘连故障",
     "辅源故障（BMS）", "预留", "预留", "预留"],
    # byte7
    ["电网电压高---告警", "电网电压低---告警", "烟感故障", "水浸故障",
     "并充模式,主枪失联", "TCU通信失败", "模块通信故障---所有模块失联", "电表通信故障"],
    # byte8
    ["枪锁故障,解锁失败", "枪锁故障,闭锁失败", "输出短路故障", "协议版本不一致",
     "主枪心跳超时", "日志超限", "桩体倾斜", "预留"],
]


class CanProtocolParser:
    """
    CAN协议解析器

    职责：
    - 使用YamlCmdFormat解析标准PF码数据
    - 处理特殊PF码（0x09对时帧、0x19/0x1C参数列表）
    - 处理告警位信息（PF 0x12/0x13）
    - 支持时间/PF码/板号/方向过滤
    - 输出与现有格式兼容的解析结果
    """

    def __init__(self, yaml_format: YamlCmdFormat) -> None:
        self._yaml_format = yaml_format
        self._should_stop = False

        # 过滤条件
        self._include_pfs: Optional[Set[int]] = None
        self._exclude_pfs: Optional[Set[int]] = None
        self._time_start: Optional[datetime] = None
        self._time_end: Optional[datetime] = None
        self._direction_filter: Optional[str] = None  # "TX" / "RX" / None

        # 进度回调
        self._progress_callback: Optional[Callable[[int, int], None]] = None

        # 性能统计
        self.perf_stats: Dict[str, Any] = {
            "cmd_counts": {},
            "errors": 0,
            "filtered": 0,
            "parsed": 0,
        }

    def set_should_stop(self, stop: bool) -> None:
        """设置停止标志"""
        self._should_stop = stop

    def set_progress_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        """设置进度回调"""
        self._progress_callback = callback

    def set_include_pfs(self, pf_list: List[int]) -> None:
        """设置包含的PF码列表"""
        self._include_pfs = set(pf_list) if pf_list else None

    def set_exclude_pfs(self, pf_list: List[int]) -> None:
        """设置排除的PF码列表"""
        self._exclude_pfs = set(pf_list) if pf_list else None

    def set_time_range(
        self, start: datetime, end: datetime
    ) -> None:
        """设置时间过滤范围"""
        self._time_start = start
        self._time_end = end

    def set_direction_filter(self, direction: Optional[str]) -> None:
        """设置方向过滤"""
        self._direction_filter = direction

    def parse(
        self, data_groups: List[CanDataGroup]
    ) -> List[Dict[str, Any]]:
        """
        解析CAN数据组列表

        Args:
            data_groups: CAN数据组列表

        Returns:
            解析结果字典列表
        """
        results: List[Dict[str, Any]] = []
        total = len(data_groups)

        for i, group in enumerate(data_groups):
            if self._should_stop:
                break

            # 过滤检查
            if not self._should_parse(group):
                self.perf_stats["filtered"] += 1
                continue

            # 解析
            parsed = self._parse_one(group)
            if parsed:
                results.append(parsed)
                self.perf_stats["parsed"] += 1

                # 统计PF码计数
                pf_key = f"0x{group.cmd:02X}"
                self.perf_stats["cmd_counts"][pf_key] = (
                    self.perf_stats["cmd_counts"].get(pf_key, 0) + 1
                )

            if self._progress_callback and i % 100 == 0:
                self._progress_callback(i, total)

        return results

    def _should_parse(self, group: CanDataGroup) -> bool:
        """检查数据组是否通过过滤条件"""
        # PF码过滤
        if self._include_pfs and group.cmd not in self._include_pfs:
            return False
        if self._exclude_pfs and group.cmd in self._exclude_pfs:
            return False

        # 方向过滤
        if self._direction_filter and group.direction != self._direction_filter:
            return False

        # 时间过滤
        if self._time_start or self._time_end:
            try:
                group_time = datetime.strptime(
                    group.time, "%Y-%m-%d %H:%M:%S"
                )
                if self._time_start and group_time < self._time_start:
                    return False
                if self._time_end and group_time > self._time_end:
                    return False
            except ValueError:
                pass  # 时间格式异常时不过滤

        return True

    def _parse_one(self, group: CanDataGroup) -> Optional[Dict[str, Any]]:
        """
        解析单个CAN数据组

        Args:
            group: CAN数据组

        Returns:
            解析结果字典，解析失败返回None
        """
        pf = group.cmd

        # 获取PF名称
        pf_name = self._get_pf_name(pf)

        # 将十六进制字符串转为字节数组
        data_bytes = self._hex_str_to_bytes(group.data)

        # 解析数据内容
        content = None
        try:
            if pf == 0x09:
                content = self._parse_pf_0x09(data_bytes)
            elif pf in (0x19, 0x1C):
                content = self._parse_pf_0x19_0x1c(data_bytes, pf)
            elif pf in (0x12, 0x13):
                content = self._parse_alarm(data_bytes)
            elif self._yaml_format.has_cmd(pf):
                content = self._yaml_format.parse_cmd_data(pf, data_bytes)
            else:
                # 未定义的PF码，显示原始数据
                content = {"原始数据": group.data}
        except Exception as e:
            logger.debug(f"解析PF 0x{pf:02X}失败: {e}")
            self.perf_stats["errors"] += 1
            content = {"解析错误": str(e), "原始数据": group.data}

        return {
            "timestamp": group.time,
            "direction": group.direction,
            "frame_id": group.frame_id,
            "tx_board": group.tx_board,
            "rx_board": group.rx_board,
            "cmd": pf,
            "cmd_name": pf_name,
            "content": content,
        }

    def _get_pf_name(self, pf: int) -> str:
        """获取PF码名称"""
        # 优先从YAML enums中查找
        if hasattr(self._yaml_format, 'config'):
            enums = self._yaml_format.config.enums
            if 'pf_names' in enums:
                pf_names = enums['pf_names']
                if hasattr(pf_names, 'values') and pf in pf_names.values:
                    return pf_names.values[pf]
        return f"PF 0x{pf:02X}"

    @staticmethod
    def _hex_str_to_bytes(hex_str: str) -> bytes:
        """将空格分隔的十六进制字符串转为bytes"""
        if not hex_str or not hex_str.strip():
            return b''
        parts = hex_str.strip().split()
        return bytes(int(h, 16) for h in parts)

    @staticmethod
    def _parse_pf_0x09(data: bytes) -> Dict[str, Any]:
        """
        解析PF 0x09对时帧（特殊逻辑）

        第一个字节=0: 后续7字节为BCD时间
        第一个字节=1: 后续7字节为桩编码ASCII
        """
        if len(data) < 2:
            return {"原始数据": data.hex().upper()}

        msg_type = data[0]
        if msg_type == 0:
            # 时间格式（BCD）
            time_bytes = data[1:8]
            date_parts = []
            date_format = ['', '', '-', '-', ' ', ':', ':']
            for idx, byte in enumerate(time_bytes[:6]):
                if byte < 10:
                    part = f"0{byte:x}"
                else:
                    part = f"{byte:x}"
                date_parts.append(f"{date_format[idx]}{part}")
            time_str = ''.join(date_parts)
            return {"报文种类": "时间", "时间": time_str}
        else:
            # 桩编码（ASCII）
            code_bytes = data[1:8]
            code_str = ''.join(
                chr(b) for b in code_bytes if b != 0
            )
            return {"报文种类": "桩编码", "桩编码": code_str}

    @staticmethod
    def _parse_pf_0x19_0x1c(
        data: bytes, pf: int
    ) -> Dict[str, Any]:
        """
        解析PF 0x19/0x1C参数列表（动态解析）

        格式: 起始索引(1) + 个数(1) + 参数值(每个2字节，小端)
        """
        if len(data) < 2:
            return {"原始数据": data.hex().upper()}

        start_index = data[0]
        para_number = data[1]

        result: Dict[str, Any] = {}
        if pf == 0x19:
            result["设置参数的起始索引"] = start_index
            result["设置参数的个数"] = para_number
        else:
            result["获取参数的起始索引"] = start_index
            result["获取参数的个数"] = para_number

        for i in range(para_number):
            offset = 2 + 2 * i
            if offset + 2 > len(data):
                break
            # 小端合并2字节
            value = data[offset] | (data[offset + 1] << 8)
            # 获取参数名称
            para_idx = start_index + i - 1
            if 0 <= para_idx < len(PARA_LIST):
                para_name = PARA_LIST[para_idx]
            else:
                para_name = f"参数{start_index + i}"
            result[para_name] = value

        return result

    @staticmethod
    def _parse_alarm(data: bytes) -> Dict[str, Any]:
        """
        解析告警位信息（PF 0x12/0x13）

        每个字节的每一位对应一个告警项，
        位值为1表示告警触发
        """
        alarm_list = []
        for byte_idx, byte_val in enumerate(data):
            if byte_idx >= len(ALARM_BIT_LIST):
                break
            for bit_idx, alarm_name in enumerate(ALARM_BIT_LIST[byte_idx]):
                if byte_val & (1 << bit_idx):
                    alarm_list.append(alarm_name)

        return {"告警位信息": alarm_list if alarm_list else ["无告警"]}
