"""
简单测试 batch_runner2.py 的命令执行
"""
import asyncio
import subprocess

async def test_command():
    cmd = [
        "uv", "run", "droidrun",
        "--provider", "Ollama",
        "--model", "qwen3-coder:30b",
        "--base_url", "http://localhost:11434",
        "--vision",
        "--steps", "15",
        "打开设置"
    ]

    print(f"执行命令: {' '.join(cmd)}")

    # 方式1: 继承标准输出
    print("\n=== 方式1: 继承标准输出 ===")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=None,
        stderr=None
    )
    await process.wait()
    print(f"返回码: {process.returncode}")

if __name__ == "__main__":
    asyncio.run(test_command())
