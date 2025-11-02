"""
配置管理
"""
import os
from typing import Optional
from pydantic import BaseModel, Field


class Config(BaseModel):
    """应用配置"""
    # LLM 配置
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "sk-"))
    api_base: str = Field(default="http://192.168.18.9:8080/v1")
    model: str = Field(default="/models")
    temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=2048)  # 降低到 2048，为输入留出更多空间

    # ADB 配置
    use_tcp: bool = Field(default=True)

    # 输出配置
    output_dir: str = Field(default="test/analysis_output")

    # 重试配置
    max_retries: int = Field(default=3)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_config() -> Config:
    """获取配置实例"""
    return Config()
