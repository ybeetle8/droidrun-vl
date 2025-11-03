# AgenticRAG-Survey 经验总结

> 基于 GitHub 项目 https://github.com/asinghcsu/AgenticRAG-Survey 的深度调研
>
> 论文: Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG (arXiv:2501.09136)

## 1. Agentic RAG 核心概念

### 1.1 定义与核心价值
Agentic RAG 通过将**自主 AI 代理**嵌入 RAG 管道，突破传统 RAG 的局限性。核心特征：

- **动态检索管理**：不再是一次性的静态检索，而是在任务执行过程中持续评估和调整检索策略
- **迭代精炼**：持续优化上下文理解，而非一锤定音
- **自适应工作流**：根据任务复杂度动态调整执行策略

### 1.2 与传统 RAG 的核心区别

| 维度 | 传统 RAG | Agentic RAG |
|------|---------|-------------|
| **检索时机** | 一次性前置检索 | 运行时动态多次检索 |
| **决策模式** | 静态规则驱动 | 自主推理驱动 |
| **工作流** | 线性管道（检索→生成） | 循环迭代（观察→推理→检索→评估→生成） |
| **错误处理** | 无自我纠错机制 | 自我反思与纠正 |
| **任务分解** | 不支持 | 自动分解为子目标 |
| **工具使用** | 固定工具链 | 自主选择和调用工具 |

### 1.3 四大 Agentic 设计模式

1. **Reflection（反思）**
   - Agent 评估和改进自己的输出
   - 使用外部验证工具
   - 实现持续性能提升

2. **Planning（规划）**
   - 将复杂任务分解为子目标
   - 创建结构化工作流
   - 支持多步骤任务编排

3. **Tool Use（工具使用）**
   - 动态集成外部资源和 API
   - 自主选择合适的工具
   - 扩展能力边界（搜索、计算、数据库等）

4. **Multi-Agent Collaboration（多智能体协作）**
   - 专业化分工（检索、推理、代码执行等）
   - 并行处理复杂工作流
   - 中间结果共享与协调

## 2. 检索策略

### 2.1 Agentic RAG 检索策略分类

#### 2.1.1 Adaptive RAG（自适应检索）
**核心思想**：根据查询复杂度动态选择检索策略

**查询分类**：
```
简单查询 → 跳过检索，直接使用模型知识
中等复杂 → 单跳检索（半结构化知识库）
复杂查询 → 多跳检索 + 外部搜索 + 工具调用
```

**实现机制**：
- 轻量级查询复杂度分类器（小模型）
- 查询路由器（Router）：根据复杂度分配资源
- 自适应预算分配：避免简单查询浪费资源

**关键引用**：
> "Adaptive RAG analyzes how complex the query is, which helps to avoid wasting resources on simple questions while ensuring the complex ones are accurately answered."

#### 2.1.2 Corrective RAG (CRAG)（纠正性检索）
**核心思想**：自我评估检索质量并触发纠正动作

**三大纠正动作**：
1. **Correct（纠正）**：检索可靠时
   - 使用"分解-重组"技术精炼文档
   - 提取最相关的片段

2. **Incorrect（错误）**：检索不可靠时
   - 丢弃错误检索
   - 触发 Web 搜索获取更可靠信息

3. **Ambiguous（模糊）**：检索置信度不确定时
   - 结合精炼检索 + Web 搜索结果

**实现机制**：
- 轻量级检索评估器（Retrieval Evaluator）
- 置信度打分系统
- 多源信息融合策略

**性能优势**：
- 主动发现并修正检索错误
- 防止错误信息影响生成质量
- 在短文本和长文本生成任务中均表现优异

#### 2.1.3 Hierarchical RAG（层次化检索）
**核心思想**：分层 Agent 结构，战略监督与战术执行分离

**架构**：
```
Supervisor Agent（监督者）
    ↓
Specialized Agents（专业 Agent）
    ├─ RAG Agent（检索）
    ├─ Code & Reasoning Agent（代码与推理）
    └─ Tool Agent（工具调用）
```

**应用场景**：长文档处理（法律、金融文档分析）

#### 2.1.4 Graph-Based RAG（图检索）
**核心思想**：将向量数据库与知识图谱结合

**架构模式**：
- 向量数据库：语义相似度检索
- 知识图谱：结构化关系推理
- 时间戳事件日志：时序记忆
- 有限状态机 / 强化学习：程序性记忆管理

### 2.2 何时检索（When to Retrieve）

**检索触发条件**：
1. **Prompt 缺乏完整初始上下文**
2. **任务需要中间决策**（intermediate decisions）
3. **知识库大型或持续变化**
4. **需要事实验证**
5. **检测到知识差距**（memory reasoning loop）

**不检索的情况**：
- 简单查询且模型内部知识足够
- 已有高置信度的缓存答案

### 2.3 如何检索（How to Retrieve）

#### 2.3.1 混合检索策略（Hybrid Retrieval）
**最佳实践**：
```python
# 混合检索 = 稠密检索 + 稀疏检索 + 重排序
retrieval_pipeline = dense_search + sparse_search + reranking
```

**工具选择**：
- **向量数据库**：FAISS, Pinecone, LanceDB
- **重排序器**：ColBERT, Cross-Encoder
- **搜索 API**：Google Search, Bing, DuckDuckGo

#### 2.3.2 交错检索与推理（Interleaved Retrieval & Reasoning）
**核心模式**：
```
观察 → 检索 → 推理 → 检索 → 推理 → ...（循环）
```

**实现方法**：
- Chain of Function Call（函数调用链）
- System 1（直觉）+ System 2（逻辑）结合
- 动态工具选择与执行顺序优化

#### 2.3.3 多模态检索（Multimodal Retrieval）
详见第 4 节

### 2.4 检索什么（What to Retrieve）

**检索目标**：
1. **语义相关文档**：基于查询的向量相似度
2. **结构化知识**：知识图谱的实体和关系
3. **程序性知识**：代码片段、API 文档
4. **多模态内容**：图像、表格、图表
5. **时间序列信息**：历史事件、状态变化

### 2.5 检索优化关键实践

**1. 查询重构（Query Reformulation）**
- 任务执行中动态重构查询
- 基于反馈优化检索关键词

**2. 多策略验证**
- 使用多种搜索策略交叉验证
- 调用额外工具验证或扩展上下文

**3. 短循环设计**
- 使用短 Agent 循环（Short Agent Loops）
- 快速迭代：检索 → 验证 → 下一步

**4. 错误处理**
- Loud Failures（显性错误）：立即检测并恢复
- Silent Failures（静默错误）：通过反思机制发现

## 3. 记忆管理

### 3.1 记忆架构

#### 3.1.1 双层记忆系统
```
┌─────────────────────────────────────┐
│   Working Memory (工作记忆)         │
│   - 7±2 容量限制                    │
│   - 即时上下文跟踪                  │
│   - 时间衰减                        │
└─────────────────────────────────────┘
              ↕
┌─────────────────────────────────────┐
│   Long-Term Memory (长期记忆)       │
│   - 向量数据库存储                  │
│   - 经验积累                        │
│   - 语义检索                        │
└─────────────────────────────────────┘
```

#### 3.1.2 工作记忆（Working Memory）设计

**本项目现有设计（来自 CLAUDE.md）**：
- 容量：7±2
- 结构：deque（双端队列）
- 特性：循环检测、时间衰减

**Agentic RAG 增强建议**：
```python
class WorkingMemory:
    # 核心属性
    capacity: int = 7  # Miller's Law
    items: deque  # 当前上下文

    # Agentic 增强
    attention_weights: dict  # 注意力权重
    decay_factor: float = 0.9  # 时间衰减系数
    loop_detector: LoopDetector  # 循环检测

    # 新增：检索触发器
    knowledge_gap_detector: Callable  # 检测知识缺口
    retrieval_threshold: float = 0.7  # 触发检索的置信度阈值
```

**工作记忆 → 检索的触发逻辑**：
1. 工作记忆容量接近满载 → 压缩或归档到长期记忆
2. 检测到知识缺口 → 从长期记忆检索
3. 置信度低于阈值 → 触发外部检索

#### 3.1.3 长期记忆（Long-Term Memory）设计

**向量存储最佳实践**：

**1. 存储内容**：
```python
class ExperienceMemory:
    # 任务经验
    task_experiences: List[Experience]

    # 空间记忆（页面导航图）
    spatial_memory: SpatialMemory

    # 模式识别
    ui_patterns: List[UIPattern]
    error_patterns: List[ErrorPattern]
    recovery_strategies: List[RecoveryStrategy]
```

**2. 向量化策略**：
- **文本嵌入**：任务描述、状态描述
- **屏幕嵌入**：UI 截图的视觉特征（VL 模型）
- **动作序列嵌入**：操作轨迹的向量表示
- **多模态融合嵌入**：文本 + 图像联合嵌入

**3. 检索策略**：
```python
# 混合检索
def retrieve_experience(query, top_k=5):
    # 1. 语义检索（向量相似度）
    semantic_results = vector_db.search(query_embedding, k=top_k)

    # 2. 元数据过滤（任务类型、应用、成功率）
    filtered_results = metadata_filter(semantic_results)

    # 3. 重排序（时间新近性、成功率、相似度综合）
    reranked_results = rerank(filtered_results)

    return reranked_results
```

### 3.2 记忆与检索的协同模式

**核心模式**：Memory-Reasoning Loop

```
┌──────────────────────────────────────────┐
│  观察屏幕（Perception）                   │
│  ↓                                        │
│  检查工作记忆（Working Memory Check）     │
│  ↓                                        │
│  知识充足？                                │
│  ├─ Yes → 决策（Decision）                │
│  └─ No → 检测知识差距                      │
│      ↓                                    │
│      检索长期记忆（Vector DB Search）      │
│      ↓                                    │
│      还不够？→ 外部检索（Web/Tools）       │
│      ↓                                    │
│      更新工作记忆 → 决策                   │
└──────────────────────────────────────────┘
```

### 3.3 向量数据库（LanceDB）集成最佳实践

**本项目已完成的基础**：
- 向量存储封装：`src/memory/vector_store.py`
- 数据路径：`data/experiences/vector_db/`

**Agentic RAG 增强建议**：

**1. 多模态索引**：
```python
# 同时索引文本和图像
class MultimodalVectorStore:
    text_index: VectorIndex  # 文本嵌入
    image_index: VectorIndex  # 图像嵌入（VL 模型）
    fusion_index: VectorIndex  # 联合嵌入
```

**2. 分层索引（Hierarchical Indexing）**：
```python
# RAPTOR 风格的分层索引
levels = {
    "atomic": atomic_experiences,  # 单个动作
    "task": task_sequences,        # 任务序列
    "strategy": high_level_plans   # 策略级别
}
```

**3. 元数据丰富化**：
```python
metadata = {
    "task_type": "login",
    "app_name": "WeChat",
    "success_rate": 0.95,
    "avg_steps": 5,
    "timestamp": "2025-01-15",
    "device_type": "Android",
    "error_count": 2
}
```

### 3.4 经验检索与复用

**首次探索 vs 后续直达**（本项目设计目标）：

```python
# 决策器检查经验库
def decide_action(current_state):
    # 1. 检索类似经验
    similar_experiences = retriever.search(
        query=current_state,
        filter={"task_type": current_task.type}
    )

    # 2. 高置信度经验 → 直接复用
    if similar_experiences[0].confidence > 0.9:
        return similar_experiences[0].action_sequence

    # 3. 中等置信度 → 参考 + 适应
    elif similar_experiences[0].confidence > 0.7:
        return adapt_experience(similar_experiences[0])

    # 4. 低置信度 → 探索新路径
    else:
        return explore_new_path()
```

## 4. 多模态 RAG

### 4.1 多模态 RAG 核心挑战
**本项目场景**：Android UI 理解（截图 + OCR + UI Tree + 自然语言任务）

**关键问题**：
- 大部分 RAG 系统仅支持文本
- 无法原生处理表格、图表、图像
- 跨模态检索困难

### 4.2 多模态融合策略

#### 4.2.1 Text Grounding（图像文本化）
**方法**：使用 VL 模型将图像转为详细文本描述

```python
# 本项目使用 Qwen3-VL
def image_to_text(screenshot):
    description = qwen3_vl.generate(
        image=screenshot,
        prompt="详细描述这个 Android 屏幕，包括所有 UI 元素、文本内容、布局结构"
    )
    return description
```

**优势**：
- 文本和图像描述存储在同一向量空间
- 简化检索逻辑

**劣势**：
- 信息损失（视觉细节）
- 描述生成成本高

#### 4.2.2 Multimodal Embedding（多模态嵌入）
**方法**：使用多模态嵌入模型（如 CLIP）将文本和图像映射到统一向量空间

```python
# CLIP 风格的联合嵌入
class MultimodalEmbedding:
    def encode_text(self, text):
        return text_encoder(text)

    def encode_image(self, image):
        return image_encoder(image)

    def search(self, query_text, image_db):
        query_emb = self.encode_text(query_text)
        # 跨模态检索：文本查询 → 图像结果
        similar_images = image_db.search(query_emb)
        return similar_images
```

**本项目应用**：
```python
# 屏幕记忆检索
def retrieve_similar_screens(current_screenshot):
    # 1. 图像编码
    screen_emb = multimodal_encoder.encode_image(current_screenshot)

    # 2. 向量搜索
    similar_screens = vector_db.search(screen_emb, k=5)

    # 3. 返回历史经验
    return [exp for exp in similar_screens if exp.success]
```

#### 4.2.3 Late Fusion（延迟融合）
**方法**：分别检索多模态内容，在生成阶段融合

**架构**：
```
文本查询 → 文本向量数据库 → 相关文本
图像查询 → 图像向量数据库 → 相关图像
    ↓
重排序（Reranker）
    ↓
发送给多模态 LLM（Qwen3-VL）
```

**本项目实现建议**：
```python
class MultimodalRetriever:
    def retrieve(self, query):
        # 1. 并发检索
        text_results = await text_db.search(query.text)
        image_results = await image_db.search(query.screenshot)
        ui_results = await ui_db.search(query.ui_tree)

        # 2. 多模态重排序
        fused_results = rerank(
            text_results + image_results + ui_results,
            query=query,
            model=qwen3_vl  # 使用 VL 模型评分
        )

        return fused_results
```

### 4.3 多模态记忆存储设计

**本项目优化方向**：

```python
# 当前：单一向量数据库
vector_db = LanceDB("data/experiences/vector_db/")

# 优化：多模态分层存储
class MultimodalMemoryStore:
    text_db: VectorDB  # 任务描述、状态文本
    screen_db: VectorDB  # 截图的视觉嵌入
    ui_tree_db: VectorDB  # UI 树结构嵌入
    fusion_db: VectorDB  # 联合嵌入（文本+图像）

    async def search(self, query):
        # 并发多库检索
        results = await asyncio.gather(
            self.text_db.search(query.text_emb),
            self.screen_db.search(query.image_emb),
            self.ui_tree_db.search(query.ui_emb)
        )
        return self.fuse(results)
```

### 4.4 多模态 Prompt 工程

**最佳实践**：
```python
# 检索增强的多模态 Prompt
prompt = f"""
# 当前任务
{task_description}

# 当前屏幕观察
{current_screenshot}  # 图像

# UI 元素检测
{ui_elements}  # OCR + UI Tree

# 历史经验（检索得到）
{retrieved_experiences}
- 类似屏幕：{similar_screenshot}  # 图像
- 成功操作：{successful_actions}

# 请决策下一步操作
"""
```

## 5. 工具增强

### 5.1 工具使用的 Agentic 模式

**核心原则**：Agent 自主选择和调用工具，而非预定义流程

#### 5.1.1 工具类型分类

**1. 检索工具**：
- 向量数据库（LanceDB）
- Web 搜索（Google, Bing）
- 知识图谱查询

**2. 计算工具**：
- 计算器
- 代码执行器（Python REPL）
- 数据分析工具

**3. 设备交互工具（本项目核心）**：
```python
# 已实现：src/device/android_controller.py
tools = [
    "tap",           # 点击
    "swipe",         # 滑动
    "input_text",    # 输入
    "press_key",     # 按键
    "screenshot",    # 截屏
    "get_ui_tree",   # UI 树
    "install_app",   # 安装 APK
    "start_app",     # 启动应用
]
```

**4. 验证工具**：
- 事实检查 API
- 计算验证器
- 逻辑一致性检查

### 5.2 工具调用决策

**何时调用工具**：

```python
# 决策器伪代码
def decide_tool_use(current_state, task):
    # 1. 检查是否需要外部信息
    if needs_external_info(current_state):
        tools = ["web_search", "vector_db"]

    # 2. 检查是否需要计算
    elif needs_computation(task):
        tools = ["calculator", "code_executor"]

    # 3. 检查是否需要设备操作
    elif needs_device_action(current_state):
        tools = select_device_tools(current_state)

    # 4. 自主选择工具
    selected_tool = llm.choose_tool(
        tools=tools,
        context=current_state,
        task=task
    )

    return execute_tool(selected_tool)
```

### 5.3 Function Calling 集成

**本项目 LLM（Qwen3-VL）Function Calling 模式**：

```python
# src/llm/client.py 增强
class LLMClient:
    def call_with_tools(self, prompt, tools):
        response = self.client.chat.completions.create(
            model=self.config.llm.model,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "tap_screen",
                        "description": "点击屏幕坐标",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"}
                            }
                        }
                    }
                },
                # ... 其他工具
            ]
        )

        # 解析 tool_calls
        if response.choices[0].message.tool_calls:
            return self.execute_tool_call(
                response.choices[0].message.tool_calls[0]
            )
```

### 5.4 工具执行链（Chain of Function Call）

**多步骤工具编排**：

```python
# Hierarchical Agent 中的 Supervisor 规划工具链
async def execute_task(task):
    # 1. 规划工具链
    tool_chain = planner.plan_tools(task)
    # 例如：["screenshot", "retrieve_experience", "tap", "screenshot", "verify"]

    # 2. 顺序执行
    results = []
    for tool in tool_chain:
        result = await execute_tool(tool, context=results)
        results.append(result)

        # 3. 错误检测 → 自适应调整
        if result.error:
            tool_chain = replanner.adjust_chain(tool_chain, error=result.error)

    return results
```

### 5.5 工具错误处理

**Loud vs Silent Failures**：

```python
class ToolExecutor:
    async def execute(self, tool, params):
        try:
            result = await tool.run(params)

            # 验证结果（Silent Failure 检测）
            if not self.validate(result):
                return self.retry_with_correction(tool, params)

            return result

        except Exception as e:  # Loud Failure
            # 记录错误模式
            self.memory.store_error_pattern(tool, params, e)

            # 查找恢复策略
            recovery = self.memory.retrieve_recovery_strategy(e)
            return await self.execute_recovery(recovery)
```

## 6. 关键亮点与最佳实践

### 6.1 核心创新点总结

#### 6.1.1 自适应检索（Adaptive Retrieval）
**创新**：根据查询复杂度动态分配检索资源

**本项目应用**：
```python
# 在 Worker Agent 决策时应用
class AdaptiveWorkerAgent:
    async def decide_action(self, state):
        # 1. 评估任务复杂度
        complexity = self.assess_complexity(state)

        # 2. 简单任务：直接决策（无检索）
        if complexity == "simple":
            return self.llm.generate(state)

        # 3. 中等任务：向量检索（长期记忆）
        elif complexity == "medium":
            experiences = await self.vector_db.search(state)
            return self.decide_with_memory(state, experiences)

        # 4. 复杂任务：多源检索 + 工具
        else:
            return await self.complex_reasoning(state)
```

#### 6.1.2 自我纠错（Self-Correction）
**创新**：检索后评估质量，自动触发纠正动作

**本项目应用**：
```python
# 在即时反馈控制器中集成
class FeedbackController:
    async def execute_with_correction(self, action):
        # 1. 执行动作
        result = await self.executor.execute(action)

        # 2. 0.5 秒后评估
        await asyncio.sleep(0.5)
        evaluation = await self.evaluate(result)

        # 3. 自我纠错
        if evaluation.confidence < 0.7:
            # 检索纠正策略
            correction = await self.retrieve_correction(evaluation)
            return await self.executor.execute(correction)

        return result
```

#### 6.1.3 交错检索与推理（Interleaved Retrieval-Reasoning）
**创新**：检索和推理不再串行，而是循环交替

**本项目应用**：
```python
# 在认知循环中实现
class CognitiveLoop:
    async def run(self):
        while not task_completed:
            # 1. 观察
            screen = await self.perceive()

            # 2. 推理（决定是否需要检索）
            decision = await self.reason(screen)

            # 3. 检索（如果需要）
            if decision.needs_retrieval:
                context = await self.retrieve(decision.query)
                # 4. 再次推理（整合检索结果）
                decision = await self.reason(screen, context)

            # 5. 执行
            await self.execute(decision.action)
```

### 6.2 架构设计最佳实践

#### 6.2.1 模块化设计
**原则**：每个 Agent 和组件职责单一、边界清晰

**本项目架构验证**：
```
✅ Master Agent（任务管理）- 单一职责
✅ Worker Agent（认知执行）- 单一职责
✅ 感知、决策、执行、记忆 - 模块分离
```

#### 6.2.2 异步并发优先
**原则**：并发感知和执行，减少等待时间

**Agentic RAG 应用**：
```python
# 并发检索多源信息
async def multi_source_retrieval(query):
    results = await asyncio.gather(
        vector_db.search(query),       # 向量数据库
        knowledge_graph.query(query),  # 知识图谱
        web_search.search(query)       # Web 搜索
    )
    return fuse_results(results)
```

#### 6.2.3 短循环快速迭代
**原则**：避免长串行流程，用短循环快速反馈

**对比**：
```python
# ❌ 传统 RAG：长流程
retrieve_all → generate_complete_answer

# ✅ Agentic RAG：短循环
while not done:
    retrieve_small_chunk → reason → act → observe → adjust
```

### 6.3 性能优化策略

#### 6.3.1 检索预算管理
**策略**：为不同复杂度查询分配不同检索预算

```python
budget = {
    "simple": 0,           # 无检索
    "medium": 1,           # 单次检索
    "complex": 3,          # 多次检索
    "very_complex": 5      # 深度检索 + Web
}
```

#### 6.3.2 缓存与复用
**策略**：缓存高频查询和高置信度结果

```python
# 结合工作记忆和 LRU 缓存
@lru_cache(maxsize=128)
def cached_retrieval(query_hash):
    return vector_db.search(query)
```

#### 6.3.3 分层索引加速
**策略**：RAPTOR 风格的分层索引，先粗后细

```python
# 第一层：快速过滤（strategy 级别）
candidates = strategy_index.search(query, k=10)

# 第二层：精细检索（task 级别）
refined = task_index.search_within(candidates, k=5)

# 第三层：原子级别（atomic 动作）
final = atomic_index.search_within(refined, k=3)
```

### 6.4 评估方法

#### 6.4.1 检索质量评估
**指标**：
- **Precision**: 检索到的相关文档比例
- **Recall**: 相关文档被检索到的比例
- **MRR (Mean Reciprocal Rank)**: 第一个相关结果的排名倒数

**基准数据集**：
- BEIR（17 个数据集，跨领域）
- MS MARCO（段落排序和问答）

#### 6.4.2 生成质量评估
**指标**：
- **Factual Accuracy**: 事实准确性
- **Contextual Relevance**: 上下文相关性
- **Hallucination Rate**: 幻觉率

#### 6.4.3 Agentic 能力评估
**指标**：
- **Self-Correction Rate**: 自我纠正成功率
- **Tool Use Accuracy**: 工具选择准确率
- **Planning Effectiveness**: 规划有效性
- **Multi-Agent Coordination**: 协作效率

**本项目特定指标**：
- **首次探索 vs 后续直达成功率**
- **异常恢复成功率**
- **平均任务完成步数**
- **并发感知响应时间**

### 6.5 本项目应用优先级

根据 droidrun-vl 的核心目标，以下是 AgenticRAG 经验的应用优先级：

**P0（立即应用）**：
1. **Adaptive Retrieval**：避免简单任务过度检索
2. **Self-Correction**：结合即时反馈机制
3. **Multimodal Embedding**：屏幕相似度检索

**P1（重要）**：
4. **Interleaved Retrieval-Reasoning**：优化认知循环
5. **Tool Execution Chain**：设备操作序列规划
6. **Memory-Reasoning Loop**：工作记忆与长期记忆协同

**P2（优化）**：
7. **Hierarchical Indexing**：RAPTOR 风格的经验分层
8. **Multi-Agent Collaboration**：Master-Worker 协作优化
9. **Graph-Based Memory**：空间记忆的图结构增强

## 7. 实施建议

### 7.1 快速集成路线图

**阶段一：基础增强（1-2 周）**
```
1. 在 vector_store.py 中添加多模态嵌入支持
2. 在 decision_maker.py 中集成自适应检索逻辑
3. 在 feedback_controller.py 中添加自我纠错机制
```

**阶段二：循环优化（2-3 周）**
```
4. 在 cognitive_loop.py 中实现交错检索-推理
5. 优化 working_memory.py 的知识缺口检测
6. 增强 retriever.py 的混合检索策略
```

**阶段三：高级特性（3-4 周）**
```
7. 实现分层索引（RAPTOR）
8. 添加 Chain of Function Call 支持
9. 构建多模态融合检索器
```

### 7.2 关键代码模板

#### 模板 1：自适应检索决策器
```python
# src/decision/adaptive_retriever.py
class AdaptiveRetriever:
    def __init__(self, vector_db, complexity_classifier):
        self.vector_db = vector_db
        self.classifier = complexity_classifier

    async def retrieve(self, query, context):
        # 1. 评估复杂度
        complexity = self.classifier.assess(query, context)

        # 2. 分配检索预算
        budget = self.get_budget(complexity)

        # 3. 执行检索
        if budget == 0:
            return None  # 跳过检索
        elif budget == 1:
            return await self.vector_db.search(query, k=5)
        else:
            return await self.multi_source_search(query, budget)
```

#### 模板 2：自我纠错检索器
```python
# src/memory/corrective_retriever.py
class CorrectiveRetriever:
    async def retrieve_with_correction(self, query):
        # 1. 初次检索
        results = await self.vector_db.search(query)

        # 2. 评估质量
        confidence = self.evaluate_quality(results)

        # 3. 纠正动作
        if confidence > 0.8:
            return self.refine_results(results)  # Correct
        elif confidence < 0.5:
            return await self.web_search(query)  # Incorrect
        else:
            return self.combine_sources(results, await self.web_search(query))
```

#### 模板 3：多模态融合检索器
```python
# src/perception/multimodal_retriever.py
class MultimodalRetriever:
    async def retrieve(self, text_query, screenshot):
        # 1. 并发多模态检索
        text_results, image_results = await asyncio.gather(
            self.text_db.search(text_query),
            self.image_db.search(screenshot)
        )

        # 2. 跨模态重排序
        fused = self.rerank(
            text_results + image_results,
            query=(text_query, screenshot)
        )

        return fused
```

---

## 总结

Agentic RAG 代表了 RAG 技术的范式转变：从**静态管道**到**自主循环**，从**一次性检索**到**动态迭代**，从**单模态**到**多模态融合**。

对于 droidrun-vl 项目，核心借鉴点：
1. **自适应检索**：避免过度检索浪费资源
2. **自我纠错**：提高任务成功率
3. **多模态记忆**：充分利用截图、UI 树、OCR 的多源信息
4. **交错循环**：优化"观察-思考-决策-执行"的认知主循环
5. **工具链编排**：更智能的设备操作序列规划

这些模式将使 Agent 更加**自主、鲁棒、高效**。
