"""
LLM 客户端封装

提供统一的 LLM API 调用接口，支持：
- Embedding 模型（文本向量化）
- Qwen3-VL 模型（视觉语言理解）
"""

import base64
from typing import List, Optional, Union

from openai import AsyncOpenAI

from ..utils.config import config


class LLMClient:
    """
    统一 LLM 客户端

    封装 Embedding 和 Vision 模型的调用
    """

    def __init__(self):
        """初始化客户端"""
        # Embedding 客户端
        self.embedding_client = AsyncOpenAI(
            api_key="dummy",  # 本地模型不需要 API key
            base_url=config.embedding_api_base,
            timeout=config.get('llm', 'embedding', 'timeout', default=30.0),
            max_retries=config.get('llm', 'embedding', 'max_retries', default=3),
        )

        # Vision 客户端
        self.vision_client = AsyncOpenAI(
            api_key="dummy",
            base_url=config.vision_api_base,
            timeout=config.get('llm', 'vision', 'timeout', default=60.0),
            max_retries=config.get('llm', 'vision', 'max_retries', default=3),
        )

    # ========================================
    # Embedding 相关方法
    # ========================================

    async def embed_text(self, text: str) -> List[float]:
        """
        将文本转换为向量

        Args:
            text: 输入文本

        Returns:
            向量表示

        Examples:
            >>> client = LLMClient()
            >>> embedding = await client.embed_text("在淘宝搜索双肩包")
            >>> len(embedding)
            768
        """
        response = await self.embedding_client.embeddings.create(
            model=config.embedding_model,
            input=text,
        )

        return response.data[0].embedding

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        response = await self.embedding_client.embeddings.create(
            model=config.embedding_model,
            input=texts,
        )

        return [data.embedding for data in response.data]

    # ========================================
    # Vision 相关方法
    # ========================================

    async def analyze_image(
        self,
        image: Union[bytes, str],
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        分析图片（视觉语言理解）

        Args:
            image: 图片（bytes 或 base64 字符串）
            prompt: 提示词
            temperature: 温度（可选）
            max_tokens: 最大 token 数（可选）

        Returns:
            模型响应文本

        Examples:
            >>> client = LLMClient()
            >>> with open("screenshot.png", "rb") as f:
            ...     image_bytes = f.read()
            >>> result = await client.analyze_image(
            ...     image_bytes,
            ...     "描述这个屏幕上的内容"
            ... )
            >>> print(result)
        """
        # 处理图片格式
        if isinstance(image, bytes):
            image_b64 = base64.b64encode(image).decode('utf-8')
        else:
            image_b64 = image

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        },
                    },
                ],
            }
        ]

        # 调用模型
        response = await self.vision_client.chat.completions.create(
            model=config.vision_model,
            messages=messages,
            temperature=temperature or config.vision_temperature,
            max_tokens=max_tokens or config.vision_max_tokens,
        )

        return response.choices[0].message.content

    async def analyze_with_context(
        self,
        image: Union[bytes, str],
        prompt: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        分析图片（带上下文）

        Args:
            image: 图片
            prompt: 提示词
            context: 上下文信息（如：最近的操作历史）
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            模型响应文本
        """
        # 处理图片格式
        if isinstance(image, bytes):
            image_b64 = base64.b64encode(image).decode('utf-8')
        else:
            image_b64 = image

        # 构建消息
        messages = []

        # 添加上下文
        if context:
            messages.append({
                "role": "system",
                "content": f"上下文信息：\n{context}",
            })

        # 添加当前问题
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    },
                },
            ],
        })

        # 调用模型
        response = await self.vision_client.chat.completions.create(
            model=config.vision_model,
            messages=messages,
            temperature=temperature or config.vision_temperature,
            max_tokens=max_tokens or config.vision_max_tokens,
        )

        return response.choices[0].message.content

    # ========================================
    # 文本生成方法（用于决策、规划等）
    # ========================================

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        生成文本（用于决策、规划等）

        Args:
            prompt: 提示词
            system_prompt: 系统提示词
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            生成的文本
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })

        messages.append({
            "role": "user",
            "content": prompt,
        })

        response = await self.vision_client.chat.completions.create(
            model=config.vision_model,
            messages=messages,
            temperature=temperature or config.vision_temperature,
            max_tokens=max_tokens or config.vision_max_tokens,
        )

        return response.choices[0].message.content

    async def generate_with_history(
        self,
        prompt: str,
        history: List[dict],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        生成文本（带对话历史）

        Args:
            prompt: 提示词
            history: 对话历史 [{"role": "user", "content": "..."}, ...]
            system_prompt: 系统提示词
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            生成的文本
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })

        messages.extend(history)

        messages.append({
            "role": "user",
            "content": prompt,
        })

        response = await self.vision_client.chat.completions.create(
            model=config.vision_model,
            messages=messages,
            temperature=temperature or config.vision_temperature,
            max_tokens=max_tokens or config.vision_max_tokens,
        )

        return response.choices[0].message.content

    # ========================================
    # 便捷方法（为其他模块提供兼容接口）
    # ========================================

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        生成文本（别名方法，用于兼容）

        Args:
            prompt: 提示词
            system_prompt: 系统提示词
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            生成的文本
        """
        return await self.generate(prompt, system_prompt, temperature, max_tokens)

    async def generate_with_image(
        self,
        prompt: str,
        image_data: Union[bytes, str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        使用图片生成文本（别名方法）

        Args:
            prompt: 提示词
            image_data: 图片数据
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            生成的文本
        """
        return await self.analyze_image(image_data, prompt, temperature, max_tokens)

    async def generate_with_images(
        self,
        prompt: str,
        image_data_list: List[Union[bytes, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        使用多张图片生成文本

        Args:
            prompt: 提示词
            image_data_list: 图片数据列表
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            生成的文本
        """
        # 处理图片格式
        image_contents = []
        for image_data in image_data_list:
            if isinstance(image_data, bytes):
                image_b64 = base64.b64encode(image_data).decode('utf-8')
            else:
                image_b64 = image_data

            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                },
            })

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    *image_contents,
                ],
            }
        ]

        # 调用模型
        response = await self.vision_client.chat.completions.create(
            model=config.vision_model,
            messages=messages,
            temperature=temperature or config.vision_temperature,
            max_tokens=max_tokens or config.vision_max_tokens,
        )

        return response.choices[0].message.content


# 全局客户端实例
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    获取全局 LLM 客户端实例（单例）

    Returns:
        LLM 客户端
    """
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


if __name__ == "__main__":
    import asyncio

    async def test():
        """测试 LLM 客户端"""
        print("=" * 50)
        print("LLM 客户端测试")
        print("=" * 50)

        client = LLMClient()

        # 测试 Embedding
        print("\n[测试 1] 文本向量化")
        text = "在淘宝搜索双肩包"
        embedding = await client.embed_text(text)
        print(f"文本: {text}")
        print(f"向量维度: {len(embedding)}")
        print(f"向量前 5 维: {embedding[:5]}")

        # 测试批量 Embedding
        print("\n[测试 2] 批量文本向量化")
        texts = ["打开设置", "搜索商品", "点击购买"]
        embeddings = await client.embed_texts(texts)
        print(f"文本数量: {len(texts)}")
        print(f"向量数量: {len(embeddings)}")

        # 测试文本生成
        print("\n[测试 3] 文本生成")
        prompt = "将任务分解为 3 个子任务: 到闲鱼购买硬盘"
        result = await client.generate(prompt)
        print(f"提示: {prompt}")
        print(f"生成结果:\n{result}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    asyncio.run(test())
