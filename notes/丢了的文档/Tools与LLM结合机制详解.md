# DroidRun 工具与大模型结合机制详解

## 概述

DroidRun 采用了一种创新的方式将设备控制工具（Tools）与大模型（LLM）结合：**不是使用 LLM 原生的 Function Calling，而是让 LLM 生成 Python 代码，然后在受控环境中执行这些代码来调用工具函数**。

这种设计被称为 **CodeAct（Code as Action）** 模式。

---

## 核心设计理念

### 传统 Function Calling vs CodeAct

| 特性 | 传统 Function Calling | CodeAct 模式 |
|------|---------------------|-------------|
| 调用方式 | LLM 返回结构化的函数调用请求 | LLM 生成 Python 代码 |
| 灵活性 | 每次只能调用一个或多个独立函数 | 可以编写复杂的逻辑、循环、条件判断 |
| 状态保持 | 需要额外机制 | 代码执行环境自动保持变量状态 |
| 学习曲线 | 需要理解特定的函数签名格式 | 直接使用熟悉的 Python 语法 |
| 错误处理 | 受限于框架实现 | 可以使用 try-catch 等标准方式 |
| 复杂操作 | 需要多轮对话 | 一次可以完成多步操作 |

### CodeAct 的优势

1. **更强的表达能力**：可以编写复杂的逻辑
   ```python
   # 传统方式需要多轮对话
   # 轮1: 点击按钮
   # 轮2: 等待
   # 轮3: 检查结果

   # CodeAct 一次完成
   tap_by_index(5)
   time.sleep(2)
   if "Success" in ui_state:
       complete(success=True, reason="操作成功")
   ```

2. **状态保持**：变量在执行环境中持久化
   ```python
   # 第一步
   counter = 0
   tap_by_index(1)

   # 第二步（可以访问 counter）
   counter += 1
   if counter < 3:
       tap_by_index(2)
   ```

3. **自然的编程范式**：LLM 可以使用完整的 Python 能力

---

## 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│                     1. 初始化阶段                            │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐    ┌──────────────┐│
│  │   Persona    │────▶│   过滤工具   │───▶│ 生成系统提示 ││
│  │ (允许的工具) │     │  Tool List   │    │ (工具描述)   ││
│  └──────────────┘     └──────────────┘    └──────────────┘│
│                              │                              │
│                              ▼                              │
│                    ┌──────────────────┐                     │
│                    │ describe_tools() │                     │
│                    │  解析函数签名    │                     │
│                    │  提取文档字符串  │                     │
│                    └──────────────────┘                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     2. 执行循环（ReAct）                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Step 1: 准备上下文                         │  │
│  │  ┌────────┐  ┌───────────┐  ┌──────────┐            │  │
│  │  │截图    │  │ UI状态    │  │设备状态  │            │  │
│  │  │(vision)│  │(ui_state) │  │(phone)   │            │  │
│  │  └───┬────┘  └─────┬─────┘  └────┬─────┘            │  │
│  │      │             │              │                   │  │
│  │      └─────────────┴──────────────┴──────┐           │  │
│  │                                            ▼           │  │
│  │                               ┌─────────────────────┐ │  │
│  │                               │   添加到聊天历史    │ │  │
│  │                               └─────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Step 2: LLM 生成代码                       │  │
│  │                                                        │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │  LLM 输入:                                     │   │  │
│  │  │  - 系统提示（包含工具描述）                   │   │  │
│  │  │  - 聊天历史                                    │   │  │
│  │  │  - 当前上下文（截图、UI、设备状态）           │   │  │
│  │  └───────────────┬───────────────────────────────┘   │  │
│  │                  │                                     │  │
│  │                  ▼                                     │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │  LLM 输出:                                     │   │  │
│  │  │  思考: "我需要点击设置按钮..."                │   │  │
│  │  │  代码:                                         │   │  │
│  │  │  ```python                                     │   │  │
│  │  │  tap_by_index(5)                               │   │  │
│  │  │  ```                                           │   │  │
│  │  └───────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Step 3: 代码执行                           │  │
│  │                                                        │  │
│  │  ┌─────────────────────────────────────┐             │  │
│  │  │    SimpleCodeExecutor.execute()     │             │  │
│  │  │                                      │             │  │
│  │  │  1. 注入 ui_state 到全局作用域     │             │  │
│  │  │  2. 注入工具函数到全局作用域        │             │  │
│  │  │  3. 异步工具转同步                  │             │  │
│  │  │  4. 执行代码（exec）                │             │  │
│  │  │  5. 捕获 stdout/stderr              │             │  │
│  │  │  6. 返回结果                        │             │  │
│  │  └───────────┬─────────────────────────┘             │  │
│  │              │                                         │  │
│  │              ▼                                         │  │
│  │  ┌─────────────────────────────────────┐             │  │
│  │  │    工具函数被调用                   │             │  │
│  │  │    (例如: AdbTools.tap_by_index)   │             │  │
│  │  └─────────────────────────────────────┘             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Step 4: 观察结果                           │  │
│  │                                                        │  │
│  │  ┌─────────────────────────────────────┐             │  │
│  │  │  执行结果添加到聊天历史:            │             │  │
│  │  │  "执行成功，输出: ..."              │             │  │
│  │  │  或 "错误: ..."                      │             │  │
│  │  └─────────────────────────────────────┘             │  │
│  │              │                                         │  │
│  │              ▼                                         │  │
│  │  ┌─────────────────────────────────────┐             │  │
│  │  │  检查是否调用了 complete()          │             │  │
│  │  │  - 是: 任务结束                     │             │  │
│  │  │  - 否: 回到 Step 1                  │             │  │
│  │  └─────────────────────────────────────┘             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 详细实现分析

### 1. 工具描述生成

工具描述是 LLM 理解如何使用工具的关键。

#### 1.1 `describe_tools()` 函数

**位置**: `droidrun/tools/tools.py:143`

```python
def describe_tools(tools: Tools, exclude_tools: Optional[List[str]] = None) -> Dict[str, Callable[..., Any]]:
    """
    返回工具函数的字典

    示例输出:
    {
        "tap_by_index": <bound method AdbTools.tap_by_index>,
        "swipe": <bound method AdbTools.swipe>,
        "input_text": <bound method AdbTools.input_text>,
        ...
    }
    """
    description = {
        "swipe": tools.swipe,
        "input_text": tools.input_text,
        "press_key": tools.press_key,
        "tap_by_index": tools.tap_by_index,
        "drag": tools.drag,
        "start_app": tools.start_app,
        "list_packages": tools.list_packages,
        "remember": tools.remember,
        "complete": tools.complete,
    }

    # 移除不允许的工具
    for tool_name in exclude_tools:
        description.pop(tool_name, None)

    return description
```

#### 1.2 `parse_tool_descriptions()` 函数

**位置**: `droidrun/agent/utils/chat_utils.py:235`

这个函数将工具函数转换为 LLM 可读的文档：

```python
def parse_tool_descriptions(tool_list) -> str:
    """
    将工具字典转换为 markdown 格式的描述

    输入: {"tap_by_index": <function>, ...}
    输出:
    '''
    def tap_by_index(index: int) -> str:
        """
        Tap the element at the given index.
        """
    ...

    def swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """
        Swipe from the given start coordinates to the given end coordinates.
        """
    ...
    '''
    """
    tool_descriptions = []

    for tool in tool_list.values():
        tool_name = tool.__name__
        tool_signature = inspect.signature(tool)  # 获取函数签名
        tool_docstring = tool.__doc__ or "No description available."

        # 格式化为 Python 函数定义
        formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
        tool_descriptions.append(formatted_signature)

    return "\n".join(tool_descriptions)
```

**生成的工具描述示例**:

```python
def tap_by_index(index: int) -> str:
    """
    Tap the element at the given index.
    """
...

def swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
    """
    Swipe from the given start coordinates to the given end coordinates.
    """
...

def input_text(text: str) -> str:
    """
    Input the given text into a focused input field.
    """
...

def complete(success: bool, reason: str = "") -> None:
    """
    Complete the tool. This is used to indicate that the tool has completed its task.
    """
...
```

---

### 2. Persona 工具过滤

通过 Persona 系统，不同的代理可以访问不同的工具集合。

#### 2.1 Persona 定义工具白名单

**示例**: `droidrun/agent/context/personas/default.py`

```python
DEFAULT = AgentPersona(
    name="Default",
    allowed_tools=[
        "swipe",
        "input_text",
        "press_key",
        "tap_by_index",
        "start_app",
        "list_packages",
        "remember",
        "complete"
    ],
    # 注意：不包含 "drag"
    ...
)
```

**UI 专家 Persona** (`ui_expert.py`):

```python
UI_EXPERT = AgentPersona(
    name="UI_EXPERT",
    allowed_tools=[
        "swipe",
        "input_text",
        "press_key",
        "tap_by_index",
        "drag",        # 包含 drag
        "remember",
        "complete"
    ],
    # 注意：不包含 "start_app" 和 "list_packages"
    ...
)
```

#### 2.2 CodeActAgent 中的工具过滤

**位置**: `droidrun/agent/codeact/codeact_agent.py:83`

```python
class CodeActAgent(Workflow):
    def __init__(self, llm, persona, tools_instance, all_tools_list, ...):
        # 只保留 Persona 允许的工具
        self.tool_list = {}
        for tool_name in persona.allowed_tools:
            if tool_name in all_tools_list:
                self.tool_list[tool_name] = all_tools_list[tool_name]

        # 生成工具描述（只包含允许的工具）
        self.tool_descriptions = chat_utils.parse_tool_descriptions(self.tool_list)

        # 将工具描述注入系统提示
        self.system_prompt_content = persona.system_prompt.format(
            tool_descriptions=self.tool_descriptions
        )
```

---

### 3. 系统提示构建

系统提示是 LLM 理解如何使用工具的核心。

#### 3.1 默认系统提示

**位置**: `droidrun/agent/context/personas/default.py:32`

```python
system_prompt = """
You are a helpful AI assistant that can write and execute Python code to solve problems.

You will be given a task to perform. You should output:
- Python code wrapped in ``` tags that provides the solution to the task, or a step towards the solution.
- If there is a precondition for the task, you MUST check if it is met.
- If a goal's precondition is unmet, fail the task by calling `complete(success=False, reason='...')` with an explanation.
- If you task is complete, you should use the complete(success:bool, reason:str) function within a code block to mark it as finished.

## Context:
The following context is given to you for analysis:
- **ui_state**: A list of all currently visible UI elements with their indices. Use this to understand what interactive elements are available on the screen.
- **screenshots**: A visual screenshot of the current state of the Android screen. This provides visual context for what the user sees.
- **phone_state**: The current app you are navigating in.
- **chat history**: You are also given the history of your actions (if any) from your previous steps.
- **execution result**: The result of your last Action

## Response Format:
Example of proper code format:
**Task Assignment:**
**Task:** "Precondition: Settings app is open. Goal: Navigate to Wi-Fi settings and connect to the network 'HomeNetwork'."

**(Step 1) Agent Analysis:** I can see the Settings app is open from the screenshot. This is a multi-step task...

**(Step 1) Agent Action:**
```python
# First step: Navigate to Wi-Fi settings
tap_by_index(3)
```

**(Step 2) Agent Analysis:** Good! I've successfully navigated to the Wi-Fi settings screen...

**(Step 2) Agent Action:**
```python
# Second step: Turn on Wi-Fi to see available networks
tap_by_index(1)
```

## Tools:
In addition to the Python Standard Library and any functions you have already written, you can use the following functions:
{tool_descriptions}

Reminder: Always place your Python code between ```...``` tags when you want to run code.
"""
```

**关键点**:
1. 明确说明可以写 Python 代码
2. 解释如何使用 `complete()` 标记任务完成
3. 说明可用的上下文（ui_state、screenshot 等）
4. 提供详细的示例展示多步推理
5. `{tool_descriptions}` 占位符会被实际的工具描述替换

---

### 4. 上下文注入

在每次调用 LLM 之前，需要添加当前的设备状态作为上下文。

#### 4.1 上下文类型

**位置**: `droidrun/agent/codeact/codeact_agent.py:170`

```python
async def handle_llm_input(self, ctx, ev):
    chat_history = ev.input

    # 根据 Persona 的 required_context 添加不同的上下文
    for context in self.required_context:

        # 1. 截图上下文
        if context == "screenshot":
            screenshot = self.tools.take_screenshot()[1]
            if self.vision == True:
                # 如果启用 vision，将截图作为图片添加到消息
                chat_history = await chat_utils.add_screenshot_image_block(
                    screenshot, chat_history
                )

        # 2. UI 状态上下文
        if context == "ui_state":
            state = self.tools.get_state()
            # 添加 UI 元素树
            chat_history = await chat_utils.add_ui_text_block(
                state["a11y_tree"], chat_history
            )
            # 添加设备状态
            chat_history = await chat_utils.add_phone_state_block(
                state["phone_state"], chat_history
            )

        # 3. 应用列表上下文
        if context == "packages":
            chat_history = await chat_utils.add_packages_block(
                self.tools.list_packages(include_system_apps=True),
                chat_history
            )

    # 调用 LLM
    response = await self._get_llm_response(ctx, chat_history)
```

#### 4.2 UI 状态格式

**UI 元素树示例** (`ui_state`):

```python
{
    "index": 0,
    "className": "android.widget.LinearLayout",
    "text": "",
    "bounds": [0, 0, 1080, 2340],
    "children": [
        {
            "index": 1,
            "className": "android.widget.Button",
            "text": "设置",
            "bounds": [100, 200, 300, 280],
            "children": []
        },
        {
            "index": 2,
            "className": "android.widget.EditText",
            "text": "",
            "bounds": [100, 300, 900, 380],
            "children": []
        }
    ]
}
```

**添加到聊天历史的格式**:

```markdown
### Current UI Elements:
```json
{
    "index": 1,
    "className": "android.widget.Button",
    "text": "设置",
    "bounds": [100, 200, 300, 280]
},
{
    "index": 2,
    "className": "android.widget.EditText",
    "text": "",
    "bounds": [100, 300, 900, 380]
}
```

### Phone State:
```json
{
    "current_activity": "com.android.settings/.Settings",
    "keyboard_shown": false,
    "focused_element": "android.widget.Button"
}
```
```

---

### 5. 代码执行引擎

这是整个机制的核心：安全地执行 LLM 生成的代码。

#### 5.1 SimpleCodeExecutor 初始化

**位置**: `droidrun/agent/utils/executer.py:27`

```python
class SimpleCodeExecutor:
    def __init__(self, loop, locals={}, globals={}, tools={}, tools_instance=None):
        """
        初始化代码执行器

        参数:
        - tools: 工具函数字典 {"tap_by_index": func, ...}
        - tools_instance: 原始工具实例（AdbTools 或 IOSTools）
        """
        self.tools_instance = tools_instance

        # 处理工具函数
        for tool_name, tool_function in tools.items():
            # 如果是异步函数，转换为同步
            if asyncio.iscoroutinefunction(tool_function):
                tool_function = async_to_sync(tool_function)
            # 添加到全局作用域
            globals[tool_name] = tool_function

        # 添加标准库模块
        import time
        globals["time"] = time

        self.globals = globals
        self.locals = locals
```

**关键特性**:
1. **异步转同步**: 自动将异步工具函数转换为同步版本
2. **工具注入**: 将工具函数添加到全局作用域
3. **状态持久化**: globals 和 locals 在多次执行间保持

#### 5.2 代码执行

**位置**: `droidrun/agent/utils/executer.py:90`

```python
async def execute(self, ctx: Context, code: str) -> str:
    """
    执行 Python 代码并捕获输出

    流程:
    1. 注入 ui_state 到全局作用域
    2. 创建空的 screenshots 和 ui_states 列表（用于 @ui_action 装饰器）
    3. 执行代码（在线程中，避免阻塞）
    4. 捕获 stdout、stderr 和异常
    5. 返回结果
    """
    # 1. 更新 UI 状态
    self.globals['ui_state'] = await ctx.store.get("ui_state", None)
    self.globals['step_screenshots'] = []
    self.globals['step_ui_states'] = []

    # 2. 设置工具实例的上下文（用于访问 Context）
    if self.tools_instance and isinstance(self.tools_instance, AdbTools):
        self.tools_instance._set_context(ctx)

    # 3. 捕获 stdout 和 stderr
    stdout = io.StringIO()
    stderr = io.StringIO()

    output = ""
    try:
        thread_exception = []
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):

            # 在线程中执行代码（避免阻塞事件循环）
            def execute_code():
                try:
                    exec(code, self.globals, self.locals)
                except Exception as e:
                    thread_exception.append((e, traceback.format_exc()))

            t = threading.Thread(target=execute_code)
            t.start()
            t.join()

        # 4. 获取输出
        output = stdout.getvalue()
        if stderr.getvalue():
            output += "\n" + stderr.getvalue()
        if thread_exception:
            e, tb = thread_exception[0]
            output += f"\nError: {type(e).__name__}: {str(e)}\n{tb}"

    except Exception as e:
        output = f"Error: {type(e).__name__}: {str(e)}\n"
        output += traceback.format_exc()

    # 5. 返回结果
    return {
        'output': output,
        'screenshots': self.globals['step_screenshots'],
        'ui_states': self.globals['step_ui_states']
    }
```

**安全机制**:
1. **白名单机制**: 只注入允许的工具函数
2. **隔离作用域**: 使用独立的 globals 和 locals
3. **异常捕获**: 捕获所有异常，防止崩溃
4. **线程隔离**: 在单独的线程中执行，避免阻塞

#### 5.3 ui_state 的特殊处理

**为什么要注入 ui_state？**

虽然 LLM 已经通过聊天历史看到了 UI 状态，但在代码执行时，LLM 生成的代码可能需要访问 `ui_state` 变量：

```python
# LLM 生成的代码可能这样写
if len(ui_state) > 0:
    first_element = ui_state[0]
    print(f"First element: {first_element['text']}")
    tap_by_index(first_element['index'])
```

所以在执行前，需要将 `ui_state` 注入到全局作用域。

---

### 6. 工具函数调用流程

当代码执行到工具函数时，会发生什么？

#### 6.1 示例代码

```python
# LLM 生成的代码
tap_by_index(5)
```

#### 6.2 执行流程

```
1. exec(code, globals, locals)
   │
   ▼
2. 查找 globals['tap_by_index']
   │
   ▼
3. 找到绑定方法: AdbTools.tap_by_index
   │
   ▼
4. 调用 tap_by_index(5)
   │
   ▼
5. AdbTools.tap_by_index(self, 5)
   │
   ▼
6. @ui_action 装饰器触发（如果 save_trajectories="action"）
   │
   ▼
7. 通过 TCP 或 Content Provider 发送点击命令到设备
   │
   ▼
8. 设备执行点击操作
   │
   ▼
9. 返回结果（字符串）
```

#### 6.3 @ui_action 装饰器

**位置**: `droidrun/tools/tools.py:19`

```python
@staticmethod
def ui_action(func):
    """
    装饰器，用于捕获 UI 动作的截图和状态

    当 save_trajectories="action" 时：
    1. 执行动作
    2. 自动截图
    3. 自动获取 UI 状态
    4. 添加到 step_screenshots 和 step_ui_states 列表
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        result = func(*args, **kwargs)  # 执行实际动作

        # 检查是否需要保存轨迹
        if hasattr(self, 'save_trajectories') and self.save_trajectories == "action":
            # 获取调用者的全局作用域
            frame = sys._getframe(1)
            caller_globals = frame.f_globals

            # 从调用者的作用域获取列表
            step_screenshots = caller_globals.get('step_screenshots')
            step_ui_states = caller_globals.get('step_ui_states')

            # 添加截图和状态
            if step_screenshots is not None:
                step_screenshots.append(self.take_screenshot()[1])
            if step_ui_states is not None:
                step_ui_states.append(self.get_state())

        return result
    return wrapper
```

**使用示例**:

```python
class AdbTools(Tools):
    @ui_action  # 自动保存动作
    def tap_by_index(self, index: int) -> str:
        # 实现点击逻辑
        ...
```

---

### 7. 结果反馈和循环

执行完代码后，需要将结果反馈给 LLM。

#### 7.1 CodeActAgent 执行步骤

**位置**: `droidrun/agent/codeact/codeact_agent.py:250`

```python
@step
async def execute_code(self, ctx: Context, ev: TaskExecutionEvent) -> TaskExecutionResultEvent:
    """执行代码"""
    code = ev.code
    logger.info(f"⚙️ Executing code:\n{code}")

    # 调用执行器
    result = await self.executor.execute(ctx, code)

    logger.info(f"📄 Execution output: {result['output']}")

    return TaskExecutionResultEvent(
        output=result['output'],
        screenshots=result['screenshots'],
        ui_states=result['ui_states']
    )

@step
async def handle_execution_result(
    self, ctx: Context, ev: TaskExecutionResultEvent
) -> TaskInputEvent | TaskEndEvent:
    """处理执行结果"""

    # 将执行结果作为观察反馈给 LLM
    observation = f"Execution Result:\n{ev.output}"
    observation_message = ChatMessage(role="user", content=observation)
    await self.chat_memory.aput(observation_message)

    # 检查是否调用了 complete()
    if "complete(" in ev.output or self._check_complete_called():
        # 任务完成
        return TaskEndEvent(success=True, reason="Task completed")
    else:
        # 继续循环
        return TaskInputEvent(input=self.chat_memory.get_all())
```

#### 7.2 ReAct 循环

```
┌──────────────────────────────────────────┐
│         ReAct 循环（持续迭代）            │
└──────────────────────────────────────────┘

Step N:
  ┌─────────────────────────────────────┐
  │  1. LLM 看到聊天历史:                │
  │     - 之前的思考和代码               │
  │     - 之前的执行结果（观察）         │
  │     - 当前的 UI 状态和截图           │
  └─────────────────────────────────────┘
                   ↓
  ┌─────────────────────────────────────┐
  │  2. LLM 生成:                        │
  │     思考: "上一步点击了设置按钮，    │
  │            现在需要找到 Wi-Fi 选项"  │
  │     代码:                            │
  │     ```python                        │
  │     tap_by_index(3)                  │
  │     ```                              │
  └─────────────────────────────────────┘
                   ↓
  ┌─────────────────────────────────────┐
  │  3. 执行代码                         │
  │     - 调用 tap_by_index(3)          │
  │     - 设备点击元素                   │
  └─────────────────────────────────────┘
                   ↓
  ┌─────────────────────────────────────┐
  │  4. 观察结果                         │
  │     "执行成功，输出: 已点击元素 3"   │
  └─────────────────────────────────────┘
                   ↓
  ┌─────────────────────────────────────┐
  │  5. 添加观察到聊天历史               │
  └─────────────────────────────────────┘
                   ↓
  ┌─────────────────────────────────────┐
  │  6. 检查是否调用了 complete()        │
  │     - 是: 结束                       │
  │     - 否: 回到步骤 1                 │
  └─────────────────────────────────────┘
```

---

## 完整示例

### 示例 1: 简单点击

**目标**: 点击设置按钮

#### 1. 系统提示（简化）

```
You can use the following functions:

def tap_by_index(index: int) -> str:
    """Tap the element at the given index."""
...

def complete(success: bool, reason: str = "") -> None:
    """Complete the tool."""
...
```

#### 2. 上下文注入

```markdown
### Current UI Elements:
```json
[
    {"index": 1, "className": "Button", "text": "设置", "bounds": [100, 200, 300, 280]},
    {"index": 2, "className": "Button", "text": "关于", "bounds": [100, 300, 300, 380]}
]
```

### Phone State:
```json
{"current_activity": "com.example.app/.MainActivity"}
```
```

#### 3. 用户提示

```
**Current Request:**
点击设置按钮

**Is the precondition met? What is your reasoning and the next step to address this request?**
Explain your thought process then provide code in ```python ... ``` tags if needed.
```

#### 4. LLM 响应

```
**Agent Analysis:**
我可以看到当前屏幕上有两个按钮：
- index 1: "设置" 按钮
- index 2: "关于" 按钮

我需要点击 "设置" 按钮，它的 index 是 1。

**Agent Action:**
```python
tap_by_index(1)
complete(success=True, reason="成功点击设置按钮")
```
```

#### 5. 代码执行

```python
# 执行环境中的 globals:
# {
#   "tap_by_index": <bound method AdbTools.tap_by_index>,
#   "complete": <bound method AdbTools.complete>,
#   "ui_state": [...],
#   "time": <module 'time'>
# }

# 执行代码
tap_by_index(1)  # 调用 AdbTools.tap_by_index(1)
complete(success=True, reason="成功点击设置按钮")  # 调用 AdbTools.complete(...)
```

#### 6. 执行结果

```
Execution Result:
已点击元素 1
```

#### 7. 检测 complete()

```python
# CodeActAgent 检测到调用了 complete()
# 任务结束，返回 TaskEndEvent(success=True)
```

---

### 示例 2: 复杂循环操作

**目标**: 滚动查找 "设置" 按钮并点击

#### Step 1

**LLM 输入**:
```markdown
**Current Request:** 滚动查找 "设置" 按钮并点击

### Current UI Elements:
[{"index": 1, "text": "主页"}, {"index": 2, "text": "消息"}]
```

**LLM 输出**:
```python
# 当前屏幕没有看到 "设置" 按钮，需要向下滚动
swipe(500, 1500, 500, 500, 300)
```

**执行结果**:
```
Execution Result:
滑动完成
```

#### Step 2

**LLM 输入**（包含上一步的结果）:
```markdown
[上一步的思考和代码]
Execution Result: 滑动完成

### Current UI Elements:
[{"index": 1, "text": "通知"}, {"index": 2, "text": "设置"}]
```

**LLM 输出**:
```python
# 太好了！滚动后可以看到 "设置" 按钮了，index 是 2
tap_by_index(2)
complete(success=True, reason="找到并点击了设置按钮")
```

**任务完成**

---

## 关键技术细节

### 1. 异步转同步

**问题**: 工具函数可能是异步的，但 `exec()` 只能执行同步代码。

**解决**: `async_to_sync()` 包装器

**位置**: `droidrun/agent/utils/async_utils.py`

```python
def async_to_sync(func):
    """
    将异步函数转换为同步函数

    原理:
    1. 获取当前事件循环
    2. 使用 loop.run_until_complete() 运行异步函数
    3. 返回同步包装器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper
```

**使用**:

```python
# 在 SimpleCodeExecutor.__init__ 中
if asyncio.iscoroutinefunction(tool_function):
    tool_function = async_to_sync(tool_function)
globals[tool_name] = tool_function
```

---

### 2. 状态持久化

**问题**: 如何在多次代码执行间保持变量状态？

**解决**: 使用相同的 `globals` 和 `locals` 字典

```python
class SimpleCodeExecutor:
    def __init__(self, ...):
        self.globals = globals  # 保存全局作用域
        self.locals = locals    # 保存局部作用域

    async def execute(self, ctx, code):
        # 每次执行使用相同的 globals 和 locals
        exec(code, self.globals, self.locals)
```

**效果**:

```python
# 第一次执行
code1 = "counter = 1"
executor.execute(code1)

# 第二次执行（可以访问 counter）
code2 = "counter += 1; print(counter)"
executor.execute(code2)  # 输出: 2
```

---

### 3. ui_state 访问

**问题**: LLM 可能想在代码中访问 `ui_state` 变量。

**解决**: 在每次执行前注入

```python
async def execute(self, ctx, code):
    # 从 Context 获取最新的 ui_state
    self.globals['ui_state'] = await ctx.store.get("ui_state", None)

    # 执行代码（现在可以访问 ui_state）
    exec(code, self.globals, self.locals)
```

**LLM 生成的代码示例**:

```python
# LLM 可以这样写
for element in ui_state:
    if element['text'] == '设置':
        tap_by_index(element['index'])
        break
```

---

### 4. 轨迹捕获

**问题**: 如何在 "action" 模式下自动捕获每个动作的截图和状态？

**解决**: `@ui_action` 装饰器 + 全局列表

**实现**:

```python
# 1. 在执行前创建列表
self.globals['step_screenshots'] = []
self.globals['step_ui_states'] = []

# 2. 工具函数使用 @ui_action 装饰
@ui_action
def tap_by_index(self, index):
    # 执行点击
    ...

# 3. @ui_action 在动作后自动添加
def ui_action(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        # 从调用者的全局作用域获取列表
        caller_globals = sys._getframe(1).f_globals
        step_screenshots = caller_globals.get('step_screenshots')
        if step_screenshots is not None:
            step_screenshots.append(self.take_screenshot()[1])
        return result
    return wrapper

# 4. 执行后返回列表
return {
    'screenshots': self.globals['step_screenshots'],
    'ui_states': self.globals['step_ui_states']
}
```

---

### 5. complete() 检测

**问题**: 如何知道 LLM 已经完成任务？

**解决**: 检查 `complete()` 函数是否被调用

**方法 1**: 检查输出字符串

```python
if "complete(" in execution_output:
    # 可能调用了 complete()
    return TaskEndEvent(success=True)
```

**方法 2**: 检查标志变量

```python
# 在 Tools.complete() 中设置标志
def complete(self, success, reason):
    self._complete_called = True
    self._complete_success = success
    self._complete_reason = reason

# 在 CodeActAgent 中检查
if self.tools._complete_called:
    return TaskEndEvent(
        success=self.tools._complete_success,
        reason=self.tools._complete_reason
    )
```

---

## 对比其他方案

### vs LangChain Tools

| 特性 | DroidRun CodeAct | LangChain Tools |
|------|-----------------|----------------|
| 调用方式 | LLM 生成 Python 代码 | LLM 返回 JSON 格式的工具调用 |
| 灵活性 | 可以写循环、条件等复杂逻辑 | 每次只能调用工具，需要多轮 |
| 状态保持 | 自动保持（globals） | 需要手动管理 |
| 学习曲线 | 熟悉 Python 即可 | 需要理解工具调用格式 |
| 安全性 | 需要沙箱 | 相对安全 |
| 错误处理 | Python 异常处理 | 受限于框架 |

### vs OpenAI Function Calling

| 特性 | DroidRun CodeAct | OpenAI Function Calling |
|------|-----------------|------------------------|
| 依赖 | 任何 LLM | 仅 OpenAI/Anthropic 等 |
| 表达能力 | Python 完整能力 | 受限于 JSON Schema |
| 多步操作 | 一次完成 | 需要多轮对话 |
| 成本 | 相同 | 相同 |
| 调试 | 可以看到生成的代码 | 黑盒 |

---

## 安全考虑

### 潜在风险

1. **任意代码执行**: LLM 生成的代码可以执行任何 Python 操作
2. **资源消耗**: 无限循环或递归
3. **敏感信息泄露**: 可能访问系统信息

### 缓解措施

1. **工具白名单**: 只注入允许的工具函数
2. **超时限制**: 在线程中执行，可以设置超时
3. **异常捕获**: 所有异常都被捕获
4. **作用域隔离**: 使用独立的 globals
5. **最大步数**: 限制 ReAct 循环次数

### 生产环境建议

如果要在生产环境使用，建议：

1. **使用沙箱**: 例如 RestrictedPython
2. **资源限制**: 限制 CPU、内存使用
3. **审计日志**: 记录所有执行的代码
4. **人工审核**: 关键操作需要人工确认

---

## 总结

### 核心机制

1. **工具描述生成**: 将工具函数转换为 LLM 可读的文档
2. **Persona 过滤**: 根据角色限制可用工具
3. **系统提示构建**: 教 LLM 如何写代码
4. **上下文注入**: 提供设备状态、UI 等信息
5. **代码执行**: 在受控环境中执行 LLM 生成的代码
6. **结果反馈**: 将执行结果反馈给 LLM
7. **ReAct 循环**: 重复"思考-代码-观察"直到完成

### 关键优势

- ✅ **强大的表达能力**: 可以写复杂的逻辑
- ✅ **状态持久化**: 变量在步骤间保持
- ✅ **灵活性**: 不依赖特定的 LLM API
- ✅ **可调试性**: 可以看到生成的代码
- ✅ **可扩展性**: 易于添加新工具

### 适用场景

- ✅ 需要多步复杂操作
- ✅ 需要状态保持
- ✅ 需要灵活的控制流
- ✅ 想要使用任何 LLM
- ✅ 需要透明的执行过程

---

**文档版本**: 1.0
**生成日期**: 2025-10-28
