"""
设备交互模块

提供 Android 设备操作能力
"""

from .android_controller import AndroidController, get_android_controller
from .execution_result import ExecutionResult

__all__ = [
    "AndroidController",
    "get_android_controller",
    "ExecutionResult",
]
