#!/bin/bash
# 生成开发用自签名 SSL 证书
# 用法: bash generate_dev_ssl.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$SCRIPT_DIR/certs"

mkdir -p "$CERT_DIR"

echo "=== 生成自签名 SSL 证书 (开发用) ==="
echo "输出目录: $CERT_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/C=CN/ST=Guangdong/L=Shenzhen/O=SmartMall-Dev/CN=localhost" 2>/dev/null

echo ""
echo "[OK] 证书已生成:"
echo "  - $CERT_DIR/fullchain.pem"
echo "  - $CERT_DIR/privkey.pem"
echo ""
echo "注意: 浏览器会显示不安全警告，点击高级 -> 继续访问即可。"
echo "      生产环境请使用 Let's Encrypt 证书 (见 certs/README.md)"
