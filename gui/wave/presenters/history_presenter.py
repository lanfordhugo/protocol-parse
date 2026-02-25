"""
文件名称: history_presenter.py
内容摘要: 历史波形 Presenter，处理静态数据的波形分析逻辑
当前版本: v1.0.0
作者: lanford
创建日期: 2026-02-09
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gui.wave.models.wave_data_manager import WaveDataManager
from gui.wave.presenters.wave_presenter_base import WavePresenterBase
from gui.wave.views.i_wave_view import IHistoryWaveView

logger = logging.getLogger(__name__)


class HistoryWavePresenter(WavePresenterBase):
    """
    历史波形 Presenter

    职责：
    - 加载 TCP 服务端的缓存数据或导入文件
    - 提供时间范围选择
    - 数据导出（JSON/CSV）

    数据流：
    TcpServerModel.all_entries → load_from_entries() → WaveDataManager
    导入文件 → import_data() → WaveDataManager
    时间范围变化 → on_time_range_changed() → View.update_all_chart_data()
    """

    def __init__(
        self,
        view: IHistoryWaveView,
        data_manager: WaveDataManager,
        protocol_config: Optional[Any] = None,
    ):
        """
        初始化历史波形 Presenter

        Args:
            view: 历史波形 View 接口
            data_manager: 波形数据管理器
            protocol_config: 协议配置对象（YamlCmdFormat），用于解析log文件
        """
        super().__init__(view=view, data_manager=data_manager)
        self._protocol_config = protocol_config

    # ============== 数据加载 ==============

    def load_from_entries(
        self,
        entries: List[Tuple[str, Optional[Dict[str, Any]], Optional[int], Optional[str]]],
    ) -> int:
        """
        从解析条目列表加载数据

        Args:
            entries: 列表，每项为 (timestamp_str, parsed_content, cmd_id, direction)

        Returns:
            成功加载的数据点数量
        """
        # 历史加载模式：记录所有字段
        self._data_manager.set_record_all(True)
        count = self._data_manager.add_entries(entries)

        if count > 0:
            self._setup_after_load()

        self._view.update_status(f"已加载 {count} 个数据点")
        logger.info("历史数据加载完成: %d 个数据点", count)
        return count

    def load_from_log_file(self, log_file_path: str) -> int:
        """
        从 .log 文件加载并解析波形数据

        使用 LogEntryParser 解析log文件，再用协议配置解析每条报文。

        Args:
            log_file_path: 日志文件路径

        Returns:
            成功加载的数据点数量
        """
        if not self._protocol_config:
            self._view.update_status("未加载协议配置，无法解析日志文件")
            return 0

        if not Path(log_file_path).exists():
            self._view.update_status(f"文件不存在: {log_file_path}")
            return 0

        try:
            from tcp_log.log_entry_parser import LogEntryParser

            log_entries = LogEntryParser.parse_file(log_file_path)
            if not log_entries:
                self._view.update_status("日志文件为空或格式不匹配")
                return 0

            config = self._protocol_config.config
            entries_data = []

            for entry in log_entries:
                try:
                    hex_str = entry.hex_data.replace(" ", "")
                    if not hex_str:
                        continue
                    byte_data = bytes.fromhex(hex_str)
                    if len(byte_data) <= config.head_len:
                        continue

                    tail = config.tail_len
                    content = (
                        byte_data[config.head_len:-tail]
                        if tail > 0
                        else byte_data[config.head_len:]
                    )
                    parsed = self._protocol_config.parse_cmd_data(
                        entry.cmd_id, content
                    )
                    if parsed:
                        entries_data.append((
                            entry.timestamp,
                            parsed,
                            entry.cmd_id,
                            entry.direction,
                        ))
                except Exception as e:
                    logger.debug("解析报文失败(cmd=%s): %s", entry.cmd_id, e)
                    continue

            if not entries_data:
                self._view.update_status("无法解析任何报文，请检查协议配置")
                return 0

            count = self.load_from_entries(entries_data)
            file_name = Path(log_file_path).name
            self._view.update_status(
                f"已从 {file_name} 加载 {count} 个数据点"
                f"（共 {len(log_entries)} 条报文）"
            )
            return count

        except Exception as e:
            logger.error("加载log文件失败: %s", e)
            self._view.update_status(f"加载失败: {e}")
            return 0

    def import_from_json(self, file_path: str) -> int:
        """
        从 JSON 文件导入数据

        Args:
            file_path: 文件路径

        Returns:
            导入的数据点数量
        """
        try:
            # 历史加载模式：记录所有字段
            self._data_manager.set_record_all(True)
            count = self._data_manager.import_from_json(file_path)
            if count > 0:
                self._setup_after_load()
            self._view.update_status(f"已从 JSON 导入 {count} 个数据点")
            return count
        except Exception as e:
            logger.error("JSON 导入失败: %s", e)
            self._view.update_status(f"导入失败: {e}")
            return 0

    def _setup_after_load(self) -> None:
        """数据加载后的初始化"""
        # 设置时间范围
        time_range = self._data_manager.time_range
        if time_range:
            start, end = time_range
            self._view_start = start
            self._view_end = end
            self._view.set_time_range_limits(
                start.timestamp(), end.timestamp()
            )

        # 历史模式：所有字段默认启用显示
        configs = self._data_manager.get_all_field_configs()
        for config in configs:
            config.enabled = True
            self._data_manager.update_field_enabled(config.field_path, True)

        # 刷新字段树
        self._view.refresh_field_tree(configs)

        # 为每个可绘图字段添加到图表
        for config in configs:
            self._view.add_chart_field(config)

        # 刷新图表
        self.refresh_all_charts()

        # 启用导出
        self._view.set_export_enabled(self._data_manager.data_count > 0)

