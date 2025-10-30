"""
Workflow 使用教程 - 像搭积木一样构建异步工作流

这个教程通过多个渐进式示例，展示 llama-index Workflow 的核心概念和用法。

核心概念：
    Workflow = 工作流引擎（总指挥）
    @step = 工作步骤（工人）
    Event = 事件（传递的信息）
    Context = 上下文（共享的记忆本）

形象比喻：
    Workflow 就像一个流水线工厂：
    - 原材料（StartEvent）进入
    - 经过多个工位（@step 函数）加工
    - 每个工位处理后传递给下一个工位（return Event）
    - 最终产出成品（StopEvent）
"""

import asyncio
from typing import Optional, Any
from dataclasses import dataclass

# 导入 llama-index 的 Workflow 组件
from llama_index.core.workflow import (
    Workflow,      # 工作流基类
    StartEvent,    # 开始事件
    StopEvent,     # 结束事件
    step,          # 步骤装饰器
    Context,       # 上下文
    Event,         # 自定义事件基类
)


# ==============================================================================
# 示例 1：最简单的 Workflow - Hello World
# ==============================================================================

print("\n" + "="*80)
print("📚 示例 1: 最简单的 Workflow")
print("="*80)

class SimpleWorkflow(Workflow):
    """
    最简单的工作流：接收输入，返回输出

    流程：
        StartEvent -> step1 -> StopEvent
    """

    @step
    async def step1(self, ev: StartEvent) -> StopEvent:
        """
        唯一的步骤：处理输入并结束

        @step 装饰器的作用：
        - 将这个函数注册为工作流的一个步骤
        - Workflow 会自动调用它
        - 根据输入事件类型（StartEvent）自动路由
        """
        name = ev.get("name", "World")
        message = f"Hello, {name}!"

        print(f"  🔹 步骤1 执行: 输入 '{name}' -> 输出 '{message}'")

        # 返回 StopEvent 表示工作流结束
        return StopEvent(result=message)


async def demo_simple_workflow():
    """运行最简单的 Workflow"""
    print("\n💡 这个 Workflow 只有一个步骤，直接处理输入并返回结果\n")

    workflow = SimpleWorkflow()

    # 运行工作流
    result = await workflow.run(name="Alice")

    print(f"\n✅ 最终结果: {result}")
    print(f"   类型: {type(result)}")


# ==============================================================================
# 示例 2：多步骤 Workflow - 流水线处理
# ==============================================================================

print("\n\n" + "="*80)
print("📚 示例 2: 多步骤 Workflow - 流水线处理")
print("="*80)


# 定义自定义事件（步骤之间传递的信息）
@dataclass
class ProcessEvent(Event):
    """处理事件：携带需要处理的数据"""
    data: str


@dataclass
class TransformEvent(Event):
    """转换事件：携带转换后的数据"""
    data: str


class PipelineWorkflow(Workflow):
    """
    流水线工作流：数据经过多个步骤处理

    流程：
        StartEvent -> step1_receive
                   -> ProcessEvent -> step2_process
                   -> TransformEvent -> step3_transform
                   -> StopEvent
    """

    @step
    async def step1_receive(self, ev: StartEvent) -> ProcessEvent:
        """
        步骤1：接收输入

        StartEvent 是工作流的入口，run() 传入的参数会在这里接收
        """
        text = ev.get("text", "")
        print(f"\n  📥 步骤1 - 接收输入: '{text}'")

        # 返回 ProcessEvent，触发下一个处理这个事件的步骤
        return ProcessEvent(data=text)

    @step
    async def step2_process(self, ev: ProcessEvent) -> TransformEvent:
        """
        步骤2：处理数据

        这个函数接收 ProcessEvent，因为上一步返回了它
        Workflow 会自动路由：ProcessEvent -> 这个函数
        """
        data = ev.data
        processed = data.upper()  # 转大写

        print(f"  ⚙️  步骤2 - 处理数据: '{data}' -> '{processed}'")

        # 返回 TransformEvent，继续传递
        return TransformEvent(data=processed)

    @step
    async def step3_transform(self, ev: TransformEvent) -> StopEvent:
        """
        步骤3：最终转换

        接收 TransformEvent，处理后返回 StopEvent 结束流程
        """
        data = ev.data
        final = f"[处理完成] {data}"

        print(f"  ✨ 步骤3 - 最终转换: '{data}' -> '{final}'")

        # 返回 StopEvent，工作流结束
        return StopEvent(result=final)


async def demo_pipeline_workflow():
    """运行流水线 Workflow"""
    print("\n💡 数据像流水线一样，经过多个步骤依次处理\n")
    print("流程: 接收 -> 处理 -> 转换 -> 完成")

    workflow = PipelineWorkflow()
    result = await workflow.run(text="hello world")

    print(f"\n✅ 最终结果: {result}")


# ==============================================================================
# 示例 3：使用 Context - 步骤间共享数据
# ==============================================================================

print("\n\n" + "="*80)
print("📚 示例 3: 使用 Context - 步骤间共享数据")
print("="*80)


@dataclass
class AddEvent(Event):
    """加法事件"""
    value: int


@dataclass
class MultiplyEvent(Event):
    """乘法事件"""
    value: int


class CalculatorWorkflow(Workflow):
    """
    计算器工作流：演示 Context 的使用

    Context 作用：
    - 在不同步骤间共享数据
    - 类似一个共享的"记忆本"
    - 每个 @step 函数都可以访问同一个 Context

    流程：
        StartEvent -> initialize (存储初始值到 Context)
                   -> AddEvent -> add_step (从 Context 读取并更新)
                   -> MultiplyEvent -> multiply_step (从 Context 读取并更新)
                   -> StopEvent
    """

    @step
    async def initialize(self, ctx: Context, ev: StartEvent) -> AddEvent:
        """
        初始化：存储初始值到 Context

        ctx: Context 参数让我们可以访问共享存储
        """
        initial_value = ev.get("value", 0)

        # 存储到 Context（记忆本）
        await ctx.store.set("result", initial_value)
        await ctx.store.set("steps", [f"初始值: {initial_value}"])

        print(f"\n  📝 初始化: result = {initial_value}")

        # 返回加法事件
        add_value = ev.get("add", 0)
        return AddEvent(value=add_value)

    @step
    async def add_step(self, ctx: Context, ev: AddEvent) -> MultiplyEvent:
        """
        加法步骤：从 Context 读取，计算后更新 Context
        """
        # 从 Context 读取当前结果
        result = await ctx.store.get("result")
        steps = await ctx.store.get("steps")

        # 执行加法
        new_result = result + ev.value

        # 更新 Context
        await ctx.store.set("result", new_result)
        steps.append(f"加 {ev.value}: {result} + {ev.value} = {new_result}")
        await ctx.store.set("steps", steps)

        print(f"  ➕ 加法: {result} + {ev.value} = {new_result}")

        # 传递乘法事件（从 StartEvent 获取参数）
        # 注意：我们需要从某处获取 multiply 参数
        # 这里演示从 Context 获取
        multiply_value = await ctx.store.get("multiply_value", 1)
        return MultiplyEvent(value=multiply_value)

    @step
    async def multiply_step(self, ctx: Context, ev: MultiplyEvent) -> StopEvent:
        """
        乘法步骤：最终计算
        """
        # 从 Context 读取当前结果
        result = await ctx.store.get("result")
        steps = await ctx.store.get("steps")

        # 执行乘法
        new_result = result * ev.value

        # 更新 Context
        await ctx.store.set("result", new_result)
        steps.append(f"乘 {ev.value}: {result} × {ev.value} = {new_result}")

        print(f"  ✖️  乘法: {result} × {ev.value} = {new_result}")
        print(f"\n  📋 计算过程:")
        for step in steps:
            print(f"     {step}")

        # 结束工作流
        return StopEvent(result=new_result)

    @step
    async def store_multiply_value(self, ctx: Context, ev: StartEvent) -> AddEvent:
        """
        改进版初始化：同时存储多个参数到 Context

        这个方法展示了另一种处理方式：
        先把所有参数存到 Context，后续步骤按需读取
        """
        initial_value = ev.get("value", 0)
        add_value = ev.get("add", 0)
        multiply_value = ev.get("multiply", 1)

        await ctx.store.set("result", initial_value)
        await ctx.store.set("multiply_value", multiply_value)
        await ctx.store.set("steps", [f"初始值: {initial_value}"])

        print(f"\n  📝 初始化: result = {initial_value}")

        return AddEvent(value=add_value)


async def demo_context_workflow():
    """运行使用 Context 的 Workflow"""
    print("\n💡 Context 像一个共享的笔记本，所有步骤都可以读写\n")
    print("计算: (10 + 5) × 3 = ?")

    workflow = CalculatorWorkflow()

    # 重写 initialize，使用改进版本
    workflow.initialize = workflow.store_multiply_value

    result = await workflow.run(value=10, add=5, multiply=3)

    print(f"\n✅ 最终结果: {result}")


# ==============================================================================
# 示例 4：条件分支 - 根据条件选择不同路径
# ==============================================================================

print("\n\n" + "="*80)
print("📚 示例 4: 条件分支 - 根据条件选择不同路径")
print("="*80)


@dataclass
class CheckEvent(Event):
    """检查事件"""
    value: int


@dataclass
class PositiveEvent(Event):
    """正数事件"""
    value: int


@dataclass
class NegativeEvent(Event):
    """负数事件"""
    value: int


class ConditionalWorkflow(Workflow):
    """
    条件分支工作流：根据输入走不同的处理路径

    流程：
        StartEvent -> check_value -> CheckEvent
                                  -> PositiveEvent -> handle_positive -> StopEvent
                                  -> NegativeEvent -> handle_negative -> StopEvent
    """

    @step
    async def check_value(self, ev: StartEvent) -> CheckEvent:
        """接收输入"""
        value = ev.get("value", 0)
        print(f"\n  🔍 检查输入: {value}")
        return CheckEvent(value=value)

    @step
    async def route_by_sign(
        self, ev: CheckEvent
    ) -> PositiveEvent | NegativeEvent:
        """
        路由步骤：根据值的正负返回不同的事件

        关键点：
        - 返回类型是联合类型（Union）
        - Workflow 会根据实际返回的事件类型，路由到对应的处理步骤
        """
        value = ev.value

        if value >= 0:
            print(f"  ➡️  路由: {value} 是正数，走正数处理路径")
            return PositiveEvent(value=value)
        else:
            print(f"  ➡️  路由: {value} 是负数，走负数处理路径")
            return NegativeEvent(value=value)

    @step
    async def handle_positive(self, ev: PositiveEvent) -> StopEvent:
        """处理正数"""
        result = f"✅ 正数: {ev.value} 的平方是 {ev.value ** 2}"
        print(f"  {result}")
        return StopEvent(result=result)

    @step
    async def handle_negative(self, ev: NegativeEvent) -> StopEvent:
        """处理负数"""
        result = f"⚠️  负数: {ev.value} 的绝对值是 {abs(ev.value)}"
        print(f"  {result}")
        return StopEvent(result=result)


async def demo_conditional_workflow():
    """运行条件分支 Workflow"""
    print("\n💡 根据输入的正负，走不同的处理路径\n")

    workflow = ConditionalWorkflow()

    print("测试 1: 正数")
    result1 = await workflow.run(value=5)
    print(f"结果: {result1}\n")

    print("测试 2: 负数")
    result2 = await workflow.run(value=-3)
    print(f"结果: {result2}")


# ==============================================================================
# 示例 5：循环处理 - 多次调用同一个步骤
# ==============================================================================

print("\n\n" + "="*80)
print("📚 示例 5: 循环处理 - 递归式的重复执行")
print("="*80)


@dataclass
class CountdownEvent(Event):
    """倒计时事件"""
    count: int


class CountdownWorkflow(Workflow):
    """
    倒计时工作流：演示如何实现循环

    流程：
        StartEvent -> start_countdown -> CountdownEvent -> countdown_step
                                                        -> CountdownEvent (循环)
                                                        -> StopEvent (结束)
    """

    @step
    async def start_countdown(self, ctx: Context, ev: StartEvent) -> CountdownEvent:
        """开始倒计时"""
        count = ev.get("count", 5)
        print(f"\n  🚀 开始倒计时，从 {count} 开始")

        await ctx.store.set("steps", [])

        return CountdownEvent(count=count)

    @step
    async def countdown_step(
        self, ctx: Context, ev: CountdownEvent
    ) -> CountdownEvent | StopEvent:
        """
        倒计时步骤：递归调用

        关键点：
        - 返回类型是 CountdownEvent | StopEvent
        - 如果返回 CountdownEvent，会再次调用这个函数（循环）
        - 如果返回 StopEvent，结束循环
        """
        count = ev.count
        steps = await ctx.store.get("steps")

        # 记录步骤
        steps.append(count)
        await ctx.store.set("steps", steps)

        print(f"  ⏱️  倒计时: {count}")

        # 模拟延迟
        await asyncio.sleep(0.3)

        if count > 0:
            # 继续倒计时（返回 CountdownEvent，触发循环）
            return CountdownEvent(count=count - 1)
        else:
            # 倒计时结束
            print(f"  🎉 倒计时结束！")
            return StopEvent(result=f"倒计时完成: {steps}")


async def demo_countdown_workflow():
    """运行倒计时 Workflow"""
    print("\n💡 通过返回相同类型的事件，实现循环处理\n")

    workflow = CountdownWorkflow()
    result = await workflow.run(count=5)

    print(f"\n✅ 最终结果: {result}")


# ==============================================================================
# 示例 6：真实场景 - 模拟 DroidRun 的 CodeActAgent
# ==============================================================================

print("\n\n" + "="*80)
print("📚 示例 6: 真实场景 - 模拟 DroidRun 的代码执行工作流")
print("="*80)


@dataclass
class TaskInputEvent(Event):
    """任务输入事件"""
    goal: str


@dataclass
class GenerateCodeEvent(Event):
    """生成代码事件"""
    code: str


@dataclass
class ExecuteCodeEvent(Event):
    """执行代码事件"""
    output: str


@dataclass
class TaskCompleteEvent(Event):
    """任务完成事件"""
    success: bool


class CodeActWorkflow(Workflow):
    """
    代码执行工作流：模拟 DroidRun 的 CodeActAgent

    这是一个接近真实项目的示例，展示了：
    - 多步骤协作
    - Context 使用
    - 条件循环
    - 最大步数限制

    流程：
        StartEvent -> prepare_task
                   -> TaskInputEvent -> generate_code
                   -> GenerateCodeEvent -> execute_code
                   -> ExecuteCodeEvent -> check_completion
                   -> TaskCompleteEvent -> StopEvent (完成)
                   -> TaskInputEvent (继续循环，最多 max_steps 次)
    """

    def __init__(self, max_steps: int = 3):
        super().__init__()
        self.max_steps = max_steps

    @step
    async def prepare_task(self, ctx: Context, ev: StartEvent) -> TaskInputEvent:
        """准备任务"""
        goal = ev.get("goal", "")

        print(f"\n  📋 任务目标: {goal}")

        # 初始化 Context
        await ctx.store.set("goal", goal)
        await ctx.store.set("step_count", 0)
        await ctx.store.set("completed", False)

        return TaskInputEvent(goal=goal)

    @step
    async def generate_code(
        self, ctx: Context, ev: TaskInputEvent
    ) -> GenerateCodeEvent:
        """生成代码（模拟 LLM 生成）"""
        step_count = await ctx.store.get("step_count")
        step_count += 1
        await ctx.store.set("step_count", step_count)

        print(f"\n  🤖 步骤 {step_count}: 生成代码...")

        # 模拟根据目标生成代码
        goal = ev.goal
        if "点击" in goal:
            code = "tap_by_index(1)"
        elif "输入" in goal:
            code = "input_text('hello')"
        else:
            code = "complete(success=True)"

        print(f"     生成的代码: {code}")

        return GenerateCodeEvent(code=code)

    @step
    async def execute_code(
        self, ctx: Context, ev: GenerateCodeEvent
    ) -> ExecuteCodeEvent:
        """执行代码"""
        code = ev.code

        print(f"  ⚙️  执行代码: {code}")

        # 模拟执行
        await asyncio.sleep(0.2)

        # 检查是否调用了 complete()
        if "complete" in code:
            await ctx.store.set("completed", True)
            output = "✅ 任务标记为完成"
        else:
            output = f"执行成功: {code}"

        print(f"     输出: {output}")

        return ExecuteCodeEvent(output=output)

    @step
    async def check_completion(
        self, ctx: Context, ev: ExecuteCodeEvent
    ) -> TaskCompleteEvent | TaskInputEvent:
        """
        检查是否完成

        这是循环控制的关键步骤：
        - 如果完成或达到最大步数，返回 TaskCompleteEvent -> 结束
        - 否则返回 TaskInputEvent -> 继续循环
        """
        completed = await ctx.store.get("completed")
        step_count = await ctx.store.get("step_count")
        goal = await ctx.store.get("goal")

        if completed:
            print(f"\n  ✅ 任务完成！共执行 {step_count} 步")
            return TaskCompleteEvent(success=True)
        elif step_count >= self.max_steps:
            print(f"\n  ⚠️  达到最大步数 ({self.max_steps})，停止执行")
            return TaskCompleteEvent(success=False)
        else:
            print(f"  🔄 继续执行下一步...")
            return TaskInputEvent(goal=goal)

    @step
    async def finalize(self, ctx: Context, ev: TaskCompleteEvent) -> StopEvent:
        """最终化：返回结果"""
        step_count = await ctx.store.get("step_count")
        goal = await ctx.store.get("goal")

        result = {
            "success": ev.success,
            "goal": goal,
            "steps": step_count
        }

        return StopEvent(result=result)


async def demo_codeact_workflow():
    """运行代码执行 Workflow"""
    print("\n💡 这是最接近 DroidRun 实际使用的例子\n")
    print("模拟场景: AI 助手尝试完成任务，最多执行 3 步")

    workflow = CodeActWorkflow(max_steps=3)

    print("\n测试 1: 会完成的任务")
    result1 = await workflow.run(goal="点击按钮并完成")
    print(f"\n结果: {result1}")

    print("\n" + "-"*80)
    print("\n测试 2: 达到最大步数的任务")
    result2 = await workflow.run(goal="点击按钮")
    print(f"\n结果: {result2}")


# ==============================================================================
# 主程序：运行所有示例
# ==============================================================================

async def main():
    """运行所有示例"""

    print("\n")
    print("🎓" * 40)
    print("\n        Workflow 使用教程 - 从入门到精通")
    print("        Learn Workflow Step by Step")
    print("\n" + "🎓" * 40)

    # 示例 1: 最简单的 Workflow
    await demo_simple_workflow()

    # 示例 2: 多步骤流水线
    await demo_pipeline_workflow()

    # 示例 3: 使用 Context
    await demo_context_workflow()

    # 示例 4: 条件分支
    await demo_conditional_workflow()

    # 示例 5: 循环处理
    await demo_countdown_workflow()

    # 示例 6: 真实场景
    await demo_codeact_workflow()

    # 总结
    print("\n\n" + "="*80)
    print("🎉 教程完成！")
    print("="*80)
    print("\n📚 你已经学会了 Workflow 的核心概念：")
    print("\n  1️⃣  基本结构")
    print("     - 继承 Workflow 类")
    print("     - 使用 @step 装饰器定义步骤")
    print("     - 通过 return Event 传递数据")
    print("\n  2️⃣  事件系统")
    print("     - StartEvent: 工作流入口")
    print("     - StopEvent: 工作流出口")
    print("     - 自定义 Event: 步骤间通信")
    print("\n  3️⃣  Context 使用")
    print("     - ctx.store.set(): 存储数据")
    print("     - ctx.store.get(): 读取数据")
    print("     - 在所有步骤间共享状态")
    print("\n  4️⃣  控制流")
    print("     - 条件分支: 返回不同类型的事件")
    print("     - 循环: 返回相同类型的事件")
    print("     - 最大步数限制")
    print("\n  5️⃣  真实应用")
    print("     - 多步骤协作")
    print("     - 状态管理")
    print("     - 错误处理")
    print("\n" + "="*80)
    print("\n💡 核心理解：")
    print("   Workflow = 流水线")
    print("   @step = 工位")
    print("   Event = 传递带（携带数据）")
    print("   Context = 共享记忆本")
    print("="*80 + "\n")

    print("\n📖 Workflow 的执行原理：")
    print("\n   1. 调用 workflow.run() 时，创建 StartEvent")
    print("   2. Workflow 查找接收 StartEvent 的 @step 函数")
    print("   3. 执行该函数，获取返回的 Event")
    print("   4. 查找接收这个 Event 的下一个 @step 函数")
    print("   5. 重复 3-4，直到返回 StopEvent")
    print("   6. 返回 StopEvent.result 作为最终结果")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # 运行教程
    asyncio.run(main())
