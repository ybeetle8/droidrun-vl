# Android界面分析AI提示词

## 背景说明

这是一个Android应用的无障碍树(Accessibility Tree)JSON数据，包含了屏幕上所有UI元素的层级结构和属性信息。

## 核心分析提示词

### 基础版本

```
请分析这个Android界面的JSON数据，它包含了屏幕的无障碍树结构。

JSON结构说明：
- data.a11y_tree: 完整的UI元素树
- 每个元素包含：
  - index: 元素的唯一索引，用于点击操作
  - resourceId: Android资源ID
  - className: UI组件类型（如TextView, Button, FrameLayout等）
  - text: 显示的文本内容
  - bounds: 元素位置 "left,top,right,bottom"（单位：像素）
  - children: 子元素数组

请回答以下问题：
1. 当前屏幕显示的是什么应用？
2. 主要内容区域有哪些？
3. 列出所有可交互的元素（按钮、输入框、可点击项等）
4. 如果我想[执行某个操作]，应该点击哪个index？
```

### 专业版本（适用于自动化任务）

```
你是一个Android UI自动化专家。请分析以下Android无障碍树JSON数据。

**数据结构**：
- 这是通过Android Accessibility Service获取的屏幕UI树
- index字段是可点击元素的唯一标识
- bounds格式：[left, top, right, bottom]，坐标单位为像素

**分析任务**：

1. **应用识别**
   - 应用名称：从phone_state.currentApp获取
   - 包名：从phone_state.packageName获取
   - 当前界面类型（主页/列表页/详情页等）

2. **布局结构分析**
   - 顶部导航栏（如有）
   - 主内容区域
   - 底部导航/操作栏（如有）

3. **交互元素识别**
   按类别列出可交互元素：
   - 按钮类：Button, ImageButton, FrameLayout(可点击)
   - 输入类：EditText, SearchView
   - 列表项：RecyclerView/ListView的子项
   - 标签页：TabLayout, ViewPager

4. **内容提取**
   提取关键信息：
   - 文本内容（包括标题、价格、描述等）
   - 图片位置（ImageView）
   - 用户头像/昵称

5. **操作建议**
   基于目标任务，给出：
   - 推荐点击的元素index
   - 操作序列（如需多步）
   - 可能的风险点（如误点其他区域）

**输出格式**：
以Markdown格式输出，包含清晰的分类和index标注。

[在此粘贴JSON数据]
```

### 商品列表专用版本

```
分析这个电商应用界面的JSON数据，识别商品列表。

**重点关注**：

1. **商品定位**
   - 在RecyclerView或类似容器中查找重复的布局结构
   - 每个商品通常包含：图片、标题、价格、卖家信息

2. **商品属性提取**
   对每个商品，提取：
   - 商品index（最外层FrameLayout/LinearLayout）
   - 商品标题（TextView，通常文字较长）
   - 价格（包含"¥"或数字的TextView）
   - 卖家名称（小字号TextView）
   - 商品图片位置（ImageView的bounds）

3. **排列顺序**
   - 根据bounds的top值判断商品的上下顺序
   - 根据bounds的left值判断左右列
   - 标注"第N个商品"

4. **点击建议**
   - 如果要查看第N个商品，应该点击哪个index
   - 说明该index对应的bounds范围

**示例输出**：
- 第1个商品：index 64，价格¥255，标题"阿斯加特内存条..."
- 第2个商品：index 72，价格¥1330，标题"i5电脑主机..."

[在此粘贴JSON数据]
```

### 调试辅助版本

```
这是Android自动化测试中获取的界面快照。请帮我：

1. **快速定位**
   我想找到包含文字"[关键词]"的元素，它的index是多少？

2. **元素验证**
   index [X] 的元素是什么？它的：
   - 类型（className）
   - 显示文本（text）
   - 位置大小（bounds）
   - 父元素和子元素

3. **点击安全性**
   如果点击index [X]，会触发什么？
   - 检查该元素及其父元素的text描述
   - 检查是否在可见区域内（bounds是否合理）

4. **替代方案**
   如果index [X]点击失败，有哪些相似的可点击元素？

[在此粘贴JSON数据]
```

## 使用技巧

### 1. 精确定位元素
```
在JSON中找到所有className为"Button"且text包含"确认"的元素，给出它们的index和bounds
```

### 2. 层级关系分析
```
找到index 72的元素，列出它的：
- 完整父级路径（从根节点到该元素）
- 所有直接子元素
- 同级元素（同一个父元素下的其他子元素）
```

### 3. 坐标计算
```
屏幕分辨率是1080x2520，请：
- 计算index 72元素占屏幕的百分比
- 判断它在屏幕的哪个区域（上/中/下，左/中/右）
- 给出元素中心点坐标（用于点击）
```

### 4. 智能搜索
```
我想[买第二个商品/点赞/搜索/返回]，但不确定具体操作。
请分析界面并给出：
- 最可能的操作元素（index + 原因）
- 备选方案（如有多个可能）
```

## 常见问题

### Q1: 为什么有些元素没有text？
A: 部分元素是容器（如FrameLayout），其text可能为空或继承自子元素。图片元素（ImageView）也通常无text。

### Q2: 如何区分可点击和不可点击元素？
A: 查看className（Button明确可点击）、是否有子元素（容器通常可点击）、text描述中是否包含操作提示。

### Q3: bounds坐标如何使用？
A: bounds格式为"left,top,right,bottom"，可以：
- 计算中心点：x=(left+right)/2, y=(top+bottom)/2
- 计算宽高：width=right-left, height=bottom-top
- 判断是否重叠：比较两个bounds的范围

### Q4: 如何处理嵌套很深的结构？
A: 通常商品卡片、列表项等会在RecyclerView的直接子元素（FrameLayout/LinearLayout）中，可以先定位这些容器级元素的index。

## 实战案例

### 案例1：识别闲鱼商品列表

**原始需求**：我想点击第二个商品

**分析步骤**：
1. 找到RecyclerView（index 34，resourceId: nested_recycler_view）
2. 查看其直接子元素：index 35(广告位), 51(红包区), 64(商品1), 72(商品2), 81(商品3), 83(商品4)
3. 通过bounds的top值确认顺序：946-1921为第二个商品区域
4. **结论**：点击 index 72

### 案例2：查找搜索框

**原始需求**：我想搜索"固态硬盘"

**分析步骤**：
1. 查找className包含"Search"或text包含"搜索"的元素
2. 找到index 11（resourceId: search_bar_layout, text: "256g固态m2,搜索,点击跳转到搜索激活页"）
3. **结论**：点击 index 11 或 14（搜索按钮）

### 案例3：底部导航切换

**原始需求**：我想进入"我的"页面

**分析步骤**：
1. 查找底部导航区域（bounds的top值接近屏幕底部2394）
2. 找到index 93（text: "我的，未选中状态"）
3. **结论**：点击 index 93

## 优化建议

1. **提供上下文**：告诉AI你的最终目标（如"购买商品""发布内容"），而不仅仅是"点击某个元素"
2. **多轮对话**：先让AI分析整体结构，再针对性提问
3. **验证结果**：让AI解释为什么选择这个index，确保逻辑正确
4. **异常处理**：询问"如果这个元素不存在怎么办？"获取备选方案

## 与DroidRun集成

在DroidRun框架中，可以这样使用：

```python
# 1. 获取界面JSON
screen_data = tools.get_screen_json()

# 2. 使用AI分析
prompt = """
分析这个界面JSON，找到"立即购买"按钮的index。
要求：优先选择明确的Button类型，如果没有则选择包含"购买"文字的可点击容器。
"""

# 3. AI返回index
target_index = 72  # AI分析结果

# 4. 执行点击
tools.click_by_index(target_index)
```
