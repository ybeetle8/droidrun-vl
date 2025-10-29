"""
批量任务执行器 - 基于命令行调用实现批量自动化任务

使用方法:
    python batch_runner2.py tasks.json
    python batch_runner2.py --config config.json --tasks tasks.json
"""

import asyncio
import json
import logging
import sys
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("batch-runner2")


class BatchTaskRunner:
    """批量任务执行器 - 基于命令行调用"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化批量任务执行器

        Args:
            config: 配置字典，包含 LLM 配置、设备配置等
        """
        self.config = config
        self.results = []
        self.loop_results = []  # 存储每轮循环的结果

    def initialize(self):
        """初始化批量任务执行器"""
        logger.info("🚀 初始化批量任务执行器...")
        logger.info("✅ 初始化完成")

    def build_command(self, task: Dict[str, Any]) -> List[str]:
        """
        构建 droidrun 命令

        Args:
            task: 任务配置字典

        Returns:
            命令列表
        """
        command = task.get("command")

        # 基础命令
        cmd = [
            "uv", "run", "droidrun",
            "--provider", self.config.get("provider", "Ollama"),
            "--model", self.config.get("model", "qwen3-coder:30b"),
            "--base_url", self.config.get("base_url", "http://localhost:11434")
        ]

        # # 添加可选参数
        # if self.config.get("temperature"):
        #     cmd.extend(["--temperature", str(self.config.get("temperature"))])

        # # 设备参数 (只有在明确指定设备时才添加)
        # device = self.config.get("device")
        # if device and device != "null":
        #     cmd.extend(["--device", device])

        # TCP 连接
        if self.config.get("use_tcp", False):
            cmd.append("--use-tcp")

        # # 任务配置
        # max_steps = task.get("steps", self.config.get("steps", 15))
        # cmd.extend(["--steps", str(max_steps)])

        # # Vision 模式
        # vision = task.get("vision", self.config.get("vision", True))
        # if vision:
        #     cmd.append("--vision")

        # Reasoning 模式
        reasoning = task.get("reasoning", self.config.get("reasoning", False))
        if reasoning:
            cmd.append("--reasoning")

        # Reflection 模式
        reflection = task.get("reflection", self.config.get("reflection", False))
        if reflection:
            cmd.append("--reflection")

        # Debug 模式
        if self.config.get("debug", False):
            cmd.append("--debug")

        # Tracing
        if self.config.get("enable_tracing", False):
            cmd.append("--tracing")

        # Save trajectory
        save_trajectory = task.get("save_trajectory", self.config.get("save_trajectory", "none"))
        if save_trajectory != "none":
            cmd.extend(["--save-trajectories", save_trajectory])

        # Allow drag
        allow_drag = task.get("allow_drag", self.config.get("allow_drag", False))
        if allow_drag:
            cmd.append("--allow-drag")

        # 添加命令文本
        cmd.append(command)

        return cmd

    async def run_task(self, task: Dict[str, Any], task_index: int) -> Dict[str, Any]:
        """
        执行单个任务

        Args:
            task: 任务配置字典
            task_index: 任务序号

        Returns:
            任务执行结果
        """
        task_name = task.get("name", f"任务 {task_index + 1}")
        command = task.get("command")

        if not command:
            return {
                "task": task_name,
                "success": False,
                "error": "Missing command field"
            }

        logger.info(f"\n{'='*60}")
        logger.info(f"📍 [{task_index + 1}] 开始执行: {task_name}")
        logger.info(f"📝 命令: {command}")
        logger.info(f"{'='*60}")

        start_time = datetime.now()

        try:
            # 构建命令
            cmd = self.build_command(task)

            # 打印命令
            cmd_str = ' '.join(cmd)
            logger.info(f"🚀 执行命令: {cmd_str}")

            # 执行命令 - 直接继承标准输出，避免管道缓冲区阻塞
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=None,  # 继承父进程的 stdout
                stderr=None   # 继承父进程的 stderr
            )

            # 等待命令完成
            await process.wait()

            # 确保进程完全终止
            try:
                process.terminate()
                await asyncio.sleep(0.1)
            except:
                pass

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 判断执行结果
            success = process.returncode == 0

            if success:
                logger.info(f"✅ 任务完成: {task_name} (耗时: {duration:.1f}秒)")
            else:
                logger.error(f"❌ 任务失败: {task_name} (返回码: {process.returncode}, 耗时: {duration:.1f}秒)")

            # 任务间延迟 - 额外增加等待时间确保资源释放
            wait_after = task.get("wait_after", self.config.get("delay", 2))
            # 至少等待 3 秒，让 Ollama 释放资源
            actual_wait = max(wait_after, 3)
            if actual_wait > 0:
                logger.info(f"⏳ 等待 {actual_wait} 秒（确保资源释放）...")
                await asyncio.sleep(actual_wait)

            # 错误处理策略
            if not success:
                on_error = task.get("on_error", self.config.get("on_error", "continue"))

                if on_error == "stop":
                    logger.error("🛑 遇到错误，停止执行后续任务")
                    raise Exception(f"Task failed with return code {process.returncode}")
                elif on_error == "retry":
                    retry_count = task.get("retry", 1)
                    logger.info(f"🔄 重试任务 (剩余 {retry_count} 次)")
                    if retry_count > 0:
                        task["retry"] = retry_count - 1
                        await asyncio.sleep(2)
                        return await self.run_task(task, task_index)

            return {
                "task": task_name,
                "command": command,
                "success": success,
                "duration": duration,
                "return_code": process.returncode
            }

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"❌ 任务失败: {task_name} - {e}")

            return {
                "task": task_name,
                "command": command,
                "success": False,
                "duration": duration,
                "error": str(e)
            }

    async def run_tasks(self, tasks: List[Dict[str, Any]]):
        """
        执行任务列表（支持循环执行）

        Args:
            tasks: 任务列表
        """
        # 获取循环配置
        loop_count = self.config.get("loop_count", 1)  # 默认执行 1 次
        loop_delay = self.config.get("loop_delay", 5)  # 循环间隔，默认 5 秒
        infinite_loop = self.config.get("infinite_loop", False)  # 是否无限循环

        total_tasks = len(tasks)

        if infinite_loop:
            logger.info(f"\n🔄 开始无限循环执行批量任务，共 {total_tasks} 个任务")
            logger.info(f"⚠️  按 Ctrl+C 停止执行\n")
        else:
            logger.info(f"\n🔄 开始循环执行批量任务，共 {total_tasks} 个任务，循环 {loop_count} 次\n")

        loop_index = 0
        try:
            while True:
                loop_index += 1

                # 检查是否达到循环次数
                if not infinite_loop and loop_index > loop_count:
                    break

                logger.info(f"\n{'='*60}")
                logger.info(f"🔁 第 {loop_index} 轮循环开始" + (f" (共 {loop_count} 轮)" if not infinite_loop else ""))
                logger.info(f"{'='*60}\n")

                # 清空当前轮次结果
                self.results = []

                # 执行所有任务
                for i, task in enumerate(tasks):
                    result = await self.run_task(task, i)
                    self.results.append(result)

                # 保存当前轮次结果
                loop_result = {
                    "loop_index": loop_index,
                    "tasks": self.results.copy(),
                    "timestamp": datetime.now().isoformat()
                }
                self.loop_results.append(loop_result)

                # 输出当前轮次汇总
                self.print_loop_summary(loop_index)

                # 检查是否继续循环
                if not infinite_loop and loop_index >= loop_count:
                    break

                # 循环间隔
                if loop_delay > 0:
                    logger.info(f"\n⏳ 等待 {loop_delay} 秒后开始下一轮循环...")
                    await asyncio.sleep(loop_delay)

        except KeyboardInterrupt:
            logger.info(f"\n\n⚠️  用户中断执行（已完成 {loop_index} 轮循环）")

        # 输出总汇总
        self.print_final_summary()

    def print_loop_summary(self, loop_index: int):
        """打印单次循环汇总"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 第 {loop_index} 轮循环汇总")
        logger.info(f"{'='*60}")

        total = len(self.results)
        success = sum(1 for r in self.results if r.get("success"))
        failed = total - success

        logger.info(f"任务数: {total}")
        logger.info(f"成功: {success} ✅")
        logger.info(f"失败: {failed} ❌")

        if self.results:
            total_duration = sum(r.get("duration", 0) for r in self.results)
            logger.info(f"耗时: {total_duration:.1f}秒")

        logger.info(f"\n详细结果:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result.get("success") else "❌"
            task_name = result.get("task", f"任务 {i}")
            duration = result.get("duration", 0)
            logger.info(f"  {status} [{i}] {task_name} ({duration:.1f}秒)")
            if not result.get("success"):
                logger.info(f"      错误: {result.get('error', 'Unknown')}")

        logger.info(f"{'='*60}")

    def print_final_summary(self):
        """打印最终汇总（所有循环）"""
        if not self.loop_results:
            return

        logger.info(f"\n\n{'='*60}")
        logger.info("🎯 最终汇总（所有循环）")
        logger.info(f"{'='*60}")

        total_loops = len(self.loop_results)
        logger.info(f"完成循环数: {total_loops}")

        # 统计所有循环的任务结果
        all_tasks = []
        for loop_result in self.loop_results:
            all_tasks.extend(loop_result["tasks"])

        total_tasks = len(all_tasks)
        success_tasks = sum(1 for t in all_tasks if t.get("success"))
        failed_tasks = total_tasks - success_tasks
        total_duration = sum(t.get("duration", 0) for t in all_tasks)

        logger.info(f"总任务执行次数: {total_tasks}")
        logger.info(f"成功: {success_tasks} ✅")
        logger.info(f"失败: {failed_tasks} ❌")
        logger.info(f"总耗时: {total_duration:.1f}秒")

        # 每轮循环的统计
        logger.info(f"\n每轮循环统计:")
        for loop_result in self.loop_results:
            loop_idx = loop_result["loop_index"]
            tasks = loop_result["tasks"]
            success = sum(1 for t in tasks if t.get("success"))
            total = len(tasks)
            duration = sum(t.get("duration", 0) for t in tasks)

            status_symbol = "✅" if success == total else ("⚠️" if success > 0 else "❌")
            logger.info(f"  {status_symbol} 第 {loop_idx} 轮: {success}/{total} 成功 ({duration:.1f}秒)")

        logger.info(f"{'='*60}\n")

        # 保存结果
        if self.config.get("save_results"):
            self.save_results()

    def save_results(self):
        """保存执行结果到文件"""
        output_file = self.config.get("output_file", "batch_results.json")

        # 如果有循环结果，保存循环结果；否则保存单次结果
        if self.loop_results:
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "total_loops": len(self.loop_results),
                "loop_results": self.loop_results
            }
        else:
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "results": self.results
            }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 结果已保存到: {output_file}")


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件"""
    if config_file and Path(config_file).exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # 默认配置 (参考 run_ollama.bat)
    return {
        "provider": "Ollama",
        "model": "qwen3-coder:30b",
        "base_url": "http://localhost:11434",
        "temperature": 0.2,
        "device": None,
        "use_tcp": False,
        "vision": True,
        "reasoning": False,
        "reflection": False,
        "steps": 15,
        "delay": 2,
        "on_error": "continue",
        "save_results": True,
        "debug": False,
        # 循环执行配置
        "loop_count": 1,        # 循环执行次数，默认 1 次（不循环）
        "loop_delay": 5,        # 循环间隔时间（秒），默认 5 秒
        "infinite_loop": False  # 是否无限循环，默认 False
    }


def load_tasks(tasks_file: str) -> List[Dict[str, Any]]:
    """加载任务文件"""
    with open(tasks_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 支持两种格式
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "tasks" in data:
        return data["tasks"]
    else:
        raise ValueError("Invalid tasks file format")


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python batch_runner2.py tasks.json")
        print("  python batch_runner2.py --config config.json --tasks tasks.json")
        sys.exit(1)

    # 解析参数
    config_file = None
    tasks_file = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--config":
            if i + 1 < len(sys.argv):
                config_file = sys.argv[i + 1]
                i += 2
            else:
                print("错误: --config 需要指定配置文件路径")
                sys.exit(1)
        elif arg == "--tasks":
            if i + 1 < len(sys.argv):
                tasks_file = sys.argv[i + 1]
                i += 2
            else:
                print("错误: --tasks 需要指定任务文件路径")
                sys.exit(1)
        elif not arg.startswith("--"):
            # 不是选项参数，当作任务文件
            if tasks_file is None:
                tasks_file = arg
            i += 1
        else:
            print(f"错误: 未知参数 {arg}")
            sys.exit(1)

    if not tasks_file:
        print("错误: 未指定任务文件")
        sys.exit(1)

    # 加载配置和任务
    config = load_config(config_file)
    tasks = load_tasks(tasks_file)

    # 执行任务
    runner = BatchTaskRunner(config)
    runner.initialize()
    await runner.run_tasks(tasks)


if __name__ == "__main__":
    asyncio.run(main())
