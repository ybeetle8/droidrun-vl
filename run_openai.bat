@echo off

REM 检查是否提供了命令参数
if "%~1"=="" (
    echo 请提供要执行的命令
    echo 使用方法: run_qwen.bat "你的命令"
    echo 例如: run_qwen.bat "打开设置应用"
    pause
    exit /b 1
)

REM 执行 DroidRun 命令
uv run droidrun --provider OpenAILike --model /models --api_base http://192.168.18.9:8080/v1 %*



