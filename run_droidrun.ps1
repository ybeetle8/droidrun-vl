#!/usr/bin/env powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Command,
    
    [switch]$Vision,
    [switch]$Reasoning,
    [switch]$Reflection,
    [switch]$DebugMode
)

# 设置 API Key
$env:OPENAI_API_KEY = "sk-blsuXRCbOyXmwGfNkP0ntcN6iYI6Vrn7CElT64pGrgPVTgEM"

# 构建基础命令
$BaseArgs = @(
    "--provider", "OpenAILike",
    "--model", "gpt-4.1-mini", 
    "--api_base", "https://chat.cloudapi.vip/v1",
    $Command
)

# 添加可选参数
if ($Vision) { $BaseArgs += "--vision" }
if ($Reasoning) { $BaseArgs += "--reasoning" }
if ($Reflection) { $BaseArgs += "--reflection" }
if ($DebugMode) { $BaseArgs += "--debug" }

Write-Host "正在执行: uv run droidrun $($BaseArgs -join ' ')" -ForegroundColor Green

# 执行命令
& uv run droidrun @BaseArgs