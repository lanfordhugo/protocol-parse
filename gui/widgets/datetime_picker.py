# gui/widgets/datetime_picker.py
"""
文件名称: datetime_picker.py
内容摘要: 日期时间选择器组件，支持精确到秒的时间选择
当前版本: v1.0.0
作者: lanford
创建日期: 2024-12-24
"""

from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QDialog,
    QCalendarWidget, QSpinBox, QLabel, QLineEdit, QDialogButtonBox,
    QGroupBox, QGridLayout
)
from PySide6.QtCore import Signal, Qt, QDate, QDateTime
from PySide6.QtGui import QFont


class TimeSpinBox(QSpinBox):
    """时间数值选择框（带前导零）"""
    
    def __init__(self, max_value: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setRange(0, max_value)
        self.setWrapping(True)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(50)
    
    def textFromValue(self, value: int) -> str:
        return f"{value:02d}"


class DateTimePickerDialog(QDialog):
    """日期时间选择对话框"""
    
    def __init__(
        self,
        initial_datetime: Optional[datetime] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("选择日期和时间")
        self.setModal(True)
        self.setMinimumWidth(350)
        
        if initial_datetime is None:
            initial_datetime = datetime.now()
        
        self._setup_ui(initial_datetime)
    
    def _setup_ui(self, initial_dt: datetime):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 日历
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate(
            initial_dt.year, initial_dt.month, initial_dt.day
        ))
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        
        # 时间选择区域
        time_group = QGroupBox("时间")
        time_layout = QHBoxLayout(time_group)
        time_layout.setAlignment(Qt.AlignCenter)
        
        # 时
        self.hour_spin = TimeSpinBox(23)
        self.hour_spin.setValue(initial_dt.hour)
        time_layout.addWidget(QLabel("时:"))
        time_layout.addWidget(self.hour_spin)
        
        time_layout.addWidget(QLabel(" : "))
        
        # 分
        self.minute_spin = TimeSpinBox(59)
        self.minute_spin.setValue(initial_dt.minute)
        time_layout.addWidget(QLabel("分:"))
        time_layout.addWidget(self.minute_spin)
        
        time_layout.addWidget(QLabel(" : "))
        
        # 秒
        self.second_spin = TimeSpinBox(59)
        self.second_spin.setValue(initial_dt.second)
        time_layout.addWidget(QLabel("秒:"))
        time_layout.addWidget(self.second_spin)
        
        layout.addWidget(time_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_datetime(self) -> datetime:
        """获取选择的日期时间"""
        date = self.calendar.selectedDate()
        return datetime(
            date.year(),
            date.month(),
            date.day(),
            self.hour_spin.value(),
            self.minute_spin.value(),
            self.second_spin.value()
        )


class DateTimePickerWidget(QWidget):
    """日期时间选择器组件"""
    
    # 信号：日期时间变化
    datetime_changed = Signal(datetime)
    
    def __init__(
        self,
        label: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._datetime: Optional[datetime] = None
        self._label = label
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签
        if self._label:
            label = QLabel(self._label)
            layout.addWidget(label)
        
        # 显示框
        self.display_edit = QLineEdit()
        self.display_edit.setReadOnly(True)
        self.display_edit.setPlaceholderText("点击选择时间...")
        self.display_edit.setMinimumWidth(160)
        layout.addWidget(self.display_edit)
        
        # 选择按钮
        self.pick_button = QPushButton("📅")
        self.pick_button.setFixedWidth(32)
        self.pick_button.setToolTip("选择日期时间")
        self.pick_button.clicked.connect(self._show_picker)
        layout.addWidget(self.pick_button)
        
        # 清除按钮
        self.clear_button = QPushButton("✕")
        self.clear_button.setFixedWidth(24)
        self.clear_button.setToolTip("清除")
        self.clear_button.clicked.connect(self._clear_datetime)
        layout.addWidget(self.clear_button)
    
    def _show_picker(self):
        """显示日期时间选择对话框"""
        dialog = DateTimePickerDialog(self._datetime, self)
        if dialog.exec() == QDialog.Accepted:
            self.set_datetime(dialog.get_datetime())
    
    def _clear_datetime(self):
        """清除日期时间"""
        self._datetime = None
        self.display_edit.clear()
        self.datetime_changed.emit(None)
    
    def set_datetime(self, dt: Optional[datetime]):
        """设置日期时间"""
        self._datetime = dt
        if dt:
            self.display_edit.setText(dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.display_edit.clear()
        self.datetime_changed.emit(dt)
    
    def get_datetime(self) -> Optional[datetime]:
        """获取日期时间"""
        return self._datetime
    
    def setEnabled(self, enabled: bool):
        """设置启用状态"""
        super().setEnabled(enabled)
        self.display_edit.setEnabled(enabled)
        self.pick_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
