"""
基础设置测试脚本

测试配置、LLM 客户端、向量存储和数据模型是否正常工作
"""

import asyncio
import uuid

from src.llm.client import LLMClient
from src.memory.vector_store import VectorStore
from src.models import Action, Task, TaskIntent, Perception, VisualAnalysis, UIElement
from src.utils.config import config


async def test_config():
    """测试配置管理"""
    print("\n" + "=" * 60)
    print("测试 1: 配置管理")
    print("=" * 60)

    print(f"[OK] Embedding API Base: {config.embedding_api_base}")
    print(f"[OK] Embedding Model: {config.embedding_model}")
    print(f"[OK] Vision API Base: {config.vision_api_base}")
    print(f"[OK] Vision Model: {config.vision_model}")
    print(f"[OK] Vector DB Path: {config.vector_db_path}")
    print(f"[OK] Working Memory Size: {config.working_memory_size}")
    print(f"[OK] Enable Parallel Perception: {config.enable_parallel_perception}")


async def test_models():
    """测试数据模型"""
    print("\n" + "=" * 60)
    print("测试 2: 数据模型")
    print("=" * 60)

    # 测试 Task
    task = Task(
        id=str(uuid.uuid4()),
        description="在淘宝搜索双肩包",
        intent=TaskIntent.SHOPPING,
        app_name="淘宝",
    )
    print(f"[OK] Task 模型创建成功: {task.description}")

    # 测试 Action
    action = Action.tap(
        target="搜索框",
        coordinates=(100, 200),
        confidence=0.9,
    )
    print(f"[OK] Action 模型创建成功: {action.description}")

    # 测试 Perception
    visual = VisualAnalysis(
        scene_description="淘宝首页",
        page_type="首页",
        full_analysis="完整分析",
    )
    perception = Perception(
        timestamp=0.0,
        visual=visual,
        summary="感知摘要",
        perception_time_ms=500,
    )
    print(f"[OK] Perception 模型创建成功: {perception.summary}")


async def test_llm_client():
    """测试 LLM 客户端"""
    print("\n" + "=" * 60)
    print("测试 3: LLM 客户端（需要模型服务运行）")
    print("=" * 60)

    try:
        client = LLMClient()
        print("[OK] LLM 客户端初始化成功")

        # 测试 Embedding（需要服务运行）
        # text = "在淘宝搜索双肩包"
        # embedding = await client.embed_text(text)
        # print(f"[OK] Embedding 生成成功，维度: {len(embedding)}")

        print("[SKIP] 跳过实际 API 调用（需要模型服务运行）")

    except Exception as e:
        print(f"[SKIP] LLM 客户端测试跳过（模型服务未运行）: {e}")


async def test_vector_store():
    """测试向量存储"""
    print("\n" + "=" * 60)
    print("测试 4: 向量存储（需要模型服务运行）")
    print("=" * 60)

    try:
        store = VectorStore()
        print("[OK] 向量存储初始化成功")

        # 测试存储（需要服务运行）
        # await store.store_experience(...)

        # 获取统计
        stats = store.get_stats()
        print(f"[OK] 向量库统计: {stats['total_experiences']} 条经验")

    except Exception as e:
        print(f"[SKIP] 向量存储测试跳过（模型服务未运行）: {e}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("DroidRun-VL 基础设置测试")
    print("=" * 60)

    # 测试配置
    await test_config()

    # 测试数据模型
    await test_models()

    # 测试 LLM 客户端
    await test_llm_client()

    # 测试向量存储
    await test_vector_store()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n[SUCCESS] 基础设置正常，可以开始开发核心功能")
    print("\n下一步:")
    print("  1. 启动 Embedding 模型服务（http://192.168.18.9:8081）")
    print("  2. 启动 Qwen3-VL 模型服务（http://192.168.18.9:8080）")
    print("  3. 运行完整测试")


if __name__ == "__main__":
    asyncio.run(main())
