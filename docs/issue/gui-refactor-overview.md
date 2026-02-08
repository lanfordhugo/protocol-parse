# V8Parse GUI 重构总体计划（MVP 模式）

**文档版本**: v3.0（最终完成版）
**修订日期**: 2025-02-08
**原始日期**: 2025-02-02
**状态**: ✅ Phase 1/2/3 全部完成

## 修订说明

v1.0 方案存在以下关键问题，v2.0 已修正：

| 问题 | v1.0 | v2.0 修正 |
|------|------|-----------|
| 架构模式错误 | MVVM（ViewModel） | **MVP（Model-View-Presenter）** |
| Service 层依赖 Qt | `ProtocolService(QObject)` 带 Signal | Model 层为纯 Python 类，不依赖 Qt |
| 文件路径错误 | 引用 `gui/pages/normal_parse_page.py` | 使用实际路径 `gui/normal_parse_page.py` |
| 过度工程 | SignalManager/WorkerManager/AppSignals 全局单例 | 去掉不必要的全局单例，保持务实 |
| fallback 策略 | try/except 新旧代码并行 | 直接重构，无双代码路径 |

## 执行摘要

将 V8Parse GUI 重构为 **MVP（Model-View-Presenter）** 模式，分 3 个阶段执行。
每阶段保证功能完全一致，仅修改代码架构。

### 重构目标

1. **建立 MVP 分层架构**：
   - View 层：PySide6 UI 组件，实现 View 接口
   - Presenter 层：协调 View 和 Model 的交互逻辑
   - Model 层：纯 Python 业务逻辑，不依赖 Qt

2. **解决核心问题**：
   - UI 与业务逻辑耦合（NormalParsePage 直接调用 YamlConfigLoader 等）
   - TcpServerPage 单文件过大（796 行）
   - 缺乏测试

3. **约束条件**：
   - 功能完全不变
   - 单文件 <600 行
   - 中文注释

### MVP 模式说明

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   View      │◄────►│  Presenter   │─────►│   Model     │
│ (Qt Widget) │      │ (协调逻辑)    │      │ (纯Python)  │
│ 实现接口     │      │ 持有View引用  │      │ 业务+数据   │
└─────────────┘      └──────────────┘      └─────────────┘

- View: 只负责 UI 展示，通过接口暴露操作
- Presenter: 处理用户交互逻辑，调用 Model，更新 View
- Model: 封装业务逻辑（协议发现/加载/验证/解析），不依赖 Qt
```

---

## 三阶段总览

### 阶段1：NormalParsePage MVP 重构

**目标**：对主页面建立 MVP 架构，分离 UI 与业务逻辑

**核心工作**：
- 创建 Model 层：`ProtocolModel`（协议发现/加载/验证）、`ParseModel`（解析）
- 创建 View 接口：`INormalParsePageView`
- 创建 Presenter：`NormalParsePresenter`
- 创建统一配置：`gui/config.py`
- 重构 `NormalParsePage` 实现 View 接口，注入 Presenter

**验收标准**：
- [ ] 所有现有功能正常（协议选择、详情、解析、验证、拖拽）
- [ ] UI 代码不再直接导入 `src.yaml_config`、`validate_configs` 等核心模块
- [ ] Model 层为纯 Python（不 import PySide6）
- [ ] PyInstaller 打包成功

### 阶段2：TcpServerPage 拆分 + MVP 重构

**目标**：拆分 796 行大文件，建立 MVP 架构

**核心工作**：
- 拆分 `tcp_log/server_panel.py` 为多个子组件
- 创建 `TcpServerModel`、`ITcpServerPageView`、`TcpServerPresenter`
- 确保所有文件 <600 行

**验收标准**：
- [ ] TCP 服务端所有功能正常
- [ ] 单文件 <600 行
- [ ] Model 层无 Qt 依赖

### 阶段3：质量提升

**目标**：补充测试、完善文档

**核心工作**：
- Model 层和 Presenter 层单元测试
- 功能验证
- 文档完善

---

## 目标架构

### MVP 分层架构图

```
┌───────────────────────────────────────────────────────────┐
│                    View Layer (UI)                         │
│  ┌─────────────────────┐  ┌─────────────────────┐        │
│  │ NormalParsePage      │  │ TcpServerPage       │        │
│  │ (实现 IView 接口)    │  │ (实现 IView 接口)    │        │
│  │ 只处理 UI 展示       │  │ 只处理 UI 展示       │        │
│  └──────────┬──────────┘  └──────────┬──────────┘        │
└─────────────┼─────────────────────────┼──────────────────┘
              │ 调用 Presenter 方法      │
              ▼                          ▼
┌───────────────────────────────────────────────────────────┐
│                  Presenter Layer                           │
│  ┌─────────────────────┐  ┌─────────────────────┐        │
│  │ NormalParsePresenter │  │ TcpServerPresenter  │        │
│  │ - 持有 View 接口引用  │  │ - 持有 View 接口引用 │        │
│  │ - 协调 Model 和 View │  │ - 协调 Model 和 View│        │
│  └──────────┬──────────┘  └──────────┬──────────┘        │
└─────────────┼─────────────────────────┼──────────────────┘
              │ 调用 Model 方法          │
              ▼                          ▼
┌───────────────────────────────────────────────────────────┐
│                   Model Layer (纯 Python)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ProtocolModel │  │ ParseModel   │  │ TcpModel     │    │
│  │ 协议发现/加载 │  │ 日志解析     │  │ TCP业务逻辑  │    │
│  │ 协议验证     │  │ 结果处理     │  │              │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼──────────────────┼──────────────────┼───────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌───────────────────────────────────────────────────────────┐
│                    Core Layer (现有)                        │
│  YamlConfigLoader, YamlUnifiedProtocol, ConfigValidator    │
│  TcpLogServer, YamlCmdFormat, LogEntryParser               │
└───────────────────────────────────────────────────────────┘
```

### 目录结构（实际路径）

```
gui/
├── config.py                    # 新增：统一配置常量（阶段1）
├── models/                      # 新增：Model 层（阶段1）
│   ├── __init__.py
│   ├── protocol_model.py        # 协议发现/加载/验证
│   └── parse_model.py           # 解析业务逻辑
├── views/                       # 新增：View 接口（阶段1）
│   ├── __init__.py
│   └── i_normal_parse_view.py   # NormalParsePage 的 View 接口
├── presenters/                  # 新增：Presenter 层（阶段1）
│   ├── __init__.py
│   └── normal_parse_presenter.py
├── normal_parse_page.py         # 修改：实现 View 接口，注入 Presenter
├── detail_panel.py              # 保持：View 子组件
├── protocol_panel.py            # 保持：View 子组件
├── log_panel.py                 # 保持：View 子组件
├── sidebar.py                   # 保持
├── unified_main_window.py       # 微调：创建 Presenter 并注入
├── shared/                      # 现有共享工具
├── widgets/                     # 现有自定义控件
├── workers/                     # 现有工作线程
└── themes.py                    # 保持

tcp_log/
├── server_panel.py              # 阶段2：拆分为多个子组件
├── server_config_widget.py      # 阶段2新增：服务器配置 UI
├── parse_result_widget.py       # 阶段2新增：解析结果表格
├── stats_widget.py              # 阶段2新增：统计组件
├── models/                      # 阶段2新增
│   └── tcp_server_model.py
├── views/                       # 阶段2新增
│   └── i_tcp_server_view.py
├── presenters/                  # 阶段2新增
│   └── tcp_server_presenter.py
└── ...                          # 其他现有文件保持不变

tests/gui/                       # 阶段3：测试
├── conftest.py
├── models/
│   ├── test_protocol_model.py
│   └── test_parse_model.py
└── presenters/
    └── test_normal_parse_presenter.py
```

---

## 详细计划文档

1. [阶段1计划](./gui-refactor-phase1-plan.md) - NormalParsePage MVP 重构
2. [阶段2计划](./gui-refactor-phase2-plan.md) - TcpServerPage 拆分 + MVP
3. [阶段3计划](./gui-refactor-phase3-plan.md) - 测试和质量提升

---

## 验收标准

### 功能验收（最高优先级）
- [ ] 所有现有功能 100% 正常
- [ ] PyInstaller 打包成功

### 架构验收
- [ ] MVP 分层清晰（View → Presenter → Model）
- [ ] Model 层不依赖 PySide6
- [ ] UI 代码不直接导入 Core 层模块
- [ ] 单文件 <600 行

### 质量验收
- [ ] Model/Presenter 层有单元测试
- [ ] 所有代码有中文注释
