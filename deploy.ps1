# ====================================================================
# SmartMall-AI 生产环境部署脚本 (Windows PowerShell)
#
# 用法:
#   .\deploy.ps1                 # 默认部署 (含构建、迁移、可选种子数据)
#   .\deploy.ps1 -SkipBuild      # 跳过镜像构建
#   .\deploy.ps1 -Seed           # 强制初始化种子数据
#   .\deploy.ps1 -Down           # 停止并移除所有服务
#   .\deploy.ps1 -Logs           # 跟踪查看日志
#
# 首次运行若被策略限制, 在管理员 PowerShell 中执行:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# ====================================================================

[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$Seed,
    [switch]$Down,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"

# ---------- 辅助函数 ----------
function Write-Step($msg)  { Write-Host "`n========== $msg ==========" -ForegroundColor Cyan }
function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ---------- 变量 ----------
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile    = Join-Path $ProjectDir "backend\.env"
$ComposeCmd = ""

Set-Location $ProjectDir

# ====================================================================
# 步骤 1: 检查 .env 文件
# ====================================================================
Write-Step "步骤 1/6: 检查环境配置文件"

if (-not (Test-Path $EnvFile)) {
    Write-Err "未找到后端环境配置文件: $EnvFile"
    Write-Warn2 "请参考 backend\.env.example 创建 backend\.env 并填写生产配置。"
    Write-Warn2 "示例命令: Copy-Item backend\.env.example backend\.env; notepad backend\.env"
    exit 1
}

$envContent = Get-Content $EnvFile -Raw
if ($envContent -match "CHANGE_ME") {
    Write-Err "backend\.env 中存在未修改的占位符 (CHANGE_ME), 请先填写真实值。"
    exit 1
}

# 强制生产环境关闭 DEBUG
$envLines = Get-Content $EnvFile
$needFix = $false
$fixedLines = $envLines | ForEach-Object {
    if ($_ -match "^DEBUG=") {
        if ($_ -notmatch "DEBUG=false") {
            $needFix = $true
            "DEBUG=false"
        } else { $_ }
    } else { $_ }
}
if ($needFix) {
    Set-Content -Path $EnvFile -Value $fixedLines -Encoding UTF8
    Write-Info "已将 backend\.env 中 DEBUG 强制设为 false (生产环境)"
}

Write-Info ".env 文件检查通过"

# ====================================================================
# 步骤 2: 检查 Docker 与 docker-compose
# ====================================================================
Write-Step "步骤 2/6: 检查 Docker 环境"

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Err "未检测到 docker, 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
}
Write-Info "docker 版本: $(& docker --version)"

# 优先使用 docker compose (v2), 回退到 docker-compose (v1)
$composeV2 = & docker compose version 2>$null
if ($LASTEXITCODE -eq 0 -and $composeV2) {
    $ComposeCmd = "docker compose"
} else {
    $composeV1 = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($composeV1) {
        $ComposeCmd = "docker-compose"
    } else {
        Write-Err "未检测到 docker-compose, 请安装 Docker Compose。"
        exit 1
    }
}
Write-Info "compose 命令: $ComposeCmd"

# 检查 docker 守护进程
$dockerInfo = & docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker 守护进程未运行, 请启动 Docker Desktop。"
    exit 1
}
Write-Info "Docker 守护进程运行正常"

# ====================================================================
# 步骤 3: 检查 SSL 证书
# ====================================================================
Write-Step "步骤 3/6: 检查 SSL 证书"

$CertDir = Join-Path $ProjectDir "nginx\certs"
$fullchain = Join-Path $CertDir "fullchain.pem"
$privkey   = Join-Path $CertDir "privkey.pem"

if (-not (Test-Path $fullchain) -or -not (Test-Path $privkey)) {
    Write-Warn2 "未找到 SSL 证书 (nginx\certs\fullchain.pem 或 privkey.pem)"
    Write-Warn2 "HTTPS 服务将无法启动! 请参考 nginx\README.md 使用 Let's Encrypt 申请证书。"
    Write-Warn2 "若仅本地测试, 可生成自签名证书 (需要 openssl 或在 WSL 中运行)。"
    $continue = Read-Host "是否继续部署? [y/N]"
    if ($continue -notmatch "^[Yy]$") { exit 1 }
} else {
    Write-Info "SSL 证书已就绪"
}

# ====================================================================
# 处理 -Down / -Logs 快捷操作
# ====================================================================
if ($Down) {
    Write-Step "停止并移除所有服务"
    Invoke-Expression "$ComposeCmd down"
    Write-Info "所有服务已停止并移除"
    exit 0
}

if ($Logs) {
    Write-Step "跟踪服务日志 (Ctrl+C 退出)"
    Invoke-Expression "$ComposeCmd logs -f"
    exit 0
}

# ====================================================================
# 步骤 4: 构建并启动服务
# ====================================================================
Write-Step "步骤 4/6: 构建并启动服务"

if ($SkipBuild) {
    Write-Info "跳过镜像构建, 直接启动..."
    Invoke-Expression "$ComposeCmd up -d"
} else {
    Write-Info "构建镜像并启动服务 (首次较慢)..."
    Invoke-Expression "$ComposeCmd up -d --build"
}

if ($LASTEXITCODE -ne 0) {
    Write-Err "服务启动失败, 请查看上方错误信息。"
    exit 1
}
Write-Info "服务启动指令已执行"

# 等待后端就绪
Write-Info "等待后端服务就绪 (最多 60 秒)..."
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    $health = & docker exec smartmall-backend curl -sf http://localhost:8001/health 2>$null
    if ($LASTEXITCODE -eq 0 -and $health) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 2
}
if ($ready) {
    Write-Info "后端服务已就绪"
} else {
    Write-Warn2 "后端健康检查超时, 请稍后查看日志: $ComposeCmd logs backend"
}

# ====================================================================
# 步骤 5: 数据库迁移
# ====================================================================
Write-Step "步骤 5/6: 执行数据库迁移 (alembic upgrade head)"

$backendRunning = & docker ps --format "{{.Names}}" 2>$null | Select-String "smartmall-backend"
if ($backendRunning) {
    & docker exec smartmall-backend alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Info "数据库迁移完成"
    } else {
        Write-Warn2 "数据库迁移失败, 可能 alembic 未安装或配置有误。"
        Write-Warn2 "可手动执行: docker exec -it smartmall-backend alembic upgrade head"
    }
} else {
    Write-Err "后端容器未运行, 跳过数据库迁移。"
}

# ====================================================================
# 步骤 6: 可选 - 初始化种子数据
# ====================================================================
if ($Seed) {
    Write-Step "步骤 6/6: 初始化种子数据 (-Seed)"
    & docker exec smartmall-backend python -c "from app.seed import main; main()"
    if ($LASTEXITCODE -eq 0) {
        Write-Info "种子数据初始化完成"
    } else {
        Write-Warn2 "种子数据初始化失败, 可手动执行:"
        Write-Warn2 "  docker exec -it smartmall-backend python -c `"from app.seed import main; main()`""
    }
} else {
    Write-Host ""
    $seedAns = Read-Host "是否初始化种子数据? [y/N]"
    if ($seedAns -match "^[Yy]$") {
        Write-Step "步骤 6/6: 初始化种子数据"
        & docker exec smartmall-backend python -c "from app.seed import main; main()"
        if ($LASTEXITCODE -eq 0) {
            Write-Info "种子数据初始化完成"
        } else {
            Write-Warn2 "种子数据初始化失败, 请查看上方错误信息。"
        }
    } else {
        Write-Info "跳过种子数据初始化 (后续可执行 .\deploy.ps1 -Seed)"
    }
}

# ====================================================================
# 完成: 显示服务状态与访问地址
# ====================================================================
Write-Step "部署完成"

Write-Host ""
Invoke-Expression "$ComposeCmd ps"

Write-Host ""
Write-Host "==================== 访问地址 ====================" -ForegroundColor Green
Write-Host "  HTTPS (推荐):  https://localhost  (或你的域名 https://smartmall.ai)" -ForegroundColor White
Write-Host "  HTTP  (自动跳转 HTTPS): http://localhost" -ForegroundColor White
Write-Host "  后端 API 文档: https://localhost/docs" -ForegroundColor White
Write-Host "  后端健康检查: https://localhost/health" -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "常用命令:"
Write-Host "  查看日志:   $ComposeCmd logs -f"
Write-Host "  查看状态:   $ComposeCmd ps"
Write-Host "  重启服务:   $ComposeCmd restart"
Write-Host "  停止服务:   $ComposeCmd down"
Write-Host "  重新部署:   .\deploy.ps1 -SkipBuild"
Write-Host ""
