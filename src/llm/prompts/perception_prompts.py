"""
感知系统 Prompt 模板

用于 VL 模型分析屏幕内容
"""


def get_screen_analysis_prompt(task_context: str = "") -> str:
    """
    获取屏幕分析 Prompt

    Args:
        task_context: 任务上下文（可选）

    Returns:
        Prompt 字符串
    """
    context_section = ""
    if task_context:
        context_section = f"""
## 任务上下文
{task_context}
"""

    prompt = f"""你是一个 Android 屏幕分析专家。请分析当前屏幕内容并提供结构化输出。

{context_section}

## 分析要求

请按照以下格式输出:

### 1. 屏幕描述
简要描述屏幕上显示的内容（2-3 句话）

### 2. 当前页面/应用
识别当前所在的应用或页面

### 3. 可交互元素
列出所有可点击/可交互的 UI 元素，包括：
- 元素类型（按钮、输入框、图标等）
- 元素文本/描述
- 大致位置（顶部、中部、底部、左侧、右侧等）

格式示例：
- [按钮] "确定" - 位于底部右侧
- [输入框] 搜索框 - 位于顶部
- [图标] 设置图标 - 位于右上角

### 4. 可见文本
列出屏幕上所有可见的重要文本内容

### 5. 状态判断
- 是否在加载中？（是/否）
- 是否有弹窗？（是/否）
- 是否有错误提示？（是/否）
- 如果有错误，错误信息是什么？

## 输出示例

### 1. 屏幕描述
这是 Android 系统的主屏幕（Launcher），显示多个应用图标排列在网格中。顶部有状态栏显示时间和系统状态。底部有导航栏。

### 2. 当前页面/应用
com.android.launcher (主屏幕)

### 3. 可交互元素
- [图标] "设置" - 位于中部偏左
- [图标] "相机" - 位于中部偏右
- [图标] "浏览器" - 位于底部中央
- [搜索框] Google 搜索 - 位于顶部

### 4. 可见文本
["设置", "相机", "浏览器", "Google 搜索"]

### 5. 状态判断
- 加载中：否
- 弹窗：否
- 错误：否

---

现在请分析当前屏幕：
"""
    return prompt


def get_change_analysis_prompt(before_action: str, expected_effect: str) -> str:
    """
    获取前后变化分析 Prompt

    Args:
        before_action: 执行的动作描述
        expected_effect: 预期效果

    Returns:
        Prompt 字符串
    """
    prompt = f"""你是一个 Android 屏幕变化分析专家。请对比执行动作前后的屏幕，判断操作效果。

## 执行的操作
{before_action}

## 预期效果
{expected_effect}

## 分析任务

请对比两张截图（操作前和操作后），回答以下问题：

### 1. 屏幕是否发生了变化？
- 如果完全相同 → 无变化
- 如果有明显差异 → 描述变化

### 2. 变化是否符合预期？
- 成功：变化符合预期效果
- 失败：变化与预期不符，或出现错误
- 无效：屏幕无变化，操作未生效

### 3. 详细分析
描述具体的变化内容：
- UI 元素的出现/消失
- 页面的切换
- 文本内容的变化
- 错误提示的出现

## 输出格式

### 变化判断
[成功/失败/无效]

### 变化描述
[详细描述屏幕的实际变化]

### 原因分析
[如果失败或无效，分析可能的原因]

---

现在请分析前后两张截图：
"""
    return prompt


def get_element_localization_prompt(element_description: str) -> str:
    """
    获取元素定位 Prompt

    Args:
        element_description: 元素描述

    Returns:
        Prompt 字符串
    """
    prompt = f"""你是一个 UI 元素定位专家。请在屏幕截图中找到目标元素。

## 目标元素
{element_description}

## 任务

1. 在截图中定位该元素
2. 估算元素的中心坐标
3. 评估定位的置信度

## 输出格式

### 是否找到
[是/否]

### 元素位置描述
[描述元素在屏幕上的位置，如："顶部中央"、"底部右侧"等]

### 估算坐标
[如果找到，给出估算的中心坐标 (x, y)，如：(540, 960)]

### 置信度
[高/中/低]

### 备注
[其他重要信息或注意事项]

---

现在请定位目标元素：
"""
    return prompt


if __name__ == "__main__":
    # 测试 Prompt 模板
    print("=" * 80)
    print("感知 Prompt 模板测试")
    print("=" * 80)

    # 测试屏幕分析 Prompt
    print("\n[1. 屏幕分析 Prompt]")
    print(get_screen_analysis_prompt("用户想要打开设置应用"))

    print("\n" + "=" * 80)
    print("\n[2. 变化分析 Prompt]")
    print(get_change_analysis_prompt("点击设置图标", "进入设置应用主页"))

    print("\n" + "=" * 80)
    print("\n[3. 元素定位 Prompt]")
    print(get_element_localization_prompt("设置图标"))
