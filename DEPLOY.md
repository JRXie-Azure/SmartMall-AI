# SmartMall-AI 生产部署指南

## 架构概览

```
用户 → Nginx (HTTPS) → Spring Boot (8000) → MySQL (3306)
                                        → Redis (6379)
                                        → DeepSeek API (AI功能)
```

## 一、环境准备

### 1.1 服务器要求
- OS: Ubuntu 22.04 / CentOS 8 / Windows Server
- Java 17+
- MySQL 8.0+
- Redis 7+
- Nginx

### 1.2 克隆项目
```bash
git clone https://github.com/JRXie-Azure/SmartMall-AI.git
cd SmartMall-AI
```

## 二、配置文件

### 2.1 环境变量

通过环境变量或 `application.yml` 覆盖配置：

```bash
# 必填
export SECRET_KEY=$(openssl rand -hex 32)
export DEEPSEEK_API_KEY=sk-your-api-key

# 数据库
export SPRING_PROFILES_ACTIVE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DB=smartmall
export MYSQL_USER=root
export MYSQL_PASSWORD=smartmall123

# Redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

### 2.2 关键配置说明
| 配置项 | 开发值 | 生产值 |
|--------|--------|--------|
| `spring.profiles.active` | h2 | mysql |
| `server.port` | 8001 | 8000 |
| `smartmall.jwt.secret-key` | dev-key | openssl rand -hex 32 |
| `smartmall.llm.deepseek-api-key` | 空 | sk-xxxxx |
| `smartmall.rate-limit.enabled` | true | true |
| `smartmall.cache.redis-enabled` | true | true |

## 三、数据库部署

### 3.1 MySQL 初始化
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS smartmall CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3.2 Flyway 自动迁移
应用启动时 Flyway 自动执行迁移脚本（`src/main/resources/db/migration/mysql/`），无需手动操作。

### 3.3 验证
```bash
mysql -u root -p smartmall -e "SHOW TABLES;"
# 应显示 20 张表
```

## 四、Redis 部署

### 4.1 安装 Redis
```bash
# Ubuntu
sudo apt install redis-server
sudo systemctl enable redis-server

# Docker
docker run -d --name smartmall-redis -p 6379:6379 \
  redis:7-alpine redis-server --appendonly yes --maxmemory 256mb
```

### 4.2 验证
```bash
redis-cli ping
# 期望输出: PONG
```

### 4.3 功能说明
- **缓存**: 商品列表/详情自动缓存 5 分钟
- **限流**: 100次/分钟 (AI接口 20次/分钟)
- **降级**: Redis 不可用时自动切换内存缓存

## 五、Nginx + HTTPS

### 5.1 SSL 证书
```bash
# 生产环境 (Let's Encrypt)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem nginx/certs/

# 开发环境 (自签名)
cd nginx
bash generate_dev_ssl.sh
```

### 5.2 启动 Nginx
```bash
# 修改 nginx.conf 中的 server_name 和 proxy_pass 为 http://localhost:8000
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 5.3 Nginx 功能
- HTTP → HTTPS 301 重定向
- HSTS 安全头
- gzip 压缩
- 静态资源缓存 30 天
- WebSocket 代理 (/api/ws/)
- API 反向代理 (/api/ → http://localhost:8000)
- 文件上传限制 20MB

## 六、AI 功能

### 6.1 配置 DeepSeek
1. 访问 https://platform.deepseek.com/
2. 注册 → 创建 API Key
3. 配置: `DEEPSEEK_API_KEY=sk-your-key`

### 6.2 AI 功能说明
| 功能 | LLM 可用 | LLM 不可用 (降级) |
|------|----------|-------------------|
| AI 对话 | DeepSeek 自然语言对话 | 内置话术回复 |
| AI 推荐 | LLM + 协同过滤 | 协同过滤算法 |
| AI 搜索 | LLM 语义理解 | TF-IDF 语义搜索 |
| 智能客服 | AI 先接 + 转人工 | 预设回复 |
| Function Calling | 智能调用商品搜索等工具 | 不支持 |

## 七、构建与启动

### 7.1 本地构建
```bash
cd backend-java
./mvnw clean package -DskipTests
java -jar target/smartmall-ai.jar --spring.profiles.active=mysql
```

### 7.2 Docker 一键部署
```bash
# 1. 配置环境变量
export DEEPSEEK_API_KEY=sk-your-key
export SECRET_KEY=$(openssl rand -hex 32)

# 2. 生成 SSL 证书
cd nginx && bash generate_dev_ssl.sh && cd ..

# 3. 一键启动
docker-compose up -d --build

# 4. 验证
curl http://localhost:8000/api/health
```

## 八、验证清单

- [ ] 环境变量配置完整 (SECRET_KEY/DEEPSEEK_API_KEY)
- [ ] MySQL 连接成功，Flyway 迁移已执行
- [ ] Redis 连接成功 (redis-cli ping → PONG)
- [ ] Nginx HTTPS 正常 (浏览器访问无证书警告)
- [ ] LLM 连接成功 (/api/ai/status → enabled)
- [ ] 后台管理系统功能正常 (admin/admin123)
- [ ] 前端页面加载正常 (http://localhost:8000)
- [ ] API 健康检查通过 (/api/health → healthy)
