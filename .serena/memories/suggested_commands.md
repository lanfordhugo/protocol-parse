# 建议的命令列表

## 项目运行命令

### 基本运行
```bash
# 运行V8协议解析 (默认)
python main.py

# 运行指定协议
python main.py v8        # V8协议
python main.py xiaoju    # 小桔协议
python main.py yunwei    # 运维协议
python main.py sinexcel  # Sinexcel协议

# 列出所有支持的协议
python main.py --list
python main.py -l
```

### 带参数运行
```bash
# 查看帮助信息
python main.py --help
python main.py -h
```

## 开发和调试命令

### Python环境
```bash
# 检查Python版本
python --version

# 运行Python交互式解释器
python

# 执行Python脚本
python script_name.py
```

### 文件操作 (Windows)
```cmd
# 查看目录内容
dir
ls  # 如果有别名设置

# 切换目录
cd path\to\directory

# 查看文件内容
type filename.txt
more filename.txt

# 搜索文件内容
findstr "pattern" filename.txt

# 查找文件
dir /s filename.txt
```

### 项目文件操作
```bash
# 查看日志文件
type input_logs\v8_com.log
type input_logs\xiaoju.log

# 查看配置文件
type protocol_configs.py
type resources\format_mcu_ccu.txt

# 查看解析结果
type parsed_log\parsed_net_log_*.txt
```

## Git命令
```bash
# 查看状态
git status

# 查看提交历史
git log --oneline

# 添加文件到暂存区
git add .
git add filename

# 提交更改
git commit -m "commit message"

# 推送到远程仓库
git push

# 拉取最新更改
git pull
```

## 测试命令
```bash
# 运行测试文件 (如果存在)
python src\test.py

# 运行Python内置测试模块
python -m unittest discover

# 检查语法错误
python -m py_compile main.py
python -m py_compile src\unified_protocol.py
```

## 日志和输出查看
```bash
# 查看系统日志
type log\log_sys.txt

# 查看最新的解析结果
dir parsed_log\*.txt /o:d
```

## 配置和格式文件编辑
```bash
# 编辑协议配置（使用系统默认编辑器）
notepad protocol_configs.py

# 编辑格式文件
notepad resources\format_mcu_ccu.txt
notepad resources\format_xiaoju.txt

# 编辑过滤配置
notepad resources\filter.txt
```

## 项目维护命令
```bash
# 清理临时文件
del __pycache__ /s /q
del src\__pycache__ /s /q

# 备份重要文件
copy protocol_configs.py protocol_configs.py.bak
copy main.py main.py.bak
```

## 常用工具命令
```bash
# 查看网络连接 (如果需要网络调试)
netstat -an

# 查看进程
tasklist | findstr python

# 获取系统信息
systeminfo
```