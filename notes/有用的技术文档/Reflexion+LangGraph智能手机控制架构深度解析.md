# Reflexion + LangGraph 智能手机控制架构深度解析

## 目录

1. [架构概述](#架构概述)
2. [核心组件详解](#核心组件详解)
3. [状态设计](#状态设计)
4. [节点实现方案](#节点实现方案)
5. [记忆系统](#记忆系统)
6. [提示工程](#提示工程)
7. [实现代码示例](#实现代码示例)
8. [性能优化](#性能优化)

---

## 架构概述

### 总体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户任务输入                              │
│                   "在淘宝搜索商品并加入购物车"                      │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph 状态图编排                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Checkpoint 持久化 (SQLite/Postgres/Redis)         │   │
│  │    - 每个节点执行后自动保存状态                             │   │
│  │    - 支持暂停/恢复                                          │   │
│  │    - Thread ID 隔离不同会话                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
┌───────────────┐                  ┌──────────────┐
│  短期记忆      │                  │  长期记忆     │
│ (State)       │                  │ (Store)      │
│ - messages    │                  │ - reflections│
│ - screenshot  │                  │ - experiences│
│ - ui_state    │                  │ - patterns   │
└───────────────┘                  └──────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Reflexion 循环                               │
│                                                                   │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐          │
│  │   Actor    │ ──→ │ Evaluator  │ ──→ │ Self-      │          │
│  │  (执行器)   │     │  (评估器)   │     │ Reflection │          │
│  │            │     │            │     │ (反思器)    │          │
│  └─────┬──────┘     └────────────┘     └──────┬─────┘          │
│        ↓                                        ↓                │
│   Capture → Analyze → Plan → Execute → Verify  │                │
│        ↑                                        │                │
│        └────────────────────────────────────────┘                │
│                    失败重试（带反思记忆）                          │
└─────────────────────────────────────────────────────────────────┘
```

---

### 设计原则

1. **状态驱动 (State-Driven)：** 所有节点通过统一的 State 对象通信
2. **类型安全 (Type-Safe)：** 使用 TypedDict 定义状态结构
3. **可序列化 (Serializable)：** 状态可保存到数据库，支持持久化
4. **可恢复 (Recoverable)：** 通过 Checkpoint 机制实现暂停/恢复
5. **自我改进 (Self-Improving)：** 通过 Reflexion 实现经验累积

---

## 核心组件详解

### 1. Actor (执行器)

**职责：** 感知环境 → 推理决策 → 生成动作

#### Actor 的三种角色

```python
# 角色1: Perception Actor (感知执行器)
async def capture_screen_node(state, config):
    """捕获屏幕状态"""
    adb = AdbTools()
    screenshot = adb.take_screenshot()
    ui_state = adb.get_state()
    return {**state, "screenshot": screenshot, "ui_state": ui_state}

# 角色2: Planning Actor (规划执行器 - ReAct 风格)
async def plan_action_node(state, config):
    """基于 ReAct 推理生成动作计划"""
    llm = config["llm"]

    prompt = f"""
    当前任务: {state['task']}
    当前屏幕: [截图分析结果]
    历史反思: {state['reflections']}

    # Thought (思考)
    分析当前状态，思考下一步应该做什么

    # Action (行动)
    决定具体的操作步骤

    # Expectation (预期)
    描述操作后的预期结果
    """

    response = await llm.ainvoke(prompt)
    return {**state, "action_plan": response}

# 角色3: Execution Actor (操作执行器)
async def execute_action_node(state, config):
    """执行具体的 ADB 操作"""
    adb = AdbTools()

    for action in state['action_plan']:
        if action['type'] == 'tap':
            adb.tap_by_index(action['index'])
        elif action['type'] == 'swipe':
            adb.swipe(action['direction'])
        elif action['type'] == 'input':
            adb.input_text(action['text'])

    return {**state, "execution_result": {"success": True}}
```

---

### 2. Evaluator (评估器)

**职责：** 验证操作结果 → 打分 → 判断成功/失败

#### 评估器的三层架构

```python
class TaskEvaluator:
    """任务评估器"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def evaluate(self, state: AndroidAgentState) -> dict:
        """
        三层评估策略：
        1. 视觉验证 (Visual Verification)
        2. 状态验证 (State Verification)
        3. 语义验证 (Semantic Verification)
        """

        # 层1: 视觉验证
        visual_score = await self._visual_verification(state)

        # 层2: 状态验证
        state_score = await self._state_verification(state)

        # 层3: 语义验证
        semantic_score = await self._semantic_verification(state)

        # 加权评分
        total_score = (
            visual_score * 0.4 +
            state_score * 0.3 +
            semantic_score * 0.3
        )

        return {
            "score": total_score,
            "passed": total_score >= 0.7,
            "visual_score": visual_score,
            "state_score": state_score,
            "semantic_score": semantic_score,
            "details": self._generate_feedback(state)
        }

    async def _visual_verification(self, state):
        """
        视觉验证：截图前后对比

        方法：
        - OCR 文本识别
        - UI 元素位置检测
        - 图像相似度计算
        """
        before_screenshot = state['screenshots'][-2]
        after_screenshot = state['screenshots'][-1]

        # 使用 MLLM 进行视觉对比
        prompt = f"""
        对比操作前后的截图：

        操作目标: {state['action_plan']['expectation']}

        判断标准:
        1. 是否出现了预期的 UI 变化？
        2. 是否有错误提示？
        3. 界面状态是否符合预期？

        给出 0-1 的评分。
        """

        response = await self.llm.ainvoke([
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": before_screenshot},
                {"type": "image_url", "image_url": after_screenshot}
            ])
        ])

        return extract_score(response)

    async def _state_verification(self, state):
        """
        状态验证：UI Hierarchy 对比

        方法：
        - 检查特定元素是否存在
        - 验证状态转换是否正确
        - 监控应用包名变化
        """
        ui_state = state['ui_state']
        expectation = state['action_plan']['expectation']

        # 检查预期元素
        expected_elements = expectation.get('elements', [])
        found_count = 0

        for elem in expected_elements:
            if self._find_element(ui_state, elem):
                found_count += 1

        return found_count / len(expected_elements) if expected_elements else 1.0

    async def _semantic_verification(self, state):
        """
        语义验证：使用 LLM 判断任务完成度

        ProRe 论文方法：
        - 主动状态探测 (Proactive State Probing)
        - 推理器分析任务需求
        - 生成探测任务收集证据
        """
        llm_prompt = f"""
        作为任务评估专家，判断以下操作是否成功完成任务。

        **原始任务:** {state['task']}

        **执行的操作:** {state['action_plan']}

        **当前状态证据:**
        1. 截图显示: [MLLM分析结果]
        2. UI状态: {state['ui_state']}
        3. 应用信息: {state['ui_state']['package']}

        **评估标准:**
        - 任务目标是否达成？
        - 是否存在明显错误？
        - 是否需要额外验证？

        输出JSON格式：
        {{
            "success": true/false,
            "confidence": 0.0-1.0,
            "reason": "评估理由",
            "missing_steps": ["如果失败，列出缺失步骤"]
        }}
        """

        response = await self.llm.ainvoke(llm_prompt)
        result = json.loads(response.content)

        return result['confidence'] if result['success'] else 0.0
```

---

### 3. Self-Reflection (自我反思器)

**职责：** 分析失败原因 → 生成语言反馈 → 存入记忆

#### 反思器的实现

```python
class ReflectionGenerator:
    """反思生成器"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def generate_reflection(self, state: AndroidAgentState) -> str:
        """
        生成自我反思

        基于 Reflexion 论文的反思模板：
        1. 什么地方出错了？(What went wrong?)
        2. 为什么会出错？(Why did it fail?)
        3. 应该如何改进？(How to improve?)
        """

        evaluation = state['evaluation_result']

        prompt = f"""
        你是一个自我反思专家，负责分析任务执行过程中的问题。

        ## 任务信息
        - 原始任务: {state['task']}
        - 执行计划: {state['action_plan']}
        - 期望结果: {state['action_plan']['expectation']}

        ## 执行结果
        - 评分: {evaluation['score']:.2f}
        - 视觉验证: {evaluation['visual_score']:.2f}
        - 状态验证: {evaluation['state_score']:.2f}
        - 语义验证: {evaluation['semantic_score']:.2f}

        ## 反馈细节
        {evaluation['details']}

        ## 历史反思
        {self._format_past_reflections(state['reflections'])}

        请按照以下结构进行深度反思：

        ### 1. 错误分析 (Error Analysis)
        - 具体哪一步出现了问题？
        - 问题的直接原因是什么？

        ### 2. 根因定位 (Root Cause)
        - 深层次的原因是什么？
        - 是理解错误、定位错误、还是操作错误？

        ### 3. 改进建议 (Improvement Strategy)
        - 下次遇到类似情况应该如何处理？
        - 需要采集哪些额外信息？
        - 是否需要调整策略？

        ### 4. 可复用经验 (Reusable Insights)
        - 这次失败能总结出什么通用规律？
        - 哪些经验可以应用到其他任务？

        输出简洁、具体、可操作的反思（200字以内）。
        """

        response = await self.llm.ainvoke(prompt)
        reflection_text = response.content

        # 结构化存储
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "task": state['task'],
            "action": state['action_plan'],
            "evaluation": evaluation,
            "reflection": reflection_text,
            "retry_count": state['retry_count']
        }

        return reflection

    def _format_past_reflections(self, reflections: list) -> str:
        """格式化历史反思，供上下文参考"""
        if not reflections:
            return "暂无历史反思"

        formatted = []
        for i, ref in enumerate(reflections[-3:], 1):  # 只取最近3次
            formatted.append(f"""
            第{i}次反思:
            - 任务: {ref['task']}
            - 问题: {ref['reflection'][:100]}...
            """)

        return "\n".join(formatted)
```

---

## 状态设计

### 完整状态定义

```python
from typing import Literal, Annotated, TypedDict
from langgraph.graph.message import add_messages

class AndroidAgentState(TypedDict):
    """
    LangGraph 状态定义

    设计原则：
    1. 所有字段可序列化（支持 Checkpoint）
    2. 使用 Annotated 支持特殊累积逻辑
    3. 区分短期状态和长期状态
    """

    # ============ 任务相关 ============
    task: str  # 用户原始任务描述
    task_status: Literal["pending", "in_progress", "completed", "failed"]

    # ============ 消息历史（自动累积）============
    messages: Annotated[list, add_messages]

    # ============ 感知数据 ============
    screenshot: bytes | None  # 当前截图
    screenshots: list[bytes]  # 历史截图序列
    ui_state: dict | None  # UI Hierarchy JSON
    ui_states: list[dict]  # 历史 UI 状态

    # ============ 分析结果 ============
    screen_analysis: dict | None  # MLLM 屏幕分析结果
    extracted_elements: list[dict] | None  # 提取的 UI 元素

    # ============ 规划与执行 ============
    action_plan: dict | None  # 当前动作计划 (ReAct 格式)
    """
    action_plan 结构:
    {
        "thought": "思考过程",
        "action": {
            "type": "tap/swipe/input",
            "target": "目标描述",
            "params": {...}
        },
        "expectation": "预期结果描述"
    }
    """

    execution_result: dict | None  # 执行结果
    """
    execution_result 结构:
    {
        "success": true/false,
        "actions_performed": [...],
        "errors": [...],
        "duration": 1.23
    }
    """

    # ============ 评估与验证 ============
    evaluation_result: dict | None  # 评估结果
    """
    evaluation_result 结构:
    {
        "score": 0.85,
        "passed": true,
        "visual_score": 0.9,
        "state_score": 0.8,
        "semantic_score": 0.85,
        "details": "详细反馈"
    }
    """

    # ============ 反思与记忆 ============
    reflections: list[dict]  # 反思历史（情景记忆缓冲区）
    """
    单个 reflection 结构:
    {
        "timestamp": "2025-01-01T12:00:00",
        "task": "原始任务",
        "action": {...},
        "evaluation": {...},
        "reflection": "反思内容",
        "retry_count": 1
    }
    """

    long_term_memory: dict | None  # 长期记忆索引
    """
    long_term_memory 结构:
    {
        "successful_patterns": [...],  # 成功的操作模式
        "failure_patterns": [...],     # 失败的操作模式
        "app_knowledge": {...},        # 应用特定知识
        "user_preferences": {...}      # 用户偏好
    }
    """

    # ============ 控制流 ============
    next_action: Literal[
        "capture",      # 捕获屏幕
        "analyze",      # 分析屏幕
        "plan",         # 规划动作
        "execute",      # 执行动作
        "verify",       # 验证结果
        "reflect",      # 自我反思
        "end"           # 结束
    ] | None

    retry_count: int  # 当前任务重试次数
    max_retries: int  # 最大重试次数（默认3次）

    # ============ 元数据 ============
    thread_id: str  # 会话 ID
    node_history: list[str]  # 节点执行历史
    start_time: str | None
    end_time: str | None

    # ============ 工具相关 ============
    tool_descriptions: str | None  # 工具描述（序列化字符串）
    available_tools: list[str]  # 可用工具列表
```

---

## 节点实现方案

### 节点1: Capture (捕获)

```python
async def capture_node(
    state: AndroidAgentState,
    config: RunnableConfig
) -> AndroidAgentState:
    """
    捕获节点：获取设备当前状态

    输入: state (任务信息)
    输出: state + screenshot + ui_state
    """
    print("📱 [Capture] 捕获屏幕状态...")

    adb = AdbTools(use_tcp=True)

    # 1. 截图
    _, screenshot_bytes = adb.take_screenshot(hide_overlay=True)

    # 2. 获取 UI Hierarchy
    ui_state = adb.get_state()

    # 3. 更新历史记录
    screenshots = state.get('screenshots', [])
    screenshots.append(screenshot_bytes)

    ui_states = state.get('ui_states', [])
    ui_states.append(ui_state)

    # 4. 记录节点访问
    node_history = state.get('node_history', [])
    node_history.append(f"capture_{len(node_history)}")

    return {
        **state,
        "screenshot": screenshot_bytes,
        "screenshots": screenshots,
        "ui_state": ui_state,
        "ui_states": ui_states,
        "node_history": node_history,
        "next_action": "analyze"
    }
```

---

### 节点2: Analyze (分析)

```python
async def analyze_node(
    state: AndroidAgentState,
    config: RunnableConfig
) -> AndroidAgentState:
    """
    分析节点：使用 MLLM 理解屏幕内容

    输入: state + screenshot + ui_state
    输出: state + screen_analysis + extracted_elements
    """
    print("🔍 [Analyze] 分析屏幕内容...")

    llm: ChatOpenAI = config["configurable"]["llm"]

    # 构造多模态分析提示
    prompt = f"""
    你是一个 Android UI 分析专家。请分析这个屏幕截图和 UI 结构。

    **当前任务:** {state['task']}

    **分析要求:**
    1. 识别屏幕上的关键 UI 元素
    2. 理解当前页面的功能和状态
    3. 提取可交互的元素（按钮、输入框、列表项等）
    4. 判断当前页面是否与任务相关

    **UI 状态数据:**
    ```json
    {json.dumps(state['ui_state'], ensure_ascii=False, indent=2)}
    ```

    **输出格式 (JSON):**
    {{
        "page_type": "页面类型（搜索页/列表页/详情页/等）",
        "current_app": "当前应用名称",
        "key_elements": [
            {{
                "type": "button/input/text/image/list_item",
                "description": "元素描述",
                "text": "元素文本",
                "index": UI元素索引,
                "bounds": [x1, y1, x2, y2],
                "interactable": true/false
            }}
        ],
        "task_relevance": "与任务的相关性分析",
        "suggested_action": "建议的下一步操作"
    }}
    """

    # 调用多模态 LLM
    messages = [
        HumanMessage(content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(state['screenshot']).decode()}"
                }
            }
        ])
    ]

    response = await llm.ainvoke(messages)
    analysis = json.loads(extract_json_from_text(response.content))

    return {
        **state,
        "screen_analysis": analysis,
        "extracted_elements": analysis['key_elements'],
        "next_action": "plan"
    }
```

---

### 节点3: Plan (规划 - ReAct 风格)

```python
async def plan_node(
    state: AndroidAgentState,
    config: RunnableConfig
) -> AndroidAgentState:
    """
    规划节点：使用 ReAct 推理生成动作计划

    输入: state + screen_analysis
    输出: state + action_plan
    """
    print("🧠 [Plan] 生成动作计划（ReAct 推理）...")

    llm: ChatOpenAI = config["configurable"]["llm"]

    # 加载历史反思
    reflections_text = ""
    if state.get('reflections'):
        reflections_text = "\n".join([
            f"- {r['reflection'][:150]}"
            for r in state['reflections'][-3:]
        ])

    # ReAct 推理提示
    prompt = f"""
    你是一个 Android 操作规划专家，使用 ReAct (Reasoning + Acting) 框架进行推理。

    ## 任务目标
    {state['task']}

    ## 当前状态
    - 页面类型: {state['screen_analysis']['page_type']}
    - 当前应用: {state['screen_analysis']['current_app']}
    - 可交互元素: {len(state['extracted_elements'])} 个

    ## 屏幕分析
    {json.dumps(state['screen_analysis'], ensure_ascii=False, indent=2)}

    ## 历史反思（经验教训）
    {reflections_text if reflections_text else "暂无历史反思"}

    ## 可用工具
    {state['tool_descriptions']}

    ---

    请按照 ReAct 格式进行推理：

    ### Thought (思考)
    分析当前状态，思考：
    1. 当前处于任务的哪个阶段？
    2. 需要完成什么子目标？
    3. 有哪些可行的操作路径？
    4. 历史反思中有什么相关经验？

    ### Action (行动计划)
    决定具体的操作步骤：
    - 操作类型 (tap/swipe/input/wait)
    - 目标元素
    - 操作参数

    ### Expectation (预期结果)
    描述操作后的预期变化：
    - 界面应该发生什么变化？
    - 如何判断操作成功？
    - 可能出现哪些异常情况？

    **输出格式 (JSON):**
    {{
        "thought": "详细的思考过程",
        "action": {{
            "type": "tap/swipe/input/back/wait",
            "target": "目标描述",
            "index": UI元素索引（如果是tap）,
            "text": "输入文本（如果是input）",
            "direction": "方向（如果是swipe）",
            "confidence": 0.0-1.0
        }},
        "expectation": {{
            "ui_changes": "预期的UI变化描述",
            "success_indicators": ["成功标志1", "成功标志2"],
            "failure_indicators": ["失败标志1", "失败标志2"],
            "next_step": "如果成功，下一步应该做什么"
        }},
        "reasoning_chain": ["推理步骤1", "推理步骤2", "推理步骤3"]
    }}
    """

    response = await llm.ainvoke(prompt)
    action_plan = json.loads(extract_json_from_text(response.content))

    # 记录推理链
    print(f"💭 思考: {action_plan['thought'][:100]}...")
    print(f"🎯 行动: {action_plan['action']['type']} - {action_plan['action']['target']}")

    return {
        **state,
        "action_plan": action_plan,
        "next_action": "execute"
    }
```

---

### 节点4: Execute (执行)

```python
async def execute_node(
    state: AndroidAgentState,
    config: RunnableConfig
) -> AndroidAgentState:
    """
    执行节点：通过 ADB 执行操作

    输入: state + action_plan
    输出: state + execution_result
    """
    print("⚡ [Execute] 执行操作...")

    adb = AdbTools(use_tcp=True)
    action = state['action_plan']['action']

    start_time = time.time()
    errors = []
    actions_performed = []

    try:
        if action['type'] == 'tap':
            index = action['index']
            adb.tap_by_index(index)
            actions_performed.append(f"Tap element #{index}")
            await asyncio.sleep(1)  # 等待 UI 响应

        elif action['type'] == 'input':
            text = action['text']
            adb.input_text(text)
            actions_performed.append(f"Input text: {text}")
            await asyncio.sleep(0.5)

        elif action['type'] == 'swipe':
            direction = action['direction']
            adb.swipe(direction)
            actions_performed.append(f"Swipe {direction}")
            await asyncio.sleep(1)

        elif action['type'] == 'back':
            adb.press_back()
            actions_performed.append("Press back")
            await asyncio.sleep(0.5)

        elif action['type'] == 'wait':
            duration = action.get('duration', 2)
            await asyncio.sleep(duration)
            actions_performed.append(f"Wait {duration}s")

        success = True

    except Exception as e:
        success = False
        errors.append(str(e))
        print(f"❌ 执行失败: {e}")

    duration = time.time() - start_time

    execution_result = {
        "success": success,
        "actions_performed": actions_performed,
        "errors": errors,
        "duration": duration
    }

    return {
        **state,
        "execution_result": execution_result,
        "next_action": "verify"
    }
```

---

### 节点5: Verify (验证 - Evaluator)

```python
async def verify_node(
    state: AndroidAgentState,
    config: RunnableConfig
) -> AndroidAgentState:
    """
    验证节点：评估操作结果

    输入: state + execution_result
    输出: state + evaluation_result + next_action
    """
    print("✅ [Verify] 验证操作结果...")

    # 先捕获新状态
    adb = AdbTools(use_tcp=True)
    new_screenshot = adb.take_screenshot()[1]
    new_ui_state = adb.get_state()

    # 更新状态
    state['screenshot'] = new_screenshot
    state['screenshots'].append(new_screenshot)
    state['ui_state'] = new_ui_state
    state['ui_states'].append(new_ui_state)

    # 使用 Evaluator 进行评估
    evaluator = TaskEvaluator(config["configurable"]["llm"])
    evaluation_result = await evaluator.evaluate(state)

    print(f"📊 评估得分: {evaluation_result['score']:.2f}")
    print(f"   - 视觉验证: {evaluation_result['visual_score']:.2f}")
    print(f"   - 状态验证: {evaluation_result['state_score']:.2f}")
    print(f"   - 语义验证: {evaluation_result['semantic_score']:.2f}")

    # 决定下一步
    if evaluation_result['passed']:
        # 成功：检查任务是否完成
        task_completed = await check_task_completion(state, config)
        next_action = "end" if task_completed else "capture"
        print("✅ 验证通过，继续下一步")
    else:
        # 失败：需要反思
        next_action = "reflect"
        print("⚠️  验证失败，需要反思")

    return {
        **state,
        "evaluation_result": evaluation_result,
        "next_action": next_action
    }
```

---

### 节点6: Reflect (反思 - Self-Reflection)

```python
async def reflect_node(
    state: AndroidAgentState,
    config: RunnableConfig
) -> AndroidAgentState:
    """
    反思节点：生成语言反馈并决定是否重试

    输入: state + evaluation_result
    输出: state + reflections + next_action
    """
    print("🤔 [Reflect] 自我反思...")

    # 生成反思
    reflection_generator = ReflectionGenerator(config["configurable"]["llm"])
    reflection = await reflection_generator.generate_reflection(state)

    # 存入情景记忆缓冲区
    reflections = state.get('reflections', [])
    reflections.append(reflection)

    # 同步到长期记忆
    long_term_memory = state.get('long_term_memory', {})
    long_term_memory = await update_long_term_memory(
        long_term_memory,
        reflection,
        config
    )

    print(f"💡 反思内容: {reflection['reflection'][:150]}...")

    # 决定是否重试
    retry_count = state.get('retry_count', 0) + 1
    max_retries = state.get('max_retries', 3)

    if retry_count < max_retries:
        print(f"🔄 重试 {retry_count}/{max_retries}")
        next_action = "plan"  # 返回规划节点，带上反思记忆
    else:
        print(f"❌ 达到最大重试次数，任务失败")
        next_action = "end"

    return {
        **state,
        "reflections": reflections,
        "long_term_memory": long_term_memory,
        "retry_count": retry_count,
        "next_action": next_action,
        "task_status": "failed" if retry_count >= max_retries else "in_progress"
    }
```

---

### 节点7: 条件路由函数

```python
def route_next_action(state: AndroidAgentState) -> str:
    """
    条件路由：根据 state['next_action'] 决定下一个节点

    LangGraph 使用此函数进行动态路由
    """
    next_action = state.get('next_action')

    routing_map = {
        "capture": "capture",
        "analyze": "analyze",
        "plan": "plan",
        "execute": "execute",
        "verify": "verify",
        "reflect": "reflect",
        "end": END
    }

    return routing_map.get(next_action, END)
```

---

## 记忆系统

### 短期记忆 (Short-Term Memory)

**实现：** 通过 LangGraph 的 State 对象

```python
# 短期记忆存储在 State 中
state = {
    "messages": [...],           # 对话历史
    "screenshots": [...],        # 最近的截图
    "ui_states": [...],          # 最近的 UI 状态
    "reflections": [...][-5:]   # 最近5次反思
}
```

**生命周期：** 单个 Thread (会话) 内有效

---

### 长期记忆 (Long-Term Memory)

**实现：** 通过 LangGraph Store API + 向量数据库

```python
from langgraph.store.memory import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

class LongTermMemoryManager:
    """长期记忆管理器"""

    def __init__(self):
        self.store = InMemoryStore()
        self.embeddings = OpenAIEmbeddings()
        self.vector_db = Chroma(embedding_function=self.embeddings)

    async def save_reflection(self, reflection: dict, namespace: str):
        """保存反思到长期记忆"""

        # 1. 结构化存储（快速检索）
        await self.store.aput(
            namespace=(namespace, "reflections"),
            key=reflection['timestamp'],
            value=reflection
        )

        # 2. 向量化存储（语义检索）
        reflection_text = f"""
        任务: {reflection['task']}
        问题: {reflection['reflection']}
        """

        self.vector_db.add_texts(
            texts=[reflection_text],
            metadatas=[{
                "timestamp": reflection['timestamp'],
                "task": reflection['task'],
                "score": reflection['evaluation']['score']
            }]
        )

    async def retrieve_relevant_reflections(
        self,
        current_task: str,
        top_k: int = 3
    ) -> list[dict]:
        """检索相关的历史反思"""

        # 语义搜索
        docs = self.vector_db.similarity_search(
            current_task,
            k=top_k
        )

        # 获取完整反思数据
        reflections = []
        for doc in docs:
            timestamp = doc.metadata['timestamp']
            reflection = await self.store.aget(
                namespace=("user", "reflections"),
                key=timestamp
            )
            reflections.append(reflection)

        return reflections

    async def extract_patterns(self, namespace: str) -> dict:
        """从历史中提取成功/失败模式"""

        # 获取所有反思
        all_reflections = await self.store.asearch(
            namespace_prefix=(namespace,)
        )

        # 分类
        successful = [r for r in all_reflections if r.value['evaluation']['passed']]
        failed = [r for r in all_reflections if not r.value['evaluation']['passed']]

        # 提取模式（使用 LLM）
        patterns = {
            "successful_patterns": await self._extract_common_patterns(successful),
            "failure_patterns": await self._extract_common_patterns(failed),
            "app_knowledge": await self._extract_app_knowledge(all_reflections)
        }

        return patterns
```

---

### 情景记忆缓冲区 (Episodic Memory Buffer)

**灵感来源：** Reflexion 论文 + 认知心理学

```python
class EpisodicMemoryBuffer:
    """
    情景记忆缓冲区

    基于 Baddeley 的工作记忆模型：
    - 短期存储多模态信息
    - 绑定来自不同来源的信息
    - 与长期记忆交互
    """

    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.buffer: list[dict] = []

    def add_episode(self, episode: dict):
        """添加一个情景"""
        self.buffer.append(episode)

        # 容量限制，移除最旧的
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

    def get_recent_episodes(self, n: int = 3) -> list[dict]:
        """获取最近的 n 个情景"""
        return self.buffer[-n:]

    def search_similar_episodes(self, query: str, top_k: int = 3) -> list[dict]:
        """搜索相似的情景"""
        # 使用向量相似度
        similarities = []
        for episode in self.buffer:
            sim = cosine_similarity(
                embed(query),
                embed(episode['description'])
            )
            similarities.append((sim, episode))

        # 排序并返回 top_k
        similarities.sort(reverse=True, key=lambda x: x[0])
        return [ep for _, ep in similarities[:top_k]]
```

---

## 提示工程

### 提示模板设计原则

1. **结构化输出：** 使用 JSON Schema 约束输出格式
2. **Few-Shot 示例：** 提供成功/失败的案例
3. **上下文注入：** 动态插入历史反思
4. **思维链 (CoT)：** 引导逐步推理
5. **自我批评：** 鼓励质疑和验证

---

### 关键提示模板

#### 1. 分析提示 (Analyze Prompt)

```python
ANALYZE_PROMPT_TEMPLATE = """
你是一个 Android UI 分析专家，擅长理解屏幕内容和提取关键信息。

## 任务目标
{task}

## 当前屏幕
[截图]

## UI 结构数据
```json
{ui_state_json}
```

## 分析步骤
1. **识别页面类型**
   - 这是什么页面？（首页/搜索页/列表页/详情页/设置页/...）
   - 主要功能是什么？

2. **提取关键元素**
   - 按钮、输入框、列表项、图片、文本
   - 标注 index 和坐标
   - 判断是否可交互

3. **关联任务目标**
   - 当前页面与任务的相关性
   - 任务进度评估
   - 建议的下一步操作

## 输出格式
```json
{{
  "page_type": "...",
  "current_app": "...",
  "key_elements": [...],
  "task_relevance": "...",
  "task_progress": "0-100%",
  "suggested_action": "..."
}}
```

## Few-Shot 示例
<example>
任务: "在淘宝搜索 iPhone"
屏幕: 淘宝首页，顶部有搜索框
输出:
{{
  "page_type": "home",
  "current_app": "com.taobao.taobao",
  "key_elements": [
    {{
      "type": "input",
      "description": "搜索框",
      "text": "请输入关键词",
      "index": 5,
      "bounds": [100, 50, 900, 150],
      "interactable": true
    }}
  ],
  "task_relevance": "高度相关，搜索框可直接完成任务",
  "task_progress": "10%",
  "suggested_action": "点击搜索框并输入 'iPhone'"
}}
</example>

开始分析！
"""
```

---

#### 2. 规划提示 (Plan Prompt - ReAct)

```python
PLAN_PROMPT_TEMPLATE = """
你是一个 Android 操作规划专家，使用 ReAct (Reasoning + Acting) 框架进行推理。

## 任务目标
{task}

## 当前状态
- 页面: {page_type}
- 应用: {current_app}
- 进度: {task_progress}

## 屏幕分析
{screen_analysis}

## 历史反思（经验教训）
{reflections}

## 可用工具
{tool_descriptions}

---

## ReAct 推理框架

### Thought (思考)
分析当前状态，逐步推理：
1. **任务分解：** 当前处于任务的哪个阶段？还需要完成什么？
2. **环境感知：** 屏幕上有哪些可用的交互元素？
3. **策略选择：** 有哪些可行的操作路径？哪个最优？
4. **经验借鉴：** 历史反思中有什么相关经验？

### Action (行动计划)
基于推理，决定具体操作：
- 操作类型
- 目标元素
- 操作参数
- 置信度评估

### Expectation (预期结果)
预测操作后的变化：
- UI 应该如何变化？
- 如何判断成功？
- 可能的异常情况？

---

## Few-Shot 示例

<example>
任务: "在淘宝搜索 iPhone 并查看第一个商品"
当前状态: 淘宝首页，搜索框可见

Thought:
1. 任务分解: 需要完成两个子任务 - (1) 搜索 iPhone (2) 点击第一个商品
2. 环境感知: 当前在淘宝首页，有一个搜索框（index=5）
3. 策略选择: 先点击搜索框，然后输入关键词，最后点击搜索按钮
4. 经验借鉴: 无相关历史反思

Action:
{{
  "type": "tap",
  "target": "搜索框",
  "index": 5,
  "confidence": 0.95
}}

Expectation:
{{
  "ui_changes": "搜索框获得焦点，弹出软键盘，可以输入文本",
  "success_indicators": ["软键盘可见", "搜索框处于编辑状态"],
  "failure_indicators": ["页面无变化", "跳转到其他页面"],
  "next_step": "输入 'iPhone' 并搜索"
}}
</example>

<example>
任务: "向下滚动查看更多商品"
当前状态: 商品列表页，已经看了前10个商品

Thought:
1. 任务分解: 简单的滚动操作，查看更多内容
2. 环境感知: 当前在列表页中间位置
3. 策略选择: 向上滑动手势
4. 经验借鉴: 历史反思显示"滑动速度要适中，避免跳过内容"

Action:
{{
  "type": "swipe",
  "direction": "up",
  "confidence": 0.98
}}

Expectation:
{{
  "ui_changes": "列表向上滚动，显示下方的商品",
  "success_indicators": ["新商品出现", "列表位置改变"],
  "failure_indicators": ["滑动到底部", "页面无响应"],
  "next_step": "继续分析新显示的商品"
}}
</example>

---

现在轮到你了！请使用 ReAct 框架进行推理并生成动作计划。

输出格式 (JSON):
```json
{{
  "thought": "详细的思考过程（200字以内）",
  "action": {{...}},
  "expectation": {{...}},
  "reasoning_chain": ["推理步骤1", "推理步骤2", "推理步骤3"]
}}
```
"""
```

---

#### 3. 反思提示 (Reflection Prompt)

```python
REFLECTION_PROMPT_TEMPLATE = """
你是一个自我反思专家，负责分析任务执行过程中的问题并生成可操作的改进建议。

## 任务信息
- 原始任务: {task}
- 执行计划: {action_plan}
- 期望结果: {expectation}

## 执行结果
- 总体得分: {score:.2f}
- 视觉验证: {visual_score:.2f}
- 状态验证: {state_score:.2f}
- 语义验证: {semantic_score:.2f}

## 反馈细节
{evaluation_details}

## 历史反思
{past_reflections}

---

## 反思框架（基于 Reflexion 论文）

### 1. 错误分析 (What went wrong?)
- 具体哪一步出现了问题？
- 问题的表现是什么？
- 与预期有什么偏差？

### 2. 根因定位 (Why did it fail?)
- 深层次的原因是什么？
- 是理解错误、定位错误、还是操作错误？
- 是否存在环境因素（网络延迟、动画未完成等）？

### 3. 改进建议 (How to improve?)
- 下次遇到类似情况应该如何处理？
- 需要采集哪些额外信息？
- 是否需要调整策略或等待时机？

### 4. 可复用经验 (Reusable Insights)
- 这次失败能总结出什么通用规律？
- 哪些经验可以应用到其他任务？
- 可以添加到知识库的模式？

---

## Few-Shot 示例

<example>
任务: 点击搜索按钮
得分: 0.3（失败）
问题: 点击后页面无响应

反思:
1. 错误分析: 点击了搜索按钮（index=10），但页面没有跳转到搜索结果页
2. 根因定位: 查看截图发现，实际点击的是一个装饰性图标，真正的搜索按钮在旁边（index=11）
3. 改进建议:
   - 仔细区分可点击元素和装饰元素
   - 通过 clickable 属性进行验证
   - 优先选择带有 onClick 事件的元素
4. 可复用经验:
   - "不要仅根据视觉位置判断，要结合 UI 属性"
   - "搜索按钮通常有 '搜索' 文本或放大镜图标"
</example>

<example>
任务: 输入文本到搜索框
得分: 0.5（部分成功）
问题: 文本输入了，但搜索没有触发

反思:
1. 错误分析: 文本成功输入到搜索框，但没有触发搜索动作
2. 根因定位: 输入文本后需要点击软键盘的"搜索"按钮或物理回车键
3. 改进建议:
   - 输入文本后，添加一个 enter 或点击搜索按钮的操作
   - 将"输入+搜索"视为一个完整流程
4. 可复用经验:
   - "输入操作后通常需要确认动作（回车/搜索/提交）"
</example>

---

请为当前失败生成简洁、具体、可操作的反思（200字以内）。

输出格式 (纯文本):
简洁总结问题和改进方案，避免冗长描述。
"""
```

---

## 实现代码示例

### 完整的 LangGraph 构建

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

def create_reflexion_android_agent() -> CompiledGraph:
    """
    创建 Reflexion + LangGraph 智能手机控制 Agent
    """

    # 1. 创建状态图
    workflow = StateGraph(AndroidAgentState)

    # 2. 添加节点
    workflow.add_node("capture", capture_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("reflect", reflect_node)

    # 3. 设置入口点
    workflow.add_edge(START, "capture")

    # 4. 添加条件边（动态路由）
    workflow.add_conditional_edges(
        "capture",
        route_next_action,
        {
            "analyze": "analyze",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "analyze",
        route_next_action,
        {
            "plan": "plan",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "plan",
        route_next_action,
        {
            "execute": "execute",
            "plan": "plan",  # 允许重新规划
            END: END
        }
    )

    workflow.add_conditional_edges(
        "execute",
        route_next_action,
        {
            "verify": "verify",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "verify",
        route_next_action,
        {
            "reflect": "reflect",
            "capture": "capture",  # 成功，继续下一轮
            END: END
        }
    )

    workflow.add_conditional_edges(
        "reflect",
        route_next_action,
        {
            "plan": "plan",  # 重试（带反思）
            END: END
        }
    )

    # 5. 编译图（使用 SQLite Checkpoint）
    memory = SqliteSaver.from_conn_string("checkpoints.db")
    app = workflow.compile(checkpointer=memory)

    return app


# 使用示例
async def main():
    """主函数"""

    # 1. 创建 Agent
    app = create_reflexion_android_agent()

    # 2. 初始化 LLM 和工具
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = get_android_tools(use_tcp=True)

    # 3. 初始化状态
    initial_state: AndroidAgentState = {
        "task": "在淘宝搜索 iPhone 15 Pro 并查看前3个商品详情",
        "task_status": "pending",
        "messages": [],
        "screenshot": None,
        "screenshots": [],
        "ui_state": None,
        "ui_states": [],
        "screen_analysis": None,
        "extracted_elements": None,
        "action_plan": None,
        "execution_result": None,
        "evaluation_result": None,
        "reflections": [],
        "long_term_memory": None,
        "next_action": "capture",
        "retry_count": 0,
        "max_retries": 3,
        "thread_id": "test_001",
        "node_history": [],
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "tool_descriptions": None,
        "available_tools": list(tools.keys())
    }

    # 4. 配置
    config = {
        "configurable": {
            "llm": llm,
            "tools": tools,
            "thread_id": "test_001"
        }
    }

    # 5. 执行工作流
    print("🚀 开始执行任务...")
    final_state = await app.ainvoke(initial_state, config)

    # 6. 输出结果
    print("\n" + "=" * 100)
    print("📊 任务执行完成")
    print("=" * 100)
    print(f"任务状态: {final_state['task_status']}")
    print(f"重试次数: {final_state['retry_count']}")
    print(f"节点轨迹: {' → '.join(final_state['node_history'])}")
    print(f"反思次数: {len(final_state['reflections'])}")

    if final_state.get('reflections'):
        print("\n最后一次反思:")
        print(final_state['reflections'][-1]['reflection'])


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 性能优化

### 1. 减少 LLM 调用次数

**策略：**
- 合并分析和规划为一个 LLM 调用
- 使用缓存机制存储常见分析结果
- 简单操作跳过反思阶段

```python
# 优化前
analyze_result = await llm.ainvoke(analyze_prompt)
plan_result = await llm.ainvoke(plan_prompt)

# 优化后
combined_result = await llm.ainvoke(combined_prompt)  # 一次调用
```

---

### 2. 截图压缩

**策略：**
- 降低分辨率（保持可读性）
- 使用 WebP 格式
- 只传输关键区域

```python
from PIL import Image
import io

def compress_screenshot(screenshot_bytes: bytes, max_size: int = 512) -> bytes:
    """压缩截图"""
    img = Image.open(io.BytesIO(screenshot_bytes))

    # 等比缩放
    img.thumbnail((max_size, max_size * 2))

    # 转为 WebP
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=80)

    return buffer.getvalue()
```

---

### 3. 并行执行

**策略：**
- 并行调用多个 LLM（分析不同方面）
- 异步执行 ADB 操作

```python
# 并行分析
results = await asyncio.gather(
    llm.ainvoke(visual_analysis_prompt),
    llm.ainvoke(semantic_analysis_prompt),
    llm.ainvoke(interaction_analysis_prompt)
)
```

---

### 4. Checkpoint 优化

**策略：**
- 使用 Postgres 代替 SQLite（生产环境）
- 定期清理旧 Checkpoint
- 只保存关键状态

```python
from langgraph.checkpoint.postgres import PostgresSaver

# 生产环境使用 Postgres
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/db"
)

app = workflow.compile(checkpointer=checkpointer)
```

---

### 5. 长期记忆检索优化

**策略：**
- 使用向量索引（FAISS/Milvus）
- 分层存储（热数据/冷数据）
- 定期总结和压缩

```python
from langchain_community.vectorstores import FAISS

# 使用 FAISS 加速检索
vector_store = FAISS.from_texts(
    texts=reflection_texts,
    embedding=OpenAIEmbeddings()
)

# 快速检索
relevant_reflections = vector_store.similarity_search(
    query=current_task,
    k=3
)
```

---

## 总结

### 核心优势

1. **自我改进：** 通过 Reflexion 机制不断从失败中学习
2. **状态管理：** LangGraph 提供清晰的状态流转和持久化
3. **可恢复性：** Checkpoint 机制支持暂停/恢复
4. **可扩展性：** 容易添加新节点和新策略
5. **可解释性：** ReAct 推理过程透明，便于调试

---

### 关键指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| **任务成功率** | > 80% | 完成任务 / 总任务数 |
| **平均重试次数** | < 1.5 | 总重试次数 / 总任务数 |
| **平均执行时间** | < 60s | 从开始到完成的时间 |
| **反思质量** | > 0.7 | LLM 评估反思的有用性 |
| **记忆检索准确率** | > 85% | 检索到的相关反思 / 总检索数 |

---

### 未来改进方向

1. **多模态理解：** 集成 Ferret-UI、CogAgent 等专用模型
2. **树搜索规划：** 结合 MCTS 进行更深度的规划
3. **多 Agent 协作：** 分工为导航 Agent 和操作 Agent
4. **主动学习：** 从人类演示中学习新模式
5. **迁移学习：** 将一个 App 的经验迁移到其他 App

---

## 参考资源

### 论文
1. **Reflexion: Language Agents with Verbal Reinforcement Learning** - NeurIPS 2023
2. **ReAct: Synergizing Reasoning and Acting in Language Models** - ICLR 2023
3. **ProRe: A Proactive Reward System for GUI Agents** - arXiv 2024
4. **LangGraph Documentation** - https://langchain-ai.github.io/langgraph/

### 代码仓库
- LangGraph Reflexion Tutorial: https://github.com/langchain-ai/langgraph/tree/main/examples/reflexion
- Official Reflexion Repo: https://github.com/noahshinn/reflexion

---

**文档版本：** v1.0
**更新日期：** 2025-01-31
**作者：** Claude Code Agent
