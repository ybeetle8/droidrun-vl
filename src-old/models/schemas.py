"""
数据模型定义
使用 Pydantic 进行数据验证
"""
from typing import Optional
from pydantic import BaseModel, Field


class Product(BaseModel):
    """商品信息模型"""
    title: str = Field(..., description="商品标题")
    price: str = Field(..., description="商品价格")
    index: int = Field(..., description="UI 元素索引")
    bounds: list[int] = Field(..., description="UI 元素坐标 [x1, y1, x2, y2]")


class AnalysisResult(BaseModel):
    """屏幕分析结果模型"""
    products: list[Product] = Field(default_factory=list, description="识别到的商品列表")
    raw_response: str = Field(..., description="LLM 原始响应")


class ExecutionResult(BaseModel):
    """代码执行结果模型"""
    success: bool = Field(..., description="执行是否成功")
    output: Optional[str] = Field(None, description="执行输出")
    error: Optional[str] = Field(None, description="错误信息")
