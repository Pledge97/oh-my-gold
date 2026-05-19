# oh-my-gold 部署文档

本文档说明如何把当前项目部署到 Linux 服务器，并通过 `systemd` 防止后端 API 和数据采集服务中断。

## 1. 部署架构

- 前端：`frontend/dist` 由 Nginx 托管。
- 后端 API：FastAPI，监听 `127.0.0.1:8000`。
- 数据采集服务：FastAPI + APScheduler，监听 `127.0.0.1:8001`。
- 数据库：SQLite，默认路径为项目根目录下的 `data/gold.db`。
- 进程保活：`systemd`，服务异常退出后自动重启。

## 2. 服务器准备

建议使用 Ubuntu/Debian 系统，并提前安装：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx sqlite3
```

如果服务器需要构建前端，还需要安装 Node.js 和 npm。也可以在本地构建前端后，只上传 `frontend/dist`。

## 3. 推荐目录

建议把项目放在固定目录：

```bash
/opt/oh-my-gold
```

示例：

```bash
sudo mkdir -p /opt/oh-my-gold
sudo chown -R "$USER":"$USER" /opt/oh-my-gold
```

把代码同步到 `/opt/oh-my-gold` 后，在项目根目录执行：

```bash
cd /opt/oh-my-gold
bash deploy_backend_services.sh
```

脚本会完成：

- 创建 Python 虚拟环境 `.venv`；
- 安装根目录和 `data_service` 的 Python 依赖；
- 创建 `data` 目录；
- 写入两个 `systemd` 服务；
- 启动并设置开机自启。

部署完成后的推荐目录结构如下：

```text
/opt/oh-my-gold/
|-- .venv/                         # Python 虚拟环境
|-- backend/                       # 后端 API 源码
|-- data_service/                  # 数据采集服务源码
|-- frontend/
|   `-- dist/                      # 前端构建产物，Nginx root 指向这里
|-- data/
|   `-- gold.db                    # SQLite 数据库文件
|-- backup/                        # 数据库备份目录，按需创建
|-- requirements.txt               # 后端 Python 依赖
|-- deploy_backend_services.sh     # 后端和数据服务一键部署脚本
|-- nginx-oh-my-gold.conf          # Nginx 站点配置模板
`-- DEPLOY.md                      # 部署文档

/etc/systemd/system/
|-- oh-my-gold-backend.service     # 后端 API systemd 服务
`-- oh-my-gold-data.service        # 数据采集 systemd 服务

/etc/nginx/sites-available/
`-- oh-my-gold.conf                # 从 nginx-oh-my-gold.conf 复制得到

/etc/nginx/sites-enabled/
`-- oh-my-gold.conf                # 指向 sites-available 的软链接
```

## 4. 服务说明

脚本会创建以下服务：

```text
oh-my-gold-backend.service
oh-my-gold-data.service
```

常用命令：

```bash
sudo systemctl status oh-my-gold-backend
sudo systemctl status oh-my-gold-data

sudo journalctl -u oh-my-gold-backend -f
sudo journalctl -u oh-my-gold-data -f

sudo systemctl restart oh-my-gold-backend
sudo systemctl restart oh-my-gold-data
```

本机健康检查：

```bash
curl http://127.0.0.1:8000/docs
curl http://127.0.0.1:8001/health
```

## 5. Nginx 部署

复制根目录的 `nginx-oh-my-gold.conf` 到 Nginx 站点配置目录：

```bash
sudo cp nginx-oh-my-gold.conf /etc/nginx/sites-available/oh-my-gold.conf
sudo ln -sf /etc/nginx/sites-available/oh-my-gold.conf /etc/nginx/sites-enabled/oh-my-gold.conf
sudo nginx -t
sudo systemctl reload nginx
```

修改配置文件中的：

```nginx
server_name your-domain.com;
root /opt/oh-my-gold/frontend/dist;
```

如果只用 IP 访问，可以暂时写：

```nginx
server_name _;
```

## 6. 前端发布

在 `frontend` 目录构建：

```bash
cd frontend
npm ci
npm run build
```

构建产物位于：

```text
frontend/dist
```

Nginx 配置中的 `root` 需要指向这个目录。

## 7. 防止服务中断

当前方案通过以下方式降低中断风险：

- `systemd` 使用 `Restart=always`，进程崩溃后自动重启；
- 后端和数据采集服务只监听 `127.0.0.1`，由 Nginx 统一对外暴露；
- WebSocket 配置了较长的 `proxy_read_timeout`；
- SQLite 数据目录固定，便于备份；
- 后端和数据服务拆成两个进程，互不依赖同一个进程生命周期。

SQLite 仍然是单文件数据库。当前项目中：

- `data_service` 写入 `prices`；
- `backend` 读取行情数据，并可能写入 `signals`、`positions`、`position_lots`；
- `backend` 启动时会通过 `fetch_and_store()` 更新 `daily_prices`。

如果后续写入频率提高，建议迁移到 PostgreSQL，或至少在应用启动时开启 SQLite WAL 模式。

## 8. 数据备份

建议定时备份 `data/gold.db`：

```bash
mkdir -p /opt/oh-my-gold/backup
sqlite3 /opt/oh-my-gold/data/gold.db ".backup '/opt/oh-my-gold/backup/gold-$(date +%F-%H%M).db'"
```

可加入 crontab：

```bash
crontab -e
```

示例，每天凌晨 3 点备份：

```cron
0 3 * * * sqlite3 /opt/oh-my-gold/data/gold.db ".backup '/opt/oh-my-gold/backup/gold-$(date +\%F-\%H\%M).db'"
```

## 9. 更新发布

更新代码后，在项目根目录执行：

```bash
bash deploy_backend_services.sh
```

如果前端也更新，需要重新构建前端并 reload Nginx：

```bash
cd frontend
npm ci
npm run build
sudo nginx -t
sudo systemctl reload nginx
```
