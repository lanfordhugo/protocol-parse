"""
文件名称: __init__.py
内容摘要: View 接口模块 - MVP 架构的 View 层接口定义
当前版本: v1.0.0
作者: lanford
创建日期: 2026-01-29
"""

# 导出所有 View 接口
from .i_protocol_panel_view import IProtocolPanelView
from .i_detail_panel_view import IDetailPanelView
from .i_log_panel_view import ILogPanelView
from .i_normal_parse_page_view import INormalParsePageView

__all__ = [
    'IProtocolPanelView',
    'IDetailPanelView',
    'ILogPanelView',
    'INormalParsePageView',
]
