#!/usr/bin/env python3
"""
文件名称: run_server.py
内容摘要: TCP Log Server 启动脚本
当前版本: v1.0.0
作者: lanford
创建日期: 2025-01-02
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from tcp_log.server_gui import main
    main()
