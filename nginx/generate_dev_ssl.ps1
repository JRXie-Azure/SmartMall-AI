# 生成开发用自签名 SSL 证书 (Windows PowerShell)
# 用法: powershell -ExecutionPolicy Bypass -File generate_dev_ssl.ps1

$ErrorActionPreference = "Stop"
$CertDir = Join-Path $PSScriptRoot "certs"
New-Item -ItemType Directory -Force -Path $CertDir | Out-Null

Write-Host "=== 生成自签名 SSL 证书 (开发用) ===" -ForegroundColor Cyan
Write-Host "输出目录: $CertDir"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
    -keyout "$CertDir\privkey.pem" `
    -out "$CertDir\fullchain.pem" `
    -subj "/C=CN/ST=Guangdong/L=Shenzhen/O=SmartMall-Dev/CN=localhost" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] 证书已生成:" -ForegroundColor Green
    Write-Host "  - $CertDir\fullchain.pem"
    Write-Host "  - $CertDir\privkey.pem"
    Write-Host ""
    Write-Host "注意: 浏览器会显示不安全警告，点击高级 -> 继续访问即可。" -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] openssl 未安装或执行失败" -ForegroundColor Red
    Write-Host "请安装 openssl 或使用 Git Bash 运行 generate_dev_ssl.sh"
}
