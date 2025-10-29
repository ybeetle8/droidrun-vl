@echo off
REM 使用本地 Ollama 运行 DroidRun

REM 检查是否提供了命令参数
if "%~1"=="" (
    echo 请提供要执行的命令
    echo 使用方法: run_ollama.bat "你的命令"
    echo 例如: run_ollama.bat "打开设置应用"
    pause
    exit /b 1
)

REM 执行 DroidRun 命令，使用本地 Ollama
uv run droidrun --provider Ollama --model gemma3:27b --base_url http://localhost:11434 %*




