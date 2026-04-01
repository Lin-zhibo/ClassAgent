# ClassAgent 古诗词学习系统启动脚本
# Usage: .\start.ps1

param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

# 1. 检查依赖
Write-Host ""
Write-Host "[CHECK] Checking dependencies..." -ForegroundColor Yellow

$requiredPkgs = @("openai", "langchain", "chromadb", "langchain-chroma")
foreach ($pkg in $requiredPkgs) {
    $installed = pip show $pkg 2>$null | Select-String "^Name:"
    if (-not $installed) {
        Write-Host "[INSTALL] Installing $pkg..." -ForegroundColor Yellow
        pip install $pkg --quiet 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] $pkg installed" -ForegroundColor Green
        }
    } else {
        Write-Host "  [OK] $pkg already installed" -ForegroundColor Green
    }
}

# 2. 检查配置文件
$configDir = Join-Path $ScriptDir "config"
$envFile = Join-Path $configDir ".env"
$modelsFile = Join-Path $configDir "models.json"

if (-not (Test-Path $envFile)) {
    Write-Host "[WARN] config/.env not found, creating template..." -ForegroundColor Yellow
    "API_KEY = `"your-api-key-here`"" | Out-File -FilePath $envFile -Encoding utf8
}

if (-not (Test-Path $modelsFile)) {
    Write-Host "[WARN] config/models.json not found, creating template..." -ForegroundColor Yellow
    @"
{
    "MODEL_NAME": "your-model-name",
    "URL": "https://api.openai.com/v1",
    "EMBEDDING_MODEL_NAME": "your-embedding-model",
    "EMBEDDING_MODEL_URL": "https://api.openai.com/v1"
}
"@ | Out-File -FilePath $modelsFile -Encoding utf8
}

# 3. 启动主程序
Write-Host ""
Write-Host "[START] Starting ClassAgent..." -ForegroundColor Green
Write-Host ""

Set-Location $ScriptDir
python main.py

if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Host ""
    Write-Host "[ERROR] Program exited with code: $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
