"""
LanceDB 向量检索教程示例
======================

本示例演示如何使用 LanceDB 进行向量检索，实现类似你需求中的多级检索策略。

核心概念：
1. 向量数据库：存储文本的向量表示（embedding）
2. 语义搜索：通过向量相似度找到语义相关的内容
3. 应用场景：经验检索、任务匹配、知识库查询

教程流程：
Step 1: 使用 vLLM Embedding 模型（Qwen3-Embedding-0.6B）
Step 2: 创建 LanceDB 数据库
Step 3: 添加经验数据
Step 4: 执行向量检索
Step 5: 多级检索策略演示

前置条件：
- vLLM 服务运行在 http://192.168.18.9:8081
- 模型：Qwen3-Embedding-0.6B
"""

import os
import asyncio
from typing import List, Dict, Any
import lancedb
import numpy as np
from openai import OpenAI

# 导入项目配置
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.utils import Config
from src.utils.logger import setup_utf8_console


# ============================================================================
# Step 1: vLLM Embedding 向量化工具
# ============================================================================
class VLLMEmbedding:
    """
    使用 vLLM 提供的 Embedding 模型

    通过 OpenAI 兼容的 API 调用本地 vLLM 服务
    """
    def __init__(self, base_url: str = "http://192.168.18.9:8081/v1", model: str = "/models"):
        """
        初始化 vLLM Embedding 客户端

        参数:
            base_url: vLLM 服务地址
            model: 模型名称/路径（需要与 vLLM 启动时的 --model 参数一致）
        """
        self.client = OpenAI(
            api_key="EMPTY",  # vLLM 不需要真实 API key
            base_url=base_url
        )
        self.model = model
        print(f"✅ vLLM Embedding 初始化: {base_url}, model={model}")

    def fit(self, texts: List[str]):
        """兼容接口，vLLM 不需要训练"""
        pass

    def encode(self, text: str) -> np.ndarray:
        """
        将文本转换为向量

        参数:
            text: 输入文本

        返回:
            向量数组 (numpy.ndarray)
        """
        response = self.client.embeddings.create(
            input=text,
            model=self.model
        )
        vector = response.data[0].embedding
        return np.array(vector, dtype=np.float32)


# ============================================================================
# Step 2: 向量检索管理器
# ============================================================================
class VectorSearchManager:
    """向量检索管理器 - 封装 LanceDB 的核心操作"""

    def __init__(self, db_path: str = "./data/lancedb", embedding_base_url: str = "http://192.168.18.9:8081/v1"):
        """
        初始化向量数据库

        参数：
            db_path: 数据库存储路径（本地文件）
            embedding_base_url: vLLM Embedding 服务地址
        """
        self.db_path = db_path

        # 创建数据库连接
        self.db = lancedb.connect(db_path)

        # 创建 vLLM embedding 工具
        self.embedder = VLLMEmbedding(base_url=embedding_base_url)

        print(f"✅ LanceDB 初始化完成: {db_path}")

    def create_table(self, table_name: str = "experiences", data: List[Dict] = None):
        """
        创建经验表并插入初始数据

        参数：
            table_name: 表名
            data: 初始数据列表
        """
        # 删除已存在的表（用于演示）
        if table_name in self.db.table_names():
            self.db.drop_table(table_name)
            print(f"🗑️  删除旧表: {table_name}")

        if data:
            # 训练向量化器
            all_texts = [item['task_description'] for item in data]
            self.embedder.fit(all_texts)

            # 为每条数据生成向量
            for item in data:
                text = item['task_description']
                item['vector'] = self.embedder.encode(text).tolist()

            # 创建表
            self.table = self.db.create_table(table_name, data=data)
            print(f"✅ 创建表 '{table_name}' 并插入 {len(data)} 条数据")
        else:
            raise ValueError("初始数据不能为空（需要训练向量化器）")

        return self.table

    def add_experiences(self, experiences: List[Dict]):
        """
        添加新经验到数据库

        参数：
            experiences: 经验数据列表
        """
        # 生成向量
        for exp in experiences:
            exp['vector'] = self.embedder.encode(exp['task_description']).tolist()

        # 插入数据
        self.table.add(experiences)
        print(f"✅ 添加 {len(experiences)} 条新经验")

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """
        语义搜索（Level 2: 语义相似）

        参数：
            query: 查询文本
            limit: 返回结果数量

        返回：
            相似度最高的经验列表
        """
        # 将查询文本转换为向量
        query_vector = self.embedder.encode(query)

        # 向量搜索
        results = (
            self.table.search(query_vector)
            .limit(limit)
            .to_list()
        )

        return results

    def multi_level_search(self, query: str) -> Dict[str, Any]:
        """
        多级检索策略实现

        Level 1: 精确匹配 (哈希查找) - 相似度 > 0.95
        Level 2: 语义相似 (向量搜索) - 相似度 > 0.85
        Level 3: 模式匹配 - 相似度 > 0.70
        Level 4: 无匹配 - 完全新探索

        返回：
            {
                'level': 匹配级别,
                'confidence': 置信度,
                'result': 检索结果,
                'action': 建议动作
            }
        """
        # 执行向量搜索
        results = self.search(query, limit=1)

        if not results:
            return {
                'level': 4,
                'confidence': 0.0,
                'result': None,
                'action': '完全新探索 (Reflexion 循环)'
            }

        top_result = results[0]
        # 计算相似度（距离越小越相似，转换为相似度分数）
        similarity = 1 / (1 + top_result.get('_distance', 1.0))

        # 多级判断
        if similarity > 0.95:
            level = 1
            action = '✅ 直接执行'
        elif similarity > 0.85:
            level = 2
            action = '🔧 轻微调整后执行'
        elif similarity > 0.70:
            level = 3
            action = '🧭 引导式探索'
        else:
            level = 4
            action = '🆕 完全新探索'

        return {
            'level': level,
            'confidence': similarity,
            'result': top_result,
            'action': action
        }


# ============================================================================
# Step 3: 演示主函数
# ============================================================================
async def demo_vector_search():
    """完整的向量检索演示"""

    # 设置 UTF-8 编码（Windows 兼容）
    setup_utf8_console()

    print("=" * 80)
    print("🎯 LanceDB 向量检索教程演示")
    print("=" * 80)
    print()

    print("📝 Step 1: 准备示例数据")
    print("-" * 80)

    # 准备经验数据（模拟手机操作任务）
    sample_experiences = [
        {
            "task_description": "打开淘宝并搜索手机壳",
            "action_sequence": "点击淘宝图标 -> 点击搜索框 -> 输入'手机壳' -> 点击搜索按钮",
            "success_rate": 0.95
        },
        {
            "task_description": "在京东购买充电器",
            "action_sequence": "打开京东 -> 搜索'充电器' -> 选择商品 -> 加入购物车 -> 结算",
            "success_rate": 0.88
        },
        {
            "task_description": "使用微信发送消息给朋友",
            "action_sequence": "打开微信 -> 点击通讯录 -> 选择好友 -> 输入消息 -> 发送",
            "success_rate": 0.98
        },
        {
            "task_description": "在抖音刷视频并点赞",
            "action_sequence": "打开抖音 -> 滑动浏览 -> 双击点赞 -> 继续滑动",
            "success_rate": 0.92
        },
        {
            "task_description": "打开支付宝查看余额",
            "action_sequence": "点击支付宝 -> 查看首页余额 -> 点击余额详情",
            "success_rate": 0.90
        }
    ]

    for i, exp in enumerate(sample_experiences, 1):
        print(f"{i}. {exp['task_description']} (成功率: {exp['success_rate']})")

    print()
    print("🔧 Step 2: 初始化向量检索管理器")
    print("-" * 80)

    # 创建管理器
    manager = VectorSearchManager(
        db_path="./data/lancedb_tutorial"
    )

    # 创建表并插入数据
    manager.create_table(table_name="experiences", data=sample_experiences)

    print()
    print("🔍 Step 3: 基础向量检索")
    print("-" * 80)

    # 测试查询
    test_queries = [
        "我想在淘宝买东西",           # 应该匹配"打开淘宝并搜索手机壳"
        "给好友发微信",               # 应该匹配"使用微信发送消息给朋友"
        "看看我的支付宝有多少钱",     # 应该匹配"打开支付宝查看余额"
    ]

    for query in test_queries:
        print(f"\n📌 查询: '{query}'")
        results = manager.search(query, limit=2)

        for i, result in enumerate(results, 1):
            distance = result.get('_distance', 0)
            similarity = 1 / (1 + distance)
            print(f"  {i}. 相似度: {similarity:.3f}")
            print(f"     任务: {result['task_description']}")
            print(f"     操作: {result['action_sequence']}")

    print()
    print("🎯 Step 4: 多级检索策略演示")
    print("-" * 80)

    # 测试不同相似度级别
    strategy_queries = [
        ("打开淘宝搜索手机壳", "高度相似 - 应该是 Level 1 或 2"),
        ("在电商平台买东西", "中度相似 - 应该是 Level 3"),
        ("打开计算器计算数学题", "低相似 - 应该是 Level 4"),
    ]

    for query, expected in strategy_queries:
        print(f"\n📌 查询: '{query}' ({expected})")
        result = manager.multi_level_search(query)

        print(f"  ✨ 匹配级别: Level {result['level']}")
        print(f"  📊 置信度: {result['confidence']:.3f}")
        print(f"  🎬 建议动作: {result['action']}")

        if result['result']:
            print(f"  📋 匹配任务: {result['result']['task_description']}")

    print()
    print("📈 Step 5: 动态添加新经验")
    print("-" * 80)

    # 添加新经验
    new_experiences = [
        {
            "task_description": "在美团点外卖",
            "action_sequence": "打开美团 -> 选择外卖 -> 浏览商家 -> 下单",
            "success_rate": 0.89
        }
    ]

    manager.add_experiences(new_experiences)

    # 再次查询验证
    query = "点外卖吃饭"
    print(f"\n📌 新查询: '{query}'")
    result = manager.multi_level_search(query)
    print(f"  ✨ 匹配级别: Level {result['level']}")
    print(f"  📊 置信度: {result['confidence']:.3f}")
    print(f"  📋 匹配任务: {result['result']['task_description']}")

    print()
    print("=" * 80)
    print("✅ 教程演示完成！")
    print("=" * 80)
    print()
    print("💡 关键要点总结:")
    print("1. LanceDB 是嵌入式向量数据库，数据存储在本地文件")
    print("2. 使用 vLLM Qwen3-Embedding 模型将文本转换为向量")
    print("3. 向量搜索通过计算余弦相似度找到语义相关内容")
    print("4. 多级检索策略可以根据相似度选择不同执行方式")
    print("5. 支持动态添加新经验，适合在线学习场景")
    print()
    print("📂 数据库位置: ./data/lancedb_tutorial")
    print("🌐 vLLM 服务: http://192.168.18.9:8081/v1")
    print("🔧 可以使用 manager.table.to_pandas() 查看所有数据")


# ============================================================================
# 入口函数
# ============================================================================
def main():
    """主入口"""
    asyncio.run(demo_vector_search())


if __name__ == "__main__":
    main()
