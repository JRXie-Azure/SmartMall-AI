# SmartMall-AI — AI 驱动的智能电商全栈平台

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://www.docker.com/)

SmartMall-AI 是一个面向求职展示的 **AI 赋能电商全栈项目**，融合了 LLM 对话、RAG 商品知识库、协同过滤推荐、WebSocket 实时客服和 Docker 容器化部署。

---

## 🎯 核心亮点

| 维度 | 能力 |
|------|------|
| **AI 对话** | DeepSeek LLM + Function Calling 工具调用，SSE 流式响应 |
| **RAG 知识库** | ChromaDB 向量检索 + Sentence-Transformers 语义搜索 |
| **智能推荐** | 协同过滤（用户行为）+ LLM 推理双层推荐 |
| **实时客服** | WebSocket 双向通信，AI 先接 → 人工接管 |
| **全文搜索** | 标题+描述全文搜索，拼音兼容 |
| **权限体系** | JWT 认证 + RBAC 三角色（买家/商家/管理员） |
| **容器化** | Docker Compose 一键部署（FastAPI + MySQL + Redis + Nginx） |

---

## 🛠 技术栈

```
前端：Vue 3 + Vite + Element Plus + Pinia + Axios + ECharts
后端：FastAPI + SQLAlchemy + Alembic + Pydantic
AI  ：LangChain + DeepSeek + ChromaDB + Sentence-Transformers
数据：MySQL 8 + Redis + MinIO
实时：WebSocket (FastAPI 原生)
部署：Docker + Docker Compose + Nginx
```

---

## 📦 项目结构

```
SmartMall-AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 多环境配置（MySQL/Redis/DeepSeek/ChromaDB）
│   │   ├── models.py            # 15+ 张数据表 ORM 模型
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── database.py          # MySQL + Redis 双数据源
│   │   ├── auth.py              # JWT + RBAC 认证授权
│   │   ├── seed.py              # 种子数据（16 商品 + 测试账号）
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
├── docker-compose.yml           # 一键启动全栈
└── README.md
```

---

## 🚀 快速启动

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/SmartMall-AI.git
cd SmartMall-AI

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env，填入 DeepSeek API Key

# 3. 一键启动
docker-compose up -d

# 4. 访问
# 前端：http://localhost
# API 文档：http://localhost:8001/docs
```

### 方式二：本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python app/seed.py          # 初始化数据
uvicorn app.main:app --port 8001

# 前端
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

---

## 🔑 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 普通用户 | demo | demo123 |

---

## 📡 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/products` | 商品列表（分页/搜索/排序/筛选） |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录（返回 JWT） |
| GET | `/api/cart/items` | 购物车列表 |
| POST | `/api/cart/items` | 添加商品到购物车 |
| GET | `/api/orders` | 订单历史 |
| POST | `/api/orders` | 创建订单 |
| POST | `/api/ai/chat` | AI 对话（SSE 流式） |
| GET | `/api/ai/recommend` | AI 智能推荐 |
| GET | `/api/search?q=` | 全文搜索 |
| WS | `/api/ws/chat` | WebSocket 实时客服 |
| GET | `/api/admin/stats` | 管理后台统计 |
| GET | `/api/admin/charts` | ECharts 图表数据 |

完整 API 文档：启动后访问 `http://localhost:8001/docs`

---

## 📊 AI 功能详解

### 1. 智能对话助手
- 基于 DeepSeek-V3 大模型
- Function Calling 工具调用（搜索商品、查订单）
- SSE 流式响应，打字机效果
- 多轮对话上下文记忆

### 2. RAG 商品知识库
- ChromaDB 向量数据库，语义级商品检索
- Sentence-Transformers 中英文向量化
- 支持"适合跑步的鞋"等自然语言查询

### 3. 协同过滤推荐
- 基于用户浏览/购买行为的协同过滤
- 混合冷启动策略（热门 + 内容推荐）
- LLM 推理补充解释推荐原因

### 4. WebSocket 实时客服
- 双向实时消息推送
- AI 先接，解决不了自动转人工
- 心跳机制 + 断线重连

---

## 🏗 数据模型（15 张表）

- **User** — 用户（买家/商家/管理员）
- **Category** — 商品分类
- **Product** — 商品
- **ProductImage** — 商品图片
- **ProductView** — 浏览记录（用于推荐）
- **CartItem** — 购物车项
- **Order** — 订单
- **OrderItem** — 订单明细
- **Favorite** — 收藏
- **SearchHistory** — 搜索历史
- **ChatSession** — 客服会话
- **ChatMessage** — 客服消息
- **Review** — 商品评价

---

## 📝 License

MIT
