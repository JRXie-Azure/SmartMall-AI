# MySQL Profile 部署与验证指南

> 状态：**静态验证通过**，待真实 MySQL 环境做端到端确认。
> 本机（2026-08-03）无 MySQL / Docker，已完成全部可离线验证项，见文末"验证边界"。

## 1. 前置条件

- MySQL 8.0+（需要 `DATETIME(6)` 与 `CHECK` 兼容性，5.7 亦可但未验证）
- 字符集 `utf8mb4`（数据含 emoji：`👟` 等）

## 2. 建库

```sql
CREATE DATABASE IF NOT EXISTS smartmall
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

## 3. 灌数据（二选一）

### 方式 A：Flyway 建表 + SQL 灌数（推荐，本项目默认流程）

```bash
# 1) 启动 Java 后端，Flyway 自动执行 db/migration/mysql/V1__init_schema.sql
export JAVA_HOME="C:/Users/谢键荣/.workbuddy/binaries/java/jdk-17.0.13+11"
cd backend-java
"$JAVA_HOME/bin/java" -jar target/smartmall-ai.jar \
  --spring.profiles.active=mysql \
  --MYSQL_HOST=localhost --MYSQL_PORT=3306 --MYSQL_DB=smartmall \
  --MYSQL_USER=root --MYSQL_PASSWORD=<your-password>

# 2) 等健康检查通过后灌数据（脚本内含 DELETE + 显式 id + AUTO_INCREMENT 复位）
mysql -u root -p smartmall < tools/dist/data_mysql.sql
```

### 方式 B：先手动建表再灌数

```bash
mysql -u root -p smartmall < src/main/resources/db/migration/mysql/V1__init_schema.sql
mysql -u root -p smartmall < tools/dist/data_mysql.sql
```

## 4. 环境变量（均可用 `--key=value` 覆盖）

| 变量 | 默认 | 说明 |
|---|---|---|
| `SPRING_PROFILES_ACTIVE` | `h2` | 生产必须显式设为 `mysql` |
| `MYSQL_HOST` / `MYSQL_PORT` | `localhost` / `3306` | |
| `MYSQL_DB` | `smartmall` | |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `root` / `smartmall123` | 生产务必覆盖密码 |
| `SECRET_KEY` | 开发默认值 | 与 Python 共用时保证 JWT 互验 |
| `DEEPSEEK_API_KEY` 等 | 空 | LLM 能力，可选 |

## 5. 端到端验证

```bash
# 健康检查（确认 database 字段为 mysql）
curl -s http://127.0.0.1:8001/api/health

# 关键数据行数（期望: products=45 users=10 orders=95 reviews=75 favorites=24）
mysql -u root -p smartmall -e "SELECT COUNT(*) FROM products; SELECT COUNT(*) FROM users; ..."

# 与 Python 后端逐接口比对（Python 跑在 8000，Java 跑在 8001）
cd backend-java
python tools/compare_api.py --verbose
```

## 6. 已验证项（静态，2026-08-03）

| 检查项 | 结果 |
|---|---|
| pom 依赖：`mysql-connector-j` + `flyway-mysql` | ✅ 齐全 |
| 实体 ID 策略：13 张表全部 `GenerationType.IDENTITY` | ✅ 匹配 `AUTO_INCREMENT` |
| MySQL schema：13 张表、列名与 H2 版逐表对齐 | ✅ 一致 |
| 索引名全局唯一（MySQL 约束：同一 schema 内索引名唯一） | ✅ 无冲突 |
| `metadata` 列（chat_messages） | ✅ 已加反引号 |
| `DATETIME(6)` 精度 | ✅ 与 SQLite 微秒对齐 |
| `data_mysql.sql` 引号/转义 | ✅ 奇数引号行 0；`\uXXXX` 已翻倍为 `\\u`（MySQL 存字面值，与 SQLite/H2 一致） |
| 数据量（users/categories/addresses/products/cart_items/orders/order_items/reviews/product_views/favorites/search_histories） | ✅ 与 H2 一致 |
| AUTO_INCREMENT 复位语句 | ✅ 均为 `max(id)+1` |

## 7. 验证边界（需真实 MySQL 实测）

- `com.mysql.cj.jdbc.Driver` 连通性、HikariCP 连接池行为
- Hibernate `MySQLDialect` 运行期 SQL 生成（尤其 `TEXT`、`DOUBLE`、`BOOLEAN`→`TINYINT(1)` 映射）
- Flyway `{vendor}` 目录解析与 `baseline-on-migrate` 行为
- `serverTimezone=Asia/Shanghai` 时区下 `DATETIME(6)` 往返一致性
- 端到端接口比对（应 ≥ 35/35，与 H2 同源数据）

> 提示：H2 profile 以 `MODE=MySQL` 运行且已 35/35 通过接口比对，SQL 方言层面已间接验证；剩余风险集中在驱动与方言的运行时差异。
