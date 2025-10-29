"""
流式对话版图片像素识别
支持连续对话和图片分析
"""
import os
import sys
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


class StreamingImageChat:
    """流式图片对话类"""

    def __init__(
        self,
        api_base: str,
        model: str = "/models",
        temperature: float = 0.0,
        timeout: float = 60.0
    ):
        """
        初始化流式对话

        Args:
            api_base: API 基础 URL
            model: 模型名称
            temperature: 温度参数
            timeout: 超时时间(秒)
        """
        self.api_base = api_base
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.messages = []  # 对话历史
        self.llm = None

        print("=" * 100)
        print("🖼️  流式图片对话系统")
        print("=" * 100)
        print(f"API Base: {api_base}")
        print(f"Model: {model}")
        print("=" * 100)
        print()

    def connect(self):
        """连接到 LLM"""
        if self.llm is None:
            print("📡 正在连接到 LLM...")
            self.llm = load_llm(
                provider_name="OpenAILike",
                model=self.model,
                api_base=self.api_base,
                api_key=os.environ["OPENAI_API_KEY"],
                temperature=self.temperature,
                request_timeout=self.timeout,
            )
            print("✅ 连接成功")
            print()

    def send_message(self, text: str, image_path: str = None):
        """
        发送消息（支持文本和图片）

        Args:
            text: 文本消息
            image_path: 可选的图片路径
        """
        self.connect()

        # 构建消息内容
        content_blocks = [TextBlock(text=text)]

        # 如果有图片，添加图片块
        if image_path:
            if not Path(image_path).exists():
                print(f"❌ 错误: 图片文件不存在: {image_path}")
                return

            print(f"📸 正在加载图片: {image_path}")
            image_bytes = load_image_as_bytes(image_path)
            content_blocks.append(ImageBlock(image=image_bytes))

        # 添加用户消息
        user_message = ChatMessage(
            role=MessageRole.USER,
            content=content_blocks,
        )
        self.messages.append(user_message)

        print(f"💬 用户: {text}")
        if image_path:
            print(f"🖼️  附件: {image_path}")
        print()
        print("🤖 助手: ", end="", flush=True)

        try:
            # 流式调用模型
            response_stream = self.llm.stream_chat(self.messages)

            # 收集完整响应
            full_response = ""
            for chunk in response_stream:
                content = chunk.delta
                if content:
                    print(content, end="", flush=True)
                    full_response += content

            print()
            print()

            # 将助手响应添加到历史
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=full_response,
            )
            self.messages.append(assistant_message)

        except Exception as e:
            print()
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()

    def clear_history(self):
        """清空对话历史"""
        self.messages = []
        print("🗑️  对话历史已清空")
        print()


def run_interactive_chat():
    """运行交互式流式对话"""
    # 配置参数
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"
    TEMPERATURE = 0.0
    TIMEOUT = 60.0

    # 创建对话实例
    chat = StreamingImageChat(
        api_base=API_BASE,
        model=MODEL,
        temperature=TEMPERATURE,
        timeout=TIMEOUT,
    )

    print("📝 使用说明:")
    print("  - 输入文本直接发送消息")
    print("  - 输入 'image:路径' 来附加图片（例如: image:test/image.jpg）")
    print("  - 输入 'clear' 清空对话历史")
    print("  - 输入 'quit' 或 'exit' 退出")
    print()
    print("=" * 100)
    print()

    while True:
        try:
            user_input = input("💬 你: ").strip()

            if not user_input:
                continue

            # 检查退出命令
            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 再见！")
                break

            # 检查清空历史命令
            if user_input.lower() == "clear":
                chat.clear_history()
                continue

            # 检查是否包含图片
            image_path = None
            text = user_input

            if user_input.lower().startswith("image:"):
                parts = user_input.split(" ", 1)
                image_path = parts[0][6:]  # 去掉 "image:" 前缀
                text = parts[1] if len(parts) > 1 else "请分析这张图片"

            # 发送消息
            print()
            chat.send_message(text, image_path)
            print("-" * 100)
            print()

        except KeyboardInterrupt:
            print()
            print("👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()


def run_demo_conversation():
    """运行演示对话"""
    # 配置参数
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"
    TEMPERATURE = 0.0
    TIMEOUT = 60.0
    IMAGE_PATH = r"test\未标题-2 拷贝.jpg"

    # 创建对话实例
    chat = StreamingImageChat(
        api_base=API_BASE,
        model=MODEL,
        temperature=TEMPERATURE,
        timeout=TIMEOUT,
    )

    # 第一轮对话：识别图片
    chat.send_message(
        "请仔细观察这张图片，告诉我这张图片上是什么,告诉我这张图片的像素大小（宽度和高度）,再找出几个圆的坐标 x y",
        image_path=IMAGE_PATH
    )

    print("-" * 100)
    print()

    # 第二轮对话：追问
    chat.send_message("蓝色圆的坐标是多少？")

    print("-" * 100)
    print()

    # 第三轮对话：再次追问
    chat.send_message("这张图片总共有几个圆？")


if __name__ == "__main__":
    # 选择运行模式
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # 演示模式：自动运行预设对话
        print("🎬 运行演示对话...")
        print()
        run_demo_conversation()
    else:
        # 交互模式：手动输入对话
        run_interactive_chat()
