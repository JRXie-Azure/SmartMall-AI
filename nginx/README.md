# SmartMall-AI SSL 证书获取指南

本项目 `nginx.conf` 启用了 HTTPS (443 端口)，需要提供 SSL 证书才能正常启动。
推荐使用 **Let's Encrypt** 免费、自动续期的 SSL 证书。

证书需要放置到 `nginx/certs/` 目录，文件名固定为：

```
nginx/certs/fullchain.pem   # 证书链 (含中间证书)
nginx/certs/privkey.pem     # 私钥
```

---

## 一、前置要求

1. 一个**已解析到服务器公网 IP** 的域名 (例如 `smartmall.ai`)
2. 服务器开放 `80` 和 `443` 端口 (云服务器安全组放行)
3. 服务器以 root 或 sudo 用户运行

> 注意：Let's Encrypt 的 HTTP-01 验证需要 80 端口可达；DNS-01 验证则不需要。

---

## 二、方式 A：直接在服务器上用 certbot (推荐，单机部署)

### 1. 安装 certbot

**Ubuntu / Debian：**
```bash
sudo apt update
sudo apt install -y certbot
```

**CentOS / RHEL：**
```bash
sudo yum install -y epel-release
sudo yum install -y certbot
```

### 2. 申请证书 (standalone 模式)

standalone 模式会临时占用 80 端口，请先停止 nginx：

```bash
# 停止占用 80 端口的服务
sudo docker-compose down          # 若用 docker 部署
# 或 sudo systemctl stop nginx

# 申请证书 (替换 yourdomain.com 为你的域名)
sudo certbot certonly --standalone \
  -d smartmall.ai -d www.smartmall.ai \
  --email you@example.com \
  --agree-tos --no-eff-email
```

### 3. 复制证书到项目目录

```bash
# 在项目根目录创建证书目录
mkdir -p nginx/certs

# 复制证书 (Let's Encrypt 默认输出路径)
sudo cp /etc/letsencrypt/live/smartmall.ai/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/smartmall.ai/privkey.pem  nginx/certs/

# 修正权限 (nginx 容器以 nginx 用户读取)
sudo chmod 644 nginx/certs/fullchain.pem
sudo chmod 600 nginx/certs/privkey.pem
```

### 4. 启动服务

```bash
docker-compose up -d
```

---

## 三、方式 B：Docker + certbot (容器化部署，无需在宿主机装 certbot)

```bash
# 1. 停止占用 80 端口的服务
docker-compose down

# 2. 用 certbot 容器申请证书
docker run -it --rm \
  -p 80:80 \
  -v "$(pwd)/nginx/certs:/etc/letsencrypt" \
  -v "$(pwd)/nginx/certbot:/var/lib/letsencrypt" \
  certbot/certbot certonly --standalone \
    -d smartmall.ai -d www.smartmall.ai \
    --email you@example.com \
    --agree-tos --no-eff-email

# 3. 软链接到 nginx/certs 目录 (certbot 输出在 live/ 下)
cp -L nginx/certs/live/smartmall.ai/fullchain.pem nginx/certs/fullchain.pem
cp -L nginx/certs/live/smartmall.ai/privkey.pem  nginx/certs/privkey.pem
```

---

## 四、方式 C：DNS-01 验证 (适用于 80 端口不可用 / 通配符证书)

适合使用 Cloudflare / 阿里云 DNS 等支持 API 的域名服务商：

```bash
sudo certbot certonly --manual \
  --preferred-challenges dns \
  -d smartmall.ai -d "*.smartmall.ai" \
  --email you@example.com \
  --agree-tos --no-eff-email
```

执行后会提示添加一条 `_acme-challenge` TXT 记录，按提示在 DNS 控制台添加即可。

---

## 五、自动续期

Let's Encrypt 证书有效期 **90 天**，建议配置自动续期。

### 方案 1：cron 定时任务

```bash
# 编辑 root 的 crontab
sudo crontab -e

# 添加以下行：每月 1 号凌晨 3 点检查并续期，续期后重启 nginx 容器
0 3 1 * * certbot renew --quiet --post-hook "cp -L /etc/letsencrypt/live/smartmall.ai/fullchain.pem /path/to/SmartMall-AI/nginx/certs/fullchain.pem && cp -L /etc/letsencrypt/live/smartmall.ai/privkey.pem /path/to/SmartMall-AI/nginx/certs/privkey.pem && docker restart smartmall-nginx"
```

### 方案 2：systemd timer

```bash
# 写入 renew-hook 脚本
sudo tee /etc/letsencrypt/renewal-hooks/deploy/smartmall.sh <<'EOF'
#!/bin/bash
PROJECT_DIR=/path/to/SmartMall-AI
cp -L /etc/letsencrypt/live/smartmall.ai/fullchain.pem $PROJECT_DIR/nginx/certs/fullchain.pem
cp -L /etc/letsencrypt/live/smartmall.ai/privkey.pem  $PROJECT_DIR/nginx/certs/privkey.pem
docker restart smartmall-nginx
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/smartmall.sh

# 启用系统自带的 certbot 续期 timer
sudo systemctl enable --now certbot.timer
```

### 手动测试续期

```bash
sudo certbot renew --dry-run
```

---

## 六、本地开发 / 无域名时的自签名证书 (仅测试用)

生产环境**不要**使用自签名证书，浏览器会报不安全警告。
仅用于本地 HTTPS 联调：

```bash
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/privkey.pem \
  -out    nginx/certs/fullchain.pem \
  -subj "/C=CN/ST=Local/L=Local/O=SmartMall/CN=localhost"
```

---

## 七、验证

1. 浏览器访问 `https://smartmall.ai`，确认锁标志正常。
2. 在线检测：https://www.ssllabs.com/ssltest/analyze.html?d=smartmall.ai
3. 证书信息查看：
   ```bash
   openssl x509 -in nginx/certs/fullchain.pem -noout -text | head -20
   ```

---

## 八、常见问题

| 问题 | 原因 / 解决 |
| --- | --- |
| nginx 启动报 `cannot load certificate` | 证书文件路径错误或为空，检查 `nginx/certs/` 下是否有 `fullchain.pem` 和 `privkey.pem` |
| 证书申请失败 `Connection refused` | 80 端口未开放或被占用，关闭占用 80 端口的服务后重试 |
| 浏览器提示证书不受信任 | 使用了自签名证书；请改用 Let's Encrypt 正式证书 |
| 续期后 nginx 仍用旧证书 | 未配置 `--post-hook` 或 renew-hook，需手动 `docker restart smartmall-nginx` |
| `nginx: [emerg] bind() to 0.0.0.0:443 failed` | 443 端口被占用，`netstat -tlnp \| grep 443` 排查 |
