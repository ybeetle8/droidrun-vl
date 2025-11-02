"""
测试图片像素识别
提交图片并让模型识别图片的像素大小
"""
import os
import sys
import base64
from pathlib import Path

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-xxx"

from droidrun.agent.utils.llm_picker import load_llm
from llama_index.core.base.llms.types import ChatMessage, MessageRole, TextBlock, ImageBlock


def load_image_as_bytes(image_path: str) -> bytes:
    """
    加载图片为字节数据

    Args:
        image_path: 图片路径

    Returns:
        图片的字节数据
    """
    with open(image_path, "rb") as image_file:
        return image_file.read()


def test_image_pixel_detection(
    image_path: str,
    api_base: str,
    model: str = "/models",
    temperature: float = 0.0,
    timeout: float = 60.0
):
    """
    测试图片像素识别

    Args:
        image_path: 图片路径
        api_base: API 基础 URL
        model: 模型名称
        temperature: 温度参数
        timeout: 超时时间(秒)
    """
    print("=" * 100)
    print("🖼️  图片像素识别测试")
    print("=" * 100)
    print(f"图片路径: {image_path}")
    print(f"API Base: {api_base}")
    print(f"Model: {model}")
    print("=" * 100)
    print()

    # 检查图片是否存在
    if not Path(image_path).exists():
        print(f"❌ 错误: 图片文件不存在: {image_path}")
        return

    try:
        # 创建 LLM (使用 OpenAILike 支持 vision)
        print("📡 正在连接到 LLM...")
        llm = load_llm(
            provider_name="OpenAILike",
            model=model,
            api_base=api_base,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=temperature,
            request_timeout=timeout,
        )

        # 加载图片
        print(f"📸 正在加载图片: {image_path}")
        image_bytes = load_image_as_bytes(image_path)

        # 构建提示消息 (使用 vision 格式)
        #prompt_text = "请仔细观察这张图片，告诉我这张图片的像素大小（宽度和高度）。格式为：宽度 x 高度。 再找出蓝色圆的坐标 x y"
        prompt_text = "请仔细观察这张图片，告诉我这张图片上是什么,告诉我这张图片的像素大小（宽度和高度） ,再找出几个圆的坐标 x y"

        print(f"💬 提示: {prompt_text}")
        print()
        print("🤖 正在调用模型识别图片像素...")

        # 构建包含文本和图片的消息块
        text_block = TextBlock(text=prompt_text)
        image_block = ImageBlock(image=image_bytes)

        # 构建包含图片的消息
        messages = [
            ChatMessage(
                role=MessageRole.USER,
                content=[text_block, image_block],
            )
        ]

        # 调用模型
        response = llm.chat(messages)

        print()
        print("=" * 100)
        print("✅ 识别结果:")
        print("=" * 100)
        print(response.message.content)
        print("=" * 100)

    except Exception as e:
        print()
        print("=" * 100)
        print("❌ 识别失败:")
        print("=" * 100)
        print(f"⚠️  错误: {e}")
        print("=" * 100)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 配置参数
    IMAGE_PATH = r"test\未标题-2 拷贝.jpg"
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"
    TEMPERATURE = 0.0
    TIMEOUT = 60.0

    # 运行测试
    test_image_pixel_detection(
        image_path=IMAGE_PATH,
        api_base=API_BASE,
        model=MODEL,
        temperature=TEMPERATURE,
        timeout=TIMEOUT,
    )
