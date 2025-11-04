"""
Android 控制器 - get_ui_tree 演示

测试获取 UI 树并打印输出
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.device.android_controller import AndroidController


async def test_get_ui_tree():
    """测试获取 UI 树"""
    print("=== Android Controller - get_ui_tree 演示 ===\n")

    # 初始化控制器（自动连接默认设备）
    controller = AndroidController()

    try:
        # 获取 UI 树
        print("正在获取 UI 树...\n")
        result = await controller.get_ui_tree()

        # 打印结果
        print(f"✓ 执行成功")
        if result.duration_ms:
            print(f"  耗时: {result.duration_ms}ms")
        print(f"  消息: {result.message}\n")

        # 打印数据内容
        if result.data:
            print("--- UI 树数据 ---")

            # 打印无障碍树
            if "a11y_tree" in result.data:
                a11y_tree = result.data["a11y_tree"]
                print(f"\n无障碍树 (前 1000 字符):")
                print(a11y_tree[:1000])
                if len(a11y_tree) > 1000:
                    print(f"...\n(总长度: {len(a11y_tree)} 字符)")

            # 打印设备状态
            if "phone_state" in result.data:
                phone_state = result.data["phone_state"]
                print(f"\n设备状态:")
                for key, value in phone_state.items():
                    print(f"  {key}: {value}")

    except Exception as e:
        print(f"✗ 执行失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_get_ui_tree())
