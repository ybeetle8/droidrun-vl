@echo off
REM 设置 API Key
set OPENAI_API_KEY=sk-Kd92LE2pud8bVtZE23B47248Bc064006Af400cB6770c8577

REM 检查是否提供了命令参数
if "%~1"=="" (
    echo 请提供要执行的命令
    echo 使用方法: run_qwen.bat "你的命令"
    echo 例如: run_qwen.bat "打开设置应用"
    pause
    exit /b 1
)

REM 执行 DroidRun 命令
uv run droidrun --provider OpenAILike --model qwen3-coder-plus-2025-07-22 --api_base https://api.vimsai.com/v1 %*