from llama_index.core.workflow import Event
from llama_index.core.base.llms.types import ChatMessage
from typing import Optional, Any
from droidrun.agent.context import Task
from droidrun.agent.usage import UsageResult

class PlanInputEvent(Event):
    input: list[ChatMessage]


class PlanThinkingEvent(Event):
    thoughts: Optional[str] = None
    code: Optional[str] = None  
    usage: Optional[UsageResult] = None


class PlanCreatedEvent(Event):
    tasks: list[Task]
