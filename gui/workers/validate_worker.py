"""
文件名称: validate_worker.py
内容摘要: 后台配置校验工作线程
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-24
"""

from typing import List, Tuple
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot


class ValidateWorker(QObject):
    """后台配置校验工作线程"""

    # 信号：单个协议校验完成 (protocol_name, is_valid, errors, warnings)
    protocol_validated = Signal(str, bool, list, list)
    # 信号：所有校验完成
    all_finished = Signal()

    def __init__(self, protocols: List[Tuple[str, str]]) -> None:
        """
        初始化校验工作线程

        Args:
            protocols: 协议列表 [(protocol_name, config_path), ...]
        """
        super().__init__()
        self._protocols = protocols
        self._should_stop = False

    def stop(self) -> None:
        """请求停止"""
        self._should_stop = True

    @Slot()
    def run(self) -> None:
        """执行校验任务"""
        try:
            from src.validate_configs import ConfigValidator
            validator = ConfigValidator()

            for protocol_name, config_path in self._protocols:
                if self._should_stop:
                    break

                is_valid = validator.validate_protocol_config(Path(config_path))
                errors = list(validator.errors)
                warnings = list(validator.warnings)

                self.protocol_validated.emit(
                    protocol_name, is_valid, errors, warnings
                )
        except Exception as e:
            # 如果导入失败，逐个标记为未知状态
            for protocol_name, _ in self._protocols:
                if self._should_stop:
                    break
                self.protocol_validated.emit(protocol_name, True, [], [str(e)])

        self.all_finished.emit()
