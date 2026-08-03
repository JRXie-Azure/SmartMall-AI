# SmartMall-AI — AI 驱动的智能电商全栈平台

[![Java](https://img.shields.io/badge/Java-17-orange)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3.2-green)](https://spring.io/projects/spring-boot)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

SmartMall-AI 是一个面向求职展示的 **AI 赋能电商全栈项目**，后端采用 Java 17 + Spring Boot 3.3.2，融合了 LLM 对话、RAG 商品知识库、协同过滤推荐、WebSocket 实时客服、API 限流和 Docker 容器化部署。

---

## 项目截图

| 首页 Hero + AI推荐 | 商品详情页 |
|:---:|:---:|
| ![首页](docs/screenshots/home.png) | ![商品详情](docs/screenshots/product_detail.png) |

| 管理后台仪表盘 | AI 智能分析 |
|:---:|:---:|
| ![管理后台](docs/screenshots/admin.png) | ![AI分析](docs/screenshots/ai_analysis.png) |

---

## 核心亮点

| 维度 | 能力 |
|------|------|
| **AI 对话** | DeepSeek LLM + Function Calling 工具调用，SSE 流式响应 |
| **RAG 知识库** | 手写 TF-IDF 向量化 + 余弦相似度语义检索（纯 Java 实现） |
| **智能推荐** | 协同过滤（用户行为）+ LLM 推理双层推荐 |
| **实时客服** | WebSocket 双向通信，AI 先接 → 人工接管 |
| **API 限流** | Redis 滑动窗口限流（AI 接口独立限流），内存降级 |
| **数据库迁移** | Flyway 版本管理，支持 H2 → MySQL 无缝切换 |
| **全文搜索** | 标题+描述+品牌+标签多字段搜索 |
| **权限体系** | Spring Security + JWT 认证 + RBAC 三角色（买家/商家/管理员） |
| **容器化** | Docker Compose 一键部署（Spring Boot + MySQL + Redis + Nginx） |

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3 CDN)                   │
│          index.html  ·  http://localhost:8000         │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / SSE / WebSocket
                       ▼
┌─────────────────────────────────────────────────────┐
│              Spring Boot 3.3.2 :8000                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ Security  │  │ RateLimit │  │   Controllers    │  │
│  │ JWT+RBAC  │  │ Redis/内存 │  │ 商品/订单/AI/管理 │  │
│  └──────────┘  └───────────┘  └────────┬─────────┘  │
│                                         │             │
│  ┌──────────────────────────────────────▼──────────┐ │
│  │              Service Layer                       │ │
│  │  LlmService · RagService · RecommendationService│ │
│  └──────────────────────────────────────┬──────────┘ │
│                                         │             │
│  ┌─────────────────┐  ┌────────────────▼──────────┐ │
│  │  Spring Data JPA │  │    WebSocket Handler      │ │
│  │  Hibernate       │  │    实时客服                │ │
│  └────────┬────────┘  └───────────────────────────┘ │
└───────────┼─────────────────────────────────────────┘
            │
            ▼
┌───────────────────┐  ┌───────────────────┐
│  H2 / MySQL       │  │  Redis            │
│  13 张表 + Flyway  │  │  缓存 + 限流计数   │
└───────────────────┘  └───────────────────┘
```

---

## 技术栈

### 后端（`backend-java/` 目录，Spring Boot 单体应用）

| 技术 | 用途 |
|------|------|
| Java 17 | 运行时 |
| Spring Boot 3.3.2 | 企业级 Web 框架（内嵌 Tomcat） |
| Spring Data JPA / Hibernate | ORM 数据库操作 |
| Flyway | 数据库迁移版本管理 |
| Spring Security | 认证与授权框架 |
| JJWT 0.12.6 | JWT 令牌生成与验证 |
| BCryptPasswordEncoder | 密码哈希加密 |
| WebSocket (Spring 原生) | 实时双向通信 |
| H2 / MySQL 8 | 数据库（开发用 H2 零配置，生产用 MySQL） |
| Redis (Lettuce) | 缓存 + 分布式限流（不可用时内存降级） |
| Maven | 构建工具 |

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 | 响应式前端框架（CDN 引入） |
| Vue Router 4 | 前端路由（Hash 模式） |
| Element Plus | UI 组件库 |
| ECharts | 数据可视化图表 |
| Font Awesome | 图标库 |

### AI 服务

| 技术 | 用途 |
|------|------|
| DeepSeek LLM | 大语言模型（兼容 OpenAI API 格式） |
| 手写 TF-IDF | 商品语义向量化（零重型依赖） |
| 余弦相似度 | 语义检索匹配 |
| User-Based 协同过滤 | 个性化推荐 |

---

## 项目结构

```
SmartMall-AI/
├── backend-java/                # ★ Java 后端（主后端）
│   ├── src/main/java/com/smartmall/
│   │   ├── SmartMallApplication.java     # Spring Boot 启动类
│   │   ├── config/
│   │   │   ├── SecurityConfig.java        # Spring Security 配置
│   │   │   ├── WebMvcConfig.java          # 静态资源 + 参数解析
│   │   │   ├── WebSocketConfig.java       # WebSocket 配置
│   │   │   ├── SmartMallProperties.java   # 业务配置绑定
│   │   │   └── ProductImageSeeder.java    # 商品图片种子
│   │   ├── controller/                    # REST API 控制器
│   │   │   ├── AuthController.java         # 认证（注册/登录）
│   │   │   ├── ProductController.java      # 商品管理
│   │   │   ├── OrderController.java        # 订单管理
│   │   │   ├── AiController.java           # AI 对话 + SSE 流式
│   │   │   ├── SearchController.java       # 搜索
│   │   │   ├── AdminController.java        # 管理后台
│   │   │   ├── CartController.java         # 购物车
│   │   │   ├── CouponController.java       # 优惠券
│   │   │   ├── SkuController.java          # SKU 管理
│   │   │   ├── BannerController.java       # Banner 管理
│   │   │   ├── MarketingController.java    # 营销活动
│   │   │   └── ...
│   │   ├── entity/                         # JPA 实体（13 张表）
│   │   ├── repository/                     # Spring Data JPA 接口
│   │   ├── service/                        # 业务逻辑层
│   │   │   ├── LlmService.java             # DeepSeek LLM 调用
│   │   │   ├── RagService.java             # TF-IDF 语义搜索
│   │   │   ├── RecommendationService.java  # 协同过滤推荐
│   │   │   └── ToolExecutorService.java    # Function Calling 工具
│   │   ├── security/                       # JWT + RBAC 安全模块
│   │   ├── common/                         # 通用组件（限流/缓存/异常）
│   │   ├── dto/                            # 请求/响应 DTO
│   │   └── websocket/                      # WebSocket 客服
│   ├── src/main/resources/
│   │   ├── application.yml                 # 主配置文件
│   │   └── db/migration/                   # Flyway 迁移脚本
│   │       ├── h2/                         # H2 建表 SQL
│   │       └── mysql/                      # MySQL 建表 SQL
│   └── pom.xml                             # Maven 配置
├── backend/                     # Python 后端（已弃用，保留参考）
│   └── static/
│       └── index.html            # 前端单文件应用（Java 后端共用）
├── docs/
│   └── screenshots/              # 项目截图
├── nginx/
│   └── nginx.conf                # 反向代理配置
├── docker-compose.yml            # 生产环境一键启动
├── docker-compose.dev.yml        # 开发环境（MySQL + Redis）
└── README.md
```

---

## 快速启动

### 方式一：本地开发（H2 内存库，零配置）

```bash
# 1. 进入 Java 后端目录
cd backend-java

# 2. 编译打包（跳过测试）
./mvnw clean package -DskipTests        # Linux/Mac
mvnw.cmd clean package -DskipTests      # Windows

# 3. 启动服务
java -jar target/smartmall-ai.jar

# 4. 访问
# 前端：http://localhost:8001
# 管理后台：http://localhost:8001/#/admin
```

> H2 文件库零配置启动，clone 即跑。Flyway 自动建表，ProductImageSeeder 自动填充数据。

### 方式二：本地开发 + MySQL/Redis

```bash
# 1. 启动 MySQL + Redis
docker-compose -f docker-compose.dev.yml up -d

# 2. 以 MySQL profile 启动
java -jar target/smartmall-ai.jar \
  --spring.profiles.active=mysql \
  --MYSQL_HOST=localhost \
  --MYSQL_DB=smartmall \
  --MYSQL_USER=root \
  --MYSQL_PASSWORD=smartmall123

# 3. 访问 http://localhost:8001
```

### 方式三：Docker Compose 全栈部署

```bash
# 1. 配置环境变量
export DEEPSEEK_API_KEY=your_api_key_here

# 2. 一键启动
docker-compose up -d

# 3. 访问
# 前端：http://localhost
# API：http://localhost/api/health
```

---

## 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 商家 | merchant | shop123 |
| 普通用户 | zhangwei | zw123456 |

---

## 功能体验指南

启动后端后，访问 `http://localhost:8001`：

| 功能 | 体验方式 |
|------|----------|
| **AI 对话** | 首页底部 AI 助手，输入"帮我找一双适合跑步的鞋" → LLM 调用 Function Calling 搜索商品 |
| **RAG 语义搜索** | AI 助手输入"轻便透气的运动鞋" → TF-IDF 语义匹配，非关键词匹配 |
| **智能推荐** | 登录后访问首页推荐区 → 基于浏览/收藏/购买行为的协同过滤 |
| **管理后台** | admin 登录 → 访问 `/#/admin` → 真实销售趋势/订单状态/热销排行图表 |
| **商品评价** | 点击任意商品 → 查看按品类定制的真实风格评价 |
| **WebSocket 客服** | 点击客服按钮 → AI 先接，输入"转人工"切换人工客服 |
| **API 限流** | 快速连续调用 AI 接口 → 触发 429 限流响应 |

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查（数据库/LLM/限流状态） |
| GET | `/api/products` | 商品列表（分页/搜索/排序/筛选） |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录（返回 JWT） |
| GET | `/api/auth/me` | 获取当前用户信息（含角色） |
| GET | `/api/cart/items` | 购物车列表 |
| POST | `/api/cart/items` | 添加商品到购物车 |
| GET | `/api/orders` | 订单历史 |
| POST | `/api/orders` | 创建订单 |
| POST | `/api/ai/chat/stream` | AI 对话（SSE 流式） |
| GET | `/api/ai/status` | AI 服务状态 |
| POST | `/api/ai/rag/search` | RAG 语义搜索 |
| GET | `/api/ai/recommendations` | AI 智能推荐 |
| GET | `/api/search?q=` | 全文搜索 |
| WS | `/api/ws/chat` | WebSocket 实时客服 |
| GET | `/api/admin/stats` | 管理后台统计 |

---

## AI 功能详解

### 1. 智能对话助手
- 基于 DeepSeek 大语言模型（deepseek-chat）
- Function Calling 工具调用（搜索商品、查详情、语义搜索、个性化推荐）
- SSE 流式响应（`/api/ai/chat/stream`），打字机效果
- 多轮对话上下文记忆
- 无 API Key 时自动降级为内置话术

### 2. RAG 商品知识库
- 手写 TF-IDF 向量化商品信息（名称+品牌+描述+分类+标签）
- 余弦相似度语义检索，支持"适合跑步的鞋子"等自然语言查询
- 纯 Java 实现，零重型依赖，秒级启动

### 3. 协同过滤推荐
- 基于用户浏览/购买/收藏行为的 User-Based 协同过滤
- 交互矩阵权重：浏览=1，收藏=3，购买=5
- 冷启动策略：相似用户 → 内容推荐 → 热销降级

### 4. WebSocket 实时客服
- Spring WebSocket 双向实时消息推送
- AI 先接，解决不了自动转人工
- 心跳机制 + 断线重连

---

## API 限流

| 接口类型 | 限制 | 说明 |
|----------|------|------|
| 普通 API | 100 次/分钟 | 商品/订单/购物车等 |
| AI 接口 | 20 次/分钟 | `/api/ai/*` 防止 LLM 滥用 |
| 健康检查 | 不限 | `/api/health` |

- 优先使用 Redis 滑动窗口（分布式限流，多实例共享）
- Redis 不可用时自动降级为内存限流（单实例）
- 超限返回 `429 Too Many Requests` + `Retry-After` 头

---

## 数据库迁移（Flyway）

```bash
# 迁移脚本位于 src/main/resources/db/migration/
# H2:  h2/V1__init_schema.sql, h2/V2__add_sku_coupon_marketing.sql
# MySQL: mysql/V1__init_schema.sql, mysql/V2__add_sku_coupon_marketing.sql

# 应用启动时 Flyway 自动执行迁移，无需手动操作
# 新增迁移脚本命名规则: V{n}__description.sql
```

---

## 数据模型（13 张表）

- **User** — 用户（买家/商家/管理员）
- **Address** — 收货地址
- **Category** — 商品分类
- **Product** — 商品
- **ProductSKU** — 商品 SKU
- **ProductVariant** — 商品规格变体
- **CartItem** — 购物车项
- **Order** — 订单
- **OrderItem** — 订单明细
- **Review** — 商品评价
- **ProductView** — 浏览记录（用于推荐）
- **Favorite** — 收藏
- **Coupon** — 优惠券
- **UserCoupon** — 用户优惠券
- **Banner** — 首页 Banner
- **MarketingCampaign** — 营销活动
- **SiteConfig** — 系统配置
- **ChatSession** — 客服会话
- **ChatMessage** — 客服消息
- **SearchHistory** — 搜索历史

---

## 配置说明

主配置文件 `backend-java/src/main/resources/application.yml`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `server.port` | 8001 | 服务端口 |
| `spring.profiles.active` | h2 | 数据库 profile（h2/mysql） |
| `smartmall.jwt.secret-key` | dev-key | JWT 签名密钥（生产必须覆盖） |
| `smartmall.llm.deepseek-api-key` | 空 | DeepSeek API Key |
| `smartmall.rate-limit.enabled` | true | 是否启用限流 |
| `smartmall.cache.redis-enabled` | true | 是否启用 Redis 缓存 |

环境变量覆盖（Docker 部署用）：

```bash
SERVER_PORT=8000
SPRING_PROFILES_ACTIVE=mysql
DEEPSEEK_API_KEY=sk-xxxxx
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=smartmall
MYSQL_USER=root
MYSQL_PASSWORD=smartmall123
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 前端体验优化

- **骨架屏加载**：首页/商品列表/AI推荐/新品/特惠页全部采用 Shimmer 骨架屏
- **图片懒加载淡入**：商品图片加载完成后 opacity 0→1 平滑过渡
- **搜索防抖**：300ms debounce，避免每输入一个字符都触发搜索
- **网络错误横幅**：API 请求失败时顶部显示红色提示条，恢复后自动消失
- **紫蓝渐变 Hero**：固定背景视差 + 浮动商品卡片动画
- **响应式布局**：适配桌面和移动端

---

## License

MIT
