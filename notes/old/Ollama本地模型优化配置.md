# Ollama 本地模型优化配置

## 问题说明

使用 Ollama 本地模型时,由于硬件性能限制,过多的上下文会导致:
- 推理速度慢
- 内存消耗大
- 每轮对话响应时间长

## 优化方案

### 1. 限制历史对话轮数

通过环境变量 `LLM_HISTORY_LIMIT` 控制每次发送给 LLM 的对话历史数量。

**配置方式:**

在 `.env` 文件中设置:

```bash
# 对于本地 Ollama 模型,建议设置为 3-5
LLM_HISTORY_LIMIT=5
```

**说明:**
- 默认值: 20 (适用于云端 API)
- Ollama 推荐值: 3-5
- 每个轮次包含 user + assistant 两条消息
- 值越小,上下文越少,速度越快,但可能丢失部分历史信息

### 2. Planner Agent 任务规划优化

已修改 `planner_agent.py` 的提示词,确保:
- 每次规划 1-3 个任务(之前是 1-5)
- 建议关键操作只规划 1 个任务
- 每个任务执行后必须验证成功才继续
- 避免批量提交多个相互依赖的任务

### 3. 工作原理

**发送给 LLM 的消息数量计算:**

```python
max_messages = LLM_HISTORY_LIMIT * 2
# 例如 LLM_HISTORY_LIMIT=5, 则最多保留 10 条消息 (5 轮对话)
```

**保留策略:**
- 始终保留第一条用户消息(包含初始目标)
- 保留最近的 N 轮对话
- 超出限制的中间对话会被丢弃

**代码位置:**
- `droidrun/agent/common/constants.py` - 参数定义
- `droidrun/agent/planner/planner_agent.py:308-326` - 历史限制逻辑
- `droidrun/agent/codeact/codeact_agent.py:433-451` - 历史限制逻辑

### 4. 使用建议

根据你的硬件配置选择合适的值:

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| **低性能本地 Ollama** | 3 | 最少上下文,最快速度 |
| **中等性能本地 Ollama** | 5 | 平衡性能和上下文 |
| **高性能本地 Ollama** | 8-10 | 较多上下文,较慢速度 |
| **云端 API** | 20+ | 无需限制 |

### 5. 验证配置

启动时查看日志,会显示实际发送的消息数量:

```
[DEBUG] - Sending 12 messages to LLM.
[DEBUG] - Final message count: 12
```

如果消息数量始终在 `2 * LLM_HISTORY_LIMIT + 1(system)` 左右,说明配置生效。

### 6. 其他优化建议

1. **减少 Vision 模式的使用**
   - 图片会占用大量 token
   - 只在需要视觉识别时启用 `--vision`

2. **关闭 Debug 模式**
   - Debug 模式会输出大量日志
   - 正常使用时不加 `--debug` 参数

3. **选择合适的模型**
   - 使用较小的模型 (如 llama3.2:3b)
   - 避免使用超大模型 (如 70b+)

## 示例配置

完整的 `.env` 文件示例:

```bash
# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434

# 历史记录限制 (针对 Ollama 优化)
LLM_HISTORY_LIMIT=5

# 其他配置...
```

## 运行示例

```bash
# 使用 Ollama 本地模型,限制历史上下文
droidrun "打开微信" --provider ollama --model llama3.2

# 启用推理模式但限制上下文
droidrun "打开微信并给张三发消息" --provider ollama --model llama3.2 --reasoning
```
