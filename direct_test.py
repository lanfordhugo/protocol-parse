import sys
from pathlib import Path

# 直接导入文件，不通过 gui 包
sys.path.insert(0, str(Path(__file__).parent / 'gui'))

from views.i_detail_panel_view import IDetailPanelView
from detail_panel import DetailPanel

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

print("=" * 60)
print("Testing DetailPanel interface implementation...")
print("=" * 60)

# Check subclass
is_subclass = issubclass(DetailPanel, IDetailPanelView)
print(f"\n1. Class inheritance check:")
print(f"   DetailPanel is subclass of IDetailPanelView: {is_subclass}")

# Create instance
try:
    panel = DetailPanel()
    is_instance = isinstance(panel, IDetailPanelView)
    print(f"\n2. Instance check:")
    print(f"   panel instance is IDetailPanelView: {is_instance}")
except Exception as e:
    print(f"\n2. Instance creation failed:")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check methods
print(f"\n3. Interface methods check:")
methods = [
    'update_protocol_info',
    'set_parse_button_enabled',
    'set_stop_button_enabled',
    'set_progress',
    'get_filter_settings',
    'set_log_path',
    'set_commands',
    'reset_progress',
]

all_methods_ok = True
for m in methods:
    has_method = hasattr(panel, m)
    is_callable = callable(getattr(panel, m, None))
    status = "✓" if (has_method and is_callable) else "✗"
    print(f"   {m}: {status}")
    if not (has_method and is_callable):
        all_methods_ok = False
        print(f"      has_method={has_method}, callable={is_callable}")

# Check signals
print(f"\n4. Interface signals check:")
signals = [
    'parse_clicked',
    'stop_clicked',
    'validate_clicked',
    'open_output_dir_clicked',
    'select_log_clicked',
    'time_range_changed',
    'command_filter_changed',
    'terminal_filter_changed',
]

all_signals_ok = True
for s in signals:
    has_signal = hasattr(panel, s)
    status = "✓" if has_signal else "✗"
    print(f"   {s}: {status}")
    if not has_signal:
        all_signals_ok = False

# Summary
print(f"\n" + "=" * 60)
print("Test Results:")
print(f"  Class inheritance: {'PASS ✓' if is_subclass else 'FAIL ✗'}")
print(f"  Instance check: {'PASS ✓' if is_instance else 'FAIL ✗'}")
print(f"  Interface methods: {'PASS ✓' if all_methods_ok else 'FAIL ✗'}")
print(f"  Interface signals: {'PASS ✓' if all_signals_ok else 'FAIL ✗'}")
print("=" * 60)

if is_subclass and is_instance and all_methods_ok and all_signals_ok:
    print("\n✓ All tests PASSED!")
    sys.exit(0)
else:
    print("\n✗ Some tests FAILED!")
    sys.exit(1)
