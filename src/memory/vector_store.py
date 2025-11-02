"""
向量存储模块

基于 LanceDB 的向量数据库封装，用于存储和检索经验
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import lancedb
from lancedb.pydantic import LanceModel, Vector

from ..llm.client import get_llm_client
from ..utils.config import config


class ExperienceRecord(LanceModel):
    """
    经验记录模型

    定义向量数据库中的数据结构
    """

    # 主键
    id: str

    # 任务信息
    task_description: str
    task_intent: Optional[str] = None
    app_name: Optional[str] = None

    # 向量（由 embedding 模型生成）
    embedding: Vector(768)  # 维度根据 embedding 模型调整

    # 操作序列（JSON 字符串）
    action_sequence: str

    # 统计信息
    success_rate: float = 1.0
    use_count: int = 0
    total_steps: int = 0
    total_duration_ms: int = 0

    # 时间信息
    created_at: str
    last_used_at: Optional[str] = None

    # 元数据（JSON 字符串）
    metadata: Optional[str] = None


class VectorStore:
    """
    向量存储管理器

    提供经验的存储、检索、更新等功能
    """

    def __init__(self):
        """初始化向量存储"""
        self.db_path = config.vector_db_path
        self.table_name = config.vector_db_table_name

        # 确保目录存在
        Path(self.db_path).mkdir(parents=True, exist_ok=True)

        # 连接数据库
        self.db = lancedb.connect(self.db_path)

        # 初始化表
        self._init_table()

        # LLM 客户端（用于生成 embedding）
        self.llm_client = get_llm_client()

    def _init_table(self) -> None:
        """初始化表（如果不存在）"""
        try:
            self.table = self.db.open_table(self.table_name)
        except Exception:
            # 表不存在，创建新表
            self.table = self.db.create_table(
                self.table_name,
                schema=ExperienceRecord,
            )

    # ========================================
    # 存储方法
    # ========================================

    async def store_experience(
        self,
        id: str,
        task_description: str,
        action_sequence: List[Dict[str, Any]],
        success: bool,
        total_steps: int,
        total_duration_ms: int,
        task_intent: Optional[str] = None,
        app_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        存储经验

        Args:
            id: 经验 ID
            task_description: 任务描述
            action_sequence: 操作序列
            success: 是否成功
            total_steps: 总步数
            total_duration_ms: 总耗时（毫秒）
            task_intent: 任务意图
            app_name: 应用名称
            metadata: 元数据
        """
        # 生成 embedding
        embedding = await self.llm_client.embed_text(task_description)

        # 构建记录
        record = ExperienceRecord(
            id=id,
            task_description=task_description,
            task_intent=task_intent,
            app_name=app_name,
            embedding=embedding,
            action_sequence=json.dumps(action_sequence, ensure_ascii=False),
            success_rate=1.0 if success else 0.0,
            use_count=0,
            total_steps=total_steps,
            total_duration_ms=total_duration_ms,
            created_at=datetime.now().isoformat(),
            metadata=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        )

        # 添加到表
        self.table.add([record.dict()])

    # ========================================
    # 检索方法
    # ========================================

    async def search_similar(
        self,
        task_description: str,
        top_k: int = 3,
        min_success_rate: Optional[float] = None,
        app_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索相似经验

        Args:
            task_description: 任务描述
            top_k: 返回数量
            min_success_rate: 最低成功率（过滤条件）
            app_name: 应用名称（过滤条件）

        Returns:
            相似经验列表

        Examples:
            >>> store = VectorStore()
            >>> results = await store.search_similar("在淘宝搜索双肩包", top_k=3)
            >>> for r in results:
            ...     print(f"任务: {r['task_description']}, 相似度: {r['_distance']}")
        """
        # 生成查询向量
        query_embedding = await self.llm_client.embed_text(task_description)

        # 构建查询
        query = self.table.search(query_embedding).limit(top_k)

        # 添加过滤条件
        if min_success_rate is not None:
            min_success_rate = min_success_rate or config.get(
                'memory', 'long_term_memory', 'min_success_rate', default=0.7
            )
            query = query.where(f"success_rate >= {min_success_rate}")

        if app_name:
            query = query.where(f"app_name = '{app_name}'")

        # 执行查询
        results = query.to_list()

        # 解析结果
        experiences = []
        for r in results:
            experience = {
                'id': r['id'],
                'task_description': r['task_description'],
                'task_intent': r.get('task_intent'),
                'app_name': r.get('app_name'),
                'action_sequence': json.loads(r['action_sequence']),
                'success_rate': r['success_rate'],
                'use_count': r['use_count'],
                'total_steps': r['total_steps'],
                'total_duration_ms': r['total_duration_ms'],
                'created_at': r['created_at'],
                'last_used_at': r.get('last_used_at'),
                'metadata': json.loads(r['metadata']) if r.get('metadata') else None,
                '_distance': r.get('_distance', 0.0),  # 相似度距离
            }
            experiences.append(experience)

        return experiences

    async def get_by_id(self, experience_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取经验

        Args:
            experience_id: 经验 ID

        Returns:
            经验记录，如果不存在则返回 None
        """
        results = self.table.search().where(f"id = '{experience_id}'").to_list()

        if not results:
            return None

        r = results[0]
        return {
            'id': r['id'],
            'task_description': r['task_description'],
            'task_intent': r.get('task_intent'),
            'app_name': r.get('app_name'),
            'action_sequence': json.loads(r['action_sequence']),
            'success_rate': r['success_rate'],
            'use_count': r['use_count'],
            'total_steps': r['total_steps'],
            'total_duration_ms': r['total_duration_ms'],
            'created_at': r['created_at'],
            'last_used_at': r.get('last_used_at'),
            'metadata': json.loads(r['metadata']) if r.get('metadata') else None,
        }

    # ========================================
    # 更新方法
    # ========================================

    def update_usage(
        self,
        experience_id: str,
        success: bool,
    ) -> None:
        """
        更新经验使用情况

        Args:
            experience_id: 经验 ID
            success: 本次是否成功
        """
        # 获取当前记录
        results = self.table.search().where(f"id = '{experience_id}'").to_list()

        if not results:
            return

        record = results[0]

        # 更新成功率（指数移动平均）
        current_success_rate = record['success_rate']
        use_count = record['use_count']
        alpha = 0.2  # 平滑系数

        new_success_rate = (
            alpha * (1.0 if success else 0.0) +
            (1 - alpha) * current_success_rate
        )

        # 更新字段
        # 注意：LanceDB 的更新操作需要删除后重新插入
        # TODO: 后续优化为增量更新
        self.table.delete(f"id = '{experience_id}'")

        record['success_rate'] = new_success_rate
        record['use_count'] = use_count + 1
        record['last_used_at'] = datetime.now().isoformat()

        self.table.add([record])

    # ========================================
    # 维护方法
    # ========================================

    def cleanup_old_experiences(
        self,
        retention_days: int = 90,
        min_success_rate: float = 0.5,
    ) -> int:
        """
        清理旧经验

        删除：
        - 超过保留期限且成功率低的经验
        - 长期未使用的经验

        Args:
            retention_days: 保留天数
            min_success_rate: 最低成功率

        Returns:
            删除数量
        """
        from datetime import timedelta

        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()

        # 查询需要删除的记录
        to_delete = self.table.search().where(
            f"created_at < '{cutoff_date}' AND success_rate < {min_success_rate}"
        ).to_list()

        count = len(to_delete)

        if count > 0:
            # 批量删除
            for record in to_delete:
                self.table.delete(f"id = '{record['id']}'")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息

        Returns:
            统计信息
        """
        total_count = len(self.table.search().to_list())

        # 成功率分布
        all_records = self.table.search().to_list()
        success_rates = [r['success_rate'] for r in all_records]

        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        return {
            'total_experiences': total_count,
            'avg_success_rate': avg_success_rate,
            'db_path': self.db_path,
            'table_name': self.table_name,
        }


# 全局实例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    获取全局向量存储实例（单例）

    Returns:
        向量存储
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


if __name__ == "__main__":
    import asyncio
    import uuid

    async def test():
        """测试向量存储"""
        print("=" * 50)
        print("向量存储测试")
        print("=" * 50)

        store = VectorStore()

        # 测试存储经验
        print("\n[测试 1] 存储经验")
        experience_id = str(uuid.uuid4())
        await store.store_experience(
            id=experience_id,
            task_description="在淘宝搜索双肩包",
            action_sequence=[
                {"type": "tap", "target": "搜索框"},
                {"type": "input", "text": "双肩包"},
                {"type": "tap", "target": "搜索按钮"},
            ],
            success=True,
            total_steps=3,
            total_duration_ms=5000,
            app_name="淘宝",
            task_intent="购物",
        )
        print(f"存储成功, ID: {experience_id}")

        # 测试检索
        print("\n[测试 2] 相似度检索")
        results = await store.search_similar("在淘宝找双肩包", top_k=3)
        print(f"找到 {len(results)} 条相似经验:")
        for r in results:
            print(f"  - 任务: {r['task_description']}")
            print(f"    相似度距离: {r['_distance']:.4f}")
            print(f"    成功率: {r['success_rate']:.2f}")

        # 测试统计
        print("\n[测试 3] 统计信息")
        stats = store.get_stats()
        print(f"总经验数: {stats['total_experiences']}")
        print(f"平均成功率: {stats['avg_success_rate']:.2f}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    asyncio.run(test())
