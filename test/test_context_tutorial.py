"""
Context 使用教程 - 像讲故事一样学习 Context

这个教程通过一个完整的"手机自动化任务"故事，展示 Context 的所有核心功能。

故事背景：
    我们要让 AI 助手完成一个任务：
    1. 打开淘宝 App
    2. 搜索"手机"
    3. 点击第一个商品
    4. 记录整个过程

在这个过程中，Context 扮演了"记忆本 + 对讲机"的角色。
"""

import asyncio
from typing import Optional, Any, Callable, List
from dataclasses import dataclass


# ==============================================================================
# 第一部分：Context 的模拟实现
# ==============================================================================

class AsyncStore:
    """
    异步字典 - Context 的"记忆本"

    就像一个笔记本，可以随时记录和查询信息。
    关键特点：
    1. 异步操作（await）- 不会阻塞其他任务
    2. 键值对存储 - 像字典一样使用
    3. 线程安全 - 多个任务同时访问不会出错
    """

    def __init__(self):
        self._data = {}  # 内部存储
        print("📔 记忆本已创建")

    async def set(self, key: str, value: Any):
        """
        记录信息到记忆本

        就像在笔记本上写：
        - 页码（key）："当前任务"
        - 内容（value）："搜索手机"
        """
        self._data[key] = value
        print(f"  ✍️  记录: {key} = {value}")

    async def get(self, key: str, default: Any = None) -> Any:
        """
        从记忆本查询信息

        就像翻开笔记本的某一页（key）查看内容。
        如果那一页不存在，返回默认值（default）。
        """
        value = self._data.get(key, default)
        print(f"  📖 查询: {key} -> {value}")
        return value

    async def has(self, key: str) -> bool:
        """检查记忆本中是否有某个记录"""
        exists = key in self._data
        print(f"  🔍 检查: {key} 存在吗? {exists}")
        return exists

    def get_all(self) -> dict:
        """查看记忆本的所有内容"""
        return self._data.copy()


@dataclass
class Event:
    """
    事件 - 通过"对讲机"发送的消息

    就像对讲机里说的话，可以通知外界发生了什么事。
    """
    name: str
    data: Any

    def __str__(self):
        return f"📡 {self.name}: {self.data}"


class Context:
    """
    Context - AI 助手的"工具包"

    包含：
    1. 记忆本（store）- 存储任务过程中的信息
    2. 对讲机（write_event_to_stream）- 向外界发送实时消息
    3. 会话ID（session_id）- 区分不同的任务会话

    就像给 AI 助手配备了：
    - 一个笔记本：记住做过的事
    - 一个对讲机：随时报告进度
    - 一个身份证：知道自己在处理哪个任务
    """

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.store = AsyncStore()
        self._event_listeners: List[Callable] = []

        print(f"\n🎒 为会话 [{session_id}] 准备工具包")
        print(f"   - 记忆本: ✅")
        print(f"   - 对讲机: ✅")

    def write_event_to_stream(self, event: Event):
        """
        通过对讲机发送消息

        就像 AI 助手拿起对讲机说：
        "我已经点击了第一个商品！"

        所有监听对讲机的人都能听到这个消息。
        """
        print(f"\n  📻 对讲机广播: {event}")

        # 通知所有监听者
        for listener in self._event_listeners:
            listener(event)

    def add_event_listener(self, listener: Callable):
        """添加事件监听器（有人在听对讲机）"""
        self._event_listeners.append(listener)


# ==============================================================================
# 第二部分：故事开始 - 模拟 AI 助手的工作流程
# ==============================================================================

class PhoneAutomationTask:
    """
    手机自动化任务 - 我们的故事主角

    这个类模拟了 DroidRun 中的 CodeActAgent，
    展示如何在多个步骤之间使用 Context 共享信息。
    """

    def __init__(self, ctx: Context):
        self.ctx = ctx
        print(f"\n🤖 AI 助手已就位，工具包ID: {ctx.session_id}")

    async def run(self):
        """
        执行完整任务

        这就像 AI 助手接到任务后，一步步执行的过程。
        每一步都会：
        1. 使用记忆本（ctx.store）记录信息
        2. 通过对讲机（write_event_to_stream）报告进度
        """
        print("\n" + "="*80)
        print("📖 故事开始：AI 助手要帮我在淘宝上搜索手机")
        print("="*80)

        await self.step1_initialize()
        await self.step2_open_app()
        await self.step3_search()
        await self.step4_click_product()
        await self.step5_summary()

        print("\n" + "="*80)
        print("✅ 故事结束：任务圆满完成！")
        print("="*80)

    async def step1_initialize(self):
        """
        步骤1：初始化 - 记录任务目标

        就像开始做事前，先在笔记本上写下"今天要干什么"。
        """
        print("\n" + "-"*80)
        print("📍 步骤 1: 初始化任务")
        print("-"*80)

        # 功能1：使用 Context 存储任务信息
        await self.ctx.store.set("goal", "搜索手机并查看第一个商品")
        await self.ctx.store.set("current_step", 1)
        await self.ctx.store.set("steps_completed", [])
        await self.ctx.store.set("errors", [])

        # 功能2：发送初始化事件
        self.ctx.write_event_to_stream(
            Event("task_started", {"goal": "搜索手机"})
        )

        print("\n💭 AI 助手心里想：好的，我知道要做什么了，记在本子上！")

    async def step2_open_app(self):
        """
        步骤2：打开淘宝 App

        AI 助手开始行动，同时记录进度。
        """
        print("\n" + "-"*80)
        print("📍 步骤 2: 打开淘宝 App")
        print("-"*80)

        # 读取当前进度
        current_step = await self.ctx.store.get("current_step")
        print(f"\n💭 AI 助手翻开笔记本：现在是第 {current_step} 步")

        # 模拟打开 App
        print("\n⚙️  正在执行: 点击淘宝图标...")
        await asyncio.sleep(0.5)  # 模拟耗时操作

        # 记录执行结果
        steps_completed = await self.ctx.store.get("steps_completed")
        steps_completed.append("opened_taobao")
        await self.ctx.store.set("steps_completed", steps_completed)

        # 更新当前步骤
        await self.ctx.store.set("current_step", 2)

        # 记录 App 状态
        await self.ctx.store.set("current_app", "com.taobao.taobao")
        await self.ctx.store.set("app_screen", "首页")

        # 发送事件
        self.ctx.write_event_to_stream(
            Event("app_opened", {"app_name": "淘宝"})
        )

        print("\n💭 AI 助手拿起对讲机：报告！淘宝已打开！")

    async def step3_search(self):
        """
        步骤3：搜索"手机"

        展示如何在步骤之间传递数据。
        """
        print("\n" + "-"*80)
        print("📍 步骤 3: 搜索商品")
        print("-"*80)

        # 功能3：检查前置条件（从 Context 读取）
        current_app = await self.ctx.store.get("current_app")

        if current_app != "com.taobao.taobao":
            print("❌ 错误：淘宝还没打开！")
            errors = await self.ctx.store.get("errors")
            errors.append("app_not_opened")
            await self.ctx.store.set("errors", errors)
            return

        print(f"\n✅ 前置条件检查通过：当前在 {current_app}")

        # 模拟搜索操作
        search_keyword = "手机"
        print(f"\n⚙️  正在执行: 在搜索框输入 '{search_keyword}'...")
        await asyncio.sleep(0.5)

        # 记录搜索信息
        await self.ctx.store.set("search_keyword", search_keyword)
        await self.ctx.store.set("search_results_count", 100)
        await self.ctx.store.set("app_screen", "搜索结果页")

        # 更新进度
        current_step = await self.ctx.store.get("current_step")
        await self.ctx.store.set("current_step", current_step + 1)

        steps_completed = await self.ctx.store.get("steps_completed")
        steps_completed.append("searched_product")
        await self.ctx.store.set("steps_completed", steps_completed)

        # 发送事件
        self.ctx.write_event_to_stream(
            Event("search_completed", {
                "keyword": search_keyword,
                "results": 100
            })
        )

        print(f"\n💭 AI 助手记在本子上：搜索 '{search_keyword}'，找到 100 个结果")

    async def step4_click_product(self):
        """
        步骤4：点击第一个商品

        展示如何使用 Context 中存储的信息做决策。
        """
        print("\n" + "-"*80)
        print("📍 步骤 4: 点击第一个商品")
        print("-"*80)

        # 功能4：基于 Context 中的信息做决策
        search_results_count = await self.ctx.store.get("search_results_count")

        if search_results_count == 0:
            print("❌ 没有搜索结果，无法点击商品")
            return

        print(f"\n💭 AI 助手查看笔记：有 {search_results_count} 个商品可以点击")

        # 模拟点击操作
        product_index = 1
        print(f"\n⚙️  正在执行: 点击第 {product_index} 个商品...")
        await asyncio.sleep(0.5)

        # 记录点击信息
        await self.ctx.store.set("clicked_product_index", product_index)
        await self.ctx.store.set("clicked_product_title", "Apple iPhone 15 Pro Max")
        await self.ctx.store.set("app_screen", "商品详情页")

        # 更新进度
        current_step = await self.ctx.store.get("current_step")
        await self.ctx.store.set("current_step", current_step + 1)

        steps_completed = await self.ctx.store.get("steps_completed")
        steps_completed.append("clicked_product")
        await self.ctx.store.set("steps_completed", steps_completed)

        # 发送事件
        self.ctx.write_event_to_stream(
            Event("product_clicked", {
                "index": product_index,
                "title": "Apple iPhone 15 Pro Max"
            })
        )

        print("\n💭 AI 助手拿起对讲机：已点击第 1 个商品！")

    async def step5_summary(self):
        """
        步骤5：任务总结

        展示如何查看 Context 中的所有信息。
        """
        print("\n" + "-"*80)
        print("📍 步骤 5: 任务总结")
        print("-"*80)

        # 功能5：读取所有记录的信息
        print("\n📊 AI 助手翻开笔记本，回顾整个过程：\n")

        goal = await self.ctx.store.get("goal")
        print(f"  🎯 任务目标: {goal}")

        steps_completed = await self.ctx.store.get("steps_completed")
        print(f"  ✅ 完成步骤: {' -> '.join(steps_completed)}")

        search_keyword = await self.ctx.store.get("search_keyword")
        print(f"  🔍 搜索关键词: {search_keyword}")

        clicked_product = await self.ctx.store.get("clicked_product_title")
        print(f"  📱 点击商品: {clicked_product}")

        current_screen = await self.ctx.store.get("app_screen")
        print(f"  📍 当前页面: {current_screen}")

        errors = await self.ctx.store.get("errors")
        if errors:
            print(f"  ⚠️  错误记录: {errors}")
        else:
            print(f"  ✨ 无错误，完美执行！")

        # 发送完成事件
        self.ctx.write_event_to_stream(
            Event("task_completed", {
                "success": True,
                "steps": len(steps_completed)
            })
        )

        # 功能6：查看记忆本的全部内容
        print("\n" + "-"*80)
        print("📔 记忆本的完整内容（Context.store 的所有数据）：")
        print("-"*80)
        all_data = self.ctx.store.get_all()
        for key, value in all_data.items():
            print(f"  {key}: {value}")


# ==============================================================================
# 第三部分：高级用法 - 多会话并发
# ==============================================================================

async def demo_concurrent_sessions():
    """
    演示：多个 AI 助手同时工作，各自有独立的 Context

    就像有两个 AI 助手，一个帮你买手机，一个帮你买电脑。
    他们各自有自己的笔记本，互不干扰。
    """
    print("\n\n" + "="*80)
    print("🎭 高级演示：两个 AI 助手同时工作")
    print("="*80)

    # 创建两个独立的 Context
    ctx1 = Context(session_id="任务A-买手机")
    ctx2 = Context(session_id="任务B-买电脑")

    # 两个助手同时开始记录信息
    print("\n📝 两个助手各自记录任务...")
    await ctx1.store.set("goal", "搜索手机")
    await ctx2.store.set("goal", "搜索电脑")

    # 验证数据隔离
    print("\n🔍 验证：两个助手的记忆本是独立的")
    goal1 = await ctx1.store.get("goal")
    goal2 = await ctx2.store.get("goal")

    print(f"\n  助手A 的任务: {goal1}")
    print(f"  助手B 的任务: {goal2}")
    print(f"\n  ✅ 确认：两个助手的记忆本互不干扰！")


# ==============================================================================
# 第四部分：事件监听 - 对讲机的完整用法
# ==============================================================================

def create_event_logger():
    """
    创建事件监听器

    就像有人在监听对讲机，听到消息就记录下来。
    """
    events_received = []

    def on_event(event: Event):
        """监听到事件时的处理函数"""
        events_received.append(event)
        print(f"    👂 监听器收到: {event}")

    return on_event, events_received


async def demo_event_system():
    """
    演示：完整的事件系统

    展示如何监听 AI 助手通过对讲机发送的所有消息。
    """
    print("\n\n" + "="*80)
    print("📡 事件系统演示：监听 AI 助手的所有报告")
    print("="*80)

    # 创建 Context 和监听器
    ctx = Context(session_id="事件演示")
    event_logger, events_received = create_event_logger()
    ctx.add_event_listener(event_logger)

    print("\n👂 监听器已就位，开始监听...")

    # 模拟发送几个事件
    print("\n🤖 AI 助手开始工作，发送实时报告：")
    ctx.write_event_to_stream(Event("started", "任务开始"))
    ctx.write_event_to_stream(Event("progress", "完成 50%"))
    ctx.write_event_to_stream(Event("completed", "任务完成"))

    # 显示收到的所有事件
    print(f"\n📊 统计：共收到 {len(events_received)} 个事件")
    print("\n📋 事件列表：")
    for i, event in enumerate(events_received, 1):
        print(f"  {i}. {event}")


# ==============================================================================
# 第五部分：实用场景 - Context 的典型用法
# ==============================================================================

async def demo_practical_patterns():
    """
    演示：Context 在实际项目中的典型使用模式
    """
    print("\n\n" + "="*80)
    print("💡 实用模式：Context 的经典用法")
    print("="*80)

    ctx = Context(session_id="实用演示")

    # 模式1：计数器模式
    print("\n📌 模式 1: 计数器（追踪执行次数）")
    print("-"*80)
    await ctx.store.set("attempt_count", 0)

    for i in range(3):
        count = await ctx.store.get("attempt_count")
        count += 1
        await ctx.store.set("attempt_count", count)
        print(f"  第 {count} 次尝试...")

    # 模式2：状态机模式
    print("\n📌 模式 2: 状态机（追踪任务状态）")
    print("-"*80)
    states = ["idle", "running", "paused", "completed"]

    for state in states:
        await ctx.store.set("task_state", state)
        current_state = await ctx.store.get("task_state")
        print(f"  任务状态: {current_state}")

    # 模式3：历史记录模式
    print("\n📌 模式 3: 历史记录（追踪操作历史）")
    print("-"*80)
    await ctx.store.set("action_history", [])

    actions = ["打开App", "搜索商品", "点击商品"]
    for action in actions:
        history = await ctx.store.get("action_history")
        history.append(action)
        await ctx.store.set("action_history", history)
        print(f"  已执行: {' -> '.join(history)}")

    # 模式4：错误处理模式
    print("\n📌 模式 4: 错误处理（记录和检查错误）")
    print("-"*80)
    await ctx.store.set("has_error", False)
    await ctx.store.set("error_message", None)

    # 模拟出错
    try:
        # 假设这里发生了错误
        raise ValueError("网络连接失败")
    except Exception as e:
        await ctx.store.set("has_error", True)
        await ctx.store.set("error_message", str(e))
        print(f"  ❌ 错误已记录: {e}")

    # 检查错误
    has_error = await ctx.store.get("has_error")
    if has_error:
        error_msg = await ctx.store.get("error_message")
        print(f"  ⚠️  发现错误: {error_msg}")

    # 模式5：条件检查模式
    print("\n📌 模式 5: 前置条件检查")
    print("-"*80)
    await ctx.store.set("app_opened", True)
    await ctx.store.set("logged_in", False)

    # 检查前置条件
    app_opened = await ctx.store.get("app_opened")
    logged_in = await ctx.store.get("logged_in")

    if app_opened and logged_in:
        print("  ✅ 可以继续执行任务")
    else:
        print(f"  ⚠️  前置条件不满足:")
        print(f"     - App 已打开: {app_opened}")
        print(f"     - 已登录: {logged_in}")


# ==============================================================================
# 第六部分：对比展示 - 有无 Context 的区别
# ==============================================================================

async def demo_without_context():
    """反面教材：不使用 Context 的混乱代码"""
    print("\n\n" + "="*80)
    print("❌ 反面教材：不使用 Context 会怎样？")
    print("="*80)

    # 使用全局变量（不好的做法）
    global_state = {
        "goal": None,
        "current_step": 0,
        "errors": []
    }

    print("\n😰 问题：")
    print("  1. 全局变量容易被意外修改")
    print("  2. 多任务并发时会相互干扰")
    print("  3. 难以追踪数据来源")
    print("  4. 没有异步支持，可能阻塞")

    print("\n💡 使用 Context 的优势：")
    print("  ✅ 数据隔离（每个任务独立）")
    print("  ✅ 异步安全（不会阻塞）")
    print("  ✅ 清晰明确（知道数据在哪）")
    print("  ✅ 事件通信（实时反馈）")


# ==============================================================================
# 主程序：运行所有演示
# ==============================================================================

async def main():
    """主程序：依次运行所有演示"""

    print("\n")
    print("🎓" * 40)
    print("\n        Context 使用教程 - 从入门到精通")
    print("        Learn Context Like a Story")
    print("\n" + "🎓" * 40)

    # 1. 基础故事：完整的任务流程
    ctx = Context(session_id="主故事")
    task = PhoneAutomationTask(ctx)
    await task.run()

    # 2. 高级演示：并发会话
    await demo_concurrent_sessions()

    # 3. 事件系统演示
    await demo_event_system()

    # 4. 实用模式演示
    await demo_practical_patterns()

    # 5. 对比演示
    await demo_without_context()

    # 总结
    print("\n\n" + "="*80)
    print("🎉 教程完成！")
    print("="*80)
    print("\n📚 你已经学会了 Context 的所有核心功能：")
    print("\n  1️⃣  异步字典（ctx.store）")
    print("     - set(): 存储数据")
    print("     - get(): 读取数据")
    print("     - has(): 检查存在")
    print("\n  2️⃣  事件通信（write_event_to_stream）")
    print("     - 发送实时消息")
    print("     - 监听器接收")
    print("\n  3️⃣  会话隔离")
    print("     - 每个任务独立的 Context")
    print("     - 并发安全")
    print("\n  4️⃣  实用模式")
    print("     - 计数器")
    print("     - 状态机")
    print("     - 历史记录")
    print("     - 错误处理")
    print("     - 条件检查")
    print("\n" + "="*80)
    print("\n💡 记住：Context = 记忆本 + 对讲机 + 身份证")
    print("="*80 + "\n")


if __name__ == "__main__":
    # 运行教程
    asyncio.run(main())
