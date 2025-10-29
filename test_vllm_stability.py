"""
测试 vLLM 服务稳定性
每次都新启会话,不停询问问题,无限循环
"""
import os
import time
import random
from datetime import datetime
from typing import List, Optional

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-Kd92LE2pud8bVtZE23B47248Bc064006Af400cB6770c8577"

from droidrun.agent.utils.llm_picker import load_llm

# 测试问题列表 - 更复杂的问题
TEST_QUESTIONS: List[str] = [
    "请详细解释深度学习中的反向传播算法,包括链式法则的应用、梯度消失和梯度爆炸问题,以及如何通过批归一化、残差连接等技术来缓解这些问题。请用数学公式和代码示例说明。",
    "设计一个高并发的分布式缓存系统,需要考虑缓存一致性、缓存穿透、缓存雪崩、缓存击穿等问题。请详细说明架构设计、数据分片策略、一致性哈希算法的实现、以及如何保证高可用性。",
    "请实现一个完整的二叉搜索树,包括插入、删除、查找、中序遍历、前序遍历、后序遍历、层序遍历、查找最小值、查找最大值、查找前驱节点、查找后继节点等操作。要求代码有完整的注释和时间复杂度分析。",
    "解释现代操作系统中的内存管理机制,包括虚拟内存、分页、分段、页面置换算法(FIFO、LRU、LFU、Clock)、内存映射文件、写时复制(Copy-on-Write)等。并说明Linux内核是如何实现这些机制的。",
    "请设计并实现一个分布式事务解决方案,对比2PC、3PC、TCC、Saga等不同模式的优缺点。详细说明在微服务架构下如何保证数据一致性,以及如何处理网络分区、节点故障等异常情况。",
    "详细解释TCP协议的拥塞控制机制,包括慢启动、拥塞避免、快速重传、快速恢复算法。说明TCP如何通过滑动窗口、累积确认、选择性确认(SACK)来提高传输效率。并对比TCP Reno、TCP Vegas、TCP BBR等不同变种。",
    "请实现一个支持事务的键值存储引擎,需要实现MVCC(多版本并发控制)、WAL(预写日志)、LSM树或B+树存储结构、Compaction压缩策略、崩溃恢复机制。要求代码结构清晰,并说明每个模块的设计思路。",
    "深入解释Java虚拟机的垃圾回收机制,包括标记-清除、标记-整理、复制算法、分代回收策略。详细说明Serial、ParNew、Parallel Scavenge、CMS、G1、ZGC等不同垃圾回收器的工作原理、适用场景和调优参数。",
    "设计一个高性能的全文搜索引擎,需要实现倒排索引、TF-IDF算法、BM25算法、向量空间模型、布尔检索、短语查询、模糊查询、拼写纠错、查询建议等功能。说明如何优化索引构建和查询性能。",
    "请详细解释Raft共识算法的工作原理,包括领导者选举、日志复制、安全性保证、集群成员变更、日志压缩等机制。对比Paxos算法的异同,并说明在实际工程中如何实现一个高可用的Raft集群。",
    "实现一个支持多种路由策略的API网关,包括负载均衡(轮询、随机、最小连接数、一致性哈希)、熔断、限流、重试、超时控制、服务发现、健康检查、动态配置更新等功能。要求支持热更新而不影响现有连接。",
    "深入解释现代编译器的工作原理,包括词法分析、语法分析、语义分析、中间代码生成、代码优化(常量折叠、死代码消除、循环优化、内联等)、目标代码生成。并实现一个简单的表达式解析器和求值器。",
    "设计一个分布式任务调度系统,需要支持定时任务、依赖任务、失败重试、任务优先级、资源隔离、任务监控、动态扩缩容等功能。说明如何保证任务不被重复执行,以及如何处理调度器节点故障。",
    "请详细解释深度学习中的注意力机制和Transformer架构,包括自注意力、多头注意力、位置编码、前馈网络、残差连接、层归一化等。说明BERT、GPT、T5等预训练模型的区别,以及如何进行微调和推理优化。",
    "实现一个高性能的消息队列系统,需要支持持久化、消息确认、消息重试、死信队列、延迟队列、消息过滤、消息追踪、事务消息等功能。说明如何保证消息不丢失、不重复、顺序性,以及如何优化吞吐量和延迟。",
    "深入解释数据库查询优化器的工作原理,包括查询重写、索引选择、连接算法(嵌套循环、哈希连接、归并连接)、代价估算、统计信息、执行计划生成等。并说明如何分析和优化慢查询。",
    "设计一个支持实时数据处理的流式计算框架,需要实现窗口操作(滚动窗口、滑动窗口、会话窗口)、水位线机制、状态管理、Exactly-Once语义、反压机制、容错恢复等功能。对比Flink、Spark Streaming、Storm的优缺点。",
    "请实现一个支持动态代理和AOP的IoC容器,需要支持构造器注入、属性注入、方法注入、循环依赖检测、Bean生命周期管理、作用域管理(单例、原型)、条件装配、配置属性绑定等功能。说明Spring的实现原理。",
    "深入解释密码学中的非对称加密算法,包括RSA、ECC、ElGamal、DSA等。详细说明密钥生成、加密、解密、数字签名、密钥交换的数学原理。并说明如何在TLS/SSL中应用这些算法,以及量子计算对密码学的威胁。",
    "设计一个支持多租户的云原生应用平台,需要实现资源隔离、配额管理、弹性伸缩、服务网格、可观测性(日志、指标、追踪)、持续部署、灰度发布、故障注入测试等功能。说明如何基于Kubernetes构建这样的平台。",
]


def calculate_token_speed(
    response_length: int,
    time_taken: float,
    avg_chars_per_token: float = 2.5
) -> tuple[int, float]:
    """
    计算 token 速度

    Args:
        response_length: 响应字符数
        time_taken: 耗时(秒)
        avg_chars_per_token: 平均每个token的字符数(中文约2-3,英文约4)

    Returns:
        (估计的token数, tokens/秒)
    """
    estimated_tokens = int(response_length / avg_chars_per_token)
    tokens_per_second = estimated_tokens / time_taken if time_taken > 0 else 0
    return estimated_tokens, tokens_per_second


def test_single_session(
    session_id: int,
    api_base: str,
    model: str,
    timeout: float = 120.0
) -> dict:
    """
    测试单个会话

    Args:
        session_id: 会话编号
        api_base: API 基础 URL
        model: 模型名称
        timeout: 超时时间(秒)

    Returns:
        包含测试结果的字典
    """
    result = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "question": None,
        "success": False,
        "response_length": 0,
        "time_taken": 0.0,
        "estimated_tokens": 0,
        "tokens_per_second": 0.0,
        "error": None,
    }

    # 随机选择一个问题
    question = random.choice(TEST_QUESTIONS)
    result["question"] = question

    start_time = time.time()

    try:
        # 每次创建新的 LLM 实例 (新会话)
        llm = load_llm(
            provider_name="OpenAILike",
            model=model,
            api_base=api_base,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0.7,
            request_timeout=timeout,
        )

        # 调用 LLM
        response = llm.complete(question, timeout=timeout)

        result["success"] = True
        result["response_length"] = len(response.text)
        result["time_taken"] = time.time() - start_time

        # 计算 token 速度
        estimated_tokens, tokens_per_second = calculate_token_speed(
            result["response_length"],
            result["time_taken"]
        )
        result["estimated_tokens"] = estimated_tokens
        result["tokens_per_second"] = tokens_per_second

        print(f"✅ 会话 {session_id}: 成功")
        print(f"   ⏱️  耗时: {result['time_taken']:.2f}s")
        print(f"   📝 响应: {result['response_length']} 字符 / ~{estimated_tokens} tokens")
        print(f"   🚀 速度: {tokens_per_second:.1f} tokens/s")
        print(f"   💬 问题: {question[:80]}...")
        print(f"   📄 响应预览: {response.text[:150]}...")

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        result["time_taken"] = time.time() - start_time

        print(f"❌ 会话 {session_id}: 失败 ({result['time_taken']:.2f}s)")
        print(f"   💬 问题: {question[:80]}...")
        print(f"   ⚠️  错误: {e}")

    return result


def run_infinite_stability_test(
    api_base: str,
    model: str = "/models",
    delay_between_requests: float = 1.0,
    timeout: float = 120.0,
    save_log_every: int = 10,
):
    """
    运行无限循环的稳定性测试

    Args:
        api_base: API 基础 URL
        model: 模型名称
        delay_between_requests: 请求之间的延迟(秒)
        timeout: 单个请求超时时间(秒)
        save_log_every: 每N次测试保存一次日志
    """
    print("=" * 100)
    print("🚀 vLLM 无限循环稳定性测试")
    print("=" * 100)
    print(f"API Base: {api_base}")
    print(f"Model: {model}")
    print(f"请求间隔: {delay_between_requests}s")
    print(f"超时时间: {timeout}s")
    print(f"每 {save_log_every} 次保存日志")
    print("按 Ctrl+C 停止测试")
    print("=" * 100)
    print()

    results = []
    session_id = 0
    success_count = 0
    total_time = 0.0
    total_tokens = 0
    total_chars = 0

    test_start_time = time.time()
    last_save_time = test_start_time

    try:
        while True:
            session_id += 1
            print(f"\n{'='*100}")
            print(f"🔄 开始会话 #{session_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*100}")

            result = test_single_session(session_id, api_base, model, timeout)
            results.append(result)

            if result["success"]:
                success_count += 1
                total_time += result["time_taken"]
                total_tokens += result["estimated_tokens"]
                total_chars += result["response_length"]

            # 计算统计信息
            current_time = time.time()
            elapsed_time = current_time - test_start_time
            success_rate = (success_count / session_id) * 100

            print(f"\n{'─'*100}")
            print(f"📊 累计统计:")
            print(f"   总请求: {session_id} | 成功: {success_count} | 失败: {session_id - success_count} | 成功率: {success_rate:.1f}%")

            if success_count > 0:
                avg_response_time = total_time / success_count
                avg_tokens = total_tokens / success_count
                avg_token_speed = total_tokens / total_time if total_time > 0 else 0

                print(f"   平均响应时间: {avg_response_time:.2f}s")
                print(f"   平均 tokens: {avg_tokens:.0f} tokens/请求")
                print(f"   平均速度: {avg_token_speed:.1f} tokens/s")
                print(f"   总 tokens: {total_tokens} (~{total_chars} 字符)")

            print(f"   运行时间: {elapsed_time/60:.1f} 分钟")
            print(f"{'─'*100}")

            # 定期保存日志
            if session_id % save_log_every == 0:
                save_log(results, api_base, model, test_start_time, current_time)
                print(f"💾 日志已保存 (第 {session_id} 次测试)")

            # 延迟下一个请求
            if delay_between_requests > 0:
                time.sleep(delay_between_requests)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 100)
        print("⏹️  测试被用户中断")
        print("=" * 100)

        # 保存最终日志
        final_time = time.time()
        save_log(results, api_base, model, test_start_time, final_time)

        # 最终统计
        print_final_statistics(results, test_start_time, final_time)


def save_log(
    results: List[dict],
    api_base: str,
    model: str,
    start_time: float,
    end_time: float
):
    """保存测试日志"""
    output_file = f"vllm_stability_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    success_results = [r for r in results if r["success"]]
    success_count = len(success_results)
    total_count = len(results)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"vLLM 稳定性测试报告\n")
        f.write(f"{'=' * 100}\n")
        f.write(f"测试时间: {datetime.fromtimestamp(start_time).isoformat()} - {datetime.fromtimestamp(end_time).isoformat()}\n")
        f.write(f"API Base: {api_base}\n")
        f.write(f"Model: {model}\n")
        f.write(f"总请求数: {total_count}\n")
        f.write(f"成功: {success_count} ({success_count/total_count*100:.1f}%)\n")
        f.write(f"失败: {total_count - success_count} ({(total_count - success_count)/total_count*100:.1f}%)\n")

        if success_count > 0:
            total_time = sum(r["time_taken"] for r in success_results)
            total_tokens = sum(r["estimated_tokens"] for r in success_results)
            avg_response_time = total_time / success_count
            avg_tokens = total_tokens / success_count
            avg_token_speed = total_tokens / total_time if total_time > 0 else 0

            f.write(f"\n平均响应时间: {avg_response_time:.2f}s\n")
            f.write(f"平均 tokens: {avg_tokens:.0f} tokens/请求\n")
            f.write(f"平均速度: {avg_token_speed:.1f} tokens/s\n")
            f.write(f"最快响应: {min(r['time_taken'] for r in success_results):.2f}s\n")
            f.write(f"最慢响应: {max(r['time_taken'] for r in success_results):.2f}s\n")
            f.write(f"最快速度: {max(r['tokens_per_second'] for r in success_results):.1f} tokens/s\n")
            f.write(f"最慢速度: {min(r['tokens_per_second'] for r in success_results):.1f} tokens/s\n")

        f.write(f"\n{'=' * 100}\n\n")
        f.write(f"详细记录:\n\n")

        for result in results:
            f.write(f"{'─' * 100}\n")
            f.write(f"会话 {result['session_id']}:\n")
            f.write(f"  时间: {result['timestamp']}\n")
            f.write(f"  问题: {result['question']}\n")
            f.write(f"  成功: {result['success']}\n")
            f.write(f"  耗时: {result['time_taken']:.2f}s\n")
            if result['success']:
                f.write(f"  响应长度: {result['response_length']} 字符\n")
                f.write(f"  估计 tokens: {result['estimated_tokens']}\n")
                f.write(f"  Token 速度: {result['tokens_per_second']:.1f} tokens/s\n")
            else:
                f.write(f"  错误: {result['error']}\n")
            f.write("\n")

    return output_file


def print_final_statistics(results: List[dict], start_time: float, end_time: float):
    """打印最终统计信息"""
    success_results = [r for r in results if r["success"]]
    success_count = len(success_results)
    total_count = len(results)
    total_time = end_time - start_time

    print()
    print("=" * 100)
    print("📈 最终测试结果统计")
    print("=" * 100)
    print(f"总测试时间: {total_time:.2f}s ({total_time/60:.1f} 分钟)")
    print(f"总请求数: {total_count}")
    print(f"成功: {success_count} ({success_count/total_count*100:.1f}%)")
    print(f"失败: {total_count - success_count} ({(total_count - success_count)/total_count*100:.1f}%)")
    print()

    if success_count > 0:
        total_response_time = sum(r["time_taken"] for r in success_results)
        total_tokens = sum(r["estimated_tokens"] for r in success_results)
        total_chars = sum(r["response_length"] for r in success_results)

        avg_response_time = total_response_time / success_count
        avg_tokens = total_tokens / success_count
        avg_token_speed = total_tokens / total_response_time if total_response_time > 0 else 0

        print(f"平均响应时间: {avg_response_time:.2f}s")
        print(f"平均 tokens: {avg_tokens:.0f} tokens/请求")
        print(f"平均速度: {avg_token_speed:.1f} tokens/s")
        print()
        print(f"最快响应: {min(r['time_taken'] for r in success_results):.2f}s")
        print(f"最慢响应: {max(r['time_taken'] for r in success_results):.2f}s")
        print(f"最快速度: {max(r['tokens_per_second'] for r in success_results):.1f} tokens/s")
        print(f"最慢速度: {min(r['tokens_per_second'] for r in success_results):.1f} tokens/s")
        print()
        print(f"总生成 tokens: {total_tokens} (~{total_chars} 字符)")

    print("=" * 100)


if __name__ == "__main__":
    # 配置参数
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"
    DELAY = 1.0  # 每次请求间隔 1 秒
    TIMEOUT = 120.0  # 超时 120 秒
    SAVE_LOG_EVERY = 10  # 每 10 次保存一次日志

    # 运行无限循环测试
    run_infinite_stability_test(
        api_base=API_BASE,
        model=MODEL,
        delay_between_requests=DELAY,
        timeout=TIMEOUT,
        save_log_every=SAVE_LOG_EVERY,
    )
