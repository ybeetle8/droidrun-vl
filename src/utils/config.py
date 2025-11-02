"""
配置管理模块

提供统一的配置加载和访问接口
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Config:
    """
    配置管理器

    单例模式，全局访问配置
    """

    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self.load_config()

    def load_config(self, config_path: Optional[str] = None) -> None:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径，默认为 configs/config.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "configs" / "config.yaml"

        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

        # 环境变量覆盖
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """
        应用环境变量覆盖

        支持的环境变量：
        - EMBEDDING_API_BASE
        - VISION_API_BASE
        - VECTOR_DB_PATH
        """
        env_mappings = {
            'EMBEDDING_API_BASE': ['llm', 'embedding', 'api_base'],
            'VISION_API_BASE': ['llm', 'vision', 'api_base'],
            'VECTOR_DB_PATH': ['vector_db', 'path'],
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(config_path, value)

    def _set_nested(self, path: list, value: Any) -> None:
        """设置嵌套配置值"""
        current = self._config
        for key in path[:-1]:
            current = current.setdefault(key, {})
        current[path[-1]] = value

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        获取配置值（支持嵌套）

        Args:
            *keys: 配置键路径，如 get('llm', 'embedding', 'api_base')
            default: 默认值

        Returns:
            配置值

        Examples:
            >>> config = Config()
            >>> config.get('llm', 'embedding', 'api_base')
            'http://192.168.18.9:8081/v1'
            >>> config.get('nonexistent', default='default_value')
            'default_value'
        """
        current = self._config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, *keys: str, value: Any) -> None:
        """
        设置配置值（支持嵌套）

        Args:
            *keys: 配置键路径
            value: 配置值
        """
        if len(keys) == 0:
            raise ValueError("至少需要一个键")

        current = self._config
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value

    @property
    def all(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()

    # ========================================
    # 便捷访问方法
    # ========================================

    @property
    def embedding_api_base(self) -> str:
        """Embedding 模型 API 基础 URL"""
        return self.get('llm', 'embedding', 'api_base')

    @property
    def embedding_model(self) -> str:
        """Embedding 模型名称"""
        return self.get('llm', 'embedding', 'model')

    @property
    def vision_api_base(self) -> str:
        """视觉模型 API 基础 URL"""
        return self.get('llm', 'vision', 'api_base')

    @property
    def vision_model(self) -> str:
        """视觉模型名称"""
        return self.get('llm', 'vision', 'model')

    @property
    def vision_temperature(self) -> float:
        """视觉模型温度"""
        return self.get('llm', 'vision', 'temperature', default=0.7)

    @property
    def vision_max_tokens(self) -> int:
        """视觉模型最大 token 数"""
        return self.get('llm', 'vision', 'max_tokens', default=2000)

    @property
    def vector_db_path(self) -> str:
        """向量数据库路径"""
        return self.get('vector_db', 'path')

    @property
    def vector_db_table_name(self) -> str:
        """向量数据库表名"""
        return self.get('vector_db', 'table_name', default='experiences')

    @property
    def working_memory_size(self) -> int:
        """工作记忆容量"""
        return self.get('memory', 'working_memory', 'size', default=7)

    @property
    def enable_parallel_perception(self) -> bool:
        """是否启用并发感知"""
        return self.get('perception', 'enable_parallel', default=True)

    @property
    def feedback_wait_time(self) -> float:
        """即时反馈等待时间（秒）"""
        return self.get('execution', 'feedback_wait_time', default=0.5)

    @property
    def max_sub_tasks(self) -> int:
        """Master Agent 最大子任务数"""
        return self.get('master', 'max_sub_tasks', default=20)

    @property
    def worker_max_steps(self) -> int:
        """Worker Agent 单个子任务最大步数"""
        return self.get('worker', 'max_steps', default=50)


# 全局配置实例
config = Config()


# 便捷函数
def get_config(*keys: str, default: Any = None) -> Any:
    """
    获取配置值

    Args:
        *keys: 配置键路径
        default: 默认值

    Returns:
        配置值
    """
    return config.get(*keys, default=default)


def reload_config(config_path: Optional[str] = None) -> None:
    """
    重新加载配置

    Args:
        config_path: 配置文件路径
    """
    config.load_config(config_path)


if __name__ == "__main__":
    # 测试配置加载
    print("=" * 50)
    print("配置测试")
    print("=" * 50)

    cfg = Config()

    print(f"Embedding API Base: {cfg.embedding_api_base}")
    print(f"Embedding Model: {cfg.embedding_model}")
    print(f"Vision API Base: {cfg.vision_api_base}")
    print(f"Vision Model: {cfg.vision_model}")
    print(f"Vector DB Path: {cfg.vector_db_path}")
    print(f"Working Memory Size: {cfg.working_memory_size}")
    print(f"Enable Parallel Perception: {cfg.enable_parallel_perception}")
    print(f"Feedback Wait Time: {cfg.feedback_wait_time}s")

    print("\n" + "=" * 50)
    print("配置加载成功!")
    print("=" * 50)
