# RAGFlow Nacos 服务注册集成文档

## 概述

本文档说明如何将 RAGFlow 项目注册到 Nacos 注册中心，实现服务发现和负载均衡。

## 前置条件

1. Nacos 服务器已部署并运行
2. Python 环境：Python 3.12+
3. RAGFlow 项目已正确配置

## 安装依赖

```bash
pip install nacos-sdk-python>=0.8.0
```

依赖已在 `pyproject.toml` 中添加，会随项目依赖一起安装。

## 配置说明

### 环境变量配置

在 `docker/.env` 文件或系统环境变量中配置以下参数：

| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `NACOS_ENABLED` | 启用 Nacos 注册 | `true` | 否 |
| `NACOS_SERVER_ADDR` | Nacos 服务器地址 | `127.0.0.1:8848` | 是 |
| `NACOS_SERVICE_NAME` | 服务名称 | `ragflow-service` | 是 |
| `NACOS_NAMESPACE` | 命名空间 | `""` (public) | 否 |
| `NACOS_USERNAME` | Nacos 用户名 | `nacos` | 是 |
| `NACOS_PASSWORD` | Nacos 密码 | `nacos` | 是 |
| `SERVICE_IP` | 服务实例 IP | 自动获取 | 否 |
| `SERVICE_PORT` | 服务端口 | `9380` | 是 |
| `NACOS_CLUSTER_NAME` | 集群名称 | `DEFAULT` | 否 |
| `NACOS_SERVICE_WEIGHT` | 服务权重 | `1.0` | 否 |
| `NACOS_HEARTBEAT_INTERVAL` | 心跳间隔（秒） | `5` | 否 |

### 配置示例

```bash
# 启用 Nacos
export NACOS_ENABLED=true

# Nacos 服务器地址
export NACOS_SERVER_ADDR=172.19.70.125:8848

# 服务配置
export NACOS_SERVICE_NAME=ragflow-service
export SERVICE_PORT=9380

# 认证信息
export NACOS_USERNAME=nacos
export NACOS_PASSWORD=nacos

# 可选配置
# export NACOS_NAMESPACE=dev
# export SERVICE_IP=192.168.1.100
# export NACOS_SERVICE_WEIGHT=1.0
# export NACOS_HEARTBEAT_INTERVAL=5
```

## 使用方法

### 方式一：使用 Docker Compose（推荐）

1. 确保 `docker/.env` 文件中已配置 Nacos 参数

2. 启动 RAGFlow 服务：
```bash
cd /root/project/ragflow/docker
docker-compose up -d
```

3. 查看日志确认注册成功：
```bash
docker-compose logs -f ragflow-server
```

成功日志示例：
```
INFO: Nacos client initialized successfully: server=172.19.70.125:8848, service=ragflow-service
INFO: Service registered to Nacos successfully: name=ragflow-service, address=192.168.1.100:9380
INFO: Nacos heartbeat thread started, interval: 5s
```

### 方式二：直接运行 Python 服务

1. 设置环境变量（或修改 `docker/.env` 后 source）：
```bash
source docker/.env
```

2. 启动后端服务：
```bash
cd /root/project/ragflow
python3 api/ragflow_server.py
```

### 方式三：使用启动脚本

使用项目提供的启动脚本：
```bash
cd /root/project/ragflow/docker
./launch_backend_service.sh
```

## 验证服务注册

### 1. 通过 Nacos 控制台验证

访问 Nacos 控制台：
```
http://172.19.70.125:8848/nacos
```

登录后进入：
- **服务管理** → **服务列表**
- 查找 `ragflow-service` 服务
- 点击 **详情** 查看注册的实例

### 2. 通过 API 验证

```bash
# 查询服务实例列表
curl -X GET \
  'http://172.19.70.125:8848/nacos/v1/ns/instance/list?serviceName=ragflow-service'

# 响应示例：
# {
#   "hosts": [
#     {
#       "ip": "192.168.1.100",
#       "port": 9380,
#       "serviceName": "ragflow-service",
#       "healthy": true,
#       "enabled": true,
#       "weight": 1.0
#     }
#   ],
#   "dom": "ragflow-service"
# }
```

### 3. 查看日志

服务启动时会输出相关日志：
```
INFO: Registering service to Nacos...
INFO: Service registered to Nacos successfully: name=ragflow-service, address=x.x.x.x:9380
INFO: Nacos heartbeat thread started, interval: 5s
```

## 功能特性

### 1. 自动服务注册
- 服务启动时自动注册到 Nacos
- 服务关闭时自动注销

### 2. 心跳维持
- 后台线程定期发送心跳（默认 5 秒）
- 心跳失败会记录日志但继续尝试

### 3. 健康检查
- Nacos 会监控服务健康状态
- 心跳超时后自动标记为不健康

### 4. 优雅关闭
- 捕获 SIGINT/SIGTERM 信号
- 主动注销服务后再退出

### 5. 可配置性
- 支持通过环境变量灵活配置
- 可以通过 `NACOS_ENABLED=false` 禁用

## 代码架构

```
ragflow/
├── api/
│   ├── utils/
│   │   └── nacos_registry.py      # Nacos 注册核心模块
│   └── ragflow_server.py          # 主服务启动文件（已集成）
├── docker/
│   └── .env                        # 环境变量配置（已添加 Nacos 配置）
└── pyproject.toml                  # 依赖声明（已添加 nacos-sdk-python）
```

### 核心类：NacosRegistry

位于 `api/utils/nacos_registry.py`，主要方法：

- `initialize()` - 初始化 Nacos 客户端
- `register_service()` - 注册服务
- `deregister_service()` - 注销服务
- `start_heartbeat()` - 启动心跳线程
- `stop_heartbeat()` - 停止心跳线程
- `send_heartbeat()` - 发送心跳
- `get_config()` - 获取配置中心配置
- `get_service_instances()` - 获取服务实例列表

## 常见问题

### Q1: 服务注册失败怎么办？

**排查步骤：**
1. 检查 Nacos 服务器是否可达
```bash
curl http://172.19.70.125:8848/nacos/v1/console/health/readiness
```

2. 检查认证信息是否正确
```bash
# 测试登录
curl -X POST 'http://172.19.70.125:8848/nacos/v1/auth/login' \
  -d 'username=nacos&password=nacos'
```

3. 查看日志中的错误信息

### Q2: 如何禁用 Nacos 注册？

在 `docker/.env` 中设置：
```bash
NACOS_ENABLED=false
```

### Q3: 如何修改心跳间隔？

```bash
export NACOS_HEARTBEAT_INTERVAL=10  # 改为 10 秒
```

### Q4: 多实例部署时如何区分？

可以通过 `SERVICE_IP` 指定不同的 IP，或使用不同的 `NACOS_SERVICE_NAME`。

### Q5: 如何使用 Nacos 配置中心？

```python
from api.utils.nacos_registry import nacos_registry

# 获取配置
config = nacos_registry.get_config("ragflow.yaml", "DEFAULT_GROUP")
```

## 生产环境建议

1. **使用独立的 Nacos 集群**：确保高可用
2. **修改默认密码**：不要使用默认的 nacos/nacos
3. **配置命名空间**：区分开发、测试、生产环境
4. **设置合理的权重**：根据服务器性能调整
5. **监控心跳状态**：确保服务持续健康
6. **使用非临时实例**：对于关键服务，考虑设置 `ephemeral=false`

## 扩展功能

### 配置中心集成

Nacos 还可以作为配置中心使用，示例：

```python
# 获取配置
config_content = nacos_registry.get_config("application.yml", "DEFAULT_GROUP")

# 监听配置变化（需要扩展实现）
def config_callback(data_id, group, config_content):
    print(f"Config changed: {data_id}")
```

### 服务发现

```python
# 获取其他服务实例
instances = nacos_registry.get_service_instances("other-service")
for instance in instances:
    print(f"Instance: {instance['ip']}:{instance['port']}")
```

## 技术支持

如有问题，请查看：
1. Nacos 官方文档：https://nacos.io/zh-cn/docs/what-is-nacos.html
2. nacos-sdk-python 文档：https://github.com/nacos-group/nacos-sdk-python
3. RAGFlow 项目文档：/root/project/ragflow/README.md
