# SmartMall-AI 生产部署指南

## 架构概览

```
用户 → Nginx (HTTPS) → FastAPI (8001) → MySQL (3306)
                     ↓               → Redis (6379)
                  前端静态文件        → S3/OSS (图片存储)
                                   → DeepSeek API (AI功能)
```

## 一、环境准备

### 1.1 服务器要求
- OS: Ubuntu 22.04 / CentOS 8 / Windows Server
- Python 3.10+
- MySQL 8.0+
- Redis 7+
- Nginx

### 1.2 克隆项目
```bash
git clone <your-repo-url> SmartMall-AI
cd SmartMall-AI
```

## 二、配置文件 (优化方案 1)

### 2.1 创建生产配置
```bash
cd backend
cp .env.production .env
# 编辑 .env，修改以下必填项:
#   SECRET_KEY     → openssl rand -hex 32 生成
#   DATABASE_URL   → MySQL 连接串
#   CORS_ORIGINS   → 你的域名
#   DEEPSEEK_API_KEY → DeepSeek API Key
```

### 2.2 关键配置说明
| 配置项 | 开发值 | 生产值 |
|--------|--------|--------|
| DEBUG | true | false |
| DATABASE_URL | sqlite:///./smartmall.db | mysql+pymysql://... |
| CORS_ORIGINS | * | https://yourdomain.com |
| STORAGE_TYPE | local | s3 |
| RATE_LIMIT_ENABLED | true | true |

## 三、数据库部署 (优化方案 2)

### 3.1 MySQL 初始化
```bash
mysql -u root -p < backend/mysql_init.sql
```

### 3.2 执行迁移
```bash
cd backend
python migrate_prod.py migrate    # 创建所有表
python migrate_prod.py seed       # 填充初始数据
python migrate_prod.py status     # 验证迁移状态
```

### 3.3 迁移管理
```bash
python migrate_prod.py rollback   # 回滚上一步
python migrate_prod.py fresh      # 删表重建 (危险!)
```

## 四、Redis 部署 (优化方案 3)

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
cd backend
python check_redis.py
# 期望输出: Redis 状态: PRODUCTION READY
```

### 4.3 功能说明
- **缓存**: 商品列表/详情自动缓存 5 分钟
- **限流**: 100次/分钟 (AI接口 20次/分钟)
- **降级**: Redis 不可用时自动切换内存缓存

## 五、Nginx + HTTPS (优化方案 4)

### 5.1 SSL 证书
```bash
# 生产环境 (Let's Encrypt)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem nginx/certs/

# 开发环境 (自签名)
cd nginx
bash generate_dev_ssl.sh
# 或 PowerShell: .\generate_dev_ssl.ps1
```

### 5.2 启动 Nginx
```bash
# 修改 nginx.conf 中的 server_name 为你的域名
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t          # 测试配置
sudo systemctl reload nginx
```

### 5.3 Nginx 功能
- HTTP → HTTPS 301 重定向
- HSTS 安全头
- gzip 压缩
- 静态资源缓存 30 天
- WebSocket 代理 (/ws/)
- API 反向代理 (/api/)
- 文件上传限制 20MB

## 六、支付接入 (优化方案 5)

### 6.1 微信支付
1. 登录 pay.weixin.cn → 获取 APPID/MCHID/APIv3密钥/证书序列号
2. 下载 apiclient_key.pem → 放到 `certs/wxpay/`
3. .env 配置: WXPAY_APPID / WXPAY_MCHID / WXPAY_API_V3_KEY / WXPAY_CERT_SERIAL_NO

### 6.2 支付宝
1. 登录 open.alipay.com → 创建应用 → 获取 APPID
2. 生成 RSA2 密钥对 → 放到 `certs/alipay/`
3. .env 配置: ALIPAY_APP_ID / ALIPAY_SANDBOX=false

### 6.3 安装 SDK
```bash
pip install wechatpayv3 alipay-sdk-python
```

### 6.4 验证
```bash
cd backend
python test_payment.py
```

### 6.5 支付流程
```
下单 → POST /api/payment/create/{order_id}
  → 微信: 返回 code_url (扫码支付)
  → 支付宝: 返回 pay_url (跳转支付)
  → 模拟: GET /api/payment/mock/{order_id} (直接完成)

支付完成 → 回调通知 → 订单状态 pending → paid
```

## 七、对象存储 (优化方案 6)

### 7.1 配置 S3/OSS
```bash
# .env 配置
STORAGE_TYPE=s3
S3_ENDPOINT=https://oss-cn-shenzhen.aliyuncs.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=smartmall-prod
S3_REGION=cn-shenzhen
S3_PUBLIC_URL=https://cdn.yourdomain.com  # CDN加速域名
```

### 7.2 支持的存储服务
| 服务商 | S3_ENDPOINT |
|--------|-------------|
| 阿里云 OSS | https://oss-cn-xxx.aliyuncs.com |
| 腾讯云 COS | https://cos.ap-xxx.myqcloud.com |
| AWS S3 | (留空, 设置 S3_REGION) |
| MinIO | http://localhost:9000 |

### 7.3 验证
```bash
cd backend
python test_s3.py
```

### 7.4 功能说明
- 图片上传自动压缩 (1200px, 85%质量)
- 自动生成 300x300 缩略图
- 支持 PNG/JPG/GIF/WEBP
- 上传/删除双模式 (本地/S3)

## 八、AI 功能 (优化方案 7)

### 8.1 配置 DeepSeek
1. 访问 https://platform.deepseek.com/
2. 注册 → 创建 API Key
3. .env 配置: `DEEPSEEK_API_KEY=sk-your-key`

### 8.2 验证
```bash
cd backend
python test_llm.py
# 期望输出: LLM 状态: READY
```

### 8.3 AI 功能说明
| 功能 | LLM 可用 | LLM 不可用 (降级) |
|------|----------|-------------------|
| AI 对话 | DeepSeek 自然语言对话 | 关键词匹配回复 |
| AI 推荐 | LLM + 协同过滤 | 协同过滤算法 |
| AI 搜索 | LLM 语义理解 | TF-IDF 语义搜索 |
| 智能客服 | AI 先接 + 转人工 | 预设回复 |
| Function Calling | 智能调用商品搜索等工具 | 不支持 |

## 九、Docker 一键部署

```bash
# 1. 配置环境
cp backend/.env.production backend/.env
# 编辑 backend/.env

# 2. 生成 SSL 证书
cd nginx && bash generate_dev_ssl.sh && cd ..

# 3. 一键启动
docker-compose up -d --build

# 4. 执行迁移
docker exec smartmall-backend python migrate_prod.py migrate
docker exec smartmall-backend python migrate_prod.py seed

# 5. 验证
docker exec smartmall-backend python check_redis.py
docker exec smartmall-backend python test_payment.py
docker exec smartmall-backend python test_s3.py
docker exec smartmall-backend python test_llm.py
```

## 十、验证清单

- [ ] .env 配置完整 (SECRET_KEY/DATABASE_URL/CORS_ORIGINS)
- [ ] MySQL 连接成功，迁移已执行
- [ ] Redis 连接成功 (check_redis.py → PRODUCTION READY)
- [ ] Nginx HTTPS 正常 (浏览器访问无证书警告)
- [ ] 支付功能可用 (test_payment.py → READY)
- [ ] 对象存储可用 (test_s3.py → READY)
- [ ] LLM 连接成功 (test_llm.py → READY)
- [ ] 后台管理系统功能正常 (admin/admin123)
- [ ] 前端页面加载正常
- [ ] API 文档可访问 (/docs)
