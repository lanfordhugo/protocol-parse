"""
文件名称: parse_model.py
内容摘要: 解析业务模型 - 封装日志解析相关的业务逻辑（纯 Python，不依赖 Qt）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-02-08
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParseParams:
    """解析参数"""

    protocol_name: str
    config_path: str
    log_path: str
    filter_settings: Dict[str, Any]


class ParseModel:
    """
    解析业务模型

    职责：
    - 构建解析参数
    - 提供解析相关的业务逻辑

    注意：实际的解析执行在 ParseWorker 中（需要线程），
    本类只负责参数准备和业务判断。
    """

    def build_parse_params(
        self,
        protocol_name: str,
        config_path: str,
        log_path: str,
        filter_settings: Dict[str, Any],
    ) -> ParseParams:
        """
        构建解析参数

        Args:
            protocol_name: 协议名称
            config_path: 配置文件路径
            log_path: 日志文件路径
            filter_settings: 过滤设置

        Returns:
            解析参数对象
        """
        return ParseParams(
            protocol_name=protocol_name,
            config_path=config_path,
            log_path=log_path,
            filter_settings=filter_settings,
        )

    @staticmethod
    def friendly_error_message(error: str) -> str:
        """
        将技术错误信息转换为友好的中文提示

        Args:
            error: 原始错误信息

        Returns:
            友好的中文错误提示
        """
        error_lower = error.lower()

        # 文件相关错误
        if "no such file" in error_lower or "找不到" in error_lower:
            return "日志文件不存在，请检查文件路径是否正确"
        if "permission denied" in error_lower or "拒绝访问" in error_lower:
            return "无法访问文件，请检查文件权限或关闭占用该文件的程序"
        if "encoding" in error_lower or "codec" in error_lower:
            return "文件编码错误，请确保日志文件为 UTF-8 或 GBK 编码"

        # 协议相关错误
        if "protocol" in error_lower and "not found" in error_lower:
            return "协议配置未找到，请检查 configs 目录下是否存在对应的 protocol.yaml"
        if "yaml" in error_lower:
            return "协议配置文件格式错误，请检查 YAML 语法是否正确"
        if "head" in error_lower or "header" in error_lower:
            return "日志格式不匹配，请确认选择了正确的协议"

        # 数据相关错误
        if "no data" in error_lower or "没有数据" in error_lower:
            return "日志文件中没有找到有效的报文数据"
        if "parse" in error_lower or "解析" in error_lower:
            return f"报文解析错误: {error}。请检查日志格式是否与协议匹配"

        # 默认返回原始错误
        return error
