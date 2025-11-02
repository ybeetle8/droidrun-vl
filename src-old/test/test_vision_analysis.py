"""
测试视觉分析功能
捕获屏幕截图和 UI 状态，传给大模型进行分析并输出结果
"""
import os
import sys
import json
import asyncio
import base64

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# 使用 src 包导入
from src.tools.vision import capture_screenshot, get_ui_state
from src.utils.config import Config
from src.utils.logger import setup_utf8_console
from src.utils.helpers import extract_json_from_text


async def test_vision_analysis():
    """测试视觉分析"""
    # 设置 UTF-8 编码
    setup_utf8_console()

    print("=" * 100)
    print("🎯 视觉分析测试")
    print("=" * 100)
    print()

    # 加载配置
    config = Config()
    os.environ["OPENAI_API_KEY"] = config.api_key

    try:
        # 1. 捕获屏幕截图
        print("📸 正在截取屏幕...")
        _, screenshot_bytes = capture_screenshot(use_tcp=config.use_tcp, hide_overlay=True)
        print(f"✅ 截图完成，大小: {len(screenshot_bytes)} 字节")

        # 2. 获取 UI 状态
        print("\n🔍 正在获取 UI 状态信息...")
        ui_state = get_ui_state(use_tcp=config.use_tcp)
        print(f"✅ UI 状态获取完成")

        # 检查是否包含 is_covered 字段（兼容两种格式）
        a11y_tree = None
        if 'a11y_tree' in ui_state:
            a11y_tree = ui_state['a11y_tree']
        elif ui_state.get('data') and ui_state['data'].get('a11y_tree'):
            a11y_tree = ui_state['data']['a11y_tree']

        if a11y_tree and len(a11y_tree) > 0:
            first_elem = a11y_tree[0]
            has_field = 'is_covered' in first_elem
            print(f"\n🔍 检查重叠检测字段: {'✓ 已添加' if has_field else '✗ 缺失'}")
            if has_field:
                print(f"   第一个元素: is_covered={first_elem.get('is_covered')}, covered_by={first_elem.get('covered_by')}")
            else:
                print(f"   ⚠️ 字段缺失！第一个元素的keys: {list(first_elem.keys())}")

        print(ui_state)  # 注释掉完整输出，太长了

        # 3. 初始化 LLM
        print("\n🤖 正在连接大模型...")
        llm = ChatOpenAI(
            model=config.model,
            base_url=config.api_base,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        print("✅ 大模型连接成功")

        # 4. 构建分析提示词
        state_json_str = json.dumps(ui_state, ensure_ascii=False, indent=2)

        prompt = f"""请分析这个Android屏幕截图和UI状态信息，提取商品列表。

**分析要求：**
1. 找出屏幕上的所有商品
2. 要返回遮挡标记 is_covered
3. 对于每个商品，提取以下信息：
   - 商品标题
   - 商品价格
   - 商品 UI元素的 index （用于点击）
   - UI元素的坐标 (bounds)
4. 按照商品在屏幕上出现的顺序列出

**输出格式（JSON）：**
```json
{{
  "products": [
    {{
      "title": "商品标题",
      "price": "商品价格",
      "index": 数字,
      "bounds": [x1, y1, x2, y2]
      "is_covered": bool
    }}
  ]
}}
```

下面是UI状态的JSON数据：
```json
{state_json_str}
```"""

        # 5. 调用大模型分析
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode()}"
                        }
                    }
                ]
            )
        ]

        print("\n🤖 大模型分析结果（流式输出）:\n")
        print("-" * 100)

        full_response = ""
        async for chunk in llm.astream(messages):
            content = chunk.content
            if content:
                print(content, end="", flush=True)
                full_response += content

        print()
        print("-" * 100)

        # 6. 提取 JSON 结果
        print("\n📊 解析结果:")
        products = extract_json_from_text(full_response)

        if products and "products" in products:
            print(f"✅ 识别到 {len(products['products'])} 个商品:")
            for i, product in enumerate(products['products'], 1):
                print(f"\n商品 {i}:")
                print(f"  标题: {product.get('title', 'N/A')}")
                print(f"  价格: {product.get('price', 'N/A')}")
                print(f"  索引: {product.get('index', 'N/A')}")
                print(f"  坐标: {product.get('bounds', 'N/A')}")
        else:
            print("⚠️  未能解析出商品信息")

        print("\n" + "=" * 100)
        print("✅ 测试完成！")
        print("=" * 100)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数"""
    asyncio.run(test_vision_analysis())


if __name__ == "__main__":
    main()
