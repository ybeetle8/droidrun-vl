"""
测试图片像素识别
提交图片并让模型识别图片的像素大小
"""
import os
import base64
from pathlib import Path

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-Kd92LE2pud8bVtZE23B47248Bc064006Af400cB6770c8577"

from llama_index.core.multi_modal_llms import MultiModalLLM
from llama_index.core.schema import ImageDocument
from llama_index.multi_modal_llms.openai import OpenAIMultiModal


def encode_image_to_base64(image_path: str) -> str:
    """
    将图片编码为 base64 字符串

    Args:
        image_path: 图片路径

    Returns:
        base64 编码的字符串
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def test_image_pixel_detection(
    image_path: str,
    api_base: str,
    model: str = "gpt-4o",
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
        # 创建多模态 LLM
        print("📡 正在连接到多模态 LLM...")
        mm_llm = OpenAIMultiModal(
            model=model,
            api_key=os.environ["OPENAI_API_KEY"],
            api_base=api_base,
            temperature=temperature,
            timeout=timeout,
        )

        # 加载图片
        print(f"📸 正在加载图片: {image_path}")
        image_document = ImageDocument(image_path=image_path)

        # 构建提示
        prompt = "请仔细观察这张图片，告诉我这张图片的像素大小（宽度和高度）。请直接给出数字，格式为：宽度 x 高度。"

        print(f"💬 提示: {prompt}")
        print()
        print("🤖 正在调用模型识别图片像素...")

        # 调用模型
        response = mm_llm.complete(
            prompt=prompt,
            image_documents=[image_document],
        )

        print()
        print("=" * 100)
        print("✅ 识别结果:")
        print("=" * 100)
        print(response.text)
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
    IMAGE_PATH = r"test\未标题-1 拷贝.jpg"
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
