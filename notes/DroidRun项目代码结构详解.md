# DroidRun 项目完整代码结构分析

## 项目概览

DroidRun 是一个通过 LLM 代理控制 Android 和 iOS 设备的自动化框架，允许使用自然语言命令进行设备交互。项目基于 llama-index 的 Workflow 系统实现，采用三层代理架构。

**版本**: 0.3.0
**核心依赖**: llama-index 0.14.4, adbutils, rich, pydantic
**支持平台**: Android (ADB), iOS (HTTP API)

---

## 完整目录树形结构

```
droidrun/
├── setup.py                             # 项目安装配置
├── adb.py                               # ADB 工具命令行脚本
│
├── droidrun/                            # 核心包
│   ├── __init__.py                      # 包入口，导出核心类和功能
│   ├── __main__.py                      # 模块入口，调用 CLI
│   ├── portal.py                        # Android Portal APK 管理和通信
│   │
│   ├── agent/                           # 代理模块（核心智能层）
│   │   ├── __init__.py                  # 导出 CodeActAgent 和 DroidAgent
│   │   ├── usage.py                     # LLM token 使用追踪
│   │   │
│   │   ├── common/                      # 通用组件
│   │   │   ├── events.py                # 通用事件定义（ScreenshotEvent、MacroEvent 等）
│   │   │   ├── default.py               # Mock Workflow（测试用）
│   │   │   └── constants.py             # 常量配置（LLM_HISTORY_LIMIT）
│   │   │
│   │   ├── context/                     # 上下文管理
│   │   │   ├── __init__.py              # 导出上下文相关类
│   │   │   ├── agent_persona.py         # AgentPersona 数据类定义
│   │   │   ├── context_injection_manager.py # Persona 管理器
│   │   │   ├── task_manager.py          # 任务状态管理（pending/completed/failed）
│   │   │   ├── episodic_memory.py       # 代理执行历史存储
│   │   │   ├── reflection.py            # 反思机制数据类
│   │   │   │
│   │   │   └── personas/                # 预定义 Persona 配置
│   │   │       ├── __init__.py          # 导出所有 Persona
│   │   │       ├── default.py           # 默认通用 Persona
│   │   │       ├── big_agent.py         # 复杂任务 Persona（包含 drag）
│   │   │       ├── ui_expert.py         # UI 交互专家 Persona
│   │   │       └── app_starter.py       # 应用启动专家 Persona
│   │   │
│   │   ├── droid/                       # DroidAgent（顶层协调器）
│   │   │   ├── __init__.py              # 导出 DroidAgent 和相关组件
│   │   │   ├── droid_agent.py           # DroidAgent 主类（协调 Planner 和 CodeAct）
│   │   │   └── events.py                # DroidAgent 事件定义
│   │   │
│   │   ├── planner/                     # PlannerAgent（任务规划）
│   │   │   ├── __init__.py              # 导出 PlannerAgent 和 prompts
│   │   │   ├── planner_agent.py         # PlannerAgent 主类（任务分解和规划）
│   │   │   ├── events.py                # 规划事件定义
│   │   │   └── prompts.py               # 规划提示词模板
│   │   │
│   │   ├── codeact/                     # CodeActAgent（任务执行）
│   │   │   ├── __init__.py              # 导出 CodeActAgent 和 prompts
│   │   │   ├── codeact_agent.py         # CodeActAgent 主类（ReAct 循环执行）
│   │   │   ├── events.py                # 执行事件定义
│   │   │   └── prompts.py               # 执行提示词模板
│   │   │
│   │   ├── oneflows/                    # 反思流程
│   │   │   └── reflector.py             # Reflector 类（反思和学习机制）
│   │   │
│   │   └── utils/                       # 工具函数
│   │       ├── __init__.py              # 空模块
│   │       ├── async_utils.py           # 异步转同步工具
│   │       ├── llm_picker.py            # LLM 动态加载器
│   │       ├── trajectory.py            # 轨迹记录和管理
│   │       ├── executer.py              # Python 代码执行器
│   │       └── chat_utils.py            # 聊天消息处理工具
│   │
│   ├── tools/                           # 设备控制工具层
│   │   ├── __init__.py                  # 导出 Tools、AdbTools、IOSTools
│   │   ├── tools.py                     # Tools 抽象基类
│   │   ├── adb.py                       # AdbTools（Android 设备控制）
│   │   └── ios.py                       # IOSTools（iOS 设备控制）
│   │
│   ├── cli/                             # 命令行接口
│   │   ├── __init__.py                  # 导出 cli 函数
│   │   ├── main.py                      # 主命令行入口（droidrun 命令）
│   │   └── logs.py                      # 日志处理和富文本输出
│   │
│   ├── macro/                           # 宏录制和回放
│   │   ├── __init__.py                  # 导出 MacroPlayer 和回放函数
│   │   ├── __main__.py                  # 宏模块入口
│   │   ├── replay.py                    # MacroPlayer 类（宏回放引擎）
│   │   └── cli.py                       # 宏命令行接口
│   │
│   └── telemetry/                       # 遥测数据收集
│       ├── __init__.py                  # 导出遥测函数和事件
│       ├── events.py                    # 遥测事件定义
│       └── tracker.py                   # PostHog 遥测追踪器
│
├── test_*.py                            # 测试脚本
├── batch_runner*.py                     # 批量任务运行器
├── simple_example.py                    # 简单示例
└── debug_cli_params.py                  # CLI 参数调试
```

---

## 核心模块详细说明

### 1. 根目录文件

#### `droidrun/__init__.py`
**功能**: 包级别入口，定义包版本和导出核心类

**关键导出**:
```python
__version__ = "0.3.0"

# 核心代理
from droidrun.agent import DroidAgent

# LLM 加载
from droidrun.agent.utils.llm_picker import load_llm

# 设备控制工具
from droidrun.tools import Tools, AdbTools, IOSTools

# 宏回放功能
from droidrun.macro import MacroPlayer, replay_macro_file, replay_macro_folder
```

#### `droidrun/__main__.py`
**功能**: Python 模块入口 (`python -m droidrun`)

**实现**: 调用 `droidrun.cli.main.cli()`

#### `droidrun/portal.py`
**功能**: 管理 Android Portal APK 的下载、安装和通信

**核心函数**:
- `download_portal_apk()`: 从 GitHub releases 下载最新 APK
- `enable_portal_accessibility()`: 启用无障碍服务
- `ping_portal()`: 检查 Portal 是否可用
- `ping_portal_tcp()` / `ping_portal_content()`: TCP/Content Provider 通信检测
- `setup_keyboard()`: 配置 DroidRun 键盘
- `toggle_overlay()`: 控制覆盖层显示
- `set_overlay_offset()`: 设置覆盖层偏移

**通信方式**:
- **TCP 模式**: 通过端口转发与 Portal 通信（高性能）
- **Content Provider 模式**: 通过 ADB shell content 命令通信（兼容性好）

---

### 2. agent/ - 代理模块（核心智能层）

#### 2.1 架构概览

DroidRun 采用**三层代理架构**，每层有明确的职责：

```
┌─────────────────────────────────────────┐
│         DroidAgent (顶层协调器)          │
│  - 管理整体执行流程                      │
│  - 协调 Planner 和 CodeAct               │
│  - 处理反思和轨迹保存                    │
└─────────────┬───────────────────────────┘
              │
      ┌───────┴────────┐
      │                │
┌─────▼──────┐  ┌─────▼──────┐
│  Planner   │  │  CodeAct   │
│  Agent     │  │  Agent     │
│ (任务规划) │  │ (任务执行) │
└────────────┘  └────────────┘
```

---

#### 2.2 `agent/common/` - 通用组件

##### `events.py`
**功能**: 定义跨模块共享的事件类型

**事件类型**:
- `ScreenshotEvent`: 截图事件（包含图像数据）
- `MacroEvent`: 宏操作基类
- `TapActionEvent`: 点击动作（index 或坐标）
- `SwipeActionEvent`: 滑动动作（起点、终点、持续时间）
- `DragActionEvent`: 拖拽动作
- `InputTextActionEvent`: 文本输入
- `KeyPressActionEvent`: 按键事件（keycode）
- `StartAppEvent`: 应用启动（package、activity）
- `RecordUIStateEvent`: UI 状态记录

##### `constants.py`
**功能**: 定义全局常量

**常量**:
```python
LLM_HISTORY_LIMIT = int(os.environ.get("LLM_HISTORY_LIMIT", "20"))
```

##### `default.py`
**功能**: 提供 Mock Workflow 用于测试

---

#### 2.3 `agent/context/` - 上下文管理

##### `agent_persona.py`
**功能**: 定义 AgentPersona 数据类，描述代理的"人格"和能力

**字段**:
```python
@dataclass
class AgentPersona:
    name: str                           # Persona 名称
    system_prompt: str                  # 系统提示词
    user_prompt: str                    # 用户提示词模板
    description: str                    # 描述
    allowed_tools: Optional[List[str]]  # 允许使用的工具列表
    required_context: List[str]         # 需要的上下文信息
    expertise_areas: List[str]          # 专业领域列表
```

**作用**: 定义专业化代理的行为和能力边界

##### `context_injection_manager.py`
**功能**: 管理和切换不同的 AgentPersona

**核心方法**:
```python
class ContextInjectionManager:
    def __init__(self, personas: List[AgentPersona])
    def get_persona(self, agent_type: str) -> AgentPersona
    def get_all_personas(self) -> Dict[str, AgentPersona]
```

**作用**: 根据任务类型动态切换 Persona

##### `task_manager.py`
**功能**: 管理任务队列和状态

**核心类**:
```python
@dataclass
class Task:
    description: str                    # 任务描述
    status: Literal["pending", "completed", "failed"]
    agent_type: str                     # 负责的 Agent 类型
    message: Optional[str] = None       # 成功消息
    failure_reason: Optional[str] = None # 失败原因
```

**TaskManager 方法**:
- `set_tasks_with_agents(task_assignments)`: 设置任务队列
- `get_current_task()`: 获取下一个待执行任务
- `complete_task(message)`: 标记任务完成
- `fail_task(reason)`: 标记任务失败
- `get_task_history()`: 获取完整历史（包含成功和失败）
- `complete_goal(message)`: 标记整体目标完成

**特点**: 维护完整的任务历史，而不是即时更新任务列表

##### `episodic_memory.py`
**功能**: 存储代理的执行历史

**数据结构**:
```python
@dataclass
class EpisodicMemoryStep:
    chat_history: List[ChatMessage]     # 聊天历史
    response: ChatResponse              # LLM 响应
    timestamp: str                      # 时间戳
    screenshot: Optional[str] = None    # 截图 Base64

@dataclass
class EpisodicMemory:
    persona: Optional[AgentPersona]     # 使用的 Persona
    steps: List[EpisodicMemoryStep]     # 执行步骤列表
```

**作用**: 记录每一步的完整上下文，用于反思和学习

##### `reflection.py`
**功能**: 反思结果数据类

**字段**:
```python
@dataclass
class Reflection:
    goal_achieved: bool                 # 是否达成目标
    summary: str                        # 总结
    advice: Optional[str]               # 改进建议（失败时提供）
    raw_response: str                   # 原始 LLM 响应
```

---

#### 2.4 `agent/context/personas/` - 预定义 Persona

##### `default.py` - DEFAULT Persona
**特点**: 通用 UI 交互，不包含 drag

**配置**:
```python
allowed_tools = [
    "swipe", "input_text", "press_key", "tap_by_index",
    "start_app", "list_packages", "remember", "complete"
]
required_context = ["ui_state", "screenshot"]
```

**适用场景**: 大多数常规 UI 交互任务

##### `big_agent.py` - BIG_AGENT Persona
**特点**: 支持复杂操作，包含 drag 工具

**配置**:
```python
allowed_tools = DEFAULT.allowed_tools + ["drag"]
```

**适用场景**: 需要拖拽操作的复杂任务

##### `ui_expert.py` - UI_EXPERT Persona
**特点**: UI 交互专家，不负责应用启动

**配置**:
```python
allowed_tools = [
    "swipe", "input_text", "press_key", "tap_by_index",
    "drag", "remember", "complete"
]
required_context = ["ui_state", "screenshot", "phone_state", "memory"]
```

**禁止**: 不包含 `start_app` 和 `list_packages`

##### `app_starter.py` - APP_STARTER_EXPERT Persona
**特点**: 应用启动专家

**配置**:
```python
allowed_tools = ["start_app", "complete"]
required_context = ["packages"]
```

**职责**: 仅负责启动应用，不处理 UI 交互

---

#### 2.5 `agent/droid/` - DroidAgent（顶层协调器）

##### `droid_agent.py`
**功能**: 协调 PlannerAgent 和 CodeActAgent 的顶层 Workflow

**核心参数**:
```python
class DroidAgent(Workflow):
    def __init__(
        self,
        goal: str,                      # 用户目标
        llm: LLM,                       # 语言模型
        tools: Tools,                   # 设备控制工具实例
        personas: List[AgentPersona],   # 可用的 Persona 列表
        max_steps: int = 30,            # 最大步数
        reasoning: bool = False,        # 是否启用规划
        reflection: bool = False,       # 是否启用反思
        save_trajectories: str = "none", # 轨迹保存级别
        timeout: int = 0,               # 超时（秒）
        vision: bool = False,           # 是否启用视觉
        enable_tracing: bool = False,   # 是否启用追踪
        debug: bool = False             # 是否启用调试
    )
```

**Workflow 步骤**:

1. **`start_handler(ev: StartEvent)`**:
   - 入口，决定直接执行或进入规划循环
   - 如果 `reasoning=True`，发送 `ReasoningLogicEvent`
   - 否则，创建单个任务并发送 `CodeActExecuteEvent`

2. **`handle_reasoning_logic(ev: ReasoningLogicEvent)`**:
   - 调用 PlannerAgent 生成任务
   - 获取下一个待执行任务
   - 发送 `CodeActExecuteEvent`

3. **`execute_task(ev: CodeActExecuteEvent)`**:
   - 创建 CodeActAgent 实例
   - 执行单个任务
   - 返回 `CodeActResultEvent`

4. **`handle_codeact_execute(ev: CodeActResultEvent)`**:
   - 处理任务执行结果
   - 如果失败且启用反思，发送 `ReflectionEvent`
   - 如果成功或失败，继续下一个任务或结束
   - 发送 `FinalizeEvent` 或 `ReasoningLogicEvent`

5. **`reflect(ev: ReflectionEvent)`**:
   - 调用 Reflector 分析执行质量
   - 返回 `ReasoningLogicEvent`（带反思结果）

6. **`finalize(ev: FinalizeEvent)`**:
   - 完成流程，保存轨迹
   - 返回 `StopEvent`（包含最终结果）

**事件流转**:
```
StartEvent
  → ReasoningLogicEvent / CodeActExecuteEvent
  → CodeActResultEvent
  → ReflectionEvent / ReasoningLogicEvent / FinalizeEvent
  → StopEvent
```

##### `events.py`
**定义的事件**:
- `CodeActExecuteEvent`: 开始执行任务（task, task_manager, persona）
- `CodeActResultEvent`: 任务执行结果（success, reason, episodic_memory）
- `ReasoningLogicEvent`: 触发规划逻辑（reflection_summary）
- `FinalizeEvent`: 最终结果（tasks, success, output）
- `TaskRunnerEvent`: 任务运行器
- `ReflectionEvent`: 触发反思（episodic_memory）

---

#### 2.6 `agent/planner/` - PlannerAgent（任务规划）

##### `planner_agent.py`
**功能**: 将复杂目标分解为可执行的子任务

**核心参数**:
```python
class PlannerAgent(Workflow):
    def __init__(
        self,
        goal: str,                      # 总体目标
        llm: LLM,                       # 语言模型
        vision: bool,                   # 是否启用视觉
        personas: List[AgentPersona],   # 可用的 Persona 列表
        task_manager: TaskManager       # 任务管理器
    )
```

**Workflow 步骤**:

1. **`prepare_chat(ev: StartEvent)`**:
   - 准备聊天上下文
   - 加载记忆和反思
   - 生成系统提示（包含 Persona 描述和工具函数）
   - 返回 `PlanInputEvent`

2. **`handle_llm_input(ev: PlanInputEvent)`**:
   - 获取当前设备状态（screenshot、ui_state、phone_state）
   - 构建用户消息（包含目标、任务历史、反思）
   - 调用 LLM 生成规划代码
   - 返回 `PlanThinkingEvent`

3. **`handle_llm_output(ev: PlanThinkingEvent)`**:
   - 提取代码和思考
   - 执行规划代码（调用 `set_tasks_with_agents` 或 `complete_goal`）
   - 返回 `PlanCreatedEvent`

4. **`finalize(ev: PlanCreatedEvent)`**:
   - 返回生成的任务列表
   - 返回 `StopEvent`

**工具函数**（注入到代码执行环境）:
```python
def set_tasks_with_agents(task_assignments: List[Dict[str, str]]):
    """
    设置任务队列，每个任务包含 'task' 和 'agent'

    示例:
    set_tasks_with_agents([
        {"task": "打开设置应用", "agent": "APP_STARTER_EXPERT"},
        {"task": "找到并点击'关于手机'", "agent": "UI_EXPERT"}
    ])
    """

def complete_goal(message: str):
    """标记目标完成"""
```

##### `prompts.py`
**功能**: PlannerAgent 的提示词模板

**核心模板**:

1. **`DEFAULT_PLANNER_SYSTEM_PROMPT`**: 系统提示
   - 解释规划规则：一次只规划 1-3 个任务
   - 强调验证：每个任务执行后需要验证
   - 任务格式：包含 precondition 和 goal
   - 任务历史：维护完整的历史（成功和失败）

2. **`DEFAULT_PLANNER_USER_PROMPT`**: 用户提示
   - 仅包含 goal

3. **`DEFAULT_PLANNER_TASK_FAILED_PROMPT`**: 任务失败后的重新规划提示
   - 分析失败原因
   - 调整策略重新规划

##### `events.py`
**定义的事件**:
- `PlanInputEvent`: 输入消息列表
- `PlanThinkingEvent`: LLM 思考结果（thoughts + code）
- `PlanCreatedEvent`: 生成的任务列表

---

#### 2.7 `agent/codeact/` - CodeActAgent（任务执行）

##### `codeact_agent.py`
**功能**: 执行具体任务，使用 ReAct 循环（Thought → Code → Observation）

**核心参数**:
```python
class CodeActAgent(Workflow):
    def __init__(
        self,
        llm: LLM,                       # 语言模型
        persona: AgentPersona,          # 使用的 Persona
        vision: bool,                   # 是否启用视觉
        tools_instance: Tools,          # 工具实例
        all_tools_list: Dict[str, str], # 所有可用工具的描述
        max_steps: int = 30             # 最大步数
    )
```

**Workflow 步骤**:

1. **`prepare_chat(ev: StartEvent)`**:
   - 准备聊天，加载目标和记忆
   - 生成系统提示（包含 Persona 和过滤后的工具）
   - 返回 `TaskInputEvent`

2. **`handle_llm_input(ev: TaskInputEvent)`**:
   - 获取上下文（screenshot、ui_state、phone_state、packages）
   - 构建用户消息
   - 调用 LLM 生成思考和代码
   - 返回 `TaskThinkingEvent`

3. **`handle_llm_output(ev: TaskThinkingEvent)`**:
   - 提取代码和思考
   - 如果有代码，返回 `TaskExecutionEvent`
   - 如果没有代码，提示并重试

4. **`execute_code(ev: TaskExecutionEvent)`**:
   - 执行 Python 代码（调用工具函数）
   - 返回 `TaskExecutionResultEvent`

5. **`handle_execution_result(ev: TaskExecutionResultEvent)`**:
   - 将执行结果作为观察反馈给 LLM
   - 检查是否调用了 `complete()` 函数
   - 如果完成，返回 `TaskEndEvent`
   - 否则，继续循环，返回 `TaskInputEvent`

6. **`finalize(ev: TaskEndEvent)`**:
   - 返回最终结果（success、reason、episodic_memory）
   - 返回 `StopEvent`

**特性**:
- 根据 Persona 过滤可用工具
- 自动注入 ui_state 到代码执行环境
- 维护 episodic_memory 记录每一步
- 支持截图上下文（vision 模式）
- 最大步数限制防止无限循环

##### `prompts.py`
**功能**: CodeActAgent 的提示词模板

**模板**:
- `DEFAULT_CODE_ACT_USER_PROMPT`: 用户提示，询问 precondition 和下一步
- `DEFAULT_NO_THOUGHTS_PROMPT`: 提醒 Agent 需要提供思考过程

##### `events.py`
**定义的事件**:
- `TaskInputEvent`: 输入消息
- `TaskThinkingEvent`: LLM 思考（thoughts + code）
- `TaskExecutionEvent`: 执行代码
- `TaskExecutionResultEvent`: 执行结果（stdout、return_value、error）
- `TaskEndEvent`: 任务结束（success + reason）
- `EpisodicMemoryEvent`: 传递 episodic memory

---

#### 2.8 `agent/oneflows/` - 反思流程

##### `reflector.py`
**功能**: Reflector 类，基于 episodic memory 反思任务执行

**核心方法**:
```python
class Reflector:
    def __init__(self, llm: LLM, vision: bool)

    def reflect_on_episodic_memory(
        self,
        episodic_memory: EpisodicMemory,
        goal: str
    ) -> Reflection:
        """
        分析执行历史，生成反思

        步骤:
        1. 创建截图网格（最多 6 张）
        2. 格式化 episodic memory 为可读文本
        3. 调用 LLM 评估是否达成目标
        4. 返回 Reflection 对象
        """
```

**反思规则**:
- 如果成功：`advice = None`
- 如果失败：提供直接的改进建议（使用"你"的形式）
- 建议聚焦于当前状态和重试策略

**示例反思输出**:
```python
Reflection(
    goal_achieved=False,
    summary="任务失败，因为找不到目标按钮",
    advice="你应该尝试滑动屏幕查找按钮，或者使用不同的定位方式",
    raw_response="..."
)
```

---

#### 2.9 `agent/utils/` - 工具函数

##### `async_utils.py`
**功能**: 异步转同步工具

**函数**:
```python
def async_to_sync(func):
    """将异步函数转换为同步函数"""
```

##### `llm_picker.py`
**功能**: 动态加载 LLM

**核心函数**:
```python
def load_llm(provider_name: str, **kwargs) -> LLM:
    """
    动态加载 LLM

    支持提供商:
    - OpenAI
    - Anthropic
    - Google GenAI
    - DeepSeek
    - Ollama
    - OpenAILike
    """
```

**实现**: 动态导入 llama-index LLM 模块，自动处理模块路径和包名

##### `trajectory.py`
**功能**: 轨迹记录和管理

**核心类**:
```python
@dataclass
class Trajectory:
    events: List[Event]                 # 事件列表
    screenshots: List[bytes]            # 截图列表
    ui_states: List[Dict]               # UI 状态列表
    macro: List[MacroEvent]             # 宏操作列表
    goal: str                           # 轨迹目标
```

**方法**:
```python
def save_trajectory(folder_path: str):
    """
    保存轨迹到文件夹
    - trajectory.json: 事件和元数据
    - macro.json: 宏序列
    - screenshots.gif: 截图 GIF
    - ui_states/: UI 状态 JSON 文件
    """

def create_screenshot_gif(screenshots: List[bytes], output_path: str):
    """创建截图 GIF"""

def load_trajectory_folder(folder_path: str) -> Trajectory:
    """加载轨迹文件夹"""

def load_macro_sequence(macro_path: str) -> List[MacroEvent]:
    """加载宏序列"""

def get_macro_summary(macro: List[MacroEvent]) -> str:
    """获取宏统计信息"""
```

##### `executer.py`
**功能**: SimpleCodeExecutor - Python 代码执行器

**核心类**:
```python
class SimpleCodeExecutor:
    def __init__(self):
        self.globals = {}               # 全局作用域
        self.locals = {}                # 局部作用域
```

**特性**:
- 维护全局和局部作用域
- 自动将异步工具转换为同步
- 捕获 stdout/stderr
- 支持工具函数注入
- 在执行前注入 ui_state

**执行流程**:
```python
def execute(code: str, tools: Dict) -> Tuple[str, Any, Optional[str]]:
    """
    执行代码

    返回: (stdout, return_value, error)
    """
```

##### `chat_utils.py`
**功能**: 聊天消息处理工具

**核心函数**:

**上下文添加函数**:
```python
def add_ui_text_block(message: ChatMessage, ui_state: Dict)
def add_screenshot_image_block(message: ChatMessage, screenshot: bytes)
def add_phone_state_block(message: ChatMessage, phone_state: Dict)
def add_packages_block(message: ChatMessage, packages: List[str])
def add_memory_block(message: ChatMessage, memory: List[str])
def add_task_history_block(message: ChatMessage, task_history: List[Task])
def add_reflection_summary(message: ChatMessage, reflection: Reflection)
```

**解析函数**:
```python
def parse_tool_descriptions(tools_dict: Dict[str, str]) -> str:
    """解析工具描述为 markdown"""

def parse_persona_description(personas: List[AgentPersona]) -> str:
    """解析 Persona 描述"""

def extract_code_and_thought(response: str) -> Tuple[str, str]:
    """从 LLM 响应提取代码和思考"""

def message_copy(message: ChatMessage) -> ChatMessage:
    """深拷贝消息对象"""
```

---

#### 2.10 `agent/usage.py`
**功能**: LLM token 使用追踪

**核心类**:
```python
@dataclass
class UsageResult:
    request_tokens: int                 # 请求 token 数
    response_tokens: int                # 响应 token 数
    total_tokens: int                   # 总 token 数
    requests: int                       # 请求次数
```

**核心函数**:
```python
def get_usage_from_response(provider: str, chat_rsp) -> UsageResult:
    """从响应提取使用信息（支持各种 LLM 提供商）"""

def track_usage(llm: LLM) -> Tuple[LLM, TokenCountingHandler]:
    """为 LLM 实例添加 token 追踪"""

def create_tracker(llm: LLM) -> TokenCountingHandler:
    """创建追踪器"""

@contextmanager
def llm_callback(llm: LLM):
    """上下文管理器，自动追踪和输出 token 使用"""
```

**支持的提供商**:
- Gemini/GoogleGenAI
- OpenAI
- Anthropic
- Ollama
- DeepSeek

---

### 3. tools/ - 设备控制工具层

#### `tools.py`
**功能**: Tools 抽象基类，定义设备控制接口

**核心方法（抽象）**:
```python
class Tools(ABC):
    @abstractmethod
    def get_state(self) -> Tuple[Dict, Dict]:
        """获取设备状态 -> (ui_state, phone_state)"""

    @abstractmethod
    def tap_by_index(self, index: int):
        """根据索引点击元素"""

    @abstractmethod
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300):
        """滑动"""

    @abstractmethod
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 1000):
        """拖拽"""

    @abstractmethod
    def input_text(self, text: str):
        """输入文本"""

    @abstractmethod
    def back(self):
        """返回"""

    @abstractmethod
    def press_key(self, keycode: str):
        """按键"""

    @abstractmethod
    def start_app(self, package: str, activity: Optional[str] = None):
        """启动应用"""

    @abstractmethod
    def take_screenshot(self) -> bytes:
        """截图"""

    @abstractmethod
    def list_packages(self, include_system_apps: bool = False) -> List[str]:
        """列出应用"""

    def remember(self, information: str):
        """记忆信息"""

    def get_memory(self) -> List[str]:
        """获取记忆"""

    def complete(self, success: bool = True, reason: str = "Task completed"):
        """标记完成"""
```

**装饰器**:
```python
@ui_action
def some_action(self):
    """自动捕获 UI 动作的截图和状态（当 save_trajectories="action"）"""
```

**工具函数**:
```python
def describe_tools(tools: Tools, exclude_tools: List[str] = []) -> Dict[str, str]:
    """生成工具描述字典"""
```

---

#### `adb.py`
**功能**: AdbTools - Android 设备控制实现

**核心特性**:
- 支持 TCP 和 Content Provider 两种通信方式
- 维护 `clickable_elements_cache` 用于索引点击
- 自动设置 DroidRun 键盘
- 支持轨迹保存（action 级别）

**初始化参数**:
```python
class AdbTools(Tools):
    def __init__(
        self,
        serial: str,                    # 设备序列号
        use_tcp: bool = False,          # 是否使用 TCP 通信
        remote_tcp_port: int = 8080,    # TCP 端口
        save_trajectories: str = "none" # 轨迹保存级别
    )
```

**TCP 相关**:
```python
def setup_tcp_forward(self):
    """设置 ADB 端口转发：localhost:{local_port} -> device:{remote_port}"""

def teardown_tcp_forward(self):
    """移除端口转发"""
```

**UI 交互**:
```python
@ui_action
def tap_by_index(self, index: int):
    """
    根据索引点击（递归查找元素，包括子元素）

    实现:
    1. 从 clickable_elements_cache 查找元素
    2. 递归搜索子元素
    3. 计算中心坐标
    4. 通过 TCP 或 Content Provider 发送点击
    """

def tap_by_coordinates(self, x: int, y: int):
    """坐标点击"""

@ui_action
def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300):
    """滑动（带延迟）"""

@ui_action
def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 1000):
    """拖拽（长按拖动）"""
```

**文本输入**:
```python
@ui_action
def input_text(self, text: str):
    """
    Base64 编码文本，通过 TCP 或 Content Provider 发送

    实现:
    1. 设置 DroidRun 键盘
    2. Base64 编码文本
    3. 通过 TCP 或 Content Provider 发送
    """
```

**应用管理**:
```python
@ui_action
def start_app(self, package: str, activity: Optional[str] = None):
    """
    启动应用（自动解析 activity）

    实现:
    1. 如果未提供 activity，尝试从包名解析
    2. 使用 adb shell am start 启动
    """

def install_app(self, apk_path: str):
    """安装 APK"""

def list_packages(self, include_system_apps: bool = False) -> List[str]:
    """列出应用"""
```

**状态获取**:
```python
def get_state(self) -> Tuple[Dict, Dict]:
    """
    获取 a11y_tree 和 phone_state

    返回:
    - a11y_tree: 可点击元素树形结构
        {
            "index": 0,
            "className": "android.widget.Button",
            "text": "确定",
            "bounds": [100, 200, 300, 400],
            "children": [...]
        }
    - phone_state: 当前应用、键盘状态、焦点元素
        {
            "current_activity": "com.example.MainActivity",
            "keyboard_shown": false,
            "focused_element": "..."
        }
    """

def take_screenshot(self, hide_overlay: bool = False) -> bytes:
    """截图（支持隐藏覆盖层）"""
```

**工具函数**:
```python
def setup_keyboard(self):
    """设置 DroidRun IME"""

def ping(self) -> bool:
    """测试 TCP 连接"""

def _parse_content_provider_output(self, output: str) -> Dict:
    """解析 Content Provider 响应"""
```

---

#### `ios.py`
**功能**: IOSTools - iOS 设备控制实现

**核心特性**:
- 通过 HTTP API 与 iOS Portal 通信
- 解析 iOS 无障碍树格式
- 自动识别交互元素（Button、TextField、Cell 等）

**初始化参数**:
```python
class IOSTools(Tools):
    def __init__(
        self,
        url: str,                       # iOS 设备 URL（如 http://device-ip:6643）
        bundle_identifiers: List[str] = [], # 应用包标识符列表
        save_trajectories: str = "none" # 轨迹保存级别
    )
```

**UI 交互**:
```python
@ui_action
def tap_by_index(self, index: int):
    """根据索引点击（使用 rect 格式）"""

@ui_action
def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300):
    """滑动（根据坐标计算方向）"""

def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 1000):
    """拖拽（未实现）"""
```

**文本输入**:
```python
@ui_action
def input_text(self, text: str):
    """使用最后点击元素的 rect"""
```

**应用管理**:
```python
@ui_action
def start_app(self, package: str):
    """启动应用（使用 bundleIdentifier）"""

def list_packages(self, include_system_apps: bool = False) -> List[str]:
    """列出系统应用和自定义应用"""
```

**状态获取**:
```python
def get_state(self) -> Tuple[Dict, Dict]:
    """获取无障碍树和设备状态"""

def _parse_ios_accessibility_tree(self, tree: Dict) -> List[Dict]:
    """
    解析 iOS 无障碍格式

    实现:
    1. 提取元素坐标、label、identifier、placeholder、value
    2. 过滤交互元素类型
    3. 生成 index 和 bounds
    """

def _get_phone_state(self) -> Dict:
    """获取当前 activity 和键盘状态"""

def take_screenshot(self) -> bytes:
    """截图"""
```

**系统应用列表**:
```python
IOS_SYSTEM_APPS = [
    "Safari", "Messages", "Calendar", "Mail", "Health",
    "Maps", "Shortcuts", "Camera", "Photos", "Clock", ...
]
```

---

### 4. cli/ - 命令行接口

#### `main.py`
**功能**: DroidRun 主命令行入口

**全局选项**:
```python
@click.option("--device", help="设备序列号")
@click.option("--provider", help="LLM 提供商")
@click.option("--model", help="模型名称")
@click.option("--temperature", type=float, help="温度")
@click.option("--steps", type=int, default=30, help="最大步数")
@click.option("--vision/--no-vision", default=False, help="启用视觉")
@click.option("--reasoning/--no-reasoning", default=False, help="启用推理")
@click.option("--reflection/--no-reflection", default=False, help="启用反思")
@click.option("--tracing/--no-tracing", default=False, help="启用追踪")
@click.option("--debug/--no-debug", default=False, help="调试模式")
@click.option("--use-tcp/--no-use-tcp", default=False, help="使用 TCP")
@click.option("--save-trajectory", type=str, help="保存轨迹")
```

**子命令**:

1. **`run <command>`**: 运行自然语言命令
```python
@cli.command()
@click.argument("command")
@click.option("--drag/--no-drag", default=False, help="启用拖拽")
@click.option("--ios/--no-ios", default=False, help="使用 iOS")
def run(command, ...):
    """
    流程:
    1. 配置日志
    2. 查找/连接设备
    3. 初始化 Tools（AdbTools 或 IOSTools）
    4. 加载 LLM
    5. 创建 DroidAgent
    6. 运行并流式输出事件
    7. 处理结果或中断
    """
```

2. **`devices`**: 列出连接的设备
```python
@cli.command()
def devices():
    """列出所有连接的设备"""
```

3. **`connect <serial>`**: 通过 TCP/IP 连接设备
```python
@cli.command()
@click.argument("serial")
def connect(serial):
    """连接设备（格式: ip:port）"""
```

4. **`disconnect <serial>`**: 断开设备连接
```python
@cli.command()
@click.argument("serial")
def disconnect(serial):
    """断开设备连接"""
```

5. **`setup`**: 安装和配置 Portal
```python
@cli.command()
@click.option("--path", help="APK 路径")
@click.option("--device", help="设备序列号")
def setup(path, device):
    """
    流程:
    1. 下载或使用指定的 APK
    2. 安装到设备
    3. 启用无障碍服务
    """
```

6. **`ping`**: 检查设备和 Portal 状态
```python
@cli.command()
@click.option("--device", help="设备序列号")
@click.option("--use-tcp/--no-use-tcp", default=False)
def ping(device, use_tcp):
    """测试 Portal 连接"""
```

7. **`macro`**: 宏相关命令
```python
cli.add_command(macro_cli, name="macro")
```

**核心函数**:
```python
async def run_command(goal, tools, llm, personas, ...):
    """
    异步执行命令的核心逻辑

    流程:
    1. 创建 DroidAgent
    2. 启动 Workflow
    3. 流式处理事件
    4. 返回结果
    """

def configure_logging(debug: bool):
    """配置日志处理器"""

def coro(f):
    """异步装饰器"""
```

---

#### `logs.py`
**功能**: LogHandler - 富文本日志处理

**核心类**:
```python
class LogHandler(logging.Handler):
    """
    使用 Rich 库实现美化输出

    维护三个面板:
    1. Activity Log: 滚动显示最近的日志条目（最多 100 条）
    2. Goal: 显示当前目标
    3. Status: 显示当前步骤和进度（带状态图标）
    """
```

**方法**:
```python
def emit(self, record: logging.LogRecord):
    """处理日志记录，添加到日志列表"""

def render(self):
    """创建 Rich Live 上下文"""

def rerender(self):
    """更新布局"""

def update_step(self, step: int):
    """更新当前步骤"""

def handle_event(self, event: Event):
    """
    处理 Workflow 事件，更新状态

    支持事件:
    - ScreenshotEvent: 显示截图提示
    - PlanInputEvent/PlanThinkingEvent/PlanCreatedEvent: 规划过程
    - TaskInputEvent/TaskThinkingEvent/TaskExecutionEvent: 执行过程
    - CodeActResultEvent/FinalizeEvent: 结果显示
    """
```

**状态图标**:
```python
STATUS_ICONS = {
    "pending": "⏳",
    "running": "🔄",
    "success": "✅",
    "error": "❌",
    "thinking": "💭"
}
```

---

### 5. macro/ - 宏录制和回放

#### `replay.py`
**功能**: MacroPlayer - 宏回放引擎

**核心类**:
```python
class MacroPlayer:
    def __init__(
        self,
        device_serial: str,             # 目标设备
        delay_between_actions: float = 1.0 # 动作间延迟
    )
```

**方法**:
```python
def load_macro_from_file(self, macro_file_path: str):
    """加载宏 JSON 文件"""

def load_macro_from_folder(self, trajectory_folder: str):
    """从轨迹文件夹加载"""

def replay_action(self, action: Dict):
    """
    回放单个动作

    支持:
    - tap: 点击（index 或坐标）
    - swipe: 滑动
    - drag: 拖拽
    - input_text: 文本输入
    - key_press: 按键
    - back: 返回
    - start_app: 启动应用
    """

def replay_macro(
    self,
    macro_data: Dict,
    start_from_step: int = 1,
    max_steps: Optional[int] = None
):
    """
    回放完整宏序列

    流程:
    1. 循环执行动作
    2. 记录成功/失败统计
    3. 显示进度和结果
    """
```

**工具函数**:
```python
def replay_macro_file(
    macro_file_path: str,
    device_serial: str,
    delay_between_actions: float = 1.0,
    start_from_step: int = 1,
    max_steps: Optional[int] = None
):
    """便捷函数，从文件回放"""

def replay_macro_folder(
    trajectory_folder: str,
    device_serial: str,
    delay_between_actions: float = 1.0,
    start_from_step: int = 1,
    max_steps: Optional[int] = None
):
    """便捷函数，从文件夹回放"""
```

---

#### `cli.py`
**功能**: 宏命令行接口

**命令**:

1. **`macro replay <path>`**: 回放宏
```python
@macro_cli.command()
@click.argument("path")
@click.option("--device", help="设备序列号")
@click.option("--delay", type=float, default=1.0, help="动作间延迟")
@click.option("--start-from", type=int, default=1, help="起始步骤（1-based）")
@click.option("--max-steps", type=int, help="最大步数")
@click.option("--debug/--no-debug", default=False, help="调试模式")
@click.option("--dry-run/--no-dry-run", default=False, help="预览模式")
def replay(path, ...):
    """
    支持文件或文件夹路径

    流程:
    1. 加载宏数据
    2. 显示预览（dry-run 模式）
    3. 回放宏
    """
```

2. **`macro list [directory]`**: 列出可用轨迹
```python
@macro_cli.command()
@click.argument("directory", default="trajectories")
def list_trajectories(directory):
    """
    流程:
    1. 扫描 trajectories/ 目录
    2. 显示表格: Folder、Description、Actions
    3. 显示回放命令提示
    """
```

**核心函数**:
```python
async def _replay_async(player, macro_data, ...):
    """异步回放逻辑"""

def _show_dry_run(macro_data: Dict):
    """显示动作预览表格"""

def configure_logging(debug: bool):
    """配置宏专用日志"""
```

---

### 6. telemetry/ - 遥测数据收集

#### `tracker.py`
**功能**: PostHog 遥测追踪器

**配置**:
```python
PROJECT_API_KEY = "phc_..."            # PostHog 项目密钥
HOST = "https://eu.i.posthog.com"      # EU PostHog 服务器
USER_ID_PATH = "~/.droidrun/user_id"   # 用户 ID 存储路径
RUN_ID = str(uuid.uuid4())             # 每次运行的唯一 ID
```

**函数**:
```python
def is_telemetry_enabled() -> bool:
    """检查遥测是否启用（环境变量 DROIDRUN_TELEMETRY_ENABLED）"""

def print_telemetry_message():
    """打印遥测启用/禁用消息"""

def get_user_id() -> str:
    """获取或生成用户 ID"""

def capture(event: str, user_id: str, **properties):
    """捕获遥测事件"""

def flush():
    """刷新遥测数据"""
```

**默认**: 遥测默认启用，可通过环境变量 `DROIDRUN_TELEMETRY_ENABLED=false` 禁用

---

#### `events.py`
**功能**: 遥测事件定义

**事件**:

1. **`DroidAgentInitEvent`**: DroidAgent 初始化
```python
@dataclass
class DroidAgentInitEvent:
    goal: str
    llm: str
    tools: str
    personas: List[str]
    max_steps: int
    timeout: int
    vision: bool
    reasoning: bool
    reflection: bool
    enable_tracing: bool
    debug: bool
    save_trajectories: str
```

2. **`DroidAgentFinalizeEvent`**: DroidAgent 完成
```python
@dataclass
class DroidAgentFinalizeEvent:
    tasks: List[str]
    success: bool
    output: str
    steps: int
```

---

## 关键设计模式和架构特点

### 1. 三层代理架构

```
┌─────────────────────────────────────────────────────────┐
│                    DroidAgent                            │
│                  (顶层协调器)                             │
│  - 管理整体执行流程                                       │
│  - 协调 Planner 和 CodeAct                               │
│  - 处理反思和轨迹保存                                     │
└───────────────────┬─────────────────────────────────────┘
                    │
            ┌───────┴────────┐
            │                │
    ┌───────▼───────┐  ┌────▼─────────┐
    │ PlannerAgent  │  │ CodeActAgent │
    │  (任务规划)   │  │  (任务执行)  │
    │               │  │              │
    │ 分解复杂目标  │  │ ReAct 循环   │
    │ 生成任务列表  │  │ 调用工具函数 │
    └───────────────┘  └──────────────┘
```

**优势**:
- **职责分离**: 规划和执行解耦
- **灵活性**: 可单独使用 CodeActAgent（无 reasoning）或组合使用
- **可维护性**: 每层独立，易于测试和扩展

---

### 2. Workflow 驱动

基于 llama-index 的 Workflow 系统:

```python
class MyAgent(Workflow):
    @step
    async def step1(self, ev: StartEvent) -> NextEvent:
        # 步骤 1 逻辑
        return NextEvent(data=...)

    @step
    async def step2(self, ev: NextEvent) -> StopEvent:
        # 步骤 2 逻辑
        return StopEvent(result=...)
```

**特点**:
- **事件驱动**: 步骤间通过 Event 通信
- **异步支持**: 原生支持 async/await
- **状态管理**: Context 用于共享状态
- **流式处理**: 支持事件流式输出

---

### 3. Persona 系统

允许创建专业化代理而无需修改核心代码:

```python
# 定义 Persona
ui_expert = AgentPersona(
    name="UI_EXPERT",
    system_prompt="你是 UI 交互专家...",
    allowed_tools=["tap_by_index", "swipe", "input_text"],
    required_context=["ui_state", "screenshot"],
    expertise_areas=["UI 交互", "元素定位"]
)

# 使用 Persona
agent = CodeActAgent(persona=ui_expert, ...)
```

**优势**:
- **工具过滤**: 根据 Persona 限制可用工具
- **提示词定制**: 每个 Persona 有独立的系统提示
- **专业化**: 不同任务使用不同专家
- **易扩展**: 新增 Persona 无需修改核心代码

---

### 4. 事件驱动通信

组件间通过 Event 解耦:

```python
# 发送事件
self.send_event(CodeActExecuteEvent(task=task))

# 接收事件
@step
async def handle_execute(self, ev: CodeActExecuteEvent):
    # 处理逻辑
    return CodeActResultEvent(success=True)
```

**优势**:
- **解耦**: 组件不直接依赖
- **可观测**: 可监控事件流
- **灵活**: 易于添加新步骤和事件处理

---

### 5. 工具注入机制

工具函数动态注入到代码执行环境:

```python
# 定义工具
class AdbTools(Tools):
    def tap_by_index(self, index: int):
        # 实现

# 注入到执行器
executor = SimpleCodeExecutor()
executor.execute(code, tools={
    "tap_by_index": tools.tap_by_index,
    ...
})

# LLM 生成的代码可以直接调用
# tap_by_index(5)
```

**特点**:
- **白名单机制**: 只注入允许的工具
- **异步转同步**: 自动转换异步工具
- **安全执行**: 隔离的执行环境

---

### 6. 上下文保持

多层次的上下文管理:

```python
# TaskManager: 任务队列和历史
task_manager.set_tasks([...])
task_manager.complete_task("完成")

# EpisodicMemory: 执行轨迹
episodic_memory.steps.append(step)

# Memory: 跨步骤信息
tools.remember("重要信息")
memory = tools.get_memory()

# Reflection: 学习反馈
reflection = reflector.reflect_on_episodic_memory(...)
```

**优势**:
- **持久化**: 跨步骤保持状态
- **学习**: 从历史中学习
- **调试**: 完整的执行记录

---

### 7. 轨迹记录

三级保存机制:

```python
# none: 不保存
# step: 每步保存（CodeActAgent 的每一步）
# action: 每个动作保存（每次工具调用）

@ui_action  # 自动保存 action
def tap_by_index(self, index: int):
    # 实现
```

**保存内容**:
- `trajectory.json`: 事件和元数据
- `macro.json`: 宏序列（可回放）
- `screenshots.gif`: 截图 GIF
- `ui_states/`: UI 状态 JSON 文件

**用途**:
- 调试分析
- 宏回放
- 数据集生成

---

### 8. 多通信方式

Android 设备支持两种通信方式:

```python
# TCP 模式（高性能）
tools = AdbTools(serial="...", use_tcp=True)

# Content Provider 模式（兼容性好）
tools = AdbTools(serial="...", use_tcp=False)
```

**自动降级**: TCP 失败时自动切换到 Content Provider

---

## 数据流示意

### 完整执行流程（--reasoning 模式）

```
用户输入 goal
    ↓
DroidAgent.start_handler()
    ↓
[规划循环开始]
    ↓
ReasoningLogicEvent → PlannerAgent
    ├── prepare_chat(): 准备提示
    ├── handle_llm_input(): 获取设备状态
    ├── 调用 LLM 生成规划代码
    └── handle_llm_output(): 执行代码，生成任务
    ↓
PlanCreatedEvent(tasks=[Task1, Task2, ...])
    ↓
DroidAgent 获取 Task1
    ↓
CodeActExecuteEvent(Task1) → CodeActAgent
    ├── prepare_chat(): 准备提示
    ├── [ReAct 循环开始]
    │   ├── handle_llm_input(): 获取上下文（截图、UI）
    │   ├── 调用 LLM 生成思考和代码
    │   ├── execute_code(): 执行代码，调用工具
    │   ├── handle_execution_result(): 观察结果
    │   └── 检查是否调用 complete()
    └── finalize(): 返回结果
    ↓
CodeActResultEvent(success/failure, episodic_memory)
    ↓
[如果启用反思且失败]
    ↓
ReflectionEvent → Reflector
    ├── 创建截图网格
    ├── 格式化 episodic memory
    ├── 调用 LLM 评估
    └── 返回 Reflection
    ↓
[回到规划循环]
    ↓
检查是否完成或失败
    ↓
FinalizeEvent
    ├── 保存轨迹（如果启用）
    └── 返回最终结果
    ↓
StopEvent
```

---

### 直接执行流程（无 --reasoning）

```
用户输入 goal
    ↓
DroidAgent.start_handler()
    ↓
直接创建 Task(goal, agent_type="DEFAULT")
    ↓
CodeActExecuteEvent(Task) → CodeActAgent
    ├── [ReAct 循环]
    │   ├── 思考 → 代码 → 执行 → 观察
    │   └── 直到调用 complete()
    └── 返回结果
    ↓
CodeActResultEvent
    ↓
FinalizeEvent
    ↓
StopEvent
```

---

### ReAct 循环详解

CodeActAgent 使用 ReAct（Reasoning + Acting）循环:

```
1. Thought（思考）
   ├── 分析当前状态（截图、UI、历史）
   └── 决定下一步行动

2. Code（代码）
   ├── 生成 Python 代码
   └── 调用工具函数

3. Observation（观察）
   ├── 执行代码
   ├── 获取结果（stdout、return_value、error）
   └── 反馈给 LLM

4. 重复 1-3，直到：
   ├── 调用 complete(success=True)
   ├── 达到最大步数
   └── 或发生错误
```

**示例**:
```
Step 1:
Thought: 需要点击"设置"按钮
Code: tap_by_index(3)
Observation: 成功点击，当前页面显示设置界面

Step 2:
Thought: 找到"关于手机"选项
Code: tap_by_index(10)
Observation: 成功点击，进入关于手机页面

Step 3:
Thought: 任务完成
Code: complete(success=True, reason="已进入关于手机页面")
Observation: 任务结束
```

---

## 依赖关系图

```
DroidAgent
├── llama_index.core.workflow (Workflow 基础)
│   ├── Workflow, Step
│   ├── StartEvent, StopEvent
│   └── Context
├── PlannerAgent (可选，reasoning 模式)
│   ├── TaskManager
│   ├── SimpleCodeExecutor
│   ├── ContextInjectionManager
│   └── LLM
├── CodeActAgent
│   ├── AgentPersona
│   ├── SimpleCodeExecutor
│   ├── EpisodicMemory
│   ├── Tools (AdbTools/IOSTools)
│   └── LLM
├── Reflector (可选，reflection 模式)
│   ├── EpisodicMemory
│   └── LLM
└── Trajectory
    └── MacroEvent

Tools
├── AdbTools
│   ├── adbutils (ADB 通信)
│   │   ├── AdbDevice
│   │   └── adb_shell
│   ├── requests (TCP 通信)
│   └── portal (Portal 管理)
│       ├── download_portal_apk
│       └── enable_portal_accessibility
└── IOSTools
    └── requests (HTTP API)

CLI
├── click (命令行解析)
├── rich (富文本输出)
│   ├── Console
│   ├── Live
│   ├── Panel
│   └── Table
├── DroidAgent
└── MacroPlayer

LLM
├── llama_index.llms
│   ├── OpenAI
│   ├── Anthropic
│   ├── Gemini
│   ├── OpenAILike (DeepSeek, Ollama)
│   └── ...
└── llama_index.core
    ├── ChatMessage
    └── ChatResponse
```

---

## 环境变量和配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LLM_HISTORY_LIMIT` | 20 | LLM 历史消息限制 |
| `DROIDRUN_TELEMETRY_ENABLED` | true | 是否启用遥测 |
| `TOKENIZERS_PARALLELISM` | false | Tokenizers 并行 |
| `GRPC_ENABLE_FORK_SUPPORT` | false | gRPC fork 支持 |
| `OPENAI_API_KEY` | - | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | - | Anthropic API 密钥 |
| `GOOGLE_API_KEY` | - | Google API 密钥 |

---

## 核心类和函数索引

### 主要类

| 类名 | 路径 | 功能 |
|------|------|------|
| `DroidAgent` | agent/droid/droid_agent.py:35 | 顶层协调器 Workflow |
| `PlannerAgent` | agent/planner/planner_agent.py:30 | 任务规划 Workflow |
| `CodeActAgent` | agent/codeact/codeact_agent.py:40 | 任务执行 Workflow |
| `Reflector` | agent/oneflows/reflector.py:20 | 反思分析器 |
| `AgentPersona` | agent/context/agent_persona.py:10 | Persona 数据类 |
| `ContextInjectionManager` | agent/context/context_injection_manager.py:15 | Persona 管理器 |
| `TaskManager` | agent/context/task_manager.py:25 | 任务队列管理 |
| `Task` | agent/context/task_manager.py:10 | 任务数据类 |
| `EpisodicMemory` | agent/context/episodic_memory.py:20 | 执行历史存储 |
| `Reflection` | agent/context/reflection.py:10 | 反思结果数据类 |
| `Tools` | tools/tools.py:30 | 工具抽象基类 |
| `AdbTools` | tools/adb.py:50 | Android 设备控制 |
| `IOSTools` | tools/ios.py:40 | iOS 设备控制 |
| `Trajectory` | agent/utils/trajectory.py:25 | 轨迹管理 |
| `SimpleCodeExecutor` | agent/utils/executer.py:20 | Python 代码执行器 |
| `MacroPlayer` | macro/replay.py:30 | 宏回放引擎 |
| `LogHandler` | cli/logs.py:40 | 富文本日志处理 |

---

### 关键函数

| 函数名 | 路径 | 功能 |
|--------|------|------|
| `load_llm` | agent/utils/llm_picker.py:15 | 动态加载 LLM |
| `describe_tools` | tools/tools.py:150 | 生成工具描述 |
| `extract_code_and_thought` | agent/utils/chat_utils.py:200 | 提取代码和思考 |
| `add_ui_text_block` | agent/utils/chat_utils.py:50 | 添加 UI 上下文 |
| `add_screenshot_image_block` | agent/utils/chat_utils.py:80 | 添加截图 |
| `get_usage_from_response` | agent/usage.py:40 | 提取 token 使用 |
| `download_portal_apk` | portal.py:30 | 下载 Portal APK |
| `enable_portal_accessibility` | portal.py:100 | 启用无障碍服务 |
| `replay_macro_file` | macro/replay.py:200 | 回放宏文件 |
| `capture` | telemetry/tracker.py:80 | 捕获遥测事件 |
| `ui_action` | tools/tools.py:100 | UI 动作装饰器 |
| `async_to_sync` | agent/utils/async_utils.py:10 | 异步转同步 |

---

## 扩展指南

### 1. 添加新的 Persona

```python
# 在 agent/context/personas/ 创建新文件

from droidrun.agent.context.agent_persona import AgentPersona

MY_PERSONA = AgentPersona(
    name="MY_CUSTOM_PERSONA",
    system_prompt="你是一个自定义专家...",
    user_prompt="目标: {goal}",
    description="自定义 Persona",
    allowed_tools=["tap_by_index", "swipe"],
    required_context=["ui_state", "screenshot"],
    expertise_areas=["自定义领域"]
)

# 在 __init__.py 导出
from .my_persona import MY_PERSONA
```

### 2. 添加新的工具函数

```python
# 在 AdbTools 或 IOSTools 类中添加新方法

@ui_action  # 自动保存 action
def my_custom_action(self, param: str):
    """自定义动作描述"""
    # 实现逻辑
    pass

# 更新 describe_tools 确保工具被导出
```

### 3. 添加新的 LLM 提供商

```python
# 在 agent/utils/llm_picker.py 添加新提供商

def load_llm(provider_name: str, **kwargs):
    if provider_name == "my_provider":
        from llama_index.llms.my_provider import MyProviderLLM
        return MyProviderLLM(**kwargs)
    # ... 现有逻辑
```

### 4. 添加新的事件类型

```python
# 在 agent/common/events.py 或模块特定的 events.py

from llama_index.core.workflow import Event

class MyCustomEvent(Event):
    data: str
    timestamp: str

# 在 Workflow 中使用
@step
async def handle_my_event(self, ev: MyCustomEvent):
    # 处理逻辑
    pass
```

---

## 最佳实践

### 1. 使用 Persona 系统
- 为不同类型的任务创建专门的 Persona
- 限制工具访问以提高安全性和性能
- 提供清晰的系统提示

### 2. 启用追踪和调试
```bash
# 开发时启用调试和追踪
droidrun "任务" --debug --tracing

# 保存轨迹用于分析
droidrun "任务" --save-trajectory action
```

### 3. 合理使用 reasoning 模式
- 简单任务：直接执行（无 --reasoning）
- 复杂任务：启用规划（--reasoning）
- 需要学习：启用反思（--reflection）

### 4. 优化 token 使用
- 调整 `LLM_HISTORY_LIMIT` 控制历史长度
- 使用 `--vision` 仅在需要视觉理解时
- 选择合适的模型（小模型更快更便宜）

### 5. 宏回放和测试
```bash
# 录制轨迹
droidrun "任务" --save-trajectory action

# 回放测试
droidrun macro replay trajectories/my_task

# 预览宏
droidrun macro replay trajectories/my_task --dry-run
```

---

## 常见问题和解决方案

### 1. Portal 连接失败
```bash
# 检查 Portal 状态
droidrun ping --device <serial>

# 重新安装 Portal
droidrun setup --device <serial>

# 尝试 TCP 模式
droidrun "任务" --use-tcp
```

### 2. LLM 响应慢或超时
- 使用更快的模型（如 gpt-4o-mini）
- 减少历史消息长度
- 禁用 vision 模式（如果不需要）

### 3. 任务执行失败
- 启用 --debug 查看详细日志
- 检查工具函数是否在 Persona 的 allowed_tools 中
- 启用 --reflection 让系统自动学习

### 4. 找不到元素
- 使用 --vision 模式提高理解能力
- 调整 Persona 的 required_context
- 手动检查 UI 状态（`tools.get_state()`）

---

## 性能优化建议

### 1. 减少 LLM 调用
- 使用更大的 max_steps 允许 Agent 在一次循环中完成更多工作
- 优化提示词减少不必要的思考步骤

### 2. 优化截图传输
- 压缩截图（调整分辨率）
- 仅在需要时启用 vision 模式

### 3. 并行处理
- 多个独立任务可以并行执行（需要修改 DroidAgent）
- 使用异步 API 提高吞吐量

### 4. 缓存优化
- 缓存常用的 UI 状态
- 缓存应用列表（`list_packages`）

---

## 总结

DroidRun 是一个设计精良、架构清晰的 LLM 驱动设备自动化框架，具有以下显著特点：

### 优势
1. ✅ **模块化架构**: 清晰的三层代理结构，职责分离
2. ✅ **灵活的 Persona 系统**: 支持专业化代理，易于扩展
3. ✅ **事件驱动设计**: 组件解耦，易于监控和调试
4. ✅ **多平台支持**: Android 和 iOS，多种通信方式
5. ✅ **完整的工具链**: CLI、宏回放、轨迹记录、遥测
6. ✅ **良好的可观测性**: 日志、事件流、token 追踪
7. ✅ **代码执行安全性**: 隔离的执行环境，工具白名单

### 适用场景
- 🎯 移动应用自动化测试
- 🎯 UI 操作录制和回放
- 🎯 自然语言控制移动设备
- 🎯 复杂任务自动化（结合 reasoning 模式）
- 🎯 数据集生成（轨迹记录）

### 技术栈
- 🔧 核心框架: llama-index 0.14.4
- 🔧 设备通信: adbutils, requests
- 🔧 CLI: click, rich
- 🔧 数据验证: pydantic
- 🔧 LLM 支持: OpenAI, Anthropic, Google, DeepSeek, Ollama

---

**文档版本**: 1.0
**生成日期**: 2025-10-28
**项目版本**: DroidRun 0.3.0
