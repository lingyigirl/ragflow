# 本地源码开发启动脚本
# 用法: .\dev_start.ps1

$env:PYTHONPATH = (Get-Location).Path
$env:UV_LINK_MODE = "copy"

# MinerU 配置
$env:MINERU_APISERVER = "http://172.19.0.3:8011"
$env:MINERU_BACKEND = "hybrid-auto-engine"

# 固定 SECRET_KEY，避免每次重启都要重新登录
$env:RAGFLOW_SECRET_KEY = "dev-local-0123456789abcdef0123456789abcdef"

# 启动 API Server（当前终端）
uv run python api/ragflow_server.py
