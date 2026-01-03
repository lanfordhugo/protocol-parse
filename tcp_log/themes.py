"""
文件名称: themes.py
内容摘要: TCP Log 工具主题样式定义
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

# 深色主题 - 现代暗色设计
DARK_THEME = """
/* === 全局样式 === */
QMainWindow {
    background-color: #1a1a2e;
}

QWidget {
    background-color: #1a1a2e;
    color: #e8e8e8;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}

/* === 分组框 === */
QGroupBox {
    border: 1px solid #3a3a5e;
    border-radius: 6px;
    margin-top: 10px;
    font-weight: bold;
    font-size: 12px;
    color: #a8b4ce;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 8px;
    color: #6c8cd5;
}

/* === 输入控件 === */
QLineEdit, QSpinBox {
    background-color: #16213e;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    padding: 6px 10px;
    color: #e8e8e8;
    selection-background-color: #4a5fad;
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #6c8cd5;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #252a48;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3a3a5e;
}

/* === 下拉框 === */
QComboBox {
    background-color: #16213e;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    padding: 6px 10px;
    color: #e8e8e8;
    min-height: 20px;
}

QComboBox:focus {
    border-color: #6c8cd5;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    background-color: #252a48;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #a8b4ce;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    selection-background-color: #4a5fad;
    color: #e8e8e8;
}

/* === 按钮 === */
QPushButton {
    background-color: #3a4070;
    border: 1px solid #4a5080;
    border-radius: 4px;
    padding: 6px 16px;
    color: #ffffff;
    font-weight: 500;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #4a5090;
    border-color: #6c8cd5;
}

QPushButton:pressed {
    background-color: #2a3060;
}

QPushButton:disabled {
    background-color: #2a2a4e;
    color: #8888aa;
    border-color: #3a3a5e;
}

/* === 复选框 === */
QCheckBox {
    color: #e8e8e8;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 2px solid #6c8cd5;
    border-radius: 2px;
    background-color: #0f0f23;
}

QCheckBox::indicator:checked {
    background-color: #6c8cd5;
    border-color: #6c8cd5;
}

QCheckBox::indicator:unchecked {
    background-color: #0f0f23;
    border-color: #6c8cd5;
}

QCheckBox::indicator:hover {
    border-color: #6c8cd5;
}

/* === 文本编辑框 === */
QTextEdit {
    background-color: #0f0f23;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    padding: 8px;
    color: #e8e8e8;
    selection-background-color: #4a5fad;
}

/* === 表格 === */
QTableWidget {
    background-color: #0f0f23;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    gridline-color: #252a48;
    color: #e8e8e8;
    alternate-background-color: #16213e;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #252a48;
}

QTableWidget::item:selected {
    background-color: #4a5fad;
}

QHeaderView::section {
    background-color: #252a48;
    color: #a8b4ce;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #6c8cd5;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #3a3a5e;
}

/* === 进度条 === */
QProgressBar {
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    background-color: #16213e;
    text-align: center;
    color: #e8e8e8;
    min-height: 20px;
    max-height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                stop:0 #4a5fad, stop:1 #6c8cd5);
    border-radius: 3px;
}

/* === 滚动条 === */
QScrollBar:vertical {
    background-color: #16213e;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3a3a5e;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4a5fad;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #16213e;
    height: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #3a3a5e;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4a5fad;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === 菜单栏 === */
QMenuBar {
    background-color: #1a1a2e;
    color: #e8e8e8;
    border-bottom: 1px solid #3a3a5e;
    padding: 4px;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #252a48;
}

QMenu {
    background-color: #1a1a2e;
    color: #e8e8e8;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #4a5fad;
}

QMenu::separator {
    height: 1px;
    background-color: #3a3a5e;
    margin: 4px 8px;
}

/* === 状态栏 === */
QStatusBar {
    background-color: #16213e;
    color: #a8b4ce;
    border-top: 1px solid #3a3a5e;
}

/* === 分割器 === */
QSplitter::handle {
    background-color: #3a3a5e;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:horizontal {
    width: 4px;
}

/* === 标签 === */
QLabel {
    color: #e8e8e8;
}

/* === 工具提示 === */
QToolTip {
    background-color: #252a48;
    color: #e8e8e8;
    border: 1px solid #3a3a5e;
    border-radius: 4px;
    padding: 4px 8px;
}
"""

# 浅色主题 - 清新明亮设计
LIGHT_THEME = """
/* === 全局样式 === */
QMainWindow {
    background-color: #f5f7fa;
}

QWidget {
    background-color: #f5f7fa;
    color: #2c3e50;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}

/* === 分组框 === */
QGroupBox {
    border: 1px solid #d4dce8;
    border-radius: 6px;
    margin-top: 10px;
    font-weight: bold;
    font-size: 12px;
    color: #5a6c7e;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 8px;
    color: #3b82f6;
}

/* === 输入控件 === */
QLineEdit, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    padding: 6px 10px;
    color: #2c3e50;
    selection-background-color: #93c5fd;
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #3b82f6;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #e8ecf2;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #d4dce8;
}

/* === 下拉框 === */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    padding: 6px 10px;
    color: #2c3e50;
    min-height: 20px;
}

QComboBox:focus {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    background-color: #e8ecf2;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #5a6c7e;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    selection-background-color: #93c5fd;
    color: #2c3e50;
}

/* === 按钮 === */
QPushButton {
    background-color: #e8ecf2;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    padding: 6px 16px;
    color: #2c3e50;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #d4dce8;
    border-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #c4d0e0;
}

QPushButton:disabled {
    background-color: #f5f7fa;
    color: #a0aec0;
    border-color: #e8ecf2;
}

/* === 复选框 === */
QCheckBox {
    color: #2c3e50;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 2px solid #3b82f6;
    border-radius: 2px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
}

QCheckBox::indicator:unchecked {
    background-color: #ffffff;
    border-color: #3b82f6;
}

QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

/* === 文本编辑框 === */
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    padding: 8px;
    color: #2c3e50;
    selection-background-color: #93c5fd;
}

/* === 表格 === */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    gridline-color: #e8ecf2;
    color: #2c3e50;
    alternate-background-color: #f8fafc;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #e8ecf2;
}

QTableWidget::item:selected {
    background-color: #93c5fd;
    color: #1e3a5f;
}

QHeaderView::section {
    background-color: #e8ecf2;
    color: #5a6c7e;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #3b82f6;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #d4dce8;
}

/* === 进度条 === */
QProgressBar {
    border: 1px solid #d4dce8;
    border-radius: 4px;
    background-color: #e8ecf2;
    text-align: center;
    color: #2c3e50;
    min-height: 20px;
    max-height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                stop:0 #3b82f6, stop:1 #60a5fa);
    border-radius: 3px;
}

/* === 滚动条 === */
QScrollBar:vertical {
    background-color: #f5f7fa;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #d4dce8;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #93c5fd;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f5f7fa;
    height: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #d4dce8;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #93c5fd;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === 菜单栏 === */
QMenuBar {
    background-color: #ffffff;
    color: #2c3e50;
    border-bottom: 1px solid #d4dce8;
    padding: 4px;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #e8ecf2;
}

QMenu {
    background-color: #ffffff;
    color: #2c3e50;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #93c5fd;
}

QMenu::separator {
    height: 1px;
    background-color: #d4dce8;
    margin: 4px 8px;
}

/* === 状态栏 === */
QStatusBar {
    background-color: #ffffff;
    color: #5a6c7e;
    border-top: 1px solid #d4dce8;
}

/* === 分割器 === */
QSplitter::handle {
    background-color: #d4dce8;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:horizontal {
    width: 4px;
}

/* === 标签 === */
QLabel {
    color: #2c3e50;
}

/* === 工具提示 === */
QToolTip {
    background-color: #ffffff;
    color: #2c3e50;
    border: 1px solid #d4dce8;
    border-radius: 4px;
    padding: 4px 8px;
}
"""


def get_theme(theme_name: str) -> str:
    """获取主题样式表
    
    Args:
        theme_name: 主题名称，'dark' 或 'light'
    
    Returns:
        主题样式表字符串
    """
    if theme_name == "dark":
        return DARK_THEME
    elif theme_name == "light":
        return LIGHT_THEME
    else:
        return DARK_THEME
