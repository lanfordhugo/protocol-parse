# main.py - V8Parse 多协议通信报文解析工具
"""
V8Parse - 基于YAML配置的协议解析框架

完全基于YAML配置的现代化协议解析工具，支持零代码扩展新协议。
直接从YAML配置文件加载协议信息，无需修改任何Python代码。
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from datetime import datetime

from src.yaml_unified_protocol import YamlUnifiedProtocol
from src.time_parser import TimeParser, parse_command_ids
from src.log_scanner import LogScanner


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


def _show_log_statistics(log_path: str):
    """
    显示日志文件统计信息

    参数:
        log_path: 日志文件路径
    """
    try:
        scanner = LogScanner(log_path)
        result = scanner.scan()

        print("\n" + "=" * 50)
        print("日志文件统计信息:")
        print("=" * 50)
        print(f"文件路径: {log_path}")
        print(f"文件大小: {result.file_size_human}")
        print(f"总行数: {result.total_lines:,}")
        print(f"扫描行数: {result.scanned_lines:,}")
        print(f"扫描耗时: {result.scan_duration:.2f} 秒")

        if result.has_valid_range:
            print(f"\n时间范围:")
            print(f"  最早: {result.min_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  最晚: {result.max_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  跨度: {result.time_span_human}")
        else:
            print("\n时间范围: 未检测到有效时间戳")

        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\n警告: 无法获取统计信息: {e}\n")


def run_protocol(protocol_name: str,
                log_file: Optional[str] = None,
                time_range: Optional[Tuple[datetime, datetime]] = None,
                include_cmds: Optional[list] = None,
                exclude_cmds: Optional[list] = None,
                show_stats: bool = False) -> bool:
    """
    运行指定协议的解析

    参数:
        protocol_name: 协议名称
        log_file: 自定义日志文件路径（可选）
        time_range: 时间范围过滤 (start_time, end_time)
        include_cmds: 包含的命令ID列表
        exclude_cmds: 排除的命令ID列表
        show_stats: 是否显示统计信息
    """
    try:
        protocols = get_available_protocols()

        if protocol_name not in protocols:
            print(f"错误: 不支持的协议 '{protocol_name}'")
            print(f"支持的协议: {', '.join(protocols.keys())}")
            return False

        protocol_info = protocols[protocol_name]

        print(f"协议名称: {protocol_name}")
        print(f"YAML配置: {protocol_info['yaml_config']}")

        # 使用自定义日志文件或默认日志文件
        if log_file:
            log_path = Path(log_file)
            print(f"日志文件: {log_path} (自定义)")
        else:
            log_path = ensure_log_file(protocol_name)
            print(f"日志文件: {log_path}")

        # 显示统计信息
        if show_stats:
            _show_log_statistics(str(log_path))

        # 检查配置文件是否存在
        if not Path(protocol_info['yaml_config']).exists():
            print(f"错误: 配置文件不存在: {protocol_info['yaml_config']}")
            return False

        if not log_path.exists():
            print(f"错误: 日志文件不存在: {log_path}")
            return False

        if log_path.stat().st_size == 0:
            print(f"提示: 日志文件 {log_path} 当前为空，请拷贝协议日志内容到该文件后重试。")
            return False

        # 创建协议解析器
        protocol = YamlUnifiedProtocol(
            str(log_path),
            protocol_info['yaml_config']
        )

        # 应用过滤器
        filter_applied = False

        # 时间过滤
        if time_range:
            start_time, end_time = time_range
            protocol.set_time_range(start_time, end_time)
            print(f"\n时间过滤: {TimeParser.format_time_range(start_time, end_time)}")
            filter_applied = True

        # 命令过滤
        if include_cmds:
            protocol.set_include_cmds(include_cmds)
            print(f"包含命令: {include_cmds}")
            filter_applied = True

        if exclude_cmds:
            protocol.set_exclude_cmds(exclude_cmds)
            print(f"排除命令: {exclude_cmds}")
            filter_applied = True

        if filter_applied:
            print()  # 过滤信息后空一行

        # 运行解析
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
        print(f"  配置存在: {'是' if yaml_config.exists() else '否'}")
        print(f"  日志文件: {log_file}")
        print(f"  日志存在: {'是' if log_file.exists() else '否'}")
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
  python main.py <protocol>                              # 解析指定协议
  python main.py --list                                  # 列出所有可用协议
  python main.py --validate                              # 验证所有配置

  # 时间过滤
  python main.py v8 --time-start "2024-01-01 00:00:00" --time-end "2024-01-31 23:59:59"
  python main.py v8 --time-last "24h"                    # 最近24小时
  python main.py v8 --time-last "7d"                     # 最近7天

  # 命令过滤
  python main.py v8 --include-cmds "2,3,5"               # 只解析命令2,3,5
  python main.py v8 --exclude-cmds "1,99"                # 排除命令1,99

  # 组合过滤
  python main.py v8 --time-last "1h" --include-cmds "2,3"

  # 日志管理
  python main.py v8 --log-file "/path/to/custom.log"  # 使用自定义日志文件
  python main.py v8 --stats                           # 显示日志统计信息

添加新协议的统一规则：
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

    # 时间过滤参数组（互斥）
    time_group = parser.add_argument_group('时间过滤选项')
    time_group.add_argument(
        '--time-start',
        type=str,
        metavar='"YYYY-MM-DD HH:MM:SS"',
        help='开始时间（绝对时间），格式：YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD'
    )
    time_group.add_argument(
        '--time-end',
        type=str,
        metavar='"YYYY-MM-DD HH:MM:SS"',
        help='结束时间（绝对时间），格式：YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD'
    )
    time_group.add_argument(
        '--time-last',
        type=str,
        metavar='<数字><单位>',
        help='相对时间，例如：1h（1小时）、24h（24小时）、7d（7天）'
    )

    # 命令过滤参数组
    cmd_group = parser.add_argument_group('命令过滤选项')
    cmd_group.add_argument(
        '--include-cmds',
        type=str,
        metavar='cmd1,cmd2,cmd3',
        help='只解析指定的命令ID（逗号分隔）'
    )
    cmd_group.add_argument(
        '--exclude-cmds',
        type=str,
        metavar='cmd1,cmd2,cmd3',
        help='排除指定的命令ID（逗号分隔）'
    )

    # 日志管理参数组
    log_group = parser.add_argument_group('日志管理选项')
    log_group.add_argument(
        '--log-file',
        type=str,
        metavar='/path/to/log.log',
        help='指定自定义日志文件路径'
    )
    log_group.add_argument(
        '--stats',
        action='store_true',
        help='显示日志文件统计信息'
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

    # 解析时间范围参数
    time_range = None
    if args.time_start or args.time_end or args.time_last:
        time_range = TimeParser.parse_time_range(
            time_start=args.time_start,
            time_end=args.time_end,
            time_last=args.time_last
        )
        if not time_range:
            # 时间解析失败，打印错误信息并退出
            sys.exit(1)

    # 解析命令过滤参数
    include_cmds = None
    exclude_cmds = None

    if args.include_cmds:
        include_cmds = parse_command_ids(args.include_cmds)
        if not include_cmds:
            sys.exit(1)

    if args.exclude_cmds:
        exclude_cmds = parse_command_ids(args.exclude_cmds)
        if not exclude_cmds:
            sys.exit(1)

    # 运行协议解析
    success = run_protocol(
        args.protocol,
        log_file=args.log_file,
        time_range=time_range,
        include_cmds=include_cmds,
        exclude_cmds=exclude_cmds,
        show_stats=args.stats
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
