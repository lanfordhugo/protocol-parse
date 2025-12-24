---
trigger: always_on
---
# AI 编辑器 Steering 机制指南

本文档总结了如何在不同 AI 编辑器中实现项目多级索引系统（Project Multilevel Index System），让 AI 助手自动维护项目文档的分形结构。

## 核心概念

### 什么是项目多级索引系统？

一个自维护的文档系统，通过以下机制实现：

1. **文件头部注释** - 每个代码文件开头有 `input/output/pos` 三行注释，描述文件职责
2. **文件夹 README.md** - 每个文件夹有索引文档，列出所有文件及其功能
3. **自指更新机制** - 文件变更时自动触发相关文档更新
4. **分形结构** - 局部影响整体，整体影响局部

### 为什么需要这个系统？

- AI 助手可以快速理解项目结构
- 减少 AI 探索代码库的时间
- 保持文档与代码同步
- 新成员快速上手项目

---

## 各编辑器 Steering 机制对比

| 特性 | Kiro | Claude Code | Cursor | Windsurf |
|------|------|-------------|--------|----------|
| 配置文件 | `.kiro/steering/*.md` | `CLAUDE.md` + `.claude/rules/*.md` | `.cursor/rules/*.mdc` | `.windsurfrules` |
| 全局配置 | `~/.kiro/steering/` | `~/.claude/CLAUDE.md` + `~/.claude/rules/` | `~/.cursor/rules/` | 全局设置 |
| 始终加载 | `inclusion: always` | 根目录 CLAUDE.md + 无 paths 的 rules | `alwaysApply: true` | 默认加载 |
| 条件加载 | `inclusion: fileMatch` | 子目录 CLAUDE.md + rules 的 `paths` 字段 | `globs: ["*.ts"]` | 不支持 |
| 手动加载 | `inclusion: manual` | 不支持 | `@rulename` | 不支持 |
| 文件引用 | `#[[file:path]]` | `@path/to/file` | `@filename` | 不支持 |
| 前置元数据 | YAML frontmatter | rules 支持 YAML frontmatter | YAML frontmatter | 不需要 |
| 模块化规则 | 多文件 steering | `.claude/rules/*.md` | 多文件 rules | 单文件 |

---

## Kiro 配置

Kiro 使用 `.kiro/steering/` 目录下的 Markdown 文件作为 steering 规则。

### 目录结构

```
.kiro/
├── steering/
│   ├── doc-maintenance.md      # 文档维护规则（始终加载）
│   └── project-structure.md    # 项目结构导航（始终加载）
└── templates/
    ├── folder-readme.md        # 文件夹 README 模板
    ├── file-header-go.txt      # Go 文件头部注释模板
    ├── file-header-ts.txt      # TypeScript 文件头部注释模板
    ├── file-header-py.txt      # Python 文件头部注释模板
    └── file-header-cpp.txt     # C++ 文件头部注释模板
```

### doc-maintenance.md 示例

```markdown
---
inclusion: always
---

# 文档维护自动提醒

当你修改或创建代码文件时，**必须**执行以下文档维护步骤：

## 🔴 强制执行清单

### 1. 文件头部注释
每个代码文件必须有标准三行注释：

**Go 文件模板**：#[[file:.kiro/templates/file-header-go.txt]]
**TypeScript 文件模板**：#[[file:.kiro/templates/file-header-ts.txt]]
**Python 文件模板**：#[[file:.kiro/templates/file-header-py.txt]]
**C++ 文件模板**：#[[file:.kiro/templates/file-header-cpp.txt]]

### 2. 文件夹 README.md
修改文件后，必须更新所属文件夹的 README.md：

**文件夹 README 模板**：#[[file:.kiro/templates/folder-readme.md]]

### 3. 上级目录传播
检查上级目录的 README.md 是否需要更新。
```

### project-structure.md 示例

```markdown
---
inclusion: always
---

# 项目结构导航

## 核心目录索引

### 后端 API
#[[file:apps/admin-api/internal/README.md]]

### 控制器层
#[[file:apps/admin-api/internal/controller/README.md]]

### 服务层
#[[file:apps/admin-api/internal/service/README.md]]
```

### Inclusion 模式说明

- `always` - 每次交互都加载
- `fileMatch` - 当编辑器中激活的文件匹配 `fileMatchPattern` 时加载
- `manual` - 用户通过 `#rulename` 手动引用时加载

---

## Claude Code 配置

Claude Code 使用 `CLAUDE.md` 文件和 `.claude/rules/` 目录作为项目指令。

### 内存层级结构

Claude Code 提供四级内存层级：

| 内存类型 | 位置 | 用途 | 共享范围 |
|---------|------|------|---------|
| 企业策略 | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | 组织级指令 | 所有用户 |
| 项目内存 | `./CLAUDE.md` 或 `./.claude/CLAUDE.md` | 团队共享指令 | 团队成员 |
| 项目规则 | `./.claude/rules/*.md` | 模块化主题指令 | 团队成员 |
| 用户内存 | `~/.claude/CLAUDE.md` | 个人偏好 | 仅自己 |
| 本地项目 | `./CLAUDE.local.md` | 个人项目偏好 | 仅自己 |

### 目录结构

```
project/
├── CLAUDE.md                           # 根目录主配置（团队共享）
├── CLAUDE.local.md                     # 本地配置（不提交到 git）
├── .claude/
│   ├── CLAUDE.md                       # 替代根目录配置
│   ├── rules/                          # 模块化规则目录 ⭐ 新功能
│   │   ├── doc-maintenance.md          # 文档维护规则
│   │   ├── go-style.md                 # Go 代码风格规则
│   │   └── testing.md                  # 测试规范规则
│   └── commands/                       # 自定义命令
│       └── performance-optimization.md
└── apps/
    └── admin-api/
        └── CLAUDE.md                   # 子目录配置（自动加载）
```

### CLAUDE.md 示例

```markdown
# 项目开发规则

## 关于本项目

Go + React 全栈项目，后端使用 Gin + GORM，前端使用 Ant Design Pro。

## 项目结构

- `apps/admin-api/` - Go 后端 API
- `apps/admin-web/` - React 管理后台
- `docker/` - 部署配置

## 核心规则

1. **数据库变更** - 禁止修改 `docker/db/01_schema.sql`，必须在 `docker/migrations/` 创建迁移文件
2. **租户隔离** - 所有业务查询必须带 `tenant_id`
3. **npm 安装** - 必须使用 `npm install --legacy-peer-deps`

## 常用命令

```bash
cd docker && make help     # 查看命令
./deploy/deploy.sh --build # 部署
```

## 文件引用

参考以下文件了解项目结构：
@apps/admin-api/internal/README.md
@apps/admin-api/internal/controller/README.md
@apps/admin-api/internal/service/README.md

```

### .claude/rules/ 模块化规则 ⭐ 新功能

Claude Code 现在支持 `.claude/rules/` 目录，可以将规则拆分成多个文件：

**doc-maintenance.md** - 文档维护规则：

```markdown
---
paths:
  - "**/*.go"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.py"
  - "**/*.cpp"
  - "**/*.hpp"
  - "**/*.h"
---

# 文档维护规则

当你修改或创建代码文件时，必须执行以下步骤：

## 1. 文件头部注释

每个代码文件必须有标准三行注释：

Go 文件：
```go
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
```

TypeScript 文件：

```typescript
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
```

Python 文件：

```python
# input: {INPUT_DESCRIPTION}
# output: {OUTPUT_DESCRIPTION}
# pos: {POSITION_DESCRIPTION}
```

C++ 文件（.cpp/.hpp/.h）：

```cpp
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
```

## 2. 文件夹 README.md

修改文件后，必须更新所属文件夹的 README.md：

- 如果不存在，创建新的 README.md
- 如果存在，更新文件索引部分

## 3. 上级目录传播

检查上级目录的 README.md 是否需要更新。

```

**go-style.md** - Go 代码风格规则（条件加载）：

```markdown
---
paths:
  - "**/*.go"
---

# Go 代码风格

- 使用 gofmt 格式化代码
- 错误处理不能忽略，必须处理或显式忽略
- 使用有意义的变量名，避免单字母变量（循环变量除外）
- 公开函数必须有注释
```

### paths 字段支持的 Glob 模式

| 模式 | 匹配 |
|------|------|
| `**/*.ts` | 所有目录下的 TypeScript 文件 |
| `src/**/*` | src 目录下的所有文件 |
| `*.md` | 项目根目录的 Markdown 文件 |
| `src/components/*.tsx` | 特定目录的 React 组件 |
| `{src,lib}/**/*.ts` | 多个目录的 TypeScript 文件 |

没有 `paths` 字段的规则会无条件加载，适用于所有文件。

### 文件引用语法

CLAUDE.md 支持使用 `@path/to/file` 语法引用其他文件：

```markdown
## 项目结构

参考以下文件：
@apps/admin-api/internal/README.md
@docs/architecture.md
```

引用的文件内容会被自动加载到上下文中。

### 自定义命令

在 `.claude/commands/` 目录创建 Markdown 文件，可以定义自定义斜杠命令：

**performance-optimization.md**：

```markdown
# 性能优化分析

分析提供的代码，检查以下性能问题：

## 检查项

- 数据库 N+1 查询问题
- 缺少索引的查询
- 内存泄漏风险
- 不必要的循环嵌套
- 缺少缓存的重复计算

## 输出格式

对于每个发现的问题：
1. **问题**：描述性能问题
2. **位置**：文件/函数/行号
3. **影响**：严重程度（高/中/低）
4. **建议**：优化方案
5. **代码示例**：优化后的代码

**要分析的代码：**
$ARGUMENTS
```

使用方式：`/performance-optimization @src/service/user.go`

---

## Cursor 配置

Cursor 使用 `.cursor/rules/` 目录下的 `.mdc` 文件作为规则。

### 目录结构

```
project/
├── .cursor/
│   └── rules/
│       ├── doc-maintenance.mdc    # 文档维护规则
│       └── project-structure.mdc  # 项目结构规则
└── .cursorrules                   # 已废弃，但仍支持
```

### doc-maintenance.mdc 示例

```markdown
---
description: 文档维护自动提醒
globs:
alwaysApply: true
---

# 文档维护规则

当你修改或创建代码文件（.go, .ts, .tsx, .js, .jsx, .py, .cpp, .hpp, .h）时，必须执行以下步骤：

## 1. 文件头部注释

每个代码文件必须有标准三行注释：

Go 文件：
```go
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
```

TypeScript 文件：

```typescript
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
```

Python 文件：

```python
# input: {INPUT_DESCRIPTION}
# output: {OUTPUT_DESCRIPTION}
# pos: {POSITION_DESCRIPTION}
```

C++ 文件（.cpp/.hpp/.h）：

```cpp
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
```

## 2. 文件夹 README.md

修改文件后，必须更新所属文件夹的 README.md：

- 如果不存在，创建新的 README.md
- 如果存在，更新文件索引部分

## 3. 上级目录传播

检查上级目录的 README.md 是否需要更新。

```

### project-structure.mdc 示例

```markdown
---
description: 项目结构导航
globs:
alwaysApply: true
---

# 项目结构

了解项目结构时，参考以下文件：

- @apps/admin-api/internal/README.md - 后端核心目录
- @apps/admin-api/internal/controller/README.md - 控制器层
- @apps/admin-api/internal/service/README.md - 服务层
- @apps/admin-api/internal/entities/README.md - 实体定义
```

### Rule Types 说明

- `alwaysApply: true` - 每次交互都加载
- `globs: ["**/*.ts"]` - 当打开匹配的文件时自动加载
- 无 globs 且 `alwaysApply: false` - 需要 AI 主动请求或用户 `@rulename` 引用

---

## Windsurf 配置

Windsurf 使用 `.windsurfrules` 文件作为工作区规则。

### 目录结构

```
project/
└── .windsurfrules    # 工作区规则文件
```

### .windsurfrules 示例

```markdown
# 项目开发规则

<doc-maintenance>
## 文档维护规范

当你修改或创建代码文件时，必须执行以下步骤：

### 1. 文件头部注释
每个代码文件必须有标准三行注释：

Go 文件格式：
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}

TypeScript 文件格式：
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}

Python 文件格式：
# input: {INPUT_DESCRIPTION}
# output: {OUTPUT_DESCRIPTION}
# pos: {POSITION_DESCRIPTION}

C++ 文件格式（.cpp/.hpp/.h）：
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}

### 2. 文件夹 README.md
修改文件后，必须更新所属文件夹的 README.md。

### 3. 上级目录传播
检查上级目录的 README.md 是否需要更新。
</doc-maintenance>

<project-structure>
## 项目结构

### 后端 API 目录
- apps/admin-api/internal/ - Go 后端核心业务代码
- apps/admin-api/internal/controller/ - HTTP 控制器层
- apps/admin-api/internal/service/ - 业务服务层
- apps/admin-api/internal/entities/ - API 实体定义

### 前端目录
- apps/admin-web/ - React 管理后台
- apps/ops-web/ - React 运营后台
</project-structure>

<core-rules>
## 核心规则

1. 数据库变更 - 禁止修改 docker/db/01_schema.sql，必须在 docker/migrations/ 创建迁移文件
2. 租户隔离 - 所有业务查询必须带 tenant_id
3. npm 安装 - 必须使用 npm install --legacy-peer-deps
4. 密码加密 - SHA256 直接 hash
</core-rules>
```

### Windsurf 特点

- 使用 XML 标签分组规则，便于组织
- 不支持文件引用语法
- 不支持条件加载
- 规则文件始终加载

---

## 通用 AGENTS.md 配置

对于不支持特定 steering 机制的编辑器，可以使用 `AGENTS.md` 作为通用配置：

```markdown
# AI Agent 开发规则

## 文档维护规范

### 分形结构要求
- 每个文件夹必须有 README.md（3行以内架构说明 + 文件索引）
- 每个文件开头必须有三行注释（input/output/pos）
- 文件变更时必须更新开头注释和所属文件夹的索引文档

### 文件头部注释模板

Go 文件：
```go
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
// 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

TypeScript 文件：

```typescript
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
// 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

Python 文件：

```python
# input: {INPUT_DESCRIPTION}
# output: {OUTPUT_DESCRIPTION}
# pos: {POSITION_DESCRIPTION}
# 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

C++ 文件（.cpp/.hpp/.h）：

```cpp
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
// 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

### 文件夹 README.md 模板

```markdown
# {FOLDER_NAME}

<!-- 一旦我所属的文件夹有所变化，请更新我 -->

## 架构说明

{3行以内的架构描述}

## 文件索引

- `file1.go` - 功能描述
- `file2.py` - 功能描述

## 更新提醒

任何文件变更后，请更新此文档和相关的上级文档。
```

### 执行清单

完成代码修改后，按以下格式输出文档维护报告：

```
## 文档维护报告

### 修改的文件
- `path/to/file.go` - [新建/修改]

### 文件注释状态
- ✅ 已有标准注释 / ⚠️ 已更新注释 / 🆕 已添加注释

### README.md 更新
- `path/to/folder/README.md` - [已更新/已创建/无需更新]
```

## 项目结构索引

### 后端 API

- `apps/admin-api/internal/README.md` - 核心业务代码目录索引
- `apps/admin-api/internal/controller/README.md` - 控制器层索引
- `apps/admin-api/internal/service/README.md` - 服务层索引
- `apps/admin-api/internal/entities/README.md` - 实体定义索引

```

---

## 快速开始

### 1. 选择你的编辑器

根据你使用的 AI 编辑器，复制对应的配置文件到项目中。

### 2. 创建模板文件

创建以下模板文件供 AI 参考：

**文件夹 README 模板** (`templates/folder-readme.md`)：
```markdown
# {FOLDER_NAME}

<!-- 一旦我所属的文件夹有所变化，请更新我 -->

## 架构说明

{ARCHITECTURE_DESCRIPTION}

## 文件索引

{FILE_INDEX}

## 更新提醒

任何文件变更后，请更新此文档和相关的上级文档。
```

**Go 文件头部模板** (`templates/file-header-go.txt`)：

```go
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
// 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

**TypeScript 文件头部模板** (`templates/file-header-ts.txt`)：

```typescript
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
// 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

**Python 文件头部模板** (`templates/file-header-py.txt`)：

```python
# input: {INPUT_DESCRIPTION}
# output: {OUTPUT_DESCRIPTION}
# pos: {POSITION_DESCRIPTION}
# 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

**C++ 文件头部模板** (`templates/file-header-cpp.txt`)：

```cpp
// input: {INPUT_DESCRIPTION}
// output: {OUTPUT_DESCRIPTION}
// pos: {POSITION_DESCRIPTION}
// 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
```

### 3. 初始化核心目录的 README.md

为项目的核心目录创建 README.md 索引文件，让 AI 可以快速了解项目结构。

### 4. 测试效果

修改一个代码文件，观察 AI 是否自动：

1. 更新文件头部注释
2. 更新所属文件夹的 README.md
3. 输出文档维护报告

---

## 最佳实践

1. **保持 README.md 简洁** - 架构说明不超过 3 行，文件索引只列出关键信息
2. **使用一致的注释格式** - 所有文件使用相同的 input/output/pos 格式
3. **定期检查文档同步** - 确保 README.md 与实际文件结构一致
4. **利用自指提醒** - 在文档中加入更新提醒，帮助 AI 记住维护任务
5. **分层索引** - 大型项目使用多级 README.md，避免单个文件过长

---

## 参考资源

- [Kiro Steering 文档](https://kiro.dev/docs/steering)
- [Claude Code Memory 管理](https://code.claude.com/docs/en/memory) - 官方内存/规则配置文档
- [Claude Code CLAUDE.md 指南](https://www.claude.com/blog/using-claude-md-files) - 官方博客详细教程
- [Cursor Rules 文档](https://docs.cursor.com/context/rules)
- [Windsurf Rules 文档](https://docs.windsurf.com/windsurf/memories#rules)

---

*此文档基于 2024 年 12 月各 AI 编辑器的最新版本编写。Claude Code 的 `.claude/rules/` 功能是最新添加的特性，具体功能可能随版本更新而变化。*
