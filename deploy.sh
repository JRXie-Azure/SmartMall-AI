#!/usr/bin/env bash
# ====================================================================
# SmartMall-AI 生产环境部署脚本 (Linux / macOS)
#
# 用法:
#   chmod +x deploy.sh
#   ./deploy.sh              # 默认部署 (含构建、迁移、可选种子数据)
#   ./deploy.sh --skip-build # 跳过镜像构建
#   ./deploy.sh --seed       # 强制初始化种子数据
#   ./deploy.sh --down       # 停止并移除所有服务
#   ./deploy.sh --logs       # 跟踪查看日志
# ====================================================================

set -euo pipefail

# ---------- 颜色与日志 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${BLUE}========== $* ==========${NC}"; }

# ---------- 变量 ----------
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${PROJECT_DIR}/backend/.env"
COMPOSE_CMD=""

# 解析参数
SKIP_BUILD=false
FORCE_SEED=false
DO_DOWN=false
DO_LOGS=false
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    --seed)       FORCE_SEED=true ;;
    --down)       DO_DOWN=true ;;
    --logs)       DO_LOGS=true ;;
    *) log_warn "未知参数: $arg" ;;
  esac
done

cd "${PROJECT_DIR}"

# ====================================================================
# 步骤 1: 检查 .env 文件
# ====================================================================
log_step "步骤 1/6: 检查环境配置文件"

if [ ! -f "${ENV_FILE}" ]; then
  log_error "未找到后端环境配置文件: ${ENV_FILE}"
  log_warn  "请参考 backend/.env.example 创建 backend/.env 并填写生产配置。"
  log_warn  "示例命令: cp backend/.env.example backend/.env && vi backend/.env"
  exit 1
fi

# 校验关键变量 (DEEPSEEK_API_KEY / SECRET_KEY 等)
if grep -q "DEEPSEEK_API_KEY=CHANGE_ME\|SECRET_KEY=CHANGE_ME\|MYSQL_ROOT_PASSWORD=CHANGE_ME" "${ENV_FILE}"; then
  log_error "backend/.env 中存在未修改的占位符 (CHANGE_ME), 请先填写真实值。"
  exit 1
fi

# 强制生产环境关闭 DEBUG
if grep -q "^DEBUG=true" "${ENV_FILE}"; then
  log_warn "检测到 DEBUG=true, 正在强制改为 DEBUG=false (生产环境)..."
  sed -i.bak 's/^DEBUG=.*/DEBUG=false/' "${ENV_FILE}"
  log_info "已将 backend/.env 中 DEBUG 设为 false"
fi

log_info ".env 文件检查通过 ✓"

# ====================================================================
# 步骤 2: 检查 Docker 与 docker-compose
# ====================================================================
log_step "步骤 2/6: 检查 Docker 环境"

if ! command -v docker &> /dev/null; then
  log_error "未检测到 docker, 请先安装 Docker: https://docs.docker.com/engine/install/"
  exit 1
fi
log_info "docker 版本: $(docker --version)"

# 优先使用 docker compose (v2), 回退到 docker-compose (v1)
if docker compose version &> /dev/null; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
  COMPOSE_CMD="docker-compose"
else
  log_error "未检测到 docker-compose, 请安装 Docker Compose。"
  exit 1
fi
log_info "compose 命令: ${COMPOSE_CMD} ($(docker compose version 2>/dev/null || docker-compose --version))"

# 检查 docker 守护进程
if ! docker info &> /dev/null; then
  log_error "Docker 守护进程未运行, 请执行: sudo systemctl start docker"
  exit 1
fi
log_info "Docker 守护进程运行正常 ✓"

# ====================================================================
# 步骤 3: 检查 SSL 证书
# ====================================================================
log_step "步骤 3/6: 检查 SSL 证书"

CERT_DIR="${PROJECT_DIR}/nginx/certs"
if [ ! -f "${CERT_DIR}/fullchain.pem" ] || [ ! -f "${CERT_DIR}/privkey.pem" ]; then
  log_warn "未找到 SSL 证书 (nginx/certs/fullchain.pem 或 privkey.pem)"
  log_warn  "HTTPS 服务将无法启动! 请参考 nginx/README.md 使用 Let's Encrypt 申请证书。"
  log_warn  "若仅本地测试, 可生成自签名证书:"
  log_warn  "  mkdir -p nginx/certs && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\"
  log_warn  "    -keyout nginx/certs/privkey.pem -out nginx/certs/fullchain.pem \\"
  log_warn  "    -subj '/C=CN/ST=Local/L=Local/O=SmartMall/CN=localhost'"
  read -p "$(echo -e ${YELLOW}是否继续部署? [y/N]: ${NC})" -n 1 -r
  echo
  [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
else
  log_info "SSL 证书已就绪 ✓"
fi

# ====================================================================
# 处理 --down / --logs 快捷操作
# ====================================================================
if [ "${DO_DOWN}" = true ]; then
  log_step "停止并移除所有服务"
  ${COMPOSE_CMD} down
  log_info "所有服务已停止并移除 ✓"
  exit 0
fi

if [ "${DO_LOGS}" = true ]; then
  log_step "跟踪服务日志 (Ctrl+C 退出)"
  ${COMPOSE_CMD} logs -f
  exit 0
fi

# ====================================================================
# 步骤 4: 构建并启动服务
# ====================================================================
log_step "步骤 4/6: 构建并启动服务"

if [ "${SKIP_BUILD}" = true ]; then
  log_info "跳过镜像构建, 直接启动..."
  ${COMPOSE_CMD} up -d
else
  log_info "构建镜像并启动服务 (首次较慢)..."
  ${COMPOSE_CMD} up -d --build
fi

log_info "服务启动指令已执行 ✓"

# 等待后端就绪
log_info "等待后端服务就绪 (最多 60 秒)..."
for i in $(seq 1 30); do
  if docker exec smartmall-backend curl -sf http://localhost:8001/health &> /dev/null \
     || docker exec smartmall-backend wget -qO- http://localhost:8001/health &> /dev/null; then
    log_info "后端服务已就绪 ✓"
    break
  fi
  sleep 2
  [ "$i" -eq 30 ] && log_warn "后端健康检查超时, 请稍后查看日志: ${COMPOSE_CMD} logs backend"
done

# ====================================================================
# 步骤 5: 数据库迁移
# ====================================================================
log_step "步骤 5/6: 执行数据库迁移 (alembic upgrade head)"

if docker ps --format '{{.Names}}' | grep -q "smartmall-backend"; then
  if docker exec smartmall-backend alembic upgrade head; then
    log_info "数据库迁移完成 ✓"
  else
    log_warn "数据库迁移失败, 可能 alembic 未安装或配置有误。"
    log_warn "可手动执行: docker exec -it smartmall-backend alembic upgrade head"
    # 迁移失败不中断, 允许查看日志排查
  fi
else
  log_error "后端容器未运行, 跳过数据库迁移。"
fi

# ====================================================================
# 步骤 6: 可选 - 初始化种子数据
# ====================================================================
if [ "${FORCE_SEED}" = true ]; then
  log_step "步骤 6/6: 初始化种子数据 (--seed)"
  if docker exec smartmall-backend python -c "from app.seed import main; main()"; then
    log_info "种子数据初始化完成 ✓"
  else
    log_warn "种子数据初始化失败, 可手动执行:"
    log_warn "  docker exec -it smartmall-backend python -c 'from app.seed import main; main()'"
  fi
else
  echo
  read -p "$(echo -e ${YELLOW}是否初始化种子数据? [y/N]: ${NC})" -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_step "步骤 6/6: 初始化种子数据"
    if docker exec smartmall-backend python -c "from app.seed import main; main()"; then
      log_info "种子数据初始化完成 ✓"
    else
      log_warn "种子数据初始化失败, 请查看上方错误信息。"
    fi
  else
    log_info "跳过种子数据初始化 (后续可执行 deploy.sh --seed)"
  fi
fi

# ====================================================================
# 完成: 显示服务状态与访问地址
# ====================================================================
log_step "部署完成"

echo
${COMPOSE_CMD} ps

echo
echo -e "${GREEN}==================== 访问地址 ====================${NC}"
echo -e "  HTTPS (推荐):  ${BLUE}https://localhost${NC}  (或你的域名 https://smartmall.ai)"
echo -e "  HTTP  (自动跳转 HTTPS): ${BLUE}http://localhost${NC}"
echo -e "  后端 API 文档: ${BLUE}https://localhost/docs${NC}"
echo -e "  后端健康检查: ${BLUE}https://localhost/health${NC}"
echo -e "${GREEN}==================================================${NC}"
echo
echo -e "常用命令:"
echo -e "  查看日志:   ${COMPOSE_CMD} logs -f"
echo -e "  查看状态:   ${COMPOSE_CMD} ps"
echo -e "  重启服务:   ${COMPOSE_CMD} restart"
echo -e "  停止服务:   ${COMPOSE_CMD} down"
echo -e "  重新部署:   ./deploy.sh --skip-build"
echo
