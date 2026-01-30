"""
文件名称: light_theme.py
内容摘要: GUI 浅色主题样式表
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

# 浅色主题
# 浅色主题
LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #333333;
}

QGroupBox {
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #0066cc;
}

QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 6px;
    color: #333333;
    selection-background-color: #cce5ff;
}

QLineEdit:focus {
    border: 1px solid #0066cc;
}

QLineEdit:disabled {
    background-color: #e8e8e8;
    color: #999999;
}

QListWidget {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    color: #333333;
    outline: none;
}

QListWidget::item {
    padding: 6px;
    border-radius: 2px;
}

QListWidget::item:selected {
    background-color: #0066cc;
    color: #ffffff;
}

QListWidget::item:hover {
    background-color: #e8e8e8;
}

QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    padding: 6px 16px;
    color: #333333;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #d0d0d0;
    border: 1px solid #b0b0b0;
}

QPushButton:pressed {
    background-color: #c0c0c0;
}

QPushButton:disabled {
    background-color: #e8e8e8;
    color: #999999;
    border: 1px solid #d0d0d0;
}

QCheckBox {
    color: #333333;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #c0c0c0;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #0066cc;
    border: 1px solid #0066cc;
}

QCheckBox::indicator:hover {
    border: 1px solid #0066cc;
}

QLabel {
    color: #333333;
}

QTextEdit {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    color: #333333;
    font-family: Consolas, 'Courier New', monospace;
}

QProgressBar {
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background-color: #e8e8e8;
    text-align: center;
    color: #333333;
}

QProgressBar::chunk {
    background-color: #0066cc;
    border-radius: 3px;
}

QStatusBar {
    background-color: #0066cc;
    color: #ffffff;
}

QMenuBar {
    background-color: #f0f0f0;
    color: #333333;
    border-bottom: 1px solid #d0d0d0;
}

QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    color: #333333;
}

QMenu::item {
    padding: 6px 30px 6px 20px;
}

QMenu::item:selected {
    background-color: #0066cc;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #d0d0d0;
    margin: 4px 0;
}

QSplitter::handle {
    background-color: #d0d0d0;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QScrollBar:vertical {
    background-color: #f5f5f5;
    width: 12px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f5f5f5;
    height: 12px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QSpinBox {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px;
    color: #333333;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #e0e0e0;
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #d0d0d0;
}

QCalendarWidget {
    background-color: #ffffff;
}

QCalendarWidget QToolButton {
    color: #333333;
    background-color: #e0e0e0;
    border-radius: 4px;
    padding: 4px;
}

QCalendarWidget QToolButton:hover {
    background-color: #d0d0d0;
}

QCalendarWidget QMenu {
    background-color: #ffffff;
    color: #333333;
}

QCalendarWidget QSpinBox {
    background-color: #ffffff;
    color: #333333;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    color: #333333;
    selection-background-color: #0066cc;
    selection-color: #ffffff;
}

QFrame {
    border: none;
}

QDialog {
    background-color: #f5f5f5;
    color: #333333;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""

