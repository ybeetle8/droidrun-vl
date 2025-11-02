# ContentBlocks 使用教程

## 概述

`content_blocks` 是 llama-index 中用于构建多模态消息的机制。它允许在一条消息中组合文本、图片等多种内容类型，特别适用于需要同时发送文字提示和图片的场景（如视觉语言模型分析）。

## 核心概念

### 基本类型

llama-index 提供了两种主要的内容块类型：

1. **TextBlock**: 纯文本内容块
2. **ImageBlock**: 图片内容块

```python
from llama_index.core.base.llms.types import ChatMessage, MessageRole, TextBlock, ImageBlock
```

### ChatMessage 结构

`ChatMessage` 可以通过两种方式承载内容：

1. **字符串方式**（简单文本）:
   ```python
   message = ChatMessage(role=MessageRole.USER, content="这是一条简单消息")
   ```

2. **内容块列表方式**（多模态）:
   ```python
   message = ChatMessage(role=MessageRole.USER, content=[TextBlock(...), ImageBlock(...)])
   ```

## 使用场景

### 场景 1: 图文混合分析（test_screen_analysis.py）

这是最常见的使用场景：发送文本提示词和截图给多模态大模型进行分析。

```python
def analyze_screen_with_llm(screenshot_bytes: bytes, state_data: dict, llm):
    # 1. 准备文本提示
    state_json_str = json.dumps(state_data, ensure_ascii=False, indent=2)
    prompt = f"""请分析这个Android屏幕截图和UI状态信息...

下面是UI状态的JSON数据：
```json
{state_json_str}
```"""

    # 2. 构建内容块列表
    content_blocks = [
        TextBlock(text=prompt),           # 文本提示词
        ImageBlock(image=screenshot_bytes) # 截图字节数据
    ]

    # 3. 创建消息
    message = ChatMessage(
        role=MessageRole.USER,
        content=content_blocks,  # 使用内容块列表
    )

    # 4. 发送给大模型
    response = llm.stream_chat([message])
```

**关键点**：
- 图片数据可以是 `bytes` 类型（PNG/JPEG字节数据）
- 文本和图片的顺序会影响某些模型的理解
- 通常文本在前、图片在后效果较好

### 场景 2: 动态添加上下文（chat_utils.py）

在对话历史中动态追加额外的上下文信息。

```python
async def add_ui_text_block(ui_state: str, chat_history: List[ChatMessage], copy=True):
    """在最后一条用户消息中添加UI状态信息"""
    if ui_state:
        # 创建UI信息文本块
        ui_block = TextBlock(text=f"\nCurrent UI elements:\n{ui_state}\n")

        if copy:
            # 复制消息避免修改原始数据
            chat_history = chat_history.copy()
            chat_history[-1] = message_copy(chat_history[-1])

        # 追加到消息的blocks列表中
        chat_history[-1].blocks.append(ui_block)

    return chat_history
```

**关键点**：
- 使用 `.blocks` 属性访问和修改内容块列表
- 建议在修改前复制消息对象，避免副作用
- 适用于需要"后期添加"上下文的场景

### 场景 3: 截图后期添加（chat_utils.py）

截图可能在构建消息后才获取，需要动态添加。

```python
async def add_screenshot_image_block(screenshot, chat_history: List[ChatMessage], copy=True):
    """在最后一条消息中添加截图"""
    if screenshot:
        image_block = ImageBlock(image=screenshot)

        if copy:
            chat_history = chat_history.copy()
            chat_history[-1] = message_copy(chat_history[-1])

        # 追加图片块
        chat_history[-1].blocks.append(image_block)

    return chat_history
```

### 场景 4: 记忆/反思信息前置（chat_utils.py）

在用户消息开头添加历史记忆或反思信息。

```python
async def add_memory_block(memory: List[str], chat_history: List[ChatMessage]):
    """在第一条用户消息前添加记忆信息"""
    memory_block = "\n### Remembered Information:\n"
    for idx, item in enumerate(memory, 1):
        memory_block += f"{idx}. {item}\n"

    for i, msg in enumerate(chat_history):
        if msg.role == "user":
            if isinstance(msg.content, str):
                # 字符串方式：直接拼接
                updated_content = f"{memory_block}\n\n{msg.content}"
                chat_history[i] = ChatMessage(role="user", content=updated_content)
            elif isinstance(msg.content, list):
                # 内容块方式：前置内存块
                memory_text_block = TextBlock(text=memory_block)
                content_blocks = [memory_text_block] + msg.content
                chat_history[i] = ChatMessage(role="user", content=content_blocks)
            break

    return chat_history
```

**关键点**：
- 处理字符串和列表两种内容格式
- 记忆信息通常放在**最前面**，确保模型优先看到
- 使用 `+` 运算符合并内容块列表

## 上下文放置的最佳实践

### 1. 内容块顺序原则

```python
content_blocks = [
    # 1️⃣ 系统级上下文（记忆、反思、历史经验）
    TextBlock(text="### Previous Experience:\n..."),

    # 2️⃣ 当前任务描述和要求
    TextBlock(text="Please analyze this screen...\n\nRequirements:\n..."),

    # 3️⃣ 结构化数据（JSON、状态信息）
    TextBlock(text=f"UI State:\n```json\n{json_data}\n```"),

    # 4️⃣ 视觉内容（截图、图表）
    ImageBlock(image=screenshot_bytes),

    # 5️⃣ 补充说明（可选）
    TextBlock(text="\nNote: Focus on clickable elements."),
]
```

### 2. 顺序的影响

不同的顺序会影响模型的注意力分配：

| 顺序 | 适用场景 | 原因 |
|------|---------|------|
| 文本 → 图片 | 图片分析、OCR、UI解析 | 模型先理解任务要求，再看图片 |
| 图片 → 文本 | 图片描述、Caption生成 | 模型先看图片，再理解输出格式 |
| 上下文 → 任务 → 数据 | 复杂推理任务 | 逐层递进，避免信息过载 |

### 3. 长上下文管理

当上下文过长时，考虑拆分：

```python
# ❌ 不推荐：一次性塞入所有信息
huge_prompt = f"""
{memory}
{reflection}
{ui_state}
{task_description}
...
"""
content_blocks = [TextBlock(text=huge_prompt), ImageBlock(image=img)]

# ✅ 推荐：分块组织
content_blocks = [
    TextBlock(text=memory),       # 记忆块
    TextBlock(text=reflection),   # 反思块
    TextBlock(text=ui_state),     # 状态块
    ImageBlock(image=img),        # 图片块
    TextBlock(text=task),         # 任务块
]
```

**优势**：
- 结构清晰，易于调试
- 可以动态启用/禁用某些块
- 某些模型能更好地理解分段内容

### 4. 动态上下文注入

DroidRun 中常见的模式：

```python
async def build_message_with_context(
    base_prompt: str,
    ui_state: Optional[dict] = None,
    screenshot: Optional[bytes] = None,
    memory: Optional[List[str]] = None,
    reflection: Optional[str] = None,
) -> ChatMessage:
    """构建带完整上下文的消息"""

    content_blocks = []

    # 1. 添加记忆（如果有）
    if memory:
        memory_text = "\n### Remembered:\n" + "\n".join(f"- {m}" for m in memory)
        content_blocks.append(TextBlock(text=memory_text))

    # 2. 添加反思（如果有）
    if reflection:
        content_blocks.append(TextBlock(text=f"\n### Reflection:\n{reflection}\n"))

    # 3. 添加主要任务提示
    content_blocks.append(TextBlock(text=base_prompt))

    # 4. 添加UI状态（如果有）
    if ui_state:
        ui_json = json.dumps(ui_state, ensure_ascii=False, indent=2)
        content_blocks.append(TextBlock(text=f"\n```json\n{ui_json}\n```"))

    # 5. 添加截图（如果有）
    if screenshot:
        content_blocks.append(ImageBlock(image=screenshot))

    return ChatMessage(role=MessageRole.USER, content=content_blocks)
```

## 常见问题

### Q1: 图片必须是 bytes 类型吗？

是的。ImageBlock 接受：
- PNG/JPEG 的字节数据（`bytes`）
- Base64 编码的字符串（部分模型支持）

```python
# ✅ 正确
with open("screenshot.png", "rb") as f:
    img_bytes = f.read()
ImageBlock(image=img_bytes)

# ✅ 也正确
import base64
img_base64 = base64.b64encode(img_bytes).decode()
ImageBlock(image=img_base64)
```

### Q2: content_blocks 为空会怎样？

会导致错误。至少需要一个内容块：

```python
# ❌ 错误
content_blocks = []
message = ChatMessage(role=MessageRole.USER, content=content_blocks)

# ✅ 正确
content_blocks = [TextBlock(text="Hello")]
message = ChatMessage(role=MessageRole.USER, content=content_blocks)
```

### Q3: 如何判断消息是字符串还是内容块？

```python
if isinstance(message.content, str):
    # 字符串类型
    text = message.content
elif isinstance(message.content, list):
    # 内容块列表
    for block in message.content:
        if isinstance(block, TextBlock):
            print(block.text)
        elif isinstance(block, ImageBlock):
            print(f"Image: {len(block.image)} bytes")
```

### Q4: 能否混合使用字符串和内容块？

不能。一个 `ChatMessage` 只能选择一种方式：

```python
# ❌ 错误：不能混合
message = ChatMessage(
    role=MessageRole.USER,
    content="text" + [TextBlock(text="block")]  # 类型错误
)

# ✅ 正确：统一使用内容块
message = ChatMessage(
    role=MessageRole.USER,
    content=[TextBlock(text="text"), TextBlock(text="block")]
)
```

## 完整示例

### 示例 1: 屏幕分析完整流程

```python
from llama_index.core.base.llms.types import ChatMessage, MessageRole, TextBlock, ImageBlock
import json

async def analyze_screen(screenshot_bytes: bytes, ui_state: dict, task: str, llm):
    """完整的屏幕分析流程"""

    # 1. 构建结构化提示
    ui_json = json.dumps(ui_state, ensure_ascii=False, indent=2)

    system_prompt = f"""你是一个Android UI分析专家。
任务: {task}

请按以下结构分析：
1. 屏幕概览
2. 关键元素识别
3. 可执行操作建议
"""

    # 2. 构建内容块（顺序很重要！）
    content_blocks = [
        TextBlock(text=system_prompt),
        TextBlock(text=f"\nUI状态数据:\n```json\n{ui_json}\n```"),
        ImageBlock(image=screenshot_bytes),
    ]

    # 3. 创建消息
    message = ChatMessage(
        role=MessageRole.USER,
        content=content_blocks,
    )

    # 4. 调用模型
    response = await llm.achat([message])

    return response.message.content
```

### 示例 2: 多轮对话中的上下文管理

```python
async def multi_turn_conversation(llm):
    """多轮对话，每轮添加新的上下文"""

    chat_history = []

    # 第1轮：初始任务
    msg1 = ChatMessage(
        role=MessageRole.USER,
        content=[TextBlock(text="打开淘宝应用")]
    )
    chat_history.append(msg1)

    response1 = await llm.achat(chat_history)
    chat_history.append(response1.message)

    # 第2轮：添加UI状态和截图
    msg2_blocks = [TextBlock(text="现在搜索'手机'")]

    # 动态添加UI信息
    ui_state = get_current_ui()
    msg2_blocks.append(TextBlock(text=f"\nUI: {ui_state}"))

    # 动态添加截图
    screenshot = take_screenshot()
    msg2_blocks.append(ImageBlock(image=screenshot))

    msg2 = ChatMessage(role=MessageRole.USER, content=msg2_blocks)
    chat_history.append(msg2)

    response2 = await llm.achat(chat_history)

    return response2.message.content
```

## 总结

### 核心要点

1. **内容块是列表**：`content_blocks = [TextBlock(...), ImageBlock(...), ...]`
2. **顺序很重要**：上下文 → 任务 → 数据 → 图片 → 补充
3. **动态添加**：使用 `.blocks.append()` 后期追加内容
4. **复制修改**：修改前复制消息，避免副作用
5. **类型检查**：处理字符串和列表两种 content 类型

### 使用建议

- ✅ 图文分析：使用 content_blocks
- ✅ 多模态输入：使用 content_blocks
- ✅ 动态上下文：使用 `.blocks.append()`
- ❌ 纯文本对话：直接用字符串即可
- ❌ 简单提示：无需 content_blocks

### 参考资源

- 项目代码：`test/test_screen_analysis.py` (完整示例)
- 工具函数：`droidrun/agent/utils/chat_utils.py` (动态添加)
- llama-index 文档：https://docs.llamaindex.ai/
