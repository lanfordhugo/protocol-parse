# main.py - 配置驱动的协议解析框架

import sys
import argparse
from src.protocol_configs import get_protocol_info, get_supported_protocols
from src.unified_protocol import UnifiedProtocol


def run_protocol(protocol_name: str):
    """运行指定协议的解析"""
    try:
        protocol_info = get_protocol_info(protocol_name)
        print(f"协议配置: {protocol_info.protocol_name}")
        print(f"日志文件: {protocol_info.log_file}")
        print(f"格式文件: {protocol_info.format_file}")
        
        protocol = UnifiedProtocol(
            protocol_info.log_file,
            protocol_info.format_file,
            protocol_info.config
        )
        protocol.run()
    except ValueError as e:
        print(f"错误: {e}")
        print(f"支持的协议: {', '.join(get_supported_protocols())}")
        return False
    except Exception as e:
        print(f"运行时错误: {e}")
        return False
    return True


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(
        description="配置驱动的协议解析框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
支持的协议: {', '.join(get_supported_protocols())}

使用示例:
  python main.py v8        # 解析V8协议
  python main.py xiaoju    # 解析小桔协议
  python main.py yunwei    # 解析运维协议
  python main.py sinexcel  # 解析Sinexcel协议

🚀 新增协议只需1步：
在 src/protocol_configs.py 的 PROTOCOL_CONFIGS 中添加新协议配置即可！
        """
    )
    
    parser.add_argument(
        'protocol',
        nargs='?',
        default='v8',
        help=f'协议名称 (默认: v8，可选: {", ".join(get_supported_protocols())})'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='列出所有支持的协议'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("支持的协议:")
        for protocol in get_supported_protocols():
            protocol_info = get_protocol_info(protocol)
            print(f"  {protocol:10} - {protocol_info.log_file}")
        return
    
    print(f"使用配置驱动协议解析: {args.protocol}")
    success = run_protocol(args.protocol)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
