"""
感知结果模型

定义感知系统输出的数据结构
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UIElement(BaseModel):
    """
    UI 元素模型

    表示屏幕上的一个可交互元素
    """

    # 基本信息
    id: str = Field(..., description="元素 ID")
    type: str = Field(..., description="元素类型（button/input/text/image 等）")
    text: Optional[str] = Field(None, description="元素文本")
    description: Optional[str] = Field(None, description="元素描述")

    # 位置信息
    bounds: tuple[int, int, int, int] = Field(..., description="边界 (left, top, right, bottom)")
    center: tuple[int, int] = Field(..., description="中心点坐标 (x, y)")

    # 属性
    clickable: bool = Field(False, description="是否可点击")
    scrollable: bool = Field(False, description="是否可滚动")
    editable: bool = Field(False, description="是否可编辑")
    visible: bool = Field(True, description="是否可见")

    # 元数据
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="检测置信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class TextRegion(BaseModel):
    """
    文本区域模型

    表示 OCR 检测到的文本区域
    """

    text: str = Field(..., description="文本内容")
    bounds: tuple[int, int, int, int] = Field(..., description="边界")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="识别置信度")
    language: Optional[str] = Field(None, description="语言")


class VisualAnalysis(BaseModel):
    """
    视觉分析结果

    VL 模型对屏幕的深度理解
    """

    # 场景理解
    scene_description: str = Field(..., description="场景描述")
    page_type: Optional[str] = Field(None, description="页面类型（首页/搜索页/详情页等）")
    app_name: Optional[str] = Field(None, description="应用名称")

    # 关键元素
    key_elements: List[str] = Field(default_factory=list, description="关键元素列表")
    actionable_items: List[str] = Field(default_factory=list, description="可操作项列表")

    # 状态信息
    is_loading: bool = Field(False, description="是否在加载")
    has_popup: bool = Field(False, description="是否有弹窗")
    has_error: bool = Field(False, description="是否有错误提示")
    error_message: Optional[str] = Field(None, description="错误信息")

    # 完整分析
    full_analysis: str = Field(..., description="完整分析文本")


class Perception(BaseModel):
    """
    完整感知结果

    融合多个感知模块的输出
    """

    # 时间戳
    timestamp: float = Field(..., description="感知时间戳")

    # 视觉分析（VL 模型）
    visual: VisualAnalysis = Field(..., description="视觉分析结果")

    # UI 元素（UI 检测器）
    ui_elements: List[UIElement] = Field(default_factory=list, description="UI 元素列表")

    # 文本区域（OCR）
    text_regions: List[TextRegion] = Field(default_factory=list, description="文本区域列表")

    # 截图
    screenshot: Optional[bytes] = Field(None, description="原始截图")

    # 融合结果
    summary: str = Field(..., description="感知摘要")
    attention_focus: Optional[str] = Field(None, description="注意力焦点（最重要的元素）")

    # 元数据
    perception_time_ms: int = Field(..., description="感知耗时（毫秒）")
    parallel_execution: bool = Field(False, description="是否并发执行")

    class Config:
        arbitrary_types_allowed = True

    def get_element_by_text(self, text: str, fuzzy: bool = True) -> Optional[UIElement]:
        """
        根据文本查找 UI 元素

        Args:
            text: 查找的文本
            fuzzy: 是否模糊匹配

        Returns:
            匹配的 UI 元素，如果没有则返回 None
        """
        for element in self.ui_elements:
            if element.text:
                if fuzzy:
                    if text.lower() in element.text.lower():
                        return element
                else:
                    if text == element.text:
                        return element
        return None

    def get_clickable_elements(self) -> List[UIElement]:
        """获取所有可点击元素"""
        return [e for e in self.ui_elements if e.clickable]

    def get_editable_elements(self) -> List[UIElement]:
        """获取所有可编辑元素"""
        return [e for e in self.ui_elements if e.editable]

    def extract_all_text(self) -> str:
        """
        提取所有文本

        Returns:
            拼接的所有文本
        """
        texts = []

        # UI 元素文本
        for element in self.ui_elements:
            if element.text:
                texts.append(element.text)

        # OCR 文本
        for region in self.text_regions:
            texts.append(region.text)

        return "\n".join(texts)


if __name__ == "__main__":
    import time

    # 测试感知模型
    print("=" * 50)
    print("感知模型测试")
    print("=" * 50)

    # 创建 UI 元素
    search_box = UIElement(
        id="search_box_1",
        type="input",
        text="搜索",
        description="顶部搜索框",
        bounds=(50, 100, 350, 150),
        center=(200, 125),
        clickable=True,
        editable=True,
    )
    print("\n[UI 元素]")
    print(search_box.model_dump_json(indent=2))

    # 创建文本区域
    text_region = TextRegion(
        text="欢迎使用淘宝",
        bounds=(100, 200, 300, 250),
        confidence=0.98,
        language="zh",
    )
    print("\n[文本区域]")
    print(text_region.model_dump_json(indent=2))

    # 创建视觉分析
    visual = VisualAnalysis(
        scene_description="淘宝首页，顶部有搜索框，下方有商品推荐",
        page_type="首页",
        app_name="淘宝",
        key_elements=["搜索框", "商品列表", "底部导航"],
        actionable_items=["搜索框", "商品卡片", "底部导航按钮"],
        full_analysis="这是淘宝的首页，用户可以通过顶部搜索框搜索商品，或浏览推荐商品列表。",
    )
    print("\n[视觉分析]")
    print(visual.model_dump_json(indent=2))

    # 创建完整感知结果
    perception = Perception(
        timestamp=time.time(),
        visual=visual,
        ui_elements=[search_box],
        text_regions=[text_region],
        summary="淘宝首页，用户可以搜索或浏览商品",
        attention_focus="搜索框",
        perception_time_ms=500,
        parallel_execution=True,
    )
    print("\n[完整感知结果]")
    print(perception.model_dump_json(indent=2, exclude={"screenshot"}))

    # 测试查询方法
    print("\n[查询方法测试]")
    found = perception.get_element_by_text("搜索")
    print(f"查找 '搜索': {found.description if found else '未找到'}")

    clickable = perception.get_clickable_elements()
    print(f"可点击元素数量: {len(clickable)}")

    all_text = perception.extract_all_text()
    print(f"所有文本:\n{all_text}")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
