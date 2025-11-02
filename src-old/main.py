"""
主入口文件
"""
import os
import sys
import asyncio

from langchain_openai import ChatOpenAI

from .agents import AndroidAgentState
from .graph import create_android_agent_graph
from .graph.builder import compile_graph
from .tools import get_demo_tools
from .utils import Config
from .utils.logger import setup_utf8_console


async def main_async():
    """主函数（异步版本）"""
    # 设置 UTF-8 编码
    setup_utf8_console()

    print("=" * 100)
    print("🎯 LangGraph 版本工具调用演示")
    print("=" * 100)
    print()

    # 加载配置
    config = Config()

    # 设置环境变量
    os.environ["OPENAI_API_KEY"] = config.api_key

    try:
        # 1. 初始化 LLM
        print("🤖 正在连接大模型...")
        llm = ChatOpenAI(
            model=config.model,
            base_url=config.api_base,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            frequency_penalty=0.05,
            presence_penalty=0.05,
        )
        print("✅ 大模型连接成功")

        # 2. 创建工作流图
        print("\n🔧 构建 LangGraph 工作流...")
        workflow = create_android_agent_graph()
        app = compile_graph(workflow, use_checkpointer=True)
        print("✅ 工作流构建完成")

        # 可选：打印工作流图结构
        try:
            print("\n📊 工作流图结构:")
            print(app.get_graph().draw_ascii())
        except Exception as e:
            print(f"⚠️  图结构可视化失败（这不影响执行）: {e}")
            print("📝 工作流节点: capture → analyze → generate_code → execute → verify")

        # 3. 准备工具
        print("\n🔧 准备工具列表...")
        demo_tools = get_demo_tools(use_tcp=config.use_tcp)
        print("✅ 工具准备完成")

        # 4. 初始化状态
        initial_state: AndroidAgentState = {
            "messages": [],
            "screenshot": None,
            "ui_state": None,
            "analysis_result": None,
            "extracted_products": None,
            "generated_code": None,
            "execution_result": None,
            "tool_descriptions": None,
            "next_action": None,
            "retry_count": 0
        }

        # 5. 执行工作流
        run_config = {
            "configurable": {
                "llm": llm,
                "tools": demo_tools,
                "thread_id": "android_agent_demo_001"
            }
        }

        print("\n" + "=" * 100)
        print("🚀 开始执行工作流")
        print("=" * 100)

        final_state = await app.ainvoke(initial_state, run_config)

        print("\n" + "=" * 100)
        print("✅ 工作流执行完成！")
        print("=" * 100)

        # 6. 输出最终状态摘要
        print("\n📋 执行摘要:")
        print(f"- 截图大小: {len(final_state['screenshot']) if final_state['screenshot'] else 0} 字节")
        print(f"- 识别商品数: {len(final_state['extracted_products']) if final_state['extracted_products'] else 0}")
        print(f"- 代码执行: {'成功' if final_state.get('execution_result', {}).get('success') else '失败'}")
        print(f"- 重试次数: {final_state['retry_count']}")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数入口"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
