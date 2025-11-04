"""
工作记忆模块

实现 7±2 容量的短期记忆，支持循环检测和时间衰减
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger


class MemoryItem:
    """记忆项"""

    def __init__(self, content: Any, metadata: Optional[Dict] = None):
        """
        初始化记忆项

        Args:
            content: 记忆内容
            metadata: 元数据
        """
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.access_count = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "access_count": self.access_count,
        }


class WorkingMemory:
    """
    工作记忆

    基于 7±2 原则的短期记忆系统
    支持循环检测和时间衰减
    """

    def __init__(
        self,
        capacity: int = 7,
        enable_loop_detection: bool = True,
        loop_threshold: int = 3,
        time_decay: bool = True,
        decay_minutes: int = 5,
    ):
        """
        初始化工作记忆

        Args:
            capacity: 记忆容量（默认 7）
            enable_loop_detection: 是否启用循环检测
            loop_threshold: 循环判定阈值（连续重复次数）
            time_decay: 是否启用时间衰减
            decay_minutes: 衰减时间（分钟）
        """
        self.capacity = capacity
        self.enable_loop_detection = enable_loop_detection
        self.loop_threshold = loop_threshold
        self.time_decay = time_decay
        self.decay_minutes = decay_minutes

        # 使用 deque 实现固定容量的队列
        self.items: deque = deque(maxlen=capacity)

        # 循环检测历史
        self.recent_actions: deque = deque(maxlen=loop_threshold * 2)

    def add(self, content: Any, metadata: Optional[Dict] = None) -> None:
        """
        添加记忆项

        Args:
            content: 记忆内容
            metadata: 元数据
        """
        item = MemoryItem(content, metadata)
        self.items.append(item)

        # 记录到循环检测历史
        if self.enable_loop_detection:
            self.recent_actions.append(content)

        logger.debug(f"添加记忆: {self._format_content(content)} (容量: {len(self.items)}/{self.capacity})")

    def get_recent(self, n: Optional[int] = None) -> List[Any]:
        """
        获取最近的 N 条记忆

        Args:
            n: 要获取的数量，默认为全部

        Returns:
            记忆内容列表
        """
        if n is None:
            n = len(self.items)

        # 应用时间衰减过滤
        if self.time_decay:
            valid_items = self._filter_by_decay()
        else:
            valid_items = list(self.items)

        # 返回最近的 N 条
        recent_items = valid_items[-n:] if n < len(valid_items) else valid_items

        return [item.content for item in recent_items]

    def detect_loop(self) -> bool:
        """
        检测是否存在循环

        Returns:
            是否检测到循环
        """
        if not self.enable_loop_detection:
            return False

        if len(self.recent_actions) < self.loop_threshold:
            return False

        # 检查最近的 N 个动作是否相同
        recent_list = list(self.recent_actions)[-self.loop_threshold :]

        # 简单判断：所有动作是否相同
        first_action = recent_list[0]
        is_loop = all(action == first_action for action in recent_list)

        if is_loop:
            logger.warning(f"检测到循环: {self._format_content(first_action)} 重复 {self.loop_threshold} 次")
            return True

        return False

    def clear(self) -> None:
        """清空记忆"""
        self.items.clear()
        self.recent_actions.clear()
        logger.debug("工作记忆已清空")

    def get_summary(self) -> dict:
        """
        获取记忆摘要

        Returns:
            记忆摘要信息
        """
        if self.time_decay:
            valid_items = self._filter_by_decay()
        else:
            valid_items = list(self.items)

        return {
            "total_items": len(self.items),
            "valid_items": len(valid_items),
            "capacity": self.capacity,
            "usage_rate": len(self.items) / self.capacity if self.capacity > 0 else 0,
            "loop_detected": self.detect_loop(),
        }

    def _filter_by_decay(self) -> List[MemoryItem]:
        """根据时间衰减过滤记忆项"""
        now = datetime.now()
        decay_threshold = now - timedelta(minutes=self.decay_minutes)

        valid_items = [item for item in self.items if item.timestamp > decay_threshold]

        decayed_count = len(self.items) - len(valid_items)
        if decayed_count > 0:
            logger.debug(f"时间衰减: {decayed_count} 条记忆已过期")

        return valid_items

    def _format_content(self, content: Any) -> str:
        """格式化内容用于日志"""
        if isinstance(content, str):
            return content[:50] + ("..." if len(content) > 50 else "")
        elif isinstance(content, dict):
            return str(content)[:50] + "..."
        else:
            return str(type(content).__name__)


if __name__ == "__main__":
    import time

    # 测试工作记忆
    print("=" * 50)
    print("工作记忆测试")
    print("=" * 50)

    # 创建工作记忆
    memory = WorkingMemory(capacity=7, loop_threshold=3)

    # 测试添加记忆
    print("\n[测试 1] 添加记忆")
    for i in range(5):
        memory.add(f"操作 {i+1}", metadata={"step": i + 1})
    print(f"摘要: {memory.get_summary()}")

    # 测试获取最近记忆
    print("\n[测试 2] 获取最近 3 条记忆")
    recent = memory.get_recent(3)
    for item in recent:
        print(f"  - {item}")

    # 测试循环检测
    print("\n[测试 3] 循环检测")
    for i in range(3):
        memory.add("重复操作", metadata={"repeat": i + 1})
    print(f"检测到循环: {memory.detect_loop()}")

    # 测试容量限制
    print("\n[测试 4] 容量限制")
    for i in range(5):
        memory.add(f"额外操作 {i+1}")
    print(f"当前容量: {len(memory.items)}/{memory.capacity}")
    print(f"最旧的记忆: {memory.get_recent(1)[0] if memory.get_recent(1) else 'None'}")

    # 测试时间衰减
    print("\n[测试 5] 时间衰减（模拟）")
    # 修改第一个记忆的时间戳（模拟过期）
    if memory.items:
        memory.items[0].timestamp = datetime.now() - timedelta(minutes=10)
    summary = memory.get_summary()
    print(f"总记忆: {summary['total_items']}, 有效记忆: {summary['valid_items']}")

    # 测试清空
    print("\n[测试 6] 清空记忆")
    memory.clear()
    print(f"清空后容量: {len(memory.items)}")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
