"""
屏幕分析测试
结合截图和UI状态信息，使用大模型进行页面分析
"""
import os
import sys
import json
import base64
from pathlib import Path

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-Kd92LE2pud8bVtZE23B47248Bc064006Af400cB6770c8577"

from droidrun.tools.adb import AdbTools
from droidrun.agent.utils.llm_picker import load_llm
from llama_index.core.base.llms.types import ChatMessage, MessageRole, TextBlock, ImageBlock


def get_screenshot_and_state(adb_tools: AdbTools):
    """
    获取截图和UI状态信息

    Args:
        adb_tools: AdbTools实例

    Returns:
        tuple: (screenshot_bytes, state_json)
    """
    print("📸 正在截取屏幕...")
    _, screenshot_bytes = adb_tools.take_screenshot(hide_overlay=True)
    print(f"✅ 截图完成，大小: {len(screenshot_bytes)} 字节")

    print("\n🔍 正在获取UI状态信息...")
    state_data = adb_tools.get_state()
    print(f"✅ UI状态获取完成")

    return screenshot_bytes, state_data


def analyze_screen_with_llm(screenshot_bytes: bytes, state_data: dict, llm, extra_params: dict = None):
    """
    使用大模型分析屏幕

    Args:
        screenshot_bytes: 截图字节数据
        state_data: UI状态JSON数据
        llm: 大模型实例
        extra_params: 额外的生成参数（如 repetition_penalty）

    Returns:
        str: 分析结果
    """
    print("\n🤖 正在分析屏幕...")
    print("=" * 100)

    if extra_params is None:
        extra_params = {}

    # 构建提示词
    state_json_str = json.dumps(state_data, ensure_ascii=False, indent=2)

    prompt = f"""请分析这个Android屏幕截图和UI状态信息，提供以下分析。

**重要提示：请精简回答，避免重复。每个信息点只需说明一次。**

1. **屏幕概览**（不超过2句话）
   - 当前应用和页面
   - 主要功能

2. **UI元素分析**（列表形式，最多列举10个重要元素）
   - 识别重要UI元素及其位置
   - 可交互元素的索引

3. **布局结构**（不超过3句话）
   - 整体布局描述
   - 主要区域划分

4. **可执行操作**（列表形式，最多列举5个操作）
   - 具体操作建议和对应索引

5. **状态信息**（仅列出以下关键信息）
   - 应用包名和活动
   - 屏幕尺寸和方向
   - 键盘状态
   - 最多3个其他重要状态

**回答要求：**
- 使用简洁的中文
- 避免重复相同信息
- 每个状态信息只说明一次
- 回答完成后立即停止

下面是UI状态的JSON数据：
```json
{state_json_str}
```"""

    # 构建消息
    content_blocks = [
        TextBlock(text=prompt),
        ImageBlock(image=screenshot_bytes)
    ]

    message = ChatMessage(
        role=MessageRole.USER,
        content=content_blocks,
    )

    # 调用大模型（传递额外参数）
    response_stream = llm.stream_chat([message], **extra_params)

    print("🤖 分析结果:\n")
    print("-" * 100)

    full_response = ""
    for chunk in response_stream:
        content = chunk.delta
        if content:
            print(content, end="", flush=True)
            full_response += content

    print()
    print("-" * 100)

    return full_response


def save_analysis_result(screenshot_bytes: bytes, state_data: dict, analysis: str, output_dir: str = "test/analysis_output"):
    """
    保存分析结果到文件

    Args:
        screenshot_bytes: 截图字节数据
        state_data: UI状态数据
        analysis: 分析结果
        output_dir: 输出目录
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 生成时间戳
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存截图
    screenshot_file = output_path / f"screenshot_{timestamp}.png"
    with open(screenshot_file, "wb") as f:
        f.write(screenshot_bytes)
    print(f"\n💾 截图已保存: {screenshot_file}")

    # 保存UI状态
    state_file = output_path / f"state_{timestamp}.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)
    print(f"💾 UI状态已保存: {state_file}")

    # 保存分析结果
    analysis_file = output_path / f"analysis_{timestamp}.md"
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(f"# 屏幕分析报告\n\n")
        f.write(f"**时间**: {timestamp}\n\n")
        f.write(f"**截图**: {screenshot_file.name}\n\n")
        f.write(f"**UI状态**: {state_file.name}\n\n")
        f.write(f"---\n\n")
        f.write(analysis)
    print(f"💾 分析结果已保存: {analysis_file}")


def main():
    """主函数"""
    print("=" * 100)
    print("🔍 Android 屏幕分析工具")
    print("=" * 100)
    print()

    # 配置参数
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"
    USE_TCP = True  # 使用TCP通信
    SAVE_RESULT = True  # 是否保存分析结果

    # LLM 生成参数 - 防止无限循环
    MAX_TOKENS = 4048  # 最大生成token数
    vLLM 额外参数（使用OpenAI兼容的参数）
    VLLM_EXTRA_PARAMS = {
        "frequency_penalty": 0.1,  # 频率惩罚，减少重复（0.0-2.0）
        "presence_penalty": 0.1,   # 存在惩罚，鼓励多样性（0.0-2.0）
    }

    try:
        # 1. 初始化ADB工具
        print("📱 正在连接Android设备...")
        adb_tools = AdbTools(use_tcp=USE_TCP)
        print(f"✅ 已连接到设备: {adb_tools.device.serial}")
        print()

        # 2. 获取截图和UI状态
        screenshot_bytes, state_data = get_screenshot_and_state(adb_tools)

        # 3. 初始化大模型
        print("\n🤖 正在连接大模型...")
        llm = load_llm(
            provider_name="OpenAILike",
            model=MODEL,
            api_base=API_BASE,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0.0,
            request_timeout=60.0,
            max_tokens=MAX_TOKENS,  # 限制最大输出token数，防止无限循环
        )
        print("✅ 大模型连接成功")

        # 4. 分析屏幕
        analysis = analyze_screen_with_llm(screenshot_bytes, state_data, llm, VLLM_EXTRA_PARAMS)

        # 5. 保存结果（可选）
        if SAVE_RESULT:
            save_analysis_result(screenshot_bytes, state_data, analysis)

        print("\n" + "=" * 100)
        print("✅ 分析完成！")
        print("=" * 100)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
