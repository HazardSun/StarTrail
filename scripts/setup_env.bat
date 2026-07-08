@echo off
REM StarTrail 开发环境一键配置脚本 (CMD)
REM 用法: scripts\setup_env.bat

echo.
echo ========================================
echo   StarTrail 开发环境配置
echo ========================================
echo.

REM 1. 检查 Python
echo [1/5] 检查 Python...
python --version
echo.

REM 2. 创建虚拟环境
echo [2/5] 创建虚拟环境...
if not exist .venv (
    python -m venv .venv
    echo   已创建 .venv
) else (
    echo   .venv 已存在，跳过
)

REM 3. 激活并安装依赖
echo [3/5] 安装依赖...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo   已安装 requirements.txt

REM 4. 安装开发工具
echo [4/5] 安装开发工具...
pip install ruff mypy pytest pytest-qt --quiet
echo   已安装开发工具

REM 5. 验证
echo [5/5] 验证环境...
if exist scripts\check_npu_env.py (
    python scripts\check_npu_env.py
) else (
    echo   跳过 NPU 检测
)

echo.
echo ========================================
echo   配置完成！
echo ========================================
echo.
echo 启动命令:
echo   .venv\Scripts\activate
echo   python main.py
echo.
pause
