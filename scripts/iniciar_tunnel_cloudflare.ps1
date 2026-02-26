# Inicia o app Flask em nova janela e, em seguida, o cloudflared tunnel.
# Uso: execute na pasta do projeto GRANPIX no PowerShell.
# Requer: Python com app rodando em localhost:5000, cloudflared instalado (winget install Cloudflare.cloudflared).

$projectPath = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }
$appPath = Join-Path $projectPath "app.py"

if (-not (Test-Path $appPath)) {
    Write-Host "ERRO: app.py nao encontrado. Execute este script da pasta GRANPIX ou de scripts." -ForegroundColor Red
    exit 1
}

Write-Host "=== GRANPIX + Cloudflare Tunnel ===" -ForegroundColor Cyan
Write-Host "Abrindo o app Flask em nova janela (porta 5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectPath'; python app.py"

Write-Host "Aguardando o app subir (10 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "Iniciando cloudflared tunnel para http://localhost:5000 ..." -ForegroundColor Green
Write-Host "Use a URL https://....trycloudflare.com que aparecer." -ForegroundColor Green
& cloudflared tunnel --url http://localhost:5000
