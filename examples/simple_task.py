"""
简单任务示例

演示如何使用策略树执行简单任务
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.strategy_tree import StrategyTree
from src.utils.config import Config
from loguru import logger


async def example_simple_task():
    """示例 1: 简单任务 - 打开设置"""
    print("=" * 60)
    print("示例 1: 简单任务 - 打开设置")
    print("=" * 60)

    # 初始化策略树
    config = Config()
    tree = StrategyTree(config)

    # 执行任务
    result = await tree.execute_task("打开设置")

    # 打印结果
    print("\n" + "=" * 60)
    print("执行结果:")
    status_str = result.status if isinstance(result.status, str) else result.status.value
    print(f"  状态: {status_str}")
    print(f"  耗时: {result.duration_seconds:.2f}s")
    print(f"  节点深度: {result.depth}")
    print(f"  执行动作数: {result.total_actions}")

    if result.error:
        print(f"  错误: {result.error}")

    print("=" * 60)

    return result


async def example_two_step_task():
    """示例 2: 两步任务 - 打开设置并进入 Wi-Fi"""
    print("\n\n" + "=" * 60)
    print("示例 2: 两步任务 - 打开设置并进入 Wi-Fi")
    print("=" * 60)

    # 初始化策略树
    config = Config()
    tree = StrategyTree(config)

    # 执行任务
    result = await tree.execute_task("打开设置并进入 Wi-Fi 页面")

    # 打印结果
    print("\n" + "=" * 60)
    print("执行结果:")
    status_str = result.status if isinstance(result.status, str) else result.status.value
    print(f"  状态: {status_str}")
    print(f"  耗时: {result.duration_seconds:.2f}s")
    print(f"  节点深度: {result.depth}")
    print(f"  执行动作数: {result.total_actions}")

    if result.sub_results:
        print(f"  子节点数: {len(result.sub_results)}")
        for i, sub in enumerate(result.sub_results):
            print(f"    子节点 {i+1}: {sub.status.value} - {sub.task_description}")

    if result.error:
        print(f"  错误: {result.error}")

    print("=" * 60)

    return result


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    try:
        # 运行示例 1
        await example_simple_task()

        # 可选：运行示例 2
        # await example_two_step_task()

    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
    except Exception as e:
        import traceback
        logger.error(f"执行失败: {e}")
        logger.error(f"详细错误:\n{traceback.format_exc()}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DroidRun-VL Phase 1 - 简单任务示例")
    print("=" * 60)
    print("\n请确保:")
    print("  1. 已连接 Android 设备 (adb devices)")
    print("  2. LLM 服务正在运行")
    print("  3. 设备屏幕已解锁")
    print("\n" + "=" * 60 + "\n")

    asyncio.run(main())
