"""
测试 DetailPanel 是否实现了 IDetailPanelView 接口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 直接导入，不通过 gui 包
from gui.views.i_detail_panel_view import IDetailPanelView
from gui.detail_panel import DetailPanel


def test_interface_implementation():
    """测试接口实现"""
    print("=" * 60)
    print("测试 DetailPanel 接口实现")
    print("=" * 60)

    # 1. 检查类继承
    is_subclass = issubclass(DetailPanel, IDetailPanelView)
    print(f"\n1. 类继承检查:")
    print(f"   DetailPanel 是 IDetailPanelView 的子类: {is_subclass}")

    # 2. 检查实例
    try:
        panel = DetailPanel()
        is_instance = isinstance(panel, IDetailPanelView)
        print(f"\n2. 实例检查:")
        print(f"   DetailPanel() 实例是 IDetailPanelView: {is_instance}")
    except Exception as e:
        print(f"\n2. 实例创建失败:")
        print(f"   错误: {e}")
        return False

    # 3. 检查接口方法
    print(f"\n3. 接口方法检查:")
    required_methods = [
        'update_protocol_info',
        'set_parse_button_enabled',
        'set_stop_button_enabled',
        'set_progress',
        'get_filter_settings',
        'set_log_path',
        'set_commands',
        'reset_progress',
    ]

    all_methods_present = True
    for method_name in required_methods:
        has_method = hasattr(panel, method_name)
        print(f"   {method_name}: {'✓' if has_method else '✗'}")
        if not has_method:
            all_methods_present = False

    # 4. 检查信号
    print(f"\n4. 接口信号检查:")
    required_signals = [
        'parse_clicked',
        'stop_clicked',
        'validate_clicked',
        'open_output_dir_clicked',
        'select_log_clicked',
        'time_range_changed',
        'command_filter_changed',
        'terminal_filter_changed',
    ]

    all_signals_present = True
    for signal_name in required_signals:
        has_signal = hasattr(panel, signal_name)
        print(f"   {signal_name}: {'✓' if has_signal else '✗'}")
        if not has_signal:
            all_signals_present = False

    # 总结
    print(f"\n" + "=" * 60)
    print("测试结果:")
    print(f"  类继承: {'✓ 通过' if is_subclass else '✗ 失败'}")
    print(f"  实例检查: {'✓ 通过' if is_instance else '✗ 失败'}")
    print(f"  接口方法: {'✓ 通过' if all_methods_present else '✗ 失败'}")
    print(f"  接口信号: {'✓ 通过' if all_signals_present else '✗ 失败'}")
    print("=" * 60)

    return is_subclass and is_instance and all_methods_present and all_signals_present


if __name__ == "__main__":
    success = test_interface_implementation()
    sys.exit(0 if success else 1)
