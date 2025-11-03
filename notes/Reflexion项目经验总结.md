# Reflexion 项目经验总结

## 项目概述

**Reflexion: Language Agents with Verbal Reinforcement Learning**

- 论文发表：NeurIPS 2023
- 作者：Noah Shinn 等（Princeton University）
- 论文链接：https://arxiv.org/abs/2303.11366
- 代码仓库：https://github.com/noahshinn/reflexion

## 1. 核心思想

### 1.1 语言式强化学习
Reflexion 提出了一种全新的强化学习范式：**不通过权重更新学习，而是通过语言反思学习**。

核心理念：
- **语言反馈（Verbal Feedback）**：将环境反馈转化为文本形式的反思
- **情节记忆（Episodic Memory）**：将反思存储在文本缓冲区中
- **迭代改进（Iterative Improvement）**：在后续尝试中参考历史反思做出更好决策

### 1.2 与传统 RL 的区别

| 传统强化学习 | Reflexion |
|------------|-----------|
| 更新模型权重 | 维护文本记忆 |
| 需要大量训练样本 | 少样本即可学习 |
| 训练成本高 | 无需训练/微调 |
| 黑盒优化 | 可解释的语言反思 |

### 1.3 适用场景
Reflexion 在三大任务类型上验证有效：
1. **推理任务（Reasoning）**：HotPotQA 问答
2. **决策任务（Decision-Making）**：AlfWorld 交互式环境
3. **编程任务（Programming）**：HumanEval 代码生成

## 2. 反思机制设计

### 2.1 反思生成流程

```python
# 核心流程（参考 agents.py）
def reflect(self, strategy: ReflexionStrategy) -> None:
    """
    根据策略生成反思
    """
    if strategy == ReflexionStrategy.LAST_ATTEMPT:
        # 策略1：直接使用上次尝试的完整轨迹
        self.reflections = [self.scratchpad]
        self.reflections_str = format_last_attempt(self.question, self.reflections[0])

    elif strategy == ReflexionStrategy.REFLEXION:
        # 策略2：生成高层次的自我反思
        self.reflections += [self.prompt_reflection()]
        self.reflections_str = format_reflections(self.reflections)

    elif strategy == ReflexionStrategy.LAST_ATTEMPT_AND_REFLEXION:
        # 策略3：同时使用轨迹和反思
        self.reflections_str = format_last_attempt(self.question, self.scratchpad)
        self.reflections += [self.prompt_reflection()]
        self.reflections_str += format_reflections(self.reflections,
                                                   header=REFLECTION_AFTER_LAST_TRIAL_HEADER)
```

### 2.2 三种反思策略

#### 策略 1：LAST_ATTEMPT（完整轨迹）
- **内容**：将上次失败的完整推理轨迹（Thought-Action-Observation）作为上下文
- **优点**：保留所有细节，LLM 可以自己分析问题
- **缺点**：占用大量 token，可能包含噪声信息

#### 策略 2：REFLEXION（纯反思）
- **内容**：LLM 生成简洁的高层次反思（2-3 句话）
- **优点**：压缩信息，聚焦核心问题，token 效率高
- **缺点**：可能丢失细节信息

#### 策略 3：LAST_ATTEMPT_AND_REFLEXION（混合）
- **内容**：同时提供轨迹和反思
- **优点**：结合两者优势，细节+总结
- **缺点**：消耗更多 token

### 2.3 反思 Prompt 设计

**反思生成 Prompt**（来自 prompts.py）：

```
You are an advanced reasoning agent that can improve based on self reflection.
You will be given a previous reasoning trial in which you were given access to
an Docstore API environment and a question to answer. You were unsuccessful in
answering the question either because you guessed the wrong answer with
Finish[<answer>], or you used up your set number of reasoning steps.

In a few sentences, Diagnose a possible reason for failure and devise a new,
concise, high level plan that aims to mitigate the same failure.
Use complete sentences.

Previous trial:
Question: {question}
{scratchpad}

Reflection:
```

**关键设计要点**：
1. **明确角色定位**：advanced reasoning agent，强调自我改进能力
2. **清晰的任务指令**：诊断失败原因 + 制定新计划
3. **输出格式约束**：few sentences, concise, high level
4. **具体场景示例**：通过 few-shot 示例展示期望的反思质量

### 2.4 反思示例分析

**示例 1：AlfWorld 环境任务**

```
任务：heat some mug and put it in coffeemachine

失败行为：
> examine stoveburner 1
> examine stoveburner 1
> examine stoveburner 1
> examine stoveburner 1
（陷入重复循环）

生成的反思：
"I was stuck in a loop in which I continually examined stoveburner 1
instead of heating mug 1 with stoveburner 1. I should have taken mug 1
from countertop 1, then heated it with stoveburner 1, then put it in
coffeemachine 1. It did not help to execute two identical actions in a row.
I will try to execute a different action if I am stuck in a loop again."
```

**反思的三个层次**：
1. **问题诊断**：识别陷入重复循环
2. **根因分析**：应该执行 heat 而不是 examine
3. **改进计划**：避免连续相同动作，检测循环

**示例 2：编程任务（Python）**

```python
# 上次实现（错误）
def add(a: int, b: int) -> int:
    return a - b

# 测试失败
assert add(1, 2) == 3  # output: -1

# 生成的反思
"The implementation failed the test cases where the input integers are
1 and 2. The issue arises because the code does not add the two integers
together, but instead subtracts the second integer from the first.
To fix this issue, we should change the operator from `-` to `+` in the
return statement."
```

**反思质量特征**：
- 具体指出错误位置（operator from `-` to `+`）
- 清晰的因果关系（because... To fix...）
- 可操作的改进建议（change the operator）

## 3. 经验积累与复用策略

### 3.1 记忆系统架构

Reflexion 使用 **情节记忆（Episodic Memory）** 设计：

```python
class ReactReflectAgent(ReactAgent):
    def __init__(self, ...):
        super().__init__(...)
        self.reflections: List[str] = []  # 反思列表
        self.reflections_str: str = ''    # 格式化后的反思文本
```

**核心特点**：
1. **纯文本存储**：无需向量化，直接拼接到 Prompt
2. **列表结构**：按时间顺序存储多次反思
3. **滑动窗口**：保留最近 3 次反思（避免 context 溢出）

### 3.2 记忆复用机制

**在 Prompt 中注入反思**（来自 agents.py）：

```python
def _build_agent_prompt(self) -> str:
    return self.agent_prompt.format(
        examples=self.react_examples,       # few-shot 示例
        reflections=self.reflections_str,   # 历史反思！
        question=self.question,
        scratchpad=self.scratchpad          # 当前推理轨迹
    )
```

**Prompt 结构**：
```
Solve a question answering task with interleaving Thought, Action, Observation...
Here are some examples:
{few-shot examples}

{reflections}  ← 插入历史反思！

Question: {question}
{scratchpad}
```

### 3.3 滑动窗口策略

**AlfWorld 环境实现**（generate_reflections.py）：

```python
def update_memory(trial_log_path: str, env_configs: List[Dict[str, Any]]):
    for i, env in enumerate(env_configs):
        if not env['is_success'] and not env['skip']:
            # 保留最近 3 次反思
            if len(env['memory']) > 3:
                memory: List[str] = env['memory'][-3:]
            else:
                memory: List[str] = env['memory']

            # 生成新反思
            reflection_query = _generate_reflection_query(env_logs[i], memory)
            reflection = get_completion(reflection_query)
            env_configs[i]['memory'] += [reflection]
```

**设计考量**：
- **为什么是 3？**：平衡信息量和 token 消耗
- **为什么滑动窗口？**：防止 context 溢出，聚焦近期经验
- **为什么不是向量检索？**：任务特定性强，顺序执行，无需复杂检索

### 3.4 跨 Trial 持久化

**AlfWorld 的环境配置持久化**（main.py）：

```python
# 每次 trial 后保存环境配置（包含记忆）
trial_env_configs_log_path = os.path.join(run_name,
                                         f'env_results_trial_{trial_idx}.json')
with open(trial_env_configs_log_path, 'w') as wf:
    json.dump(env_configs, wf, indent=4)

# 恢复运行时加载历史记忆
if args.is_resume:
    env_config_path = os.path.join(args.resume_dir,
                                   f'env_results_trial_{start_trial_num - 1}.json')
    with open(env_config_path, 'r') as rf:
        env_configs = json.load(rf)
```

**环境配置结构**：
```json
{
  "name": "env_0",
  "memory": [
    "Trial 0: I was stuck in a loop...",
    "Trial 1: I should have checked...",
    "Trial 2: The key issue was..."
  ],
  "is_success": false,
  "skip": false
}
```

## 4. Trial-and-Error 机制

### 4.1 多轮尝试框架

**编程任务的迭代循环**（reflexion.py）：

```python
def run_reflexion(dataset, model_name, max_iters, pass_at_k, ...):
    for i, item in enumerate_resume(dataset, log_path):
        cur_pass = 0
        is_solved = False
        reflections = []
        implementations = []
        test_feedback = []

        while cur_pass < pass_at_k and not is_solved:
            # 第一次尝试
            cur_func_impl = gen.func_impl(item["prompt"], model, "simple")
            implementations.append(cur_func_impl)
            is_passing, feedback, _ = exe.execute(cur_func_impl, tests_i)
            test_feedback.append(feedback)

            if is_passing:
                is_solved = exe.evaluate(item["entry_point"], cur_func_impl,
                                        item["test"], timeout=10)
                break

            # 反思-改进循环
            cur_iter = 1
            cur_feedback = feedback
            while cur_iter < max_iters:
                # 生成反思
                reflection = gen.self_reflection(cur_func_impl, cur_feedback, model)
                reflections += [reflection]

                # 基于反思改进
                cur_func_impl = gen.func_impl(
                    func_sig=item["prompt"],
                    model=model,
                    strategy="reflexion",
                    prev_func_impl=cur_func_impl,
                    feedback=cur_feedback,
                    self_reflection=reflection
                )
                implementations.append(cur_func_impl)

                # 测试新实现
                is_passing, cur_feedback, _ = exe.execute(cur_func_impl, tests_i)
                test_feedback.append(cur_feedback)

                if is_passing:
                    is_solved = exe.evaluate(...)
                    break

                cur_iter += 1
            cur_pass += 1
```

### 4.2 两层循环设计

**外层循环（pass_at_k）**：
- 目标：从头开始多次尝试同一任务
- 类似 pass@k 评估：k 次独立尝试，有一次成功即可
- 每次都重置反思记忆

**内层循环（max_iters）**：
- 目标：在同一次尝试中反思-改进
- 累积反思：每次迭代都参考之前所有反思
- 限制最大迭代次数防止无限循环

### 4.3 早停机制

**成功即停止**：
```python
if is_passing:
    is_passing = exe.evaluate(...)  # 完整测试
    if is_passing:
        item["solution"] = cur_func_impl
        is_solved = True
        num_success += 1
    break  # 立即退出内层循环
```

**超过最大迭代**：
```python
if is_passing or cur_iter == max_iters - 1:
    # 最后一次尝试，无论是否通过都要完整测试
    is_passing = exe.evaluate(...)
    break
```

### 4.4 反馈类型

Reflexion 支持多种反馈信号：

1. **二元反馈（Binary）**：
   ```python
   is_correct = EM(self.answer, self.key)  # Exact Match
   if is_correct:
       observation = 'Answer is CORRECT'
   else:
       observation = 'Answer is INCORRECT'
   ```

2. **执行反馈（Execution）**：
   ```python
   # 编程任务
   is_passing, feedback, _ = executor.execute(code, tests)
   # feedback: "Tested passed: ... \nTests failed: assert add(1,2)==3 # output: -1"
   ```

3. **环境反馈（Environment）**：
   ```python
   # AlfWorld 交互
   observation, reward, done, info = env.step([action])
   # observation: "You pick up the mug 1 from the countertop 1."
   ```

4. **自由文本反馈（Free-form Language）**：
   - 可以是 LLM 生成的评价
   - 可以是人类评审意见
   - Reflexion 框架对反馈类型无限制

## 5. 记忆系统设计

### 5.1 工作记忆（Working Memory）

**Scratchpad 机制**：
```python
class ReactAgent:
    def __init__(self, ...):
        self.scratchpad: str = ''  # 当前推理轨迹

    def step(self):
        self.scratchpad += f'\nThought {self.step_n}:'
        self.scratchpad += ' ' + self.prompt_agent()

        self.scratchpad += f'\nAction {self.step_n}:'
        action = self.prompt_agent()
        self.scratchpad += ' ' + action

        self.scratchpad += f'\nObservation {self.step_n}: '
        # ...执行动作获取观察...
```

**特点**：
- **实时追加**：每次 Thought-Action-Observation 都追加到 scratchpad
- **完整轨迹**：保留从开始到当前的所有推理步骤
- **上下文窗口**：直接喂给 LLM，实现 in-context learning
- **重置机制**：每次新尝试前清空 `self.scratchpad = ''`

### 5.2 长期记忆（Long-term Memory）

**反思列表**：
```python
self.reflections: List[str] = []  # 跨 trial 的经验积累
```

**存储内容**：
- 不是完整轨迹（太长）
- 是高层次的反思总结（2-3 句话）
- 聚焦失败原因和改进策略

**检索策略**：
- **无需复杂检索**：顺序任务，直接使用最近 k 次
- **滑动窗口**：最近 3 次反思最相关
- **格式化注入**：拼接成文本，插入 Prompt 的特定位置

### 5.3 Scratchpad 截断策略

**问题**：推理轨迹可能很长，超出 context 限制

**解决方案**（来自 agents.py）：

```python
def truncate_scratchpad(scratchpad: str, n_tokens: int = 1600,
                       tokenizer=gpt2_enc) -> str:
    """智能截断 scratchpad，保留关键信息"""
    lines = scratchpad.split('\n')
    observations = filter(lambda x: x.startswith('Observation'), lines)
    observations_by_tokens = sorted(observations,
                                   key=lambda x: len(tokenizer.encode(x)))

    while len(gpt2_enc.encode('\n'.join(lines))) > n_tokens:
        # 删除最长的 observation（通常是维基百科摘录）
        largest_observation = observations_by_tokens.pop(-1)
        ind = lines.index(largest_observation)
        lines[ind] = largest_observation.split(':')[0] + ': [truncated wikipedia excerpt]'

    return '\n'.join(lines)
```

**设计亮点**：
1. **智能选择**：优先删除最长的 Observation（信息密度低）
2. **保留结构**：保留 "Observation X: [truncated...]"，不破坏格式
3. **保留 Thought/Action**：决策推理过程比观察结果更重要

### 5.4 记忆在不同任务中的体现

| 任务类型 | 工作记忆 | 长期记忆 | 记忆格式 |
|---------|---------|---------|---------|
| **推理（HotPotQA）** | 当前 Question 的 Thought-Action-Observation | 同一 Question 的历史反思（最多 3 次） | 文本列表 |
| **决策（AlfWorld）** | 当前 Episode 的完整交互轨迹 | 同一任务类型的历史反思（跨 Episode） | JSON 持久化 |
| **编程（HumanEval）** | 当前代码实现 + 测试反馈 | 同一题目的历史反思（跨尝试） | 文本列表 + 代码块 |

## 6. 关键亮点与最佳实践

### 6.1 架构亮点

#### 1. 零训练学习（Zero-shot to Few-shot）
- **无需微调**：直接使用预训练 LLM（GPT-4/GPT-3.5）
- **低成本**：避免昂贵的强化学习训练
- **快速部署**：改 Prompt 即可上线

#### 2. 可解释性（Interpretability）
- **反思可读**：每次失败原因一目了然
- **调试友好**：可以人工检查反思质量
- **可人工干预**：支持 human edit 注入知识

#### 3. 即插即用（Plug-and-Play）
- **框架无关**：可用于 ReAct、CoT、任何 Agent 架构
- **任务无关**：推理、决策、编程都适用
- **模型无关**：支持任何 LLM（GPT-4, Claude, 开源模型）

### 6.2 Prompt 工程最佳实践

#### 1. 清晰的角色定位
```
You are an advanced reasoning agent that can improve based on self reflection.
```
- **明确能力**：advanced reasoning, self reflection
- **暗示迭代**：improve based on reflection

#### 2. 结构化的 Few-shot
```
Example 1:
[previous impl]:
<code>
[unit test results]:
<feedback>
[reflection on previous impl]:
<reflection>
[improved impl]:
<code>
```
- **标签清晰**：[previous impl], [reflection], [improved impl]
- **完整闭环**：展示从错误到反思到改进的完整流程

#### 3. 约束输出格式
```
In a few sentences, Diagnose a possible reason for failure and devise a new,
concise, high level plan...
```
- **数量约束**：a few sentences（防止冗长）
- **质量要求**：concise, high level（聚焦核心）
- **任务分解**：Diagnose + devise（两步思考）

### 6.3 性能提升效果

**HumanEval 编程基准**：
- GPT-4 Baseline（无反思）：80% pass@1
- GPT-4 + Reflexion：**91% pass@1**
- 提升：**+11%**（相对提升 13.75%）

**AlfWorld 决策任务**：
- Trial 1（无记忆）：~50% 成功率
- Trial 6（累积反思）：**>80% 成功率**
- 提升：**+30%**（通过 6 次迭代学习）

**HotPotQA 推理任务**：
- ReAct Baseline：51% 准确率
- ReAct + Reflexion：**57% 准确率**
- 提升：**+6%**

### 6.4 Token 效率优化

**反思 vs. 完整轨迹**：

| 方法 | 平均 Token 消耗 | 信息保留 |
|------|---------------|---------|
| 完整轨迹（LAST_ATTEMPT） | ~800 tokens | 100% |
| 纯反思（REFLEXION） | ~50 tokens | 60% |
| 混合（LAST_ATTEMPT_AND_REFLEXION） | ~850 tokens | 90% |

**推荐策略**：
- **Token 充足**：使用混合策略（效果最好）
- **Token 受限**：使用纯反思（效率高）
- **复杂任务**：使用完整轨迹（细节重要）

### 6.5 循环检测机制

**AlfWorld 的重复动作检测**（env_history.py）：

```python
class EnvironmentHistory:
    def __init__(self, ...):
        self._last_action: str = ''
        self._is_exhausted: bool = False

    def add(self, label: str, value: str):
        if label == 'action':
            if value == self._last_action:
                self._is_exhausted = True  # 检测到重复！
            else:
                self._last_action = value

    def check_is_exhausted(self) -> bool:
        return self._is_exhausted
```

**反思对循环的处理**：
```
Reflection: "I was stuck in a loop in which I continually examined
stoveburner 1. It did not help to execute two identical actions in a row.
I will try to execute a different action if I am stuck in a loop again."
```

**效果**：Agent 在下次尝试中会主动避免重复动作

### 6.6 适用性边界

**适合 Reflexion 的场景**：
- ✅ 有明确的成功/失败反馈
- ✅ 允许多次尝试
- ✅ 失败模式可语言化描述
- ✅ 历史经验有参考价值

**不适合的场景**：
- ❌ 一次性任务（无法重试）
- ❌ 反馈模糊（无法判断对错）
- ❌ 随机性极强（历史经验无价值）
- ❌ 超长 horizon（反思难以覆盖）

## 7. 与我们项目的结合点

### 7.1 直接借鉴的设计

#### 1. 反思生成机制
```python
# 在 Worker Agent 中集成
class WorkerAgent:
    def __init__(self):
        self.reflections: List[str] = []  # 历史反思
        self.current_scratchpad: str = ''  # 当前轨迹

    async def generate_reflection(self, task_result):
        """任务失败后生成反思"""
        reflection_prompt = f"""
        You are an Android automation agent. Analyze why the task failed.

        Task: {task_result.task}
        Actions taken: {self.current_scratchpad}
        Final result: {task_result.error}

        Diagnose the failure and devise a new plan.
        Reflection:
        """
        reflection = await self.llm.generate(reflection_prompt)
        self.reflections.append(reflection)

        # 滑动窗口：保留最近 3 次
        if len(self.reflections) > 3:
            self.reflections = self.reflections[-3:]
```

#### 2. 记忆注入策略
```python
# 在决策 Prompt 中注入反思
def build_decision_prompt(self, screen_info, task):
    prompt = f"""
    Task: {task}
    Current screen: {screen_info}

    {self._format_reflections()}  # 注入历史反思

    What action should you take?
    """
    return prompt

def _format_reflections(self):
    if not self.reflections:
        return ""
    return "Your past reflections on similar tasks:\n" + \
           "\n".join(f"- {r}" for r in self.reflections)
```

#### 3. 循环检测
```python
class ActionExecutor:
    def __init__(self):
        self.last_action: Optional[Action] = None
        self.repeat_count: int = 0

    async def execute(self, action: Action):
        # 检测重复动作
        if action == self.last_action:
            self.repeat_count += 1
            if self.repeat_count >= 3:
                raise LoopDetectedException(
                    f"Repeated action {action} 3 times, likely stuck in loop"
                )
        else:
            self.repeat_count = 0

        self.last_action = action
        return await self._do_execute(action)
```

### 7.2 需要适配的部分

#### 1. 反馈信号设计
Reflexion 依赖明确的成功/失败反馈，我们需要设计：

```python
class TaskFeedback:
    """任务执行反馈"""
    success: bool
    error_type: Optional[str]  # "element_not_found", "timeout", "wrong_app"
    screen_before: Image
    screen_after: Image
    expected_state: str
    actual_state: str

    def to_text_feedback(self) -> str:
        """转换为适合反思的文本描述"""
        if self.success:
            return "Task completed successfully"
        return f"""
        Task failed: {self.error_type}
        Expected: {self.expected_state}
        Actual: {self.actual_state}
        """
```

#### 2. 多模态反思
Reflexion 原论文只处理文本，我们需要扩展到视觉：

```python
async def generate_multimodal_reflection(self,
                                        task_result: TaskFeedback):
    """基于屏幕截图和文本反馈生成反思"""
    reflection_prompt = f"""
    Task: {task_result.task}

    Screen before action:
    <image: {task_result.screen_before}>

    Screen after action:
    <image: {task_result.screen_after}>

    Error: {task_result.to_text_feedback()}

    Why did this fail? What should be done differently?
    """
    reflection = await self.vl_model.generate(reflection_prompt)
    return reflection
```

#### 3. 长期记忆持久化
```python
class ExperienceStore:
    """长期记忆管理"""

    async def save_reflection(self,
                             task_type: str,
                             reflection: str,
                             context: dict):
        """保存反思到向量数据库"""
        embedding = await self.embed_model.embed(reflection)
        await self.vector_store.add(
            text=reflection,
            embedding=embedding,
            metadata={
                "task_type": task_type,
                "timestamp": time.time(),
                "context": context
            }
        )

    async def retrieve_relevant_reflections(self,
                                           current_task: str,
                                           k: int = 3):
        """检索相关的历史反思"""
        query_embedding = await self.embed_model.embed(current_task)
        results = await self.vector_store.search(
            query_embedding,
            k=k,
            filter={"task_type": self._classify_task(current_task)}
        )
        return [r.text for r in results]
```

### 7.3 创新扩展点

#### 1. 分层反思
```python
class LayeredReflection:
    """分层反思：不同抽象层次"""

    async def generate_tactical_reflection(self):
        """战术层反思：具体操作失败原因"""
        # "I tapped on the wrong button because OCR misread '设置' as '设定'"
        pass

    async def generate_strategic_reflection(self):
        """战略层反思：任务规划问题"""
        # "I should have checked if app is already open before launching"
        pass

    async def generate_metacognitive_reflection(self):
        """元认知反思：决策模式问题"""
        # "I tend to rush into actions without verifying element visibility"
        pass
```

#### 2. 对比式反思
```python
async def generate_contrastive_reflection(self,
                                         failed_attempt,
                                         successful_attempt):
    """对比成功和失败案例生成反思"""
    prompt = f"""
    Failed attempt:
    {failed_attempt.trajectory}
    Result: FAIL

    Successful attempt:
    {successful_attempt.trajectory}
    Result: SUCCESS

    What was the key difference?
    """
    return await self.llm.generate(prompt)
```

#### 3. 主动反思触发
```python
class ProactiveReflection:
    """主动反思：不等失败，预先思考"""

    async def before_critical_action(self, action: Action):
        """关键操作前的预先反思"""
        prompt = f"""
        You are about to execute: {action}

        Past reflections on similar actions:
        {self._get_relevant_reflections(action)}

        What could go wrong? How to prevent it?
        """
        preventive_reflection = await self.llm.generate(prompt)
        return preventive_reflection
```

## 8. 实现清单

### 优先级 P0（核心功能）
- [ ] `WorkerAgent.generate_reflection()` - 反思生成
- [ ] `WorkerAgent._format_reflections()` - 反思格式化
- [ ] `WorkerAgent.reflections: List[str]` - 反思存储
- [ ] `ActionExecutor.detect_loop()` - 循环检测
- [ ] `TaskFeedback` 数据模型 - 结构化反馈

### 优先级 P1（增强功能）
- [ ] `ExperienceStore.save_reflection()` - 持久化
- [ ] `ExperienceStore.retrieve_relevant_reflections()` - 检索
- [ ] 多模态反思（基于屏幕截图）
- [ ] 反思质量评估（自动/人工）

### 优先级 P2（高级功能）
- [ ] 分层反思（tactical/strategic/metacognitive）
- [ ] 对比式反思（成功 vs. 失败）
- [ ] 主动反思（预防性）
- [ ] 反思压缩（长期记忆总结）

## 9. 参考资源

### 论文与博客
- 论文：https://arxiv.org/abs/2303.11366
- 博客：https://nanothoughts.substack.com/p/reflecting-on-reflexion
- 代码：https://github.com/noahshinn/reflexion

### 相关工作
- ReAct：https://arxiv.org/abs/2210.03629
- Chain of Thought：https://arxiv.org/abs/2201.11903
- Self-Consistency：https://arxiv.org/abs/2203.11171

### 扩展实现
- Appl 版本：https://github.com/appl-team/reppl/tree/main/reflexion
- LeetcodeHardGym：https://github.com/GammaTauAI/leetcode-hard-gym

---

**总结**：Reflexion 的核心价值在于将强化学习从参数空间转移到语言空间，通过简洁的文本反思实现高效的经验学习。这对我们的 Android 自动化 Agent 极具参考价值，可以显著提升试错能力和长期学习能力。
