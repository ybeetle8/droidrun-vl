"""
决策系统 Prompt 模板

用于生成任务规划和动作决策
"""

from typing import List, Optional


def get_decision_prompt(
    task: str,
    screen_description: str,
    interactive_elements: List[dict],
    visible_text: List[str],
    history: Optional[List[str]] = None,
) -> str:
    """
    获取决策生成 Prompt

    Args:
        task: 任务描述
        screen_description: 屏幕描述
        interactive_elements: 可交互元素列表
        visible_text: 可见文本列表
        history: 历史操作（可选）

    Returns:
        Prompt 字符串
    """
    # 格式化交互元素
    elements_text = "\n".join(
        f"- [{elem.get('type', 'unknown')}] {elem.get('text', '未知')} - {elem.get('location', '位置未知')}"
        for elem in interactive_elements
    )

    # 格式化历史
    history_section = ""
    if history and len(history) > 0:
        history_text = "\n".join(f"{i+1}. {action}" for i, action in enumerate(history))
        history_section = f"""
## 历史操作
已执行的操作:
{history_text}
"""

    prompt = f"""你是一个 Android 自动化 Agent 的决策系统。你的任务是分析当前状态，决定下一步应该执行什么操作。

## 任务目标
{task}

## 当前屏幕状态
{screen_description}

## 可交互元素
{elements_text if elements_text else "无可交互元素"}

## 可见文本
{', '.join(visible_text) if visible_text else '无'}

{history_section}

## 决策要求

请按照以下步骤进行推理：

### 步骤 1: 任务理解
- 理解当前任务的目标
- 分析当前状态与目标的差距

### 步骤 2: 状态判断
- 当前处于什么状态？
- 目标是否已经达成？

### 步骤 3: 复杂度评估
判断任务是简单还是复杂：
- **简单任务（TERMINAL）**: 可以通过单个原子操作完成（如点击、输入、滑动等）
- **复杂任务（BRANCH）**: 需要分解为多个子任务

### 步骤 4: 生成执行计划

#### 如果是简单任务（TERMINAL）:
输出格式:
```
节点类型: TERMINAL
目标已达成: [是/否]

动作类型: [tap/swipe/input/press_back/press_home/wait]
目标元素: [元素描述]
预期效果: [操作后的预期结果]
置信度: [0.0-1.0]

推理过程:
1. [推理步骤1]
2. [推理步骤2]
...
```

支持的动作类型:
- tap: 点击元素（需要指定目标元素）
- swipe: 滑动（需要指定方向: up/down/left/right）
- input: 输入文本（需要指定输入内容）
- press_back: 按返回键
- press_home: 按 Home 键
- wait: 等待（需要指定秒数）

#### 如果是复杂任务（BRANCH）:
输出格式:
```
节点类型: BRANCH
目标已达成: [是/否]

子任务列表:
1. [子任务描述1]
2. [子任务描述2]
3. [子任务描述3]
...

推理过程:
1. [推理步骤1]
2. [推理步骤2]
...
```

## 示例

### 示例 1: TERMINAL 决策
```
节点类型: TERMINAL
目标已达成: 否

动作类型: tap
目标元素: 设置图标
预期效果: 进入设置应用主界面
置信度: 0.95

推理过程:
1. 任务是"打开设置"，目标明确且单一
2. 当前在主屏幕，可以看到设置图标
3. 只需点击设置图标即可完成任务
4. 这是一个简单的原子操作，选择 TERMINAL 节点
```

### 示例 2: BRANCH 决策
```
节点类型: BRANCH
目标已达成: 否

子任务列表:
1. 打开设置应用
2. 在设置中找到并点击"Wi-Fi"选项
3. 进入 Wi-Fi 详细页面

推理过程:
1. 任务是"打开设置并进入 Wi-Fi 页面"，包含多个步骤
2. 需要先打开设置，然后在设置中导航到 Wi-Fi
3. 这是一个复杂任务，需要分解为多个子任务
4. 选择 BRANCH 节点，将任务分解为 3 个子任务
```

---

现在请进行决策：
"""
    return prompt


def get_branch_generation_prompt(task: str, screen_state: str, reasoning: str) -> str:
    """
    获取分支生成 Prompt

    Args:
        task: 任务描述
        screen_state: 屏幕状态
        reasoning: 推理过程

    Returns:
        Prompt 字符串
    """
    prompt = f"""你是一个任务分解专家。请将复杂任务分解为有序的子任务。

## 任务
{task}

## 当前状态
{screen_state}

## 已有推理
{reasoning}

## 分解要求

1. 将任务分解为 2-5 个子任务
2. 子任务应该按执行顺序排列
3. 每个子任务应该明确、可执行
4. 子任务之间应该有逻辑连贯性

## 输出格式

```
子任务列表:
1. [子任务1描述] - 优先级: [1-5] - 预期结果: [结果描述]
2. [子任务2描述] - 优先级: [1-5] - 预期结果: [结果描述]
3. [子任务3描述] - 优先级: [1-5] - 预期结果: [结果描述]
...

推理说明:
[解释为什么这样分解，以及各子任务的作用]
```

---

现在请分解任务：
"""
    return prompt


if __name__ == "__main__":
    # 测试决策 Prompt 模板
    print("=" * 80)
    print("决策 Prompt 模板测试")
    print("=" * 80)

    # 测试 TERMINAL 场景
    print("\n[1. TERMINAL 决策 Prompt]")
    prompt = get_decision_prompt(
        task="打开设置",
        screen_description="主屏幕，显示多个应用图标",
        interactive_elements=[
            {"type": "icon", "text": "设置", "location": "中部偏左"},
            {"type": "icon", "text": "相机", "location": "中部偏右"},
        ],
        visible_text=["设置", "相机", "浏览器"],
        history=["启动设备"],
    )
    print(prompt[:500] + "...")

    # 测试 BRANCH 场景
    print("\n" + "=" * 80)
    print("\n[2. BRANCH 生成 Prompt]")
    prompt2 = get_branch_generation_prompt(
        task="打开设置并进入 Wi-Fi 页面",
        screen_state="主屏幕",
        reasoning="任务包含多个步骤，需要分解",
    )
    print(prompt2[:500] + "...")
