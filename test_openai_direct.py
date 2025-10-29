"""
直接测试 OpenAILike 的初始化和调用
"""
import os

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-Kd92LE2pud8bVtZE23B47248Bc064006Af400cB6770c8577"
os.environ["OPENAI_BASE_URL"] = "https://api.vimsai.com/v1"

print("=" * 60)
print("测试 OpenAILike 直接调用")
print(f"API Key: {os.environ['OPENAI_API_KEY'][:10]}...{os.environ['OPENAI_API_KEY'][-4:]}")
print(f"Base URL: {os.environ['OPENAI_BASE_URL']}")
print("=" * 60)

from droidrun.agent.utils.llm_picker import load_llm

# 测试1: 只传 api_base 和 api_key（模仿 CLI）
print("\n测试1: 传递 api_base + api_key")
try:
    llm = load_llm(
        provider_name="OpenAILike",
        model="qwen3-coder-plus-2025-07-22",
        api_base="https://api.vimsai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0.2,
        request_timeout=120.0
    )
    print(f"✅ LLM 初始化成功: {type(llm).__name__}")
    print(f"📊 Metadata: {llm.metadata}")

    # 尝试简单调用
    print("\n尝试简单调用...")
    response = llm.complete("Say 'test'", timeout=30.0)
    print(f"✅ 调用成功: {response.text[:100]}")
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()
