# 启动 Redis 容器（供 TradingAgents 使用）
# 端口 6380，密码 tradingagents123，与 .env 中 REDIS_PORT=6380 一致

$container = "tradingagents-redis-local"
$port = 6380
$password = "tradingagents123"

# 检查容器是否已存在且运行中
$existing = docker ps -a --filter "name=$container" --format "{{.Names}} {{.Status}}"
if ($existing -match "Up") {
    Write-Host "[OK] Redis 已在运行: $container"
    exit 0
}

# 若存在但已停止，则启动
if ($existing -match $container) {
    docker start $container
    Write-Host "[OK] 已启动现有容器: $container"
    exit 0
}

# 创建并启动新容器
Write-Host "[INFO] 创建 Redis 容器 (端口 $port)..."
docker run -d `
  --name $container `
  -p "${port}:6379" `
  redis:latest `
  redis-server --appendonly yes --requirepass $password

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Redis 已启动: localhost:$port (密码: $password)"
    Write-Host "      .env 中需设置: REDIS_ENABLED=true, REDIS_PORT=$port, REDIS_PASSWORD=$password"
} else {
    Write-Host "[ERROR] 启动失败，请确保已安装 Docker"
    exit 1
}
