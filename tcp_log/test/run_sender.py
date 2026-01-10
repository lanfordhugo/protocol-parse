#!/usr/bin/env python3
"""
文件名称: run_sender.py
内容摘要: TCP Log Sender 启动脚本(测试工具)
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
# 从 tcp_log/test/run_sender.py 向上两级到达项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from tcp_log.sender_gui import main
    main()
