# AGENT.md

## 1. 项目目标

本仓库是一个**多协议通信报文解析工具**：

- 通过 `configs/<protocol>/protocol.yaml` 描述协议结构（类型、枚举、命令字段、兼容字段等）。
- 通过 `input_logs/<protocol>.log` 提供待解析的原始日志文本。
- 解析结果输出到 `parsed_log/` 目录。

项目核心诉求是“**零代码扩展新协议**”：新增协议优先通过新增 YAML 配置完成，避免修改 Python 代码。

## 2. 关键入口与数据流

- **命令行入口**：`main.py`
  - `python main.py --list` 扫描 `configs/`，列出可用协议。
  - `python main.py --validate` 调用 `src/validate_configs.py --all` 验证所有 YAML 配置。
  - `python main.py <protocol>` 解析指定协议。

- **核心解析器**：`src/yaml_unified_protocol.py` -> `YamlUnifiedProtocol`
  - 读取日志：`extract_data_from_file()`
    - 以时间戳行切分数据块，尝试抽取方向关键字 `Send|Recv`。
    - 依据 `config.compatibility.frame_head`（正则）确定从哪一段开始收集十六进制字节串。
  - 解析数据：`parse_data_content()`
    - 先解析包头：`_parse_header()`（使用 `compatibility.head_fields`）
    - 取出 `cmd` 后按命令布局解析内容：`YamlCmdFormat.parse_cmd_data()`
  - 输出结果：`screen_parse_data()`
    - 控制台打印
    - 写入 `parsed_log/parsed_<protocol>_log_YYYY-MM-DD HH-MM-SS.txt`

- **YAML配置加载与模型**：`src/yaml_config.py`
  - `yaml_loader.load_protocol_config(path)` 负责加载并缓存配置。
  - `ProtocolConfig` 包含 `meta/types/enums/cmds` 以及 `compatibility`（包头/包尾/头字段等）。

- **字段解析**：`src/yaml_field_parser.py` -> `YamlFieldParser`
  - 支持 `uint/int/str/hex/bcd/time.cp56time2a/binary_str/bitset/bitfield`
  - 支持循环结构：`repeat_const` / `repeat_by`

- **命令格式管理**：`src/yaml_cmdformat.py` -> `YamlCmdFormat`
  - 负责根据 `cmd_id` 获取字段布局并驱动 `YamlFieldParser` 解析。

## 3. 运行方式（你应该优先这样验证改动）

### 3.1 依赖说明

仓库 README 中提到“仅标准库”，但代码中使用了 `import yaml`，因此运行需要安装 **PyYAML**。

- 解析运行：至少需要 `pyyaml`
- 单测运行：需要 `pytest`

（仓库未提供 `requirements.txt`，如需补齐依赖文件请先与维护者确认是否允许引入。）

### 3.2 常用命令

- **列出协议**：
  - `python main.py --list`

- **验证所有配置**：
  - `python main.py --validate`
  - 或 `python src/validate_configs.py --all`

- **解析某个协议**：
  - `python main.py v8`
  - `python main.py xiaoju`
  - `python main.py yunwei`
  - `python main.py sinexcel`
  - `python main.py yunkuaichong`

- **运行测试**：
  - `pytest -q`

## 4. 配置与文件约定（非常重要）

### 4.1 协议目录与日志文件命名

- 协议目录：`configs/<protocol_name>/protocol.yaml`
- 日志文件：`input_logs/<protocol_name>.log`

`main.py` 的统一规则：

- 以 `configs/` 的**目录名**作为协议名称（`protocol_dir.name`）。
- 如果 `input_logs/<protocol_dir.name>.log` 不存在，会自动创建空文件并提示。

建议保持一致：

- `meta.protocol` 建议与 `<protocol_name>` 一致（便于输出文件命名与排查）。

### 4.2 YAML结构（高层约定）

配置由以下部分组成（按代码实际使用）：

- `meta`: 协议元信息
- `types`: 类型定义（`TypeDef`）
- `enums`: 枚举映射
- `cmds`: 命令布局（字段列表，支持循环组）
- `compatibility`: 兼容字段（解析器依赖）
  - `head_len` / `tail_len`
  - `frame_head`（正则）
  - `head_fields`（头字段定义，`YamlUnifiedProtocol._parse_header()` 使用）

### 4.3 头字段（head_fields）的关键点

`YamlUnifiedProtocol._parse_header()` 依赖 `head_fields` 内每个字段配置：

- `name`
- `offset`
- `length`
- `endian`（当前实现期望为 `little` 或 `big`）
- `type`（`uint/const/hex/ascii`）

注意：`Field` 模型里 `endian` 常用值是 `LE/BE`，但头字段解析里用的是 `little/big`。修改这里时必须谨慎，避免引入不兼容。

## 5. 代码修改原则（给自动化代理/协作者）

- **优先通过 YAML 扩展功能**：
  - 新增协议、新增命令字段，优先改 `configs/*/protocol.yaml`。

- **修改解析行为前先定位责任边界**：
  - 日志抽取问题优先看 `YamlUnifiedProtocol.extract_data_from_file()`。
  - 字段类型解析优先看 `YamlFieldParser`（新增类型需要在 `_build_type_parsers()` 注册）。
  - 命令布局/循环问题优先看 `yaml_config.py` 的 `_parse_fields()` 和 `YamlFieldParser._parse_group()`。

- **保持输出稳定**：
  - `parsed_log/` 的输出文件命名、字段结构尽量保持兼容；如需变更，先确认下游是否依赖。

- **保持中文日志/注释风格**：
  - 项目当前打印与提示多为中文；新增日志/提示信息保持中文。

- **不要“猜接口”**：
  - 如果需要新增 YAML 字段/语义，先在代码里全局搜索现有字段用法，确认没有同名语义。

## 6. 变更自检清单（提交前至少过一遍）

- **配置兼容性**：现有 `configs/*/protocol.yaml` 是否仍能通过 `python main.py --validate`。
- **最小回归测试**：`pytest` 是否通过（至少 `tests/test_yaml_config.py`、`tests/test_bitfield.py`）。
- **路径/命名一致性**：新增协议是否满足 `configs/<name>/protocol.yaml` + `input_logs/<name>.log`。
- **输出目录**：解析输出是否仍在 `parsed_log/`，且不会覆盖旧文件（当前按时间戳生成）。
- **异常信息可读**：失败时是否能从控制台提示快速定位（优先中文）。
