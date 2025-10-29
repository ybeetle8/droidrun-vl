"""Max number of recent conversation steps to include in LLM prompt
可以通过环境变量 LLM_HISTORY_LIMIT 控制
对于 Ollama 本地模型,建议设置为 3-5 以减少上下文消耗
默认值 20 适用于云端 API
"""
import os
LLM_HISTORY_LIMIT = int(os.getenv("LLM_HISTORY_LIMIT", "20"))
