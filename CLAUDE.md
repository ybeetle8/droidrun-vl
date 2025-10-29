# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

DroidRun 是一个通过 LLM 代理控制 Android 和 iOS 设备的框架。它允许使用自然语言命令自动化设备交互。

## 文档操作
文档都写到 notes 目录中,用md格式,用中文命名

## 核心命令

### 安装和开发环境设置
```bash
# 安装项目（带开发依赖）
pip install -e ".[dev]"

# 安装特定提供商的依赖
pip install 'droidrun[google,anthropic,openai,deepseek,ollama,dev]'
```

### 运行 DroidRun
```bash
# 基本运行
droidrun "你的自然语言命令"

# 使用特定设备
droidrun "命令" --device SERIAL_NUMBER

# 启用调试模式
droidrun "命令" --debug

# 启用视觉能力
droidrun "命令" --vision

# 启用推理模式（使用 PlannerAgent）
droidrun "命令" --reasoning

# 启用追踪（Arize Phoenix）
droidrun "命令" --tracing
```

### 代码质量检查
```bash
# 代码格式化
ruff format droidrun

# 代码检查
ruff check droidrun

# 安全检查
bandit -r droidrun
safety scan
```

## 架构概览

### 三层代理架构

DroidRun 使用分层架构实现复杂的设备控制：

1. **DroidAgent** (droidrun/agent/droid/droid_agent.py)
   - 顶层协调器，管理整个任务执行流程
   - 协调 PlannerAgent 和 CodeActAgent 之间的交互
   - 基于 llama-index 的 Workflow 系统实现

2. **PlannerAgent** (droidrun/agent/planner/planner_agent.py)
   - 负责任务规划和分解
   - 使用 TaskManager 管理任务状态
   - 将复杂目标分解为可执行的子任务
   - 只在 `--reasoning` 模式下启用

3. **CodeActAgent** (droidrun/agent/codeact/codeact_agent.py)
   - 执行具体操作的代理
   - 使用 ReAct 循环：思考 -> 代码 -> 观察
   - 通过 Python 代码执行工具函数

### Persona 系统

代理使用 Persona 系统实现专业化（droidrun/agent/context/）：

- **AgentPersona** (agent_persona.py): 定义代理的系统提示、允许工具和专业领域
- **ContextInjectionManager** (context_injection_manager.py): 管理不同的 Persona
- **预定义 Personas** (context/personas/):
  - `DEFAULT`: 通用 UI 交互
  - `BIG_AGENT`: 复杂任务处理
  - `UI_EXPERT`: UI 专家
  - `APP_STARTER`: 应用启动专家

### 工具系统

工具提供设备交互能力（droidrun/tools/）：

- **Tools** (tools.py): 基类，定义工具接口
- **AdbTools** (adb.py): Android 设备控制（通过 ADB）
  - 支持 TCP 和标准 ADB 连接
  - 提供截图、点击、滑动、输入等功能
  - 维护可点击元素缓存用于索引式点击
- **IOSTools** (ios.py): iOS 设备控制

### 上下文管理

- **TaskManager** (context/task_manager.py): 管理任务列表和状态（pending/completed/failed）
- **EpisodicMemory** (context/episodic_memory.py): 存储代理的执行历史
- **Reflection** (context/reflection.py): 反思和学习机制

### 工作流事件系统

使用 llama-index 的事件驱动工作流：
- **Common Events** (agent/common/events.py): ScreenshotEvent, MacroEvent 等
- **Droid Events** (agent/droid/events.py): DroidAgent 特定事件
- **Planner Events** (agent/planner/events.py): 规划相关事件
- **CodeAct Events** (agent/codeact/events.py): 执行相关事件

### CLI 入口

- **main.py** (cli/main.py): 命令行接口主入口
- **logs.py** (cli/logs.py): 日志处理和富文本输出

### Portal 通信

- **portal.py**: 管理 Android Portal APK 的下载、安装和通信
- 支持 TCP 和 Content Provider 两种通信方式

## 关键设计模式

1. **Workflow 模式**: 使用 llama-index 的 Workflow 和 Step 装饰器实现异步任务流
2. **事件驱动**: 组件之间通过事件通信（StartEvent, StopEvent, 自定义事件）
3. **工具注入**: 根据 Persona 动态过滤和注入可用工具
4. **上下文保持**: 使用 llama-index 的 Context 在工作流步骤间共享状态

## 依赖关系

- **llama-index 0.14.4**: 核心 LLM 框架和工作流引擎
- **adbutils**: Android 设备通信
- **rich**: 终端富文本输出
- **pydantic**: 数据验证
- 支持多个 LLM 提供商：OpenAI, Anthropic, Google, DeepSeek, Ollama

## 测试和开发

项目当前没有测试目录，开发时注意：
- 使用 `--debug` 模式查看详细执行日志
- 使用 `--tracing` 启用 Arize Phoenix 追踪
- 安全检查是必需的：运行 `bandit` 和 `safety` 检查

## 重要注意事项

- 代码使用 Python 3.11+
- 所有核心代理都基于 llama-index Workflow
- TaskManager 维护任务历史，而不是即时更新任务列表
- Persona 系统允许创建专业化代理而无需修改核心代码
- 支持保存执行轨迹（`save_trajectories`: "none"/"step"/"action"）
