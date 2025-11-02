# CLAUDE.md

如果写文档没有特殊说明,都以md 格式放到,notes 目录

这是一个 uv 框架的 python 项目
运行代码要用  uv run xxx.py
安装包要用 uv add 包名

## 核心设计原则

### 1. 自研框架 - 完全控制
- **不使用 LangGraph**：抛弃外部框架束缚，完全自主控制执行流程
- **异步并发优先**：使用 asyncio 实现并发感知、后台观察等核心特性
- **性能优势**：并发感知速度提升 3 倍（0.5s vs 1.5s）
- **代码简洁**：即时反馈 1 个函数搞定（vs LangGraph 5 个节点）

### 2. 双层 Agent 架构
- **Master Agent（任务管理层）**：
  - 任务分解与调度
  - Worker 执行监督
  - 异常检测与恢复
  - 循环任务管理

- **Worker Agent（认知执行层）**：
  - 观察屏幕（并发感知）
  - 决策操作（CoT + 元认知）
  - 执行动作（即时反馈）
  - 记忆管理

### 3. 人类认知模拟
- **观察 → 思考 → 决策 → 执行 → 反馈** 完整循环
- **工作记忆**：7±2 容量，循环检测，时间衰减
- **长期记忆**：经验积累，向量检索，首次探索后续直达
- **持续观察**：后台 0.5 秒间隔监控，自动处理弹窗/加载/错误
- **试错纠错**：执行后 0.5 秒即时判断，错误立即回退

## 项目目录结构

```
droidrun-vl/
│
├── src/                          # 核心源代码
│   ├── core/                     # 核心认知引擎（自研）
│   │   ├── master_agent.py       # Master Agent（任务管理）
│   │   ├── worker_agent.py       # Worker Agent（认知执行）
│   │   ├── cognitive_loop.py     # 认知主循环
│   │   └── state_manager.py      # 状态管理器
│   │
│   ├── perception/               # 感知系统（并发）
│   │   ├── vision_analyzer.py    # 视觉分析（VL 模型）
│   │   ├── ui_detector.py        # UI 元素检测
│   │   ├── ocr_extractor.py      # 文本提取
│   │   ├── screen_observer.py    # 持续观察（后台任务）
│   │   └── fusion.py             # 多模态融合
│   │
│   ├── decision/                 # 决策系统
│   │   ├── decision_maker.py     # 核心决策器（CoT）
│   │   ├── metacognition.py      # 元认知监控
│   │   ├── planner.py            # 任务规划器
│   │   └── risk_evaluator.py     # 风险评估
│   │
│   ├── execution/                # 执行系统
│   │   ├── action_executor.py    # 动作执行（tap/swipe/input）
│   │   ├── feedback_controller.py # 即时反馈控制器
│   │   ├── trial_error.py        # 试错机制
│   │   └── recovery.py           # 异常恢复
│   │
│   ├── memory/                   # 记忆系统
│   │   ├── working_memory.py     # 工作记忆（7±2, deque）
│   │   ├── vector_store.py       # 向量存储（LanceDB）
│   │   ├── long_term_memory.py   # 长期记忆管理
│   │   ├── spatial_memory.py     # 空间记忆（页面导航图）
│   │   └── retriever.py          # 经验检索器
│   │
│   ├── device/                   # 设备交互层
│   │   ├── android_controller.py # Android 控制器（基于 droidrun）
│   │   ├── adb_tools.py          # ADB 工具封装
│   │   └── screen_capture.py     # 截屏工具
│   │
│   ├── models/                   # 数据模型（Pydantic）
│   │   ├── task.py               # 任务模型
│   │   ├── action.py             # 动作模型
│   │   ├── perception.py         # 感知结果模型
│   │   ├── decision.py           # 决策模型
│   │   └── experience.py         # 经验模型
│   │
│   ├── llm/                      # LLM 集成
│   │   ├── client.py             # LLM 客户端（统一接口）✅
│   │   ├── prompts/              # Prompt 模板
│   │   └── parsers.py            # 输出解析器
│   │
│   ├── utils/                    # 工具函数
│   │   ├── config.py             # 配置管理 ✅
│   │   ├── logger.py             # 日志系统
│   │   ├── metrics.py            # 性能指标
│   │   └── helpers.py            # 辅助函数
│   │
│   └── main.py                   # 程序入口
│
├── data/                         # 数据存储
│   ├── experiences/              # 经验库
│   │   └── vector_db/            # 向量数据库（LanceDB）✅
│   ├── spatial_maps/             # 空间记忆
│   ├── screenshots/              # 运行时截图
│   └── logs/                     # 执行日志
│
├── configs/                      # 配置文件
│   └── config.yaml               # 统一配置文件 ✅
│
├── examples/                     # 示例代码
│   ├── simple_task.py            # 简单任务示例
│   ├── loop_task.py              # 循环任务示例
│   └── recovery_demo.py          # 异常恢复演示
│
├── tests/                        # 测试目录
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   └── fixtures/                 # 测试数据
│
├── notes/                        # 设计文档
│   ├── 顶层架构设计2.md
│   ├── 项目工程代码结构规划2.md
│   └── ...
│
├── pyproject.toml                # 项目配置
├── uv.lock                       # 依赖锁定
├── README.md
└── CLAUDE.md                     # 本文件
```

## 模型配置

### Embedding 模型
- API Base: `http://192.168.18.9:8081/v1`
- Model: `/models`
- 用途: 文本向量化，用于经验检索

### Qwen3-VL 视觉语言模型
- API Base: `http://192.168.18.9:8080/v1`
- Model: `/models`
- 用途: 屏幕理解、决策生成、任务规划

### 向量数据库
- 类型: LanceDB
- 路径: `data/experiences/vector_db/`
- 用途: 长期记忆存储，经验检索

## 开发状态

### 已完成 ✅
- [x] 项目目录结构
- [x] 配置管理模块（`src/utils/config.py`）
- [x] LLM 客户端封装（`src/llm/client.py`）
- [x] 向量存储封装（`src/memory/vector_store.py`）

### 进行中 🚧
- [ ] 基础数据模型（`src/models/*.py`）
- [ ] Master Agent 核心实现
- [ ] Worker Agent 认知循环
- [ ] 感知系统（并发）
- [ ] 决策系统（CoT + 元认知）
- [ ] 执行系统（即时反馈）

## 快速开始

### 安装依赖
```bash
uv add openai pydantic lancedb pyyaml loguru
```

### 测试配置
```bash
uv run src/utils/config.py
```

### 测试 LLM 客户端
```bash
uv run src/llm/client.py
```

### 测试向量存储
```bash
uv run src/memory/vector_store.py
```

