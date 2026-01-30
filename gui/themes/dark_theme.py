"""
文件名称: dark_theme.py
内容摘要: GUI 深色主题样式表
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

# 深色主题样式表
DARK_THEME = """

QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #569cd6;
}

QLineEdit {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 6px;
    color: #d4d4d4;
    selection-background-color: #264f78;
}

QLineEdit:focus {
    border: 1px solid #569cd6;
}

QLineEdit:disabled {
    background-color: #252525;
    color: #6d6d6d;
}

QListWidget {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #d4d4d4;
    outline: none;
}

QListWidget::item {
    padding: 6px;
    border-radius: 2px;
}

QListWidget::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QListWidget::item:hover {
    background-color: #2a2d2e;
}

QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #4c4c4c;
    border-radius: 4px;
    padding: 6px 16px;
    color: #d4d4d4;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #4c4c4c;
    border: 1px solid #5c5c5c;
}

QPushButton:pressed {
    background-color: #2d2d2d;
}

QPushButton:disabled {
    background-color: #2d2d2d;
    color: #6d6d6d;
    border: 1px solid #3c3c3c;
}

QCheckBox {
    color: #d4d4d4;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    background-color: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #569cd6;
    border: 1px solid #569cd6;
}

QCheckBox::indicator:hover {
    border: 1px solid #569cd6;
}

QLabel {
    color: #d4d4d4;
}

QTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #d4d4d4;
    font-family: Consolas, 'Courier New', monospace;
}

QProgressBar {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    background-color: #2d2d2d;
    text-align: center;
    color: #d4d4d4;
}

QProgressBar::chunk {
    background-color: #569cd6;
    border-radius: 3px;
}

QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}

QMenuBar {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border-bottom: 1px solid #3c3c3c;
}

QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
}

QMenuBar::item:selected {
    background-color: #3c3c3c;
}

QMenu {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    color: #d4d4d4;
}

QMenu::item {
    padding: 6px 30px 6px 20px;
}

QMenu::item:selected {
    background-color: #094771;
}

QMenu::separator {
    height: 1px;
    background-color: #3c3c3c;
    margin: 4px 0;
}

QSplitter::handle {
    background-color: #3c3c3c;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #3c3c3c;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4c4c4c;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #3c3c3c;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4c4c4c;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QSpinBox {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 4px;
    color: #d4d4d4;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #3c3c3c;
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #4c4c4c;
}

QCalendarWidget {
    background-color: #2d2d2d;
}

QCalendarWidget QToolButton {
    color: #d4d4d4;
    background-color: #3c3c3c;
    border-radius: 4px;
    padding: 4px;
}

QCalendarWidget QToolButton:hover {
    background-color: #4c4c4c;
}

QCalendarWidget QMenu {
    background-color: #2d2d2d;
    color: #d4d4d4;
}

QCalendarWidget QSpinBox {
    background-color: #2d2d2d;
    color: #d4d4d4;
}

QCalendarWidget QAbstractItemView {
    background-color: #252526;
    color: #d4d4d4;
    selection-background-color: #094771;
    selection-color: #ffffff;
}

QFrame {
    border: none;
}

QDialog {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""


