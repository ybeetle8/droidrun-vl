@echo off
REM 设置 API Key
set OPENAI_API_KEY=sk-blsuXRCbOyXmwGfNkP0ntcN6iYI6Vrn7CElT64pGrgPVTgEM

REM 检查是否提供了命令参数
if "%~1"=="" (
    echo 请提供要执行的命令
    echo 使用方法: run_droidrun.bat "你的命令"
    echo 例如: run_droidrun.bat "打开设置应用"
    pause
    exit /b 1
)

REM 执行 DroidRun 命令
uv run droidrun --provider Ollama --model gpt-4.1-mini --api_base https://chat.cloudapi.vip/v1 %*