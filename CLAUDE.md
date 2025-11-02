# CLAUDE.md

如果写文档没有特殊说明,都以md 格式放到,notes 目录

这是一个 uv 框架的 python 项目
运行代码要用  uv run xxx.py
安装包要用 uv add 包名

## 项目结构

### src/ 主要模块
- **main.py** - 程序入口，初始化 LLM 并执行 LangGraph 工作流
- **agents/** - LangGraph Agent 定义
  - state.py - 状态管理（TypedDict）
  - nodes.py - 工作流节点（capture/analyze/generate/execute/verify）
- **graph/** - LangGraph 工作流构建
  - builder.py - 创建和编译状态图
- **tools/** - 工具集
  - android.py - Android ADB 操作工具
  - vision.py - 视觉分析工具
  - file.py - 文件操作工具
- **models/** - 数据模型（Pydantic schemas）
- **utils/** - 工具函数
  - config.py - 配置管理（API/ADB/输出配置）
  - logger.py - 日志工具
  - ui_processor.py - UI 界面处理

### 工作流程
capture → analyze → generate_code → execute → verify

### 主要依赖
- LangGraph - 工作流编排
- droidrun - Android 设备操作




