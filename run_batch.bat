@echo off
REM 批量任务执行脚本 - 使用 Ollama 本地模型

REM 检查是否提供了任务文件参数
if "%~1"=="" (
    echo 请提供任务文件
    echo.
    echo 使用方法:
    echo   run_batch.bat tasks.json
    echo   run_batch.bat batch_tasks_example.json
    echo.
    echo 使用自定义配置:
    echo   run_batch.bat --config batch_config.json --tasks batch_tasks_example.json
    echo.
    pause
    exit /b 1
)

REM 执行批量任务
echo ========================================
echo 🚀 DroidRun 批量任务执行器
echo ========================================
echo.

uv run python batch_runner.py %*

echo.
echo ========================================
echo 执行完成
echo ========================================
pause
