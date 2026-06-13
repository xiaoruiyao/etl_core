# FDS ETL 部署说明

## 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0

## 目录结构

```
fds_etl/
├── api_server.py          # FastAPI 后端
├── etl_core/              # ETL 调度器
├── biz-dashboard/         # Vue 前端
├── Dockerfile             # 后端镜像
├── docker-compose.yml     # 编排配置
└── requirements.txt       # Python 依赖
```

## 快速部署

### 1. 克隆项目到服务器

```bash
git clone <repo-url> fds_etl
cd fds_etl
```

### 2. 配置数据库连接

确认 `api_server.py` 和 `etl_core/` 中的数据库连接参数（host、port、user、password、database）已指向目标 PostgreSQL 实例。

### 3. 构建并启动

```bash
docker-compose up -d --build
```

首次构建需要下载基础镜像和安装依赖，耗时约 5~10 分钟。

### 4. 查看启动状态

```bash
docker-compose ps
```

正常状态：

```
NAME             STATUS
fds_api          Up (healthy)
fds_scheduler    Up
fds_frontend     Up
```

> `fds_scheduler` 会等待 `fds_api` 健康检查通过后才启动。

## 访问地址

| 服务     | 地址                        |
| -------- | --------------------------- |
| 前端界面 | http://<服务器IP>:8050      |
| 后端 API | http://<服务器IP>:8000/docs |

## 常用命令

```bash
# 查看所有容器状态
docker-compose ps

# 查看某个服务的日志（实时）
docker-compose logs -f api
docker-compose logs -f scheduler
docker-compose logs -f frontend

# 停止所有服务
docker-compose down

# 停止并删除镜像（完全清理）
docker-compose down --rmi all

# 重新构建并启动某个服务
docker-compose up -d --build api

# 进入容器调试
docker exec -it fds_api bash
```

## 更新部署

代码更新后重新构建：

```bash
git pull
docker-compose up -d --build
```

## 端口说明

| 端口 | 服务                |
| ---- | ------------------- |
| 8050 | 前端（nginx）       |
| 8000 | 后端 API（FastAPI） |

如需修改端口，编辑 `docker-compose.yml` 中对应的 `ports` 配置，格式为 `"宿主机端口:容器端口"`。

## 故障排查

**构建失败 - pip 依赖冲突**

检查 `requirements.txt`，确保 `fastapi` 和 `sse-starlette` 未锁定冲突版本。

**前端无法访问后端接口**

前端通过 nginx 反向代理访问 `/api/`，nginx 将请求转发至 `http://api:8000`（Docker 内部网络）。确认 `fds_api` 容器状态为 `healthy`。

**调度器未启动**

`fds_scheduler` 依赖 `fds_api` 健康检查通过，检查 API 服务是否正常：

```bash
docker-compose logs api
```
