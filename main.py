# main.py - V8Parse 多协议通信报文解析工具
"""
V8Parse - 基于YAML配置的协议解析框架

完全基于YAML配置的现代化协议解析工具，支持零代码扩展新协议。
直接从YAML配置文件加载协议信息，无需修改任何Python代码。
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

from src.yaml_unified_protocol import YamlUnifiedProtocol


LOGS_DIR = Path("input_logs")


def ensure_log_file(protocol_name: str) -> Path:
    """确保协议的日志文件存在，不存在时创建空文件并提醒用户"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{protocol_name}.log"

    if not log_file.exists():
        log_file.touch()
        print(f"提示: 已在 {log_file} 创建空文件，请拷贝协议日志内容到此文件后重试。")

    return log_file


def get_available_protocols() -> Dict[str, Dict[str, str]]:
    """获取所有可用的协议配置"""
    configs_dir = Path("configs")
    protocols = {}
    
    if not configs_dir.exists():
        return protocols
    
    for protocol_dir in configs_dir.iterdir():
        if protocol_dir.is_dir():
            yaml_config = protocol_dir / "protocol.yaml"
            
            # 统一策略：日志文件名必须与协议目录名一致
            log_file = ensure_log_file(protocol_dir.name)
            
            # 只有配置文件存在才认为是有效协议
            if yaml_config.exists():
                protocols[protocol_dir.name] = {
                    'yaml_config': str(yaml_config),
                    'log_file': str(log_file)
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
        log_path = ensure_log_file(protocol_name)
        print(f"日志文件: {log_path}")
        print(f"提示: 请先将日志内容拷贝到上述文件中再执行解析。")

        # 检查配置文件是否存在
        if not Path(protocol_info['yaml_config']).exists():
            print(f"错误: 配置文件不存在: {protocol_info['yaml_config']}")
            return False

        if log_path.stat().st_size == 0:
            print(f"提示: 日志文件 {log_path} 当前为空，请拷贝协议日志内容到该文件后重试。")
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
        sys.executable, "src/validate_configs.py", "--all"
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
  python main.py <protocol>  # 解析指定协议
  python main.py --list      # 列出所有可用协议
  python main.py --validate  # 验证所有配置

🚀 添加新协议的统一规则：
1. 在 configs/<protocol_name>/ 目录下创建 protocol.yaml
2. 将日志文件命名为 input_logs/<protocol_name>.log
3. 配置文件和日志文件都存在才会被识别为有效协议
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
