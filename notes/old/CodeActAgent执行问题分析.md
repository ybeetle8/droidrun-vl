# CodeActAgent 执行问题分析

## 问题描述

执行任务时,Agent 会在一次回复中连续执行多个操作,没有等待验证每步结果:

```python
# 问题示例:一次性执行多个操作
input_text("m.2 固态")
tap_by_index(14)
complete(success=True, reason="...")
```

这导致:
- 操作之间没有间隔
- 没有验证每步是否成功
- UI 可能还没更新就执行下一步
- 容易出错

## 根本原因

### 1. 提示词示例误导

`droidrun/agent/context/personas/default.py:56-80` 中的示例展示了一次性规划多个步骤:

```python
**(Step 1) Agent Analysis:** ...
**(Step 1) Agent Action:**
tap_by_index(3)

**(Step 2) Agent Analysis:** ...  # ❌ 问题所在
**(Step 2) Agent Action:**
tap_by_index(1)

**(Step 3) Agent Analysis:** ...
tap_by_index(5)
complete(...)
```

这个示例让 LLM 误以为:
- 可以在一个 Python 代码块中写多个操作
- 可以提前规划后续步骤
- 不需要等待观察结果

### 2. 缺少明确限制

提示词中没有明确说明:
- 每次只能执行一个操作
- 必须等待观察结果
- 需要基于实际结果决定下一步

## 期望的执行流程

### ReAct 循环 (Reasoning-Action-Observation)

```
Round 1:
  User: 请搜索 "m.2 固态"

  Agent Analysis: 我看到搜索框,需要先输入文本
  Agent Action: input_text("m.2 固态")

  System: [执行代码,返回结果]
  Observation: 文本已输入,搜索框显示 "m.2 固态"

Round 2:
  User: [自动继续任务]

  Agent Analysis: 文本已输入成功,现在需要点击搜索按钮
  Agent Action: tap_by_index(14)

  System: [执行代码,返回结果]
  Observation: 搜索已触发,正在加载结果页面

Round 3:
  Agent Analysis: 搜索成功,任务完成
  Agent Action: complete(success=True, reason="...")
```

## 解决方案

### 方案 1: 修改示例(推荐)

将示例改为**单步执行**:

```python
## Response Format:
Example of proper code format:

**Task Assignment:**
**Task:** "Precondition: Settings app is open. Goal: Navigate to Wi-Fi settings and connect to 'HomeNetwork'."

**Agent Analysis:**
I can see the Settings app is open from the screenshot. This is a multi-step task.
My FIRST step is to navigate to Wi-Fi settings by tapping the Wi-Fi option at index 3.
I will wait for the result before planning the next step.

**Agent Action:**
```python
# Navigate to Wi-Fi settings (Step 1 of multiple)
tap_by_index(3)
```

---
[After execution and observing the result...]

**Agent Analysis:**
Good! I've successfully navigated to Wi-Fi settings. Now I can see Wi-Fi is turned off.
My NEXT step is to turn on Wi-Fi by tapping the toggle at index 1.

**Agent Action:**
```python
# Turn on Wi-Fi to see available networks
tap_by_index(1)
```

---
[After execution and observing the result...]

**Agent Analysis:**
Excellent! Wi-Fi is now enabled and I can see 'HomeNetwork' at index 5.
This is my FINAL step - connect to the network.

**Agent Action:**
```python
# Connect to the target network
tap_by_index(5)
complete(success=True, reason="Successfully connected to HomeNetwork")
```
```

### 方案 2: 添加明确规则

在 `system_prompt` 中添加:

```python
## CRITICAL EXECUTION RULES:

1. **ONE ACTION PER RESPONSE**: You must execute ONLY ONE action in each code block
2. **WAIT FOR OBSERVATION**: After each action, you will receive:
   - Execution result
   - New screenshot
   - Updated UI state
3. **OBSERVE THEN DECIDE**: Base your next action on the ACTUAL result, not assumptions
4. **NO BATCH OPERATIONS**: Do NOT write multiple operations in one code block unless they are atomic (like setting multiple related values)

Example of CORRECT single-step execution:
```python
# Do one thing
tap_by_index(3)
```

Example of INCORRECT multi-step execution:
```python
# Do NOT do this - multiple separate actions
tap_by_index(3)  # ❌ Wrong
sleep(1)         # ❌ Wrong
tap_by_index(5)  # ❌ Wrong
complete(...)    # ❌ Wrong
```

The only exception is when calling `complete()` with a final action:
```python
# This is OK - final action + completion
tap_by_index(5)
complete(success=True, reason="Task completed")
```
```

### 方案 3: 工具函数限制

在代码执行器中添加检测:
- 检测是否调用了多个工具函数
- 如果发现多个操作,只执行第一个并警告

## 推荐实施步骤

1. **立即修改**: 修改 `default.py` 和其他 persona 的示例,改为单步执行
2. **添加规则**: 在 system_prompt 中明确说明"一次一个操作"
3. **强化提示**: 在每次执行后的反馈中提醒"基于结果决定下一步"
4. **调整 Planner**: 确保 Planner 只分配单个明确的任务

## 与 Planner 优化的配合

之前已经修改了 Planner 提示词:
- Planner: 每次规划 1-3 个**任务** ✅
- CodeActAgent: 每次执行 1 个**操作** (本次修改)

两者结合:
```
Planner: 分配任务 "导航到 Wi-Fi 设置"
  └─> CodeActAgent Round 1: tap_by_index(3)
  └─> CodeActAgent Round 2: complete(...)

Planner: 分配任务 "打开 Wi-Fi"
  └─> CodeActAgent Round 1: tap_by_index(1)
  └─> CodeActAgent Round 2: complete(...)
```

## 测试验证

修改后,执行日志应该显示:

```
Round 1:
  Analysis: 需要输入搜索文本
  Action: input_text("m.2 固态")
  [等待执行]
  Result: 文本已输入

Round 2:
  Analysis: 输入成功,现在点击搜索按钮
  Action: tap_by_index(14)
  [等待执行]
  Result: 搜索已触发

Round 3:
  Analysis: 搜索完成
  Action: complete(success=True, reason="...")
```

而不是:
```
Round 1:
  Analysis: ...
  Action:
    input_text("m.2 固态")    # ❌ 一次性执行多个
    tap_by_index(14)          # ❌
    complete(...)             # ❌
```
