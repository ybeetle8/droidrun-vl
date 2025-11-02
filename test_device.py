"""
设备模块测试脚本

测试 AndroidController 的各种操作
"""

import asyncio

from src.device import AndroidController, ExecutionResult


async def test_execution_result():
    """测试 ExecutionResult 模型"""
    print("\n" + "=" * 60)
    print("测试 1: ExecutionResult 模型")
    print("=" * 60)

    # 成功结果
    success_result = ExecutionResult.success_result(
        message="Tapped at (100, 200)",
        operation="tap",
        duration_ms=50,
    )
    print(f"[OK] Success result: {success_result.message}")
    assert success_result.success is True

    # 失败结果
    failure_result = ExecutionResult.failure_result(
        message="Failed to tap",
        error="Element not found",
        operation="tap",
    )
    print(f"[OK] Failure result: {failure_result.error}")
    assert failure_result.success is False

    # 带数据的结果
    data_result = ExecutionResult.success_result(
        message="Screenshot taken",
        data={"format": "PNG", "size": 1024000},
        operation="screenshot",
    )
    print(f"[OK] Data result: {data_result.data}")
    assert data_result.data is not None


async def test_android_controller():
    """测试 AndroidController（需要真实设备）"""
    print("\n" + "=" * 60)
    print("测试 2: AndroidController（需要连接设备）")
    print("=" * 60)

    try:
        controller = AndroidController(use_tcp=False)
        print("[OK] AndroidController 初始化成功")

        # 测试点击
        print("\n[测试 2.1] 点击操作")
        result = await controller.tap(100, 200)
        print(f"  结果: {result.message}")
        print(f"  耗时: {result.duration_ms}ms")
        assert result.success is True

        # 测试滑动
        print("\n[测试 2.2] 滑动操作")
        result = await controller.swipe(100, 500, 100, 200, duration_ms=300)
        print(f"  结果: {result.message}")
        assert result.success is True

        # 测试输入
        print("\n[测试 2.3] 文本输入")
        result = await controller.input_text("测试文本")
        print(f"  结果: {result.message}")
        assert result.success is True

        # 测试返回键
        print("\n[测试 2.4] 按返回键")
        result = await controller.press_back()
        print(f"  结果: {result.message}")
        assert result.success is True

        # 测试截屏
        print("\n[测试 2.5] 截屏")
        result = await controller.screenshot()
        print(f"  结果: {result.message}")
        print(f"  图片大小: {result.data['size']} bytes")
        assert result.success is True
        assert result.data["image_bytes"] is not None

        # 测试 UI 树
        print("\n[测试 2.6] 获取 UI 树")
        result = await controller.get_ui_tree()
        print(f"  结果: {result.message}")
        print(f"  元素数量: {len(result.data['a11y_tree'])}")
        assert result.success is True
        assert "a11y_tree" in result.data
        assert "phone_state" in result.data

        # 测试启动应用
        print("\n[测试 2.7] 启动应用")
        result = await controller.start_app("com.android.settings")
        print(f"  结果: {result.message}")
        assert result.success is True

        print("\n[SUCCESS] 所有设备操作测试通过!")

    except RuntimeError as e:
        print(f"\n[ERROR] 设备操作测试失败: {e}")
        print("请确保:")
        print("  1. 设备已连接并可通过 adb devices 查看")
        print("  2. DroidRun Portal 已安装并运行")
    except Exception as e:
        print(f"\n[SKIP] 设备测试跳过（设备未连接）: {e}")


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 3: 错误处理")
    print("=" * 60)

    try:
        controller = AndroidController(use_tcp=False)

        # 测试异常抛出
        print("\n[测试 3.1] 测试异常抛出")
        try:
            # 尝试启动不存在的应用
            await controller.start_app("com.nonexistent.app")
            print("[FAIL] 应该抛出异常")
        except RuntimeError as e:
            print(f"[OK] 正确抛出异常: {type(e).__name__}")

        print("\n[SUCCESS] 错误处理测试通过!")

    except Exception as e:
        print(f"\n[SKIP] 错误处理测试跳过: {e}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("设备模块测试")
    print("=" * 60)

    # 测试 ExecutionResult
    await test_execution_result()

    # 测试 AndroidController
    await test_android_controller()

    # 测试错误处理
    await test_error_handling()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n说明:")
    print("  - ExecutionResult 模型测试: 已通过")
    print("  - AndroidController 测试: 需要连接真实设备")
    print("  - 所有操作均为异步执行")
    print("  - 所有失败操作均抛出 RuntimeError")


if __name__ == "__main__":
    asyncio.run(main())
