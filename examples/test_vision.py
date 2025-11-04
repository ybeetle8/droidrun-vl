"""
测试视觉分析器

最简单的示例 - 只测试 VisionAnalyzer 的屏幕分析功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.perception.vision_analyzer import VisionAnalyzer
from src.llm.client import LLMClient
from src.utils.config import Config
from src.device.android_controller import AndroidController
from loguru import logger


async def main():
    """主函数 - 测试视觉分析"""
    print("=" * 60)
    print("视觉分析器测试")
    print("=" * 60)

    try:
        # 1. 初始化配置和客户端
        print("\n[1/4] 初始化配置...")
        llm_client = LLMClient()
        analyzer = VisionAnalyzer(llm_client)
        print("[OK] LLM 客户端和视觉分析器初始化完成")

        # 2. 初始化设备控制器
        print("\n[2/4] 连接 Android 设备...")
        device = AndroidController()
        print(f"[OK] 设备已连接")

        # 3. 截取屏幕
        print("\n[3/4] 截取当前屏幕...")
        screenshot_result = await device.screenshot()
        screenshot_bytes = screenshot_result.data["image_bytes"]
        print(f"[OK] 截图完成 ({len(screenshot_bytes)} bytes)")

        # 4. 分析屏幕
        print("\n[4/4] 分析屏幕内容...")

        # 先获取原始 LLM 响应用于调试
        from src.llm.prompts.perception_prompts import get_screen_analysis_prompt
        prompt = get_screen_analysis_prompt("测试屏幕分析功能")
        raw_response = await llm_client.generate_with_image(
            prompt=prompt, image_data=screenshot_bytes, max_tokens=1500
        )

        print("\n[DEBUG] 原始 LLM 响应:")
        print("-" * 60)
        print(raw_response)
        print("-" * 60)

        # 再执行正常分析
        result = await analyzer.analyze_screen(
            screenshot=screenshot_bytes,
            task_context="测试屏幕分析功能"
        )

        # 打印分析结果
        print("\n" + "=" * 60)
        print("分析结果:")
        print("=" * 60)

        print(f"\n【当前页面】")
        print(f"  {result.current_page or '未识别'}")

        print(f"\n【屏幕描述】")
        print(f"  {result.screen_description}")

        print(f"\n【可交互元素】 (共 {len(result.interactive_elements)} 个)")
        for i, elem in enumerate(result.interactive_elements[:10], 1):  # 最多显示10个
            print(f"  {i}. [{elem['type']}] \"{elem['text']}\"")
            if elem.get('location'):
                print(f"     位置: {elem['location']}")

        if len(result.interactive_elements) > 10:
            print(f"  ... 还有 {len(result.interactive_elements) - 10} 个元素")

        print(f"\n【可见文本】 (共 {len(result.visible_text)} 条)")
        for i, text in enumerate(result.visible_text[:10], 1):  # 最多显示10条
            print(f"  {i}. {text}")

        if len(result.visible_text) > 10:
            print(f"  ... 还有 {len(result.visible_text) - 10} 条文本")

        print(f"\n【状态判断】")
        print(f"  加载中: {'是' if result.is_loading else '否'}")
        print(f"  有弹窗: {'是' if result.has_popup else '否'}")
        print(f"  有错误: {'是' if result.has_error else '否'}")

        if result.has_error and result.error_message:
            print(f"  错误信息: {result.error_message}")

        print("\n" + "=" * 60)
        print("[SUCCESS] 测试完成!")
        print("=" * 60)

    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
    except Exception as e:
        import traceback
        logger.error(f"\n❌ 测试失败: {e}")
        logger.error(f"详细错误:\n{traceback.format_exc()}")


if __name__ == "__main__":
    print("\n请确保:")
    print("  1. 已连接 Android 设备 (adb devices)")
    print("  2. Qwen3-VL 服务正在运行 (http://192.168.18.9:8080)")
    print("  3. 设备屏幕已解锁")
    print()

    asyncio.run(main())
