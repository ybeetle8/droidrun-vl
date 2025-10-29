# Android 无障碍树（Accessibility Tree）数据分析提示词

## 数据格式概述

这些 JSON 文件包含了 Android 应用界面的无障碍树（Accessibility Tree）数据，用于描述 UI 元素的层次结构和属性。数据由 DroidRun Portal 通过 Android Accessibility Service 抓取。

## JSON 结构说明

### 顶层结构
```json
{
  "status": "success",           // 状态标识，"success" 表示抓取成功
  "data": {
    "a11y_tree": [...],          // 无障碍树数组，包含完整的 UI 层次结构
    "phone_state": {...}         // 设备当前状态信息
  }
}
```

### a11y_tree 节点属性

每个 UI 元素节点包含以下关键属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `index` | 整数 | 节点在树中的全局索引，从 1 开始递增 |
| `resourceId` | 字符串 | Android 资源 ID，格式为 `包名:id/id名称`，可能为空 |
| `className` | 字符串 | UI 组件类名（如 TextView、Button、FrameLayout） |
| `text` | 字符串 | 节点的文本内容或描述信息 |
| `bounds` | 字符串 | 元素在屏幕上的边界，格式为 `"left, top, right, bottom"` |
| `children` | 数组 | 子节点列表，可能为空数组 |

### phone_state 设备状态

```json
{
  "currentApp": "应用显示名称",
  "packageName": "应用包名",
  "keyboardVisible": false,      // 键盘是否可见
  "isEditable": false,           // 当前是否有可编辑元素获得焦点
  "focusedElement": {            // 当前获得焦点的元素
    "resourceId": "资源ID",
    "className": "类名"
  }
}
```

## 常见场景分析示例

### 1. 识别可点击元素
```
任务：找出页面中所有可点击的按钮和链接

分析方法：
- 查找 className 为 Button、ImageButton、TextView（带点击文本）的节点
- 检查 text 属性是否包含操作提示（如"搜索"、"发送"、"登录"）
- 通过 bounds 确定元素位置和大小
```

### 2. 提取列表数据
```
任务：提取闲鱼商品列表的商品信息

分析方法：
- 定位 RecyclerView 或 ListView 节点（className 为 RecyclerView）
- 遍历其 children，每个 FrameLayout 通常代表一个商品卡片
- 提取每个商品的：
  - 商品描述（text 属性较长的 View/TextView）
  - 价格信息（text 包含 "¥" 的 TextView）
  - 卖家昵称（底部 TextView）
  - 点赞数（resourceId 包含 "like_count" 的 TextView）
```

### 3. 识别导航结构
```
任务：分析应用的底部导航栏

分析方法：
- 查找 bounds 的 top 值接近屏幕底部（如 2263-2394）的节点
- 这些节点通常是 FrameLayout，包含图标和文本
- text 属性会显示导航名称（如"闲鱼"、"消息"、"我的"）
- 检查 text 是否包含"选中状态"或"未选中状态"
```

### 4. 表单输入检测
```
任务：识别可输入的搜索框

分析方法：
- 查找 className 为 EditText 的节点
- 或查找 text 包含"搜索"、"输入"等提示的元素
- 检查 resourceId 是否包含 "search"、"input" 等关键词
- 通过 phone_state.isEditable 确认是否有输入框获得焦点
```

### 5. WebView 内容分析
```
任务：分析内嵌网页内容

分析方法：
- 查找 className 为 WebView 的节点
- WebView 的子节点结构可能与原生组件不同
- 注意 resourceId 可能为 "root" 或自定义网页元素 ID
- 文本内容可能分散在多个嵌套的 View 节点中
```

## 坐标系统说明

### bounds 格式
`"left, top, right, bottom"` - 使用像素为单位的屏幕坐标

示例：`"435, 79, 645, 383"`
- left: 435px（左边界）
- top: 79px（上边界）
- right: 645px（右边界）
- bottom: 383px（下边界）

### 计算元素尺寸
- 宽度：`right - left`
- 高度：`bottom - top`
- 中心点 X：`(left + right) / 2`
- 中心点 Y：`(top + bottom) / 2`

### 典型屏幕尺寸（示例数据中）
- 屏幕宽度：1080px
- 屏幕高度：2520px
- 可视区域高度：2394px（不包括状态栏/导航栏）

## 数据分析最佳实践

### 1. 层次遍历策略
```
- 从根节点（index: 1）开始深度优先遍历
- 记录每个节点的父子关系
- 构建完整的 UI 树结构图
```

### 2. 元素定位优先级
```
1. 优先使用 resourceId（最稳定）
2. 其次使用 className + text 组合
3. 最后使用 bounds 位置信息（容易变化）
```

### 3. 内容提取技巧
```
- text 为空的节点可能是纯布局容器
- ImageView 通常 text 为 resourceId 名称
- 多层嵌套的 FrameLayout 可能包含复杂的自定义组件
- RecyclerView 的 children 只包含当前可见的列表项
```

### 4. 应用状态判断
```
- 通过 phone_state.packageName 确认当前应用
- keyboardVisible 判断输入场景
- focusedElement 确定用户交互焦点
```

## 常见问题处理

### 1. 找不到目标元素
- 元素可能被其他视图遮挡
- 元素可能在 WebView 内部（需深入 WebView 子树）
- 元素可能在屏幕外（RecyclerView 未加载的部分）

### 2. resourceId 为空
- 使用 className + text + bounds 组合定位
- 检查父节点的 resourceId
- 利用兄弟节点的相对位置

### 3. 动态内容识别
- 列表滚动会改变 children 数组
- 商品卡片的 bounds 位置会变化
- 使用内容特征（价格格式、文本模式）而非绝对位置

## AI 分析任务模板

### 任务类型 A：元素查找
```
请在 a11y_tree 中找到所有满足以下条件的元素：
- className 为 [目标类型]
- text 包含 [关键词]
- bounds 位于屏幕 [区域描述]

输出格式：
- index: [索引]
- 完整路径：根节点 -> ... -> 目标节点
- 可点击坐标：[中心点坐标]
```

### 任务类型 B：数据提取
```
请提取 [应用名称] 界面中的以下信息：
1. [数据项 1]：路径 [...] -> 属性 [...]
2. [数据项 2]：路径 [...] -> 属性 [...]

输出格式：JSON 结构化数据
```

### 任务类型 C：界面理解
```
分析当前界面的功能和布局：
1. 应用名称和包名
2. 主要功能区域（顶部导航、内容区、底部导航）
3. 可交互元素列表
4. 当前页面状态（焦点、输入状态）
```

### 任务类型 D：操作建议
```
为实现 [目标操作]，请提供操作步骤：
1. 需要点击的元素（index、坐标）
2. 需要输入的文本
3. 需要滑动的方向和距离
```

## 示例：闲鱼商品分析提示词

```
请分析以下闲鱼应用的 a11y_tree 数据，提取首页推荐商品信息：

要求：
1. 定位 RecyclerView（resourceId: "com.taobao.idlefish:id/nested_recycler_view"）
2. 遍历商品卡片（FrameLayout children）
3. 提取每个商品的：
   - 商品描述（text 最长的 View 节点）
   - 价格（包含 "¥" 的 TextView，取纯数字部分）
   - 卖家昵称（商品描述下方的 TextView）
   - 点赞数（resourceId 包含 "like_count" 的节点）
   - 商品位置（bounds 的中心坐标）

输出格式：
[
  {
    "index": 商品卡片的 index,
    "description": "商品描述",
    "price": "价格（数字）",
    "seller": "卖家昵称",
    "likes": "点赞数（数字）",
    "clickPosition": [x, y]
  }
]

注意：忽略包含红包、广告等非商品内容的卡片
```

## 数据特征总结

### 闲鱼应用特征
- 商品列表：双列瀑布流布局
- 价格格式：TextView 包含 "¥" + 数字
- 底部导航：4-5 个 Tab，bounds.top ≈ 2263
- 搜索栏：resourceId 包含 "search_bar_layout"

### 系统设置特征
- 列表项：LinearLayout 包含 title + summary
- 滚动容器：ScrollView 包含 RecyclerView
- 搜索入口：resourceId 为 "search_action_bar"

### 桌面启动器特征
- 应用图标：TextView 包含应用名称
- Google 搜索栏：AppWidgetHostView 包含多个 ImageButton
- 布局容器：ScrollView (resourceId: "workspace")
