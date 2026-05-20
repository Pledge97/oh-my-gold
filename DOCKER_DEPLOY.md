# Docker 部署文档

本文档说明如何使用 Docker Compose 部署当前项目。该方式会同时启动前端、后端 API 和数据采集服务，并通过挂载宿主机 `data` 目录持久化 SQLite 数据库。

## 1. 部署结构

```text
/opt/oh-my-gold/
|-- backend/                 # 后端 API 源码
|-- data_service/            # 数据采集服务源码
|-- frontend/                # 前端源码
|-- data/                    # SQLite 持久化目录
|   `-- gold.db
|-- backup/                  # 数据库备份目录，按需创建
|-- Dockerfile.backend       # 后端镜像构建文件
|-- Dockerfile.data          # 数据采集镜像构建文件
|-- Dockerfile.frontend      # 前端 Nginx 镜像构建文件
|-- docker-compose.yml       # Docker Compose 编排文件
|-- nginx.docker.conf        # 容器内 Nginx 配置
|-- .dockerignore            # Docker 构建忽略文件
`-- DOCKER_DEPLOY.md         # Docker 部署文档
```

容器关系：

```text
frontend 容器 Nginx :80
|-- /api/  -> backend:8000
|-- /ws    -> backend:8000/ws
`-- /data/ -> data-service:8001

backend 容器
`-- /app/data -> 宿主机 ./data

data-service 容器
`-- /app/data -> 宿主机 ./data
```

## 2. 安装 Docker

如果服务器可以访问 Docker 官方源，推荐安装 Docker 官方版本。若官方源不可用，可以先使用系统源的 `docker.io` 和旧版 `docker-compose`。

Ubuntu/Debian 系统源安装方式：

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
```

验证：

```bash
docker version
docker-compose version
```

如果安装的是 Docker Compose 插件，则验证命令是：

```bash
docker compose version
```

## 3. 上传项目

建议部署目录：

```bash
/opt/oh-my-gold
```

示例：

```bash
cd /opt
git clone https://github.com/Pledge97/oh-my-gold
```

把代码同步到该目录后继续执行后续命令。

## 4. 创建数据目录

```bash
mkdir -p data backup
```

`data` 目录会挂载到容器内 `/app/data`，用于保存：

```text
data/gold.db
```

容器重建不会删除该数据库文件。

## 5. 启动服务

如果你的服务器支持新版 Compose 插件：

```bash
docker compose up -d --build
```

如果安装的是旧版 `docker-compose`：

```bash
docker-compose up -d --build
```

首次启动会构建三个镜像：

- `oh-my-gold-backend`
- `oh-my-gold-data-service`
- `oh-my-gold-frontend`

## 6. 查看状态和日志

```bash
docker compose ps
docker compose logs -f
docker compose logs -f backend
docker compose logs -f data-service
docker compose logs -f frontend
```

## 7. 访问服务

浏览器访问：

```text
http://服务器IP
```

接口代理：

```text
/api/  -> 后端 API
/ws    -> 后端 WebSocket
/data/ -> 数据采集服务
```

本机检查：

```bash
curl http://127.0.0.1/api/signals
curl http://127.0.0.1/data/health
```

## 8. 更新部署

拉取或上传新代码后：

```bash
docker compose up -d --build
```

`./data/gold.db` 保存在宿主机，不会因为镜像重建丢失。

## 9. 停止服务

新版 Compose：

```bash
docker compose down
```

旧版 Compose：

```bash
docker-compose down
```

该命令只停止和删除容器，不会删除 `./data`。

## 10. 备份数据库

```bash
mkdir -p backup
sqlite3 data/gold.db ".backup 'backup/gold-$(date +%F-%H%M).db'"
```

建议加入定时任务：

```bash
crontab -e
```

每天凌晨 3 点备份：

```cron
0 3 * * * cd /opt/oh-my-gold && sqlite3 data/gold.db ".backup 'backup/gold-$(date +\%F-\%H\%M).db'"
```

## 11. 常见问题

### docker compose 命令不存在

说明你安装的是旧版 Compose，改用：

```bash
docker-compose up -d --build
```

### 端口 80 被占用

修改 `docker-compose.yml`：

```yaml
ports:
  - "8080:80"
```

然后访问：

```text
http://服务器IP:8080
```

### 数据库文件没有生成

检查挂载目录权限：

```bash
ls -ld data
chmod 755 data
```

如果容器日志提示 SQLite 无法写入，执行：

```bash
sudo chown -R 1000:1000 data
```

### 查看容器内文件

新版 Compose：

```bash
docker compose exec backend ls -la /app/data
docker compose exec data-service ls -la /app/data
```

旧版 Compose：

```bash
docker-compose exec backend ls -la /app/data
docker-compose exec data-service ls -la /app/data
```
