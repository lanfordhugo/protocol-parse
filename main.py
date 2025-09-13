# main.py - V8Parse 多协议通信报文解析工具
"""
V8Parse - 基于YAML配置的协议解析框架

完全基于YAML配置的现代化协议解析工具，支持零代码扩展新协议。
直接从YAML配置文件加载协议信息，无需修改任何Python代码。
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

from src.yaml_unified_protocol import YamlUnifiedProtocol


def get_available_protocols() -> Dict[str, Dict[str, str]]:
    """获取所有可用的协议配置"""
    configs_dir = Path("configs")
    protocols = {}
    
    if not configs_dir.exists():
        return protocols
    
    for protocol_dir in configs_dir.iterdir():
        if protocol_dir.is_dir():
            yaml_config = protocol_dir / "protocol.yaml"
            
            # 特殊处理各协议的日志文件名
            if protocol_dir.name == "sinexcel":
                log_file = Path("input_logs") / "sincexcel.log"
            elif protocol_dir.name == "v8":
                log_file = Path("input_logs") / "v8_com.log"
            else:
                log_file = Path("input_logs") / f"{protocol_dir.name}.log"
            
            if yaml_config.exists():
                protocols[protocol_dir.name] = {
                    'yaml_config': str(yaml_config),
                    'log_file': str(log_file) if log_file.exists() else f"input_logs/{protocol_dir.name}.log"
                }
    
    return protocols


def run_protocol(protocol_name: str) -> bool:
    """运行指定协议的解析"""
    try:
        protocols = get_available_protocols()
        
        if protocol_name not in protocols:
            print(f"错误: 不支持的协议 '{protocol_name}'")
            print(f"支持的协议: {', '.join(protocols.keys())}")
            return False
        
        protocol_info = protocols[protocol_name]
        
        print(f"协议名称: {protocol_name}")
        print(f"YAML配置: {protocol_info['yaml_config']}")
        print(f"日志文件: {protocol_info['log_file']}")
        
        # 检查配置文件是否存在
        if not Path(protocol_info['yaml_config']).exists():
            print(f"错误: 配置文件不存在: {protocol_info['yaml_config']}")
            return False
        
        # 创建并运行协议解析器
        protocol = YamlUnifiedProtocol(
            protocol_info['log_file'],
            protocol_info['yaml_config']
        )
        protocol.run()
        
        return True
        
    except Exception as e:
        print(f"运行时错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_protocols():
    """列出所有可用的协议"""
    protocols = get_available_protocols()
    
    if not protocols:
        print("没有找到可用的协议配置")
        return
    
    print("可用的协议配置:")
    print("=" * 50)
    
    for protocol_name, info in protocols.items():
        yaml_config = Path(info['yaml_config'])
        log_file = Path(info['log_file'])
        
        print(f"协议: {protocol_name}")
        print(f"  配置文件: {yaml_config}")
        print(f"  配置存在: {'✅' if yaml_config.exists() else '❌'}")
        print(f"  日志文件: {log_file}")
        print(f"  日志存在: {'✅' if log_file.exists() else '❌'}")
        print()


def validate_all_configs():
    """验证所有协议配置"""
    print("验证所有协议配置...")
    
    # 使用已有的验证工具
    import subprocess
    result = subprocess.run([
        sys.executable, "tools/validate_configs.py", "--all"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode == 0


def main():
    """主函数，处理命令行参数"""
    protocols = get_available_protocols()
    
    parser = argparse.ArgumentParser(
        description="基于YAML配置的协议解析框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
支持的协议: {', '.join(protocols.keys()) if protocols else '无'}

使用示例:
  python main.py v8        # 解析V8协议
  python main.py xiaoju    # 解析小桔协议
  python main.py yunwei    # 解析运维协议
  python main.py sinexcel  # 解析Sinexcel协议
  python main.py --list    # 列出所有协议
  python main.py --validate # 验证所有配置

🚀 添加新协议只需2步：
1. 在 configs/<protocol_name>/ 目录下创建 protocol.yaml
2. 将日志文件放到 input_logs/<protocol_name>.log
        """
    )
    
    # 位置参数
    parser.add_argument(
        'protocol',
        nargs='?',
        help='要解析的协议名称'
    )
    
    # 选项参数
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='列出所有可用的协议'
    )
    
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='验证所有协议配置'
    )
    
    args = parser.parse_args()
    
    # 处理选项
    if args.list:
        list_protocols()
        return
    
    if args.validate:
        success = validate_all_configs()
        sys.exit(0 if success else 1)
    
    # 处理协议解析
    if not args.protocol:
        parser.print_help()
        print(f"\n错误: 请指定要解析的协议")
        sys.exit(1)
    
    success = run_protocol(args.protocol)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
