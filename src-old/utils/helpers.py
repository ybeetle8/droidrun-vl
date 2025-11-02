"""
辅助函数
"""
import json
import re
import inspect
from typing import Dict, Callable, Optional


def parse_tool_descriptions(tool_list: Dict[str, Callable]) -> str:
    """
    将工具字典转换为 LLM 可读的 markdown 格式描述

    Args:
        tool_list: 工具字典

    Returns:
        工具描述的 markdown 字符串
    """
    tool_descriptions = []

    for tool in tool_list.values():
        tool_name = tool.__name__
        tool_signature = inspect.signature(tool)
        tool_docstring = tool.__doc__ or "No description available."
        formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
        tool_descriptions.append(formatted_signature)

    return "\n\n".join(tool_descriptions)


def extract_json_from_text(text: str) -> Optional[dict]:
    """
    从文本中提取 JSON 数据

    Args:
        text: 包含 JSON 的文本

    Returns:
        提取的 JSON 对象，如果未找到则返回 None
    """
    patterns = [
        r'```json\s*\n(.*?)```',
        r'```\s*\n(\{.*?\})```',
        r'\{.*?\}'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                continue

    return None


def extract_code_from_markdown(text: str) -> str:
    """
    从 markdown 格式的文本中提取 Python 代码块

    Args:
        text: 包含代码块的 markdown 文本

    Returns:
        提取的代码字符串，如果未找到则返回空字符串
    """
    patterns = [
        r'```python\s*\n(.*?)```',
        r'```\s*\n(.*?)```'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()

    return ""
