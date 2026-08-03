# SmartMall-AI 后端迁移完成报告
### Python (FastAPI) → Java (Spring Boot 3) · 全量接口兼容 · 完整演示指南

> 报告生成时间：2026-08-03
> 本报告面向无项目上下文的读者/Agent，包含：迁移成果、启动步骤、可执行演示脚本、接口清单、数据账号、关键约定与已知事项。照此操作即可完整复现演示。

---

## 1. 项目概览

SmartMall-AI 是一个 AI 增强的 B2C 电商商城（Vue3 前端 + 后端 API），核心能力：

- **商城基础**：商品浏览/搜索/筛选、购物车、下单、模拟支付、订单管理、收藏、评价
- **管理后台**：运营统计（销售/用户/订单/热销 TOP）、商品/用户/订单管理、RBAC 权限
- **AI 能力**：DeepSeek LLM 对话客服、协同过滤商品推荐、RAG 商品检索、WebSocket 客服

本次迁移将后端从 **Python FastAPI + SQLAlchemy + SQLite** 整体迁移到 **Java Spring Boot 3 + Spring Data JPA + H2（MySQL 兼容）**，前端零改动。

## 2. 迁移成果摘要

| 维度 | 结果 |
|---|---|
| 接口兼容性 | **35/35 全量比对通过**（与 Python 逐字段一致，连排序并列的兜底顺序都对齐），连跑 3 轮稳定 |
| 业务链路 | 9 大环节 30+ 接口端到端演示全部 OK |
| 数据 | 13 张表完整迁移：45 商品 / 95 订单 / 75 评价 / 128 浏览 / 24 收藏 / 15 搜索历史 / 10 用户 |
| 运行态 | 前端 Vite → 代理 → Java 后端（H2），LLM 已启用（deepseek-v4-flash） |
| 生产就绪 | 双 profile：`h2`（零配置开发）/ `mysql`（生产，Flyway + 迁移脚本，静态验证已过） |

### 技术栈对比

| | Python（旧） | Java（新） |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | Spring Boot 3 (WebMVC) |
| ORM | SQLAlchemy | Spring Data JPA + Hibernate |
| 认证 | PyJWT | jjwt + Spring Security 过滤器链 |
| 数据库 | SQLite | H2 (MODE=MySQL) / MySQL 8 |
| 迁移 | — | Flyway（h2/mysql 两套脚本） |
| LLM | openai SDK | Spring RestClient 直连 DeepSeek/OpenAI |
| 构建 | pip/venv | Maven → 可执行 fat-jar |

## 3. 代码结构（backend-java）

```
backend-java/
├── src/main/java/com/smartmall/
│   ├── controller/      # 11 个 REST 控制器（auth/products/search/cart/orders/payment/admin/ai/chat...）
│   ├── service/         # 业务服务（LLM/RAG/协同过滤/支付）
│   ├── repository/      # Spring Data JPA（13 张表）
│   ├── entity/          # JPA 实体
│   ├── dto/             # 请求/响应 DTO（snake_case 对齐前端）
│   ├── config/          # Security / WebMvc / WebSocket / 限流
│   └── common/          # 全局异常处理、缓存、ApiException
├── src/main/resources/
│   ├── application.yml          # 双 profile 配置（h2/mysql）
│   └── db/migration/{h2,mysql}/ # Flyway 表结构脚本
├── tools/
│   ├── compare_api.py           # 接口比对脚本（Python 基准 vs Java）
│   ├── demo_flow.py             # ★ 完整业务流演示脚本（本报告第 5 节）
│   ├── migrate_sqlite.py        # SQLite → H2/MySQL SQL 数据迁移
│   └── dist/data_h2.sql         # 已生成的 H2 数据
├── docs/
│   ├── MYSQL_DEPLOY.md          # MySQL 部署指南
│   └── MIGRATION_REPORT.md      # 本报告
└── target/smartmall-ai.jar      # 可执行产物
```

## 4. 启动步骤（照做即可）

### 4.1 环境
- JDK 17（本项目使用：`C:/Users/谢键荣/.workbuddy/binaries/java/jdk-17.0.13+11`）
- 前端依赖已装（`frontend/node_modules` 存在）

### 4.2 启动 Java 后端（端口 8001，含 LLM）

```bash
export JAVA_HOME="C:/Users/谢键荣/.workbuddy/binaries/java/jdk-17.0.13+11"
cd /c/Users/谢键荣/SmartMall-AI/backend-java

# LLM key 取自 Python 侧 .env（与本项目共用）
DEEPSEEK_API_KEY=$(grep "^DEEPSEEK_API_KEY=" ../backend/.env | cut -d= -f2-)
DEEPSEEK_BASE_URL=$(grep "^DEEPSEEK_BASE_URL=" ../backend/.env | cut -d= -f2-)
DEEPSEEK_MODEL=$(grep "^DEEPSEEK_MODEL=" ../backend/.env | cut -d= -f2-)
export DEEPSEEK_API_KEY DEEPSEEK_BASE_URL DEEPSEEK_MODEL

"$JAVA_HOME/bin/java" -jar target/smartmall-ai.jar --server.port=8001
```

若 jar 不存在则先构建：
```bash
"C:/Users/谢键荣/.workbuddy/binaries/maven/apache-maven-3.9.9/bin/mvn.cmd" -q -o package -DskipTests
```

健康检查（应看到 `llm_enabled: true`）：
```bash
curl http://127.0.0.1:8001/api/health
# {"status":"ok","version":"2.0.0","llm_enabled":true,"llm_model":"deepseek-v4-flash","database":"H2","rate_limit":"enabled"}
```

### 4.3 启动前端（端口 5173，代理指向 8001）

```bash
cd /c/Users/谢键荣/SmartMall-AI/frontend
node node_modules/vite/bin/vite.js --port 5173   # 用本机 node
```

访问 **http://localhost:5173**（注意：Vite 默认只监听 IPv6 `[::1]`，请用 `localhost` 而非 `127.0.0.1`）。`vite.config.js` 已把 `/api`、`/static` 代理到 `http://localhost:8001`，WebSocket 已启用。

## 5. 完整演示（两种方式）

### 方式 A：一键 API 全链路演示（推荐，可自动化）

```bash
cd /c/Users/谢键荣/SmartMall-AI/backend-java
python tools/demo_flow.py     # 用本机 python3
```

脚本自动执行 9 阶段，覆盖 30+ 接口，输出示例：

```
① 系统健康检查        → status=ok  database=H2  llm_enabled=True
② 用户注册 → 登录     → 注册成功: demo_xxxxxx / user
③ 商品浏览            → total=45；价格升序 ¥199→¥459；分类/关键词/详情/评价
④ 搜索与联想          → '手机' 命中 Samsung Galaxy S24 Ultra；联想 ni→3商品3品牌；热门/品牌榜
⑤ 收藏 + 购物车       → 收藏#30；加购2种共3件；角标=2
⑥ 下单 → 支付         → 下单 SM... ¥857 → pay(支付宝/微信/银行卡,1800s) → pay-confirm → paid → 统计正确
⑦ AI 能力             → 协同过滤推荐 5 个；RAG 检索'跑步鞋' 5 条
⑧ 管理后台            → 用户16/商品45/订单99/销售额¥78万；热销TOP；普通用户访问admin → 403
⑨ 安全与异常路径      → 未登录→401 Not authenticated；不存在→404；伪造token(公开接口)→200忽略
```

### 方式 B：前端 UI 手动演示

1. 打开 http://localhost:5173
2. 用现成账号登录：**admin / admin123**（管理员）或 **zhangwei / zw123456**（普通用户），也可注册新用户
3. 推荐演示路径：
   - 首页浏览/搜索 → 商品详情 → 加购物车 → 结算下单 → 支付（模拟）→ 订单页看状态
   - AI 客服/聊天（DeepSeek 已启用）→ AI 推荐位
   - admin 登录 → 管理后台看统计图表、商品/用户/订单管理

## 6. 接口清单（35 个已比对用例）

| 模块 | 接口 |
|---|---|
| 系统 | `GET /api/health` |
| 认证 | `POST /api/auth/register` `POST /api/auth/login` `GET/PUT /api/auth/me` |
| 商品 | `GET /api/products`（排序/分类/价格区间/关键词/推荐位）`GET /api/products/{id}` `GET /api/products/categories` `GET /api/products/{id}/reviews` `POST/GET /api/products/{id}/favorite` |
| 搜索 | `GET /api/search` `GET /api/search/suggestions` `GET /api/search/hot` `GET /api/search/brands` |
| 购物车 | `GET/POST /api/cart/items` `PUT/DELETE /api/cart/items/{id}` `DELETE /api/cart/items` `GET /api/cart/count` |
| 订单 | `GET/POST /api/orders` `GET /api/orders/{id}` `PUT /api/orders/{id}/status` `GET /api/orders/stats/summary` `POST /api/orders/{id}/pay` `POST /api/orders/{id}/pay-confirm` |
| 管理端 | `GET /api/admin/stats` `GET /api/admin/products` `GET /api/admin/users` `GET /api/admin/orders` |
| AI | `GET /api/ai/status` `GET /api/ai/recommendations` `POST /api/ai/rag/search` `POST /api/ai/chat`（SSE）`WS /api/chat/ws`（客服） |

## 7. 数据与账号

- **数据源**：`backend/smartmall.db`（SQLite canonical）→ `migrate_sqlite.py` 生成 → H2 `data/smartmall.mv.db`
- **种子账号**：

| 账号 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| zhangwei | zw123456 | 普通用户（有订单/收藏等行为数据） |
| 任意新注册 | 自定 | user |

## 8. 关键实现约定（维护者必读）

以下是从 35/35 比对中沉淀的兼容性要点，**改动代码时务必遵守**，否则会破坏与 Python/前端的契约：

1. **排序并列兜底方向**：SQLite 的兜底取决于执行计划 —— 有 `created_at` 索引的表（orders）并列按 **id DESC**，无索引的表按 **id ASC**。Java 侧所有排序查询必须显式加二级 `id` 兜底（H2 的默认兜底顺序与 SQLite 不同，不能"碰巧一致"）。
2. **401 文案语义**：完全无 token → `Not authenticated`；有 token 但无效 → `无效的认证凭证`。
3. **响应字段**：Python 所有商品输出**不含** `updated_at`，DTO 不要加；JSON 用 `snake_case`（Jackson 已配置）。
4. **收藏路由**：只有 `GET/POST /api/products/{id}/favorite`；`/api/products/favorites/list` 两端都不存在（返回 404）。
5. **接口返回结构**（易踩坑）：
   - `suggestions` 的 `products` 是**字符串数组**；hot 字段名是 `hot_keywords`
   - `/api/search/hot`、`/api/search/brands` 返回**裸数组**
   - 用户订单列表 `/api/orders` 返回**裸数组**（无分页包装）；管理端的是分页包装
   - `/api/admin/stats` 字段：`total_users/total_products/total_orders/total_sales`；`top_products[].sales`
   - 商品列表 `keyword` 只匹配商品名（多为英文名）；中文关键词搜索用 `/api/search`（匹配描述）
6. **静态资源兜底**：`/**` 映射到静态目录后，未匹配的 `/api/**` 会抛 `NoResourceFoundException`（不是 `NoHandlerFoundException`），异常处理器需单独接住返回 404。
7. **数据脚本转义**：`\uXXXX` Unicode 转义写入 SQL 时必须翻倍为 `\\u`（MySQL 会丢弃反斜杠）；`migrate_sqlite.py` 已处理，勿手动改坏。
8. **H2 MySQL 模式限制**：`DISTINCT + ORDER BY 非投影列` 非法，用 `GROUP BY ... ORDER BY MIN(col)` 等价实现。

## 9. 已知事项与后续

- **MySQL 生产库**：`src/main/resources/db/migration/mysql/V1__init_schema.sql` + `tools/dist/data_mysql.sql` 已就绪，静态验证全过（依赖、ID 策略、schema 对齐、转义、索引唯一性）。本机无 MySQL/Docker，**端到端未实测**；有 MySQL 环境后按 `docs/MYSQL_DEPLOY.md` 跑 `--spring.profiles.active=mysql`，并重跑 `compare_api.py` 应 ≥35/35。
- **Python 后端已停**：迁移完成，Python 仅作为历史参照（若需重新比对，需先重启 Python 8000）。
- **数据污染**：演示脚本会注册新用户/下订单，属于正常演示行为；如需要干净数据，删 `backend-java/data/smartmall.mv.db` 后用 `RunScript` 重灌 `tools/dist/data_h2.sql`。

## 附：快速验证命令

```bash
# 健康检查
curl http://127.0.0.1:8001/api/health

# 登录拿 token
curl -X POST http://127.0.0.1:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 商品列表
curl "http://127.0.0.1:8001/api/products?page=1&page_size=5"

# AI 状态
curl http://127.0.0.1:8001/api/ai/status
```
