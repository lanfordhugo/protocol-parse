# 贡献指南

感谢你对 V8Parse 项目的关注！我们欢迎各种形式的贡献。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone <repository-url>
cd v8parse
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 或安装开发依赖（包含测试工具）
pip install -e ".[dev]"
```

## 代码风格

### Python 代码规范

本项目遵循以下代码规范：

- **PEP 8**: Python 代码风格指南
- **行长度**: 最大 100 字符
- **导入顺序**: 标准库 → 第三方库 → 本地模块
- **命名规范**:
  - 类名: `CamelCase`
  - 函数/变量: `snake_case`
  - 常量: `UPPER_SNAKE_CASE`

### 代码格式化工具

```bash
# 使用 black 格式化代码
black src/ tests/

# 使用 isort 整理导入
isort src/ tests/

# 使用 flake8 检查代码质量
flake8 src/ tests/
```

## 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_yaml_config.py

# 运行特定测试方法
python -m pytest tests/test_yaml_config.py::test_meta_parsing

# 查看测试覆盖率
python -m pytest tests/ --cov=src --cov-report=html
```

### 测试规范

- 使用 **pytest** 框架
- 测试文件命名: `test_*.py`
- 测试类命名: `Test*`
- 测试方法命名: `test_*`
- 断言密度: ≥ 2.5（断言数/测试数）
- 测试覆盖率: ≥ 85%

## 添加新协议

### 1. 创建协议配置目录

```bash
mkdir configs/new_protocol
```

### 2. 创建 protocol.yaml

参考 `protocol_template.yaml` 或现有协议配置：

```yaml
meta:
  protocol: new_protocol
  version: 1
  default_endian: LE

compatibility:
  head_len: 2
  tail_len: 2
  frame_head: "AA BB"

types:
  uint8: { base: uint, bytes: 1, signed: false }

cmds:
  1:
    - {len: 1, name: field_name, type: uint8}
```

### 3. 添加日志文件

将日志文件放置在 `input_logs/new_protocol.log`

### 4. 验证配置

```bash
python main.py --validate
python main.py new_protocol
```

## 提交代码

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 编写提交信息

提交信息格式：

```
<type>: <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 代码重构
- `style`: 代码格式调整
- `chore`: 构建/工具链相关

**示例**:

```
feat: 添加支持 BCD 时间格式解析

- 新增 time.cp56time2a 类型解析器
- 添加对应测试用例
- 更新文档说明

Closes #123
```

### 3. 推送分支

```bash
git push origin feature/your-feature-name
```

## Pull Request 流程

1. **描述清晰**: 说明 PR 的目的和改动内容
2. **关联 Issue**: 如果相关，关联对应的 Issue
3. **测试通过**: 确保所有测试通过
4. **代码审查**: 响应审查意见并进行修改

### PR 检查清单

- [ ] 代码通过所有测试
- [ ] 测试覆盖率 ≥ 85%
- [ ] 代码符合 PEP 8 规范
- [ ] 添加了必要的文档和注释
- [ ] 更新了相关文档

## 项目结构

```
v8parse/
├── configs/              # 协议配置文件
│   ├── v8/
│   ├── xiaoju/
│   └── ...
├── docs/                 # 项目文档
├── input_logs/           # 输入日志文件
├── parsed_log/           # 解析结果输出
├── src/                  # 源代码
│   ├── m_print.py
│   ├── yaml_config.py
│   └── ...
├── tests/                # 测试代码
│   ├── test_yaml_config.py
│   └── ...
├── main.py              # CLI 入口
├── main_gui.py          # GUI 入口
├── requirements.txt     # 核心依赖
├── requirements-gui.txt # GUI 依赖
└── README.md            # 项目说明
```

## 获取帮助

- 📖 查看 [README.md](README.md) 了解项目概述
- 📧 提交 Issue 报告问题或建议
- 💬 查看 [CLAUDE.md](CLAUDE.md) 了解架构设计

## 行为准则

- 尊重不同观点和经验
- 使用欢迎和包容的语言
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

## 许可证

贡献的代码将采用与项目相同的 MIT 许可证。
