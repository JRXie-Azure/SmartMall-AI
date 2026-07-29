# SmartMall-AI — AI 驱动的智能电商全栈平台

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-30%20passed-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

SmartMall-AI 是一个面向求职展示的 **AI 赋能电商全栈项目**，融合了 LLM 对话、RAG 商品知识库、协同过滤推荐、WebSocket 实时客服、API 限流和 Docker 容器化部署。

---

## 📸 项目截图

| 首页 Hero + AI推荐 | 商品详情页 |
|:---:|:---:|
| ![首页](docs/screenshots/home.png) | ![商品详情](docs/screenshots/product_detail.png) |

| 管理后台仪表盘 | AI 智能分析 |
|:---:|:---:|
| ![管理后台](docs/screenshots/admin.png) | ![AI分析](docs/screenshots/ai_analysis.png) |

---

## 🎯 核心亮点

| 维度 | 能力 |
|------|------|
| **AI 对话** | DeepSeek V4 LLM + Function Calling 工具调用，SSE 流式响应 |
| **RAG 知识库** | TF-IDF 向量化 + 余弦相似度语义检索（scikit-learn） |
| **智能推荐** | 协同过滤（用户行为）+ LLM 推理双层推荐 |
| **实时客服** | WebSocket 双向通信，AI 先接 → 人工接管 |
| **API 限流** | Redis 滑动窗口限流（AI 接口独立限流），内存降级 |
| **数据库迁移** | Alembic 版本管理，支持 SQLite → MySQL 无缝切换 |
| **全文搜索** | 标题+描述+品牌+标签多字段搜索 |
| **权限体系** | JWT 认证 + RBAC 三角色（买家/商家/管理员） |
| **容器化** | Docker Compose 一键部署（FastAPI + MySQL + Redis + Nginx） |
| **测试覆盖** | pytest 30 个测试（认证/商品/AI/RAG/推荐/限流/迁移/部署/评价） |

---

## 🏗 系统架构

```mermaid
graph TB
    subgraph 前端
        Vue["Vue 3 + Vite + Element Plus :5173"]
        Single["单文件应用 (CDN) :8001"]
    end

    subgraph "后端 FastAPI :8001"
        MW["限流中间件<br/>Redis 滑动窗口 / 内存降级"]
        Auth["JWT + RBAC 认证<br/>买家/商家/管理员"]
        Router["API 路由层<br/>商品/订单/AI/管理后台"]
    end

    subgraph "AI 服务层"
        LLM["DeepSeek V4 LLM<br/>Function Calling + SSE"]
        RAG["RAG 语义搜索<br/>TF-IDF + 余弦相似度"]
        CF["协同过滤推荐<br/>User-Based CF"]
        WS["WebSocket 客服<br/>AI 接入 → 人工接管"]
    end

    subgraph "数据层"
        DB[("MySQL 8 / SQLite<br/>13 张表 + Alembic 迁移")]
        Cache[("Redis<br/>缓存 + 限流计数")]
    end

    Vue -->|"HTTP / SSE"| Router
    Single -->|"HTTP"| Router
    Router --> MW
    MW --> Auth
    Auth --> DB
    Router --> LLM
    Router --> RAG
    Router --> CF
    Router --> WS
    RAG --> DB
    CF --> DB
    MW --> Cache
```

---

## 🛠 技术栈

```
前端：Vue 3 + Vite + Element Plus + Pinia + Axios + ECharts
后端：FastAPI + SQLAlchemy + Alembic + Pydantic
AI  ：DeepSeek V4 + Function Calling + SSE 流式
RAG ：scikit-learn TF-IDF + 余弦相似度
推荐：scikit-learn 协同过滤（User-Based CF）
限流：Redis 滑动窗口（内存降级 fallback）
数据：MySQL 8 + Redis（SQLite 自动降级）
实时：WebSocket (FastAPI 原生)
部署：Docker + Docker Compose + Nginx
测试：pytest + TestClient
```

### 技术选型理由

| 选择 | 理由 |
|------|------|
| **FastAPI** 而非 Django/Flask | 异步原生支持（SSE/WebSocket）、自动 OpenAPI 文档、Pydantic 类型安全 |
| **TF-IDF** 而非 sentence-transformers | 零重型依赖、秒级启动、适配所有 Python 版本； sacrificing 精度换取部署友好 |
| **DeepSeek** 而非 OpenAI | 国产大模型、API 兼容 OpenAI 格式、成本低；支持 Function Calling |
| **SQLite 降级** 而非强制 MySQL | 零配置启动（面试官 clone 即跑）、演示友好；生产环境切 MySQL 仅改一行配置 |
| **Redis 内存降级** | Redis 不可用时自动降级为内存限流，保证服务可用性 |
| **Alembic** 而非 `create_all` | 版本化数据库迁移、支持回滚、生产环境标准实践 |

---

## 📦 项目结构

```
SmartMall-AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + 中间件注册
│   │   ├── config.py            # 多环境配置（MySQL/Redis/DeepSeek/限流）
│   │   ├── models.py            # 13 张数据表 ORM 模型
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── database.py          # MySQL + Redis 双数据源（缓存降级）
│   │   ├── auth.py              # JWT + RBAC 认证授权
│   │   ├── middleware.py        # 限流中间件 + 请求日志
│   │   ├── seed.py              # 种子数据（45 商品 + 10 用户 + 95 订单 + 75 评价）
│   │   ├── routers/
│   │   │   ├── products.py      # 商品管理（CRUD + 缓存）
│   │   │   ├── auth.py          # 注册/登录
│   │   │   ├── cart.py          # 购物车
│   │   │   ├── orders.py        # 订单状态机（6 状态）
│   │   │   ├── ai.py            # LLM 对话 + RAG + SSE 流式
│   │   │   ├── admin.py         # 管理后台（图表 + CRUD）
│   │   │   ├── search.py        # 全文搜索引擎
│   │   │   └── websocket.py     # WebSocket 实时客服
│   │   └── services/
│   │       ├── llm_service.py           # DeepSeek LLM 服务
│   │       ├── rag_service.py           # RAG 向量检索
│   │       └── recommendation_service.py # 协同过滤推荐
│   ├── alembic/                 # Alembic 数据库迁移
│   │   ├── env.py               # 迁移环境配置
│   │   └── versions/            # 迁移脚本
│   ├── tests/                   # pytest 测试套件（30 个测试）
│   ├── alembic.ini              # Alembic 配置
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/               # 10 个页面
│   │   ├── components/          # 可复用组件
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── api/                 # Axios API 封装
│   │   └── router/              # Vue Router 路由
│   └── Dockerfile
├── nginx/
│   └── nginx.conf               # 反向代理 + HTTPS
├── docker-compose.yml           # 生产环境一键启动全栈
├── docker-compose.dev.yml       # 开发环境（仅 MySQL + Redis）
└── README.md
```

---

## 🚀 快速启动

### 方式一：本地开发（SQLite，零依赖）

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt
python -m app.seed            # 初始化数据（45 商品 + 10 用户 + 95 订单）
uvicorn app.main:app --port 8001 --reload

# 运行测试
venv\Scripts\python.exe -m pytest tests/ -v

# 前端
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### 方式二：本地开发 + MySQL/Redis（Docker）

```bash
# 1. 启动 MySQL + Redis
docker-compose -f docker-compose.dev.yml up -d

# 2. 修改 backend/.env
#    DATABASE_URL=mysql+pymysql://root:smartmall123@localhost:3306/smartmall?charset=utf8mb4
#    REDIS_URL=redis://localhost:6379/0

# 3. 运行数据库迁移 + 填充数据
cd backend
alembic upgrade head           # 创建表结构
python -m app.seed             # 填充演示数据

# 4. 启动后端
uvicorn app.main:app --port 8001 --reload
```

### 方式三：Docker Compose 全栈部署

```bash
# 1. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env，填入 DeepSeek API Key

# 2. 一键启动
docker-compose up -d

# 3. 访问
# 前端：http://localhost
# API 文档：http://localhost:8001/docs
```

---

## 🔑 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 商家 | merchant | shop123 |
| 普通用户 | zhangwei | zw123456 |

---

## 🎮 功能体验指南

启动后端后（`uvicorn app.main:app --port 8001`），访问 `http://localhost:8001`：

| 功能 | 体验方式 |
|------|----------|
| **AI 对话** | 首页底部 AI 助手，输入"帮我找一双适合跑步的鞋" → LLM 调用 Function Calling 搜索商品 |
| **RAG 语义搜索** | AI 助手输入"轻便透气的运动鞋" → TF-IDF 语义匹配，非关键词匹配 |
| **智能推荐** | 登录后访问首页推荐区 → 基于浏览/收藏/购买行为的协同过滤 |
| **管理后台** | admin 登录 → 访问 `/#/admin` → 真实销售趋势/订单状态/热销排行图表 |
| **商品评价** | 点击任意商品 → 查看按品类定制的真实风格评价 |
| **WebSocket 客服** | 点击客服按钮 → AI 先接，输入"转人工"切换人工客服 |
| **API 限流** | 快速连续调用 AI 接口 → 触发 429 限流响应 |
| **API 文档** | 访问 `/docs` → FastAPI 自动生成的交互式 Swagger 文档 |

---

## 📡 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查（数据库/LLM/限流状态） |
| GET | `/api/products` | 商品列表（分页/搜索/排序/筛选） |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录（返回 JWT） |
| GET | `/api/cart/items` | 购物车列表 |
| POST | `/api/cart/items` | 添加商品到购物车 |
| GET | `/api/orders` | 订单历史 |
| POST | `/api/orders` | 创建订单 |
| POST | `/api/ai/chat` | AI 对话（SSE 流式） |
| GET | `/api/ai/status` | AI 服务状态 |
| POST | `/api/ai/rag/search` | RAG 语义搜索 |
| GET | `/api/ai/recommendations` | AI 智能推荐 |
| GET | `/api/search?q=` | 全文搜索 |
| WS | `/api/ws/chat` | WebSocket 实时客服 |
| GET | `/api/admin/stats` | 管理后台统计 |

完整 API 文档：启动后访问 `http://localhost:8001/docs`

---

## 📊 AI 功能详解

### 1. 智能对话助手
- 基于 DeepSeek V4 大模型（deepseek-v4-flash）
- Function Calling 工具调用（搜索商品、查详情、语义搜索、个性化推荐）
- SSE 流式响应，打字机效果
- 多轮对话上下文记忆

### 2. RAG 商品知识库
- TF-IDF 向量化商品信息（名称+品牌+描述+分类+标签）
- 余弦相似度语义检索，支持"适合跑步的鞋子"等自然语言查询
- 无重型依赖（scikit-learn 实现），适配所有 Python 版本

### 3. 协同过滤推荐
- 基于用户浏览/购买/收藏行为的 User-Based 协同过滤
- 交互矩阵权重：浏览=1，收藏=3，购买=5
- 冷启动策略：相似用户 → 内容推荐 → 热销降级

### 4. WebSocket 实时客服
- 双向实时消息推送
- AI 先接，解决不了自动转人工
- 心跳机制 + 断线重连

---

## 🛡️ API 限流

| 接口类型 | 限制 | 说明 |
|----------|------|------|
| 普通 API | 100 次/分钟 | 商品/订单/购物车等 |
| AI 接口 | 20 次/分钟 | `/api/ai/*` 防止 LLM 滥用 |
| 健康检查 | 不限 | `/api/health` |

- 优先使用 Redis 滑动窗口（分布式限流，多实例共享）
- Redis 不可用时自动降级为内存限流（单实例）
- 超限返回 `429 Too Many Requests` + `Retry-After` 头

---

## 📐 数据库迁移（Alembic）

```bash
# 生成迁移脚本（检测模型变更）
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

---

## 🏗 数据模型（13 张表）

- **User** — 用户（买家/商家/管理员）
- **Address** — 收货地址
- **Category** — 商品分类
- **Product** — 商品
- **CartItem** — 购物车项
- **Order** — 订单
- **OrderItem** — 订单明细
- **Review** — 商品评价
- **ProductView** — 浏览记录（用于推荐）
- **Favorite** — 收藏
- **ChatSession** — 客服会话
- **ChatMessage** — 客服消息
- **SearchHistory** — 搜索历史

---

## ✨ 前端体验优化

- **骨架屏加载**：首页/商品列表/AI推荐/新品/特惠页全部采用 Shimmer 骨架屏，替代传统 Spinner
- **图片懒加载淡入**：商品图片加载完成后 opacity 0→1 平滑过渡
- **搜索防抖**：300ms debounce，避免每输入一个字符都触发搜索请求
- **网络错误横幅**：API 请求失败时顶部显示红色提示条，恢复后自动消失
- **紫蓝渐变 Hero**：固定背景视差 + 浮动商品卡片动画
- **响应式布局**：适配桌面和移动端

---

## 📝 License

MIT
