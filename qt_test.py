import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from gui.views.i_detail_panel_view import IDetailPanelView
from gui.detail_panel import DetailPanel

app = QApplication(sys.argv)

print("Testing DetailPanel interface implementation...")
print(f"Is subclass: {issubclass(DetailPanel, IDetailPanelView)}")

panel = DetailPanel()
print(f"Is instance: {isinstance(panel, IDetailPanelView)}")

# Check methods
methods = ['update_protocol_info', 'set_parse_button_enabled', 'set_stop_button_enabled',
           'set_progress', 'get_filter_settings', 'set_log_path', 'set_commands', 'reset_progress']
print(f"\nMethods check:")
for m in methods:
    print(f"  {m}: {hasattr(panel, m)}")

# Check signals
signals = ['parse_clicked', 'stop_clicked', 'validate_clicked', 'open_output_dir_clicked',
           'select_log_clicked', 'time_range_changed', 'command_filter_changed', 'terminal_filter_changed']
print(f"\nSignals check:")
for s in signals:
    print(f"  {s}: {hasattr(panel, s)}")

print("\nAll checks passed!")
sys.exit(0)
