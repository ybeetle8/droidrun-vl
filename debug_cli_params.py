"""
调试 CLI 参数 - 打印 CLI 实际传递的参数
"""
import sys
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# Monkey patch load_llm 和 DroidAgent 来打印参数
from droidrun.agent.utils import llm_picker
from droidrun.agent.droid import droid_agent

original_load_llm = llm_picker.load_llm
original_droid_agent_init = droid_agent.DroidAgent.__init__

def patched_load_llm(**kwargs):
    print("\n" + "="*60)
    print("CLI load_llm 调用参数:")
    print("="*60)
    for k, v in sorted(kwargs.items()):
        print(f"  {k}: {v}")
    print("="*60 + "\n")
    return original_load_llm(**kwargs)

def patched_droid_agent_init(self, **kwargs):
    print("\n" + "="*60)
    print("CLI DroidAgent 调用参数:")
    print("="*60)
    for k, v in sorted(kwargs.items()):
        if k not in ["llm", "tools"]:
            print(f"  {k}: {v}")
    print("="*60 + "\n")
    return original_droid_agent_init(self, **kwargs)

llm_picker.load_llm = patched_load_llm
droid_agent.DroidAgent.__init__ = patched_droid_agent_init

# 导入并运行 CLI
from droidrun.cli.main import cli

if __name__ == "__main__":
    sys.argv = [
        "droidrun",
        "--provider", "Ollama",
        "--model", "qwen3-coder:30b",
        "--base_url", "http://localhost:11434",
        "打开闲鱼"
    ]
    cli()
