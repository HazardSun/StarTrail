# StarTrail 开发环境一键配置脚本 (PowerShell)
# 用法: .\scripts\setup_env.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  StarTrail 开发环境配置" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. 检查 Python 版本
Write-Host "[1/6] 检查 Python 版本..." -ForegroundColor Yellow
$pyVer = python --version 2>&1
Write-Host "  $pyVer"
if ($pyVer -notmatch "3\.1[12]") {
    Write-Host "  ⚠️  建议使用 Python 3.11 或 3.12" -ForegroundColor Yellow
}

# 2. 创建虚拟环境
Write-Host "[2/6] 创建虚拟环境..." -ForegroundColor Yellow
$venvPath = Join-Path $root ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Host "  ✅ .venv 已创建"
} else {
    Write-Host "  ✅ .venv 已存在，跳过"
}

# 3. 激活虚拟环境
Write-Host "[3/6] 激活虚拟环境..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

# 4. 安装依赖
Write-Host "[4/6] 安装依赖..." -ForegroundColor Yellow
$reqFile = Join-Path $root "requirements.txt"
if (Test-Path $reqFile) {
    pip install -r $reqFile --quiet
    Write-Host "  ✅ requirements.txt 已安装"
} else {
    Write-Host "  ❌ requirements.txt 不存在" -ForegroundColor Red
}

# 5. 安装开发依赖
Write-Host "[5/6] 安装开发工具..." -ForegroundColor Yellow
pip install ruff mypy pytest pytest-qt --quiet
Write-Host "  ✅ 开发工具已安装"

# 6. 验证环境
Write-Host "[6/6] 验证环境..." -ForegroundColor Yellow
$checkScript = Join-Path $root "scripts\check_npu_env.py"
if (Test-Path $checkScript) {
    python $checkScript
} else {
    Write-Host "  ⚠️  check_npu_env.py 不存在，跳过检测"
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`n启动命令:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host "  python main.py`n"
