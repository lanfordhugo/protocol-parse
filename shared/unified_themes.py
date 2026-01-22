"""
文件名称: unified_themes.py
内容摘要: 统一主题系统（合并 gui/themes.py 和 tcp_log/themes.py）
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-10
"""

from tcp_log.themes import get_theme as get_tcp_theme


def get_unified_theme(theme_name: str) -> str:
    """获取统一主题样式表

    Args:
        theme_name: 主题名称 ('dark' 或 'light')

    Returns:
        完整的样式表字符串
    """
    # 基础主题（使用 tcp_log/themes.py，因为它更完整）
    base_theme = get_tcp_theme(theme_name)

    # 添加侧边栏导航样式
    sidebar_style = """
    /* === 侧边栏容器 === */
    #sidebar_container {
        background-color: #1a1a2e;
        border-right: 1px solid #3a3a5e;
    }

    /* === 侧边栏标题 === */
    #sidebar_title QLabel {
        color: #e8e8e8;
    }

    /* === 侧边栏分组框 === */
    #sidebar_container QGroupBox {
        border: 1px solid #3a3a5e;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: bold;
        color: #a8b4ce;
    }

    #sidebar_container QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
    }

    /* === 导航按钮样式 === */
    QWidget#nav_普通解析,
    QWidget#nav_TCP服务端 {
        background-color: transparent;
        border-radius: 6px;
        border: 2px solid transparent;
        margin: 4px;
    }

    QWidget#nav_普通解析:hover,
    QWidget#nav_TCP服务端:hover {
        background-color: #252a48;
        border-color: #3a3a5e;
    }

    QWidget#nav_普通解析[selected="true"],
    QWidget#nav_TCP服务端[selected="true"] {
        background-color: #3a4070;
        border-color: #6c8cd5;
    }

    QWidget#nav_普通解析[selected="true"] QLabel,
    QWidget#nav_TCP服务端[selected="true"] QLabel {
        color: #ffffff;
    }

    /* === 版本信息 === */
    #version_label {
        color: #888;
        background-color: transparent;
    }
    """

    return base_theme + sidebar_style
