# Video Tempo Studio Windows 运行指南（详细版）

本文档按“从零到可运行”说明如何在 Windows 主机启动本项目。

适用日期：2026-04-18

## 1. 目标与说明

- 你将得到：
  - Web 管理界面（Next.js，默认 `http://localhost:3000`）
  - 后端处理器（Python worker，持续扫描目录并处理视频）
  - SQLite 数据库（任务与运行记录）
- 本文优先使用 PowerShell 命令。
- 由于 Windows 上常见是 `python`/`py -3`，而项目部分 npm 脚本使用了 `python3`，本文会给出“Windows 直接可用命令”。

## 2. 先决条件

请先安装以下软件（建议最新稳定版）：

1. Git
2. Node.js 20+（建议 22 或 24）
3. Python 3.10+（建议 3.12）
4. FFmpeg（必须包含 `ffmpeg` 和 `ffprobe`）

安装后打开 PowerShell 验证：

```powershell
git --version
node -v
npm -v
py -3 --version
ffmpeg -version
ffprobe -version
```

如果 `ffprobe` 报找不到，请把 FFmpeg 的 `bin` 目录加入系统 PATH 后重开终端。

## 2.1 Windows 安装 FFmpeg / FFprobe（详细）

`ffprobe` 会随 `ffmpeg` 一起安装，不需要单独装。

### 方式 A：用 `winget`（推荐）

以管理员身份打开 PowerShell：

```powershell
winget install -e --id Gyan.FFmpeg
```

安装完成后重开 PowerShell，验证：

```powershell
ffmpeg -version
ffprobe -version
```

### 方式 B：用 Chocolatey

如果你已经安装了 Chocolatey：

```powershell
choco install ffmpeg -y
```

然后验证：

```powershell
ffmpeg -version
ffprobe -version
```

### 方式 C：手动安装（离线也常用）

1. 下载 Windows 版 FFmpeg 压缩包（例如 `ffmpeg-release-full.7z`）。
2. 解压到固定目录，例如：`C:\ffmpeg`
3. 确认可执行文件路径存在：
   - `C:\ffmpeg\bin\ffmpeg.exe`
   - `C:\ffmpeg\bin\ffprobe.exe`
4. 把 `C:\ffmpeg\bin` 加入系统环境变量 `Path`：
   - `系统设置 -> 高级系统设置 -> 环境变量 -> Path -> 新建`
5. 关闭并重新打开 PowerShell，验证：

```powershell
ffmpeg -version
ffprobe -version
```

如果仍提示找不到命令，通常是终端没有重开，或者 `Path` 加错目录（应加到 `bin`）。

## 3. 获取项目代码

```powershell
cd D:\
mkdir scripts -ErrorAction SilentlyContinue
cd scripts
git clone <你的仓库地址> video-tempo-studio
cd video-tempo-studio
```

## 4. 安装依赖

在项目根目录执行：

```powershell
npm install
```

## 5. 初始化数据库（关键）

### 5.1 推荐：初始化时直接写入你的监视目录

示例（按你自己的目录改）：

```powershell
py -3 backend\db\init_db.py --watch-directory "D:\Dropbox\视频变速自动化"
```

### 5.2 验证数据库是否创建成功

```powershell
Test-Path .\backend\db\biansu.db
```

如果返回 `True`，说明数据库文件已创建。

## 6. 开发模式启动（推荐先跑通）

需要两个终端窗口。

### 终端 A：启动前端

```powershell
cd D:\scripts\video-tempo-studio
npm run dev
```

打开浏览器访问：

```text
http://localhost:3000
```

### 终端 B：启动 worker（Windows 版命令）

```powershell
cd D:\scripts\video-tempo-studio
py -3 backend\apps\worker.py --watch --poll-interval 30
```

日志里看到类似：

```text
Watch cycle stats: {'discovered': X, 'executed': Y}
```

表示 worker 正常运行。

## 7. 生产/常驻模式（PM2）

如果你希望意外退出后自动拉起，可用 PM2。

### 7.1 构建前端

```powershell
cd D:\scripts\video-tempo-studio
npm run build -w web
```

### 7.2 启动 web（PM2）

```powershell
npm run web:pm2:start
```

### 7.3 启动 worker（Windows 版 PM2 命令）

```powershell
npx pm2 start py --name video-worker -- -3 backend\apps\worker.py --watch --poll-interval 30
```

### 7.4 查看状态与日志

```powershell
npx pm2 status
npx pm2 logs video-web --lines 100
npx pm2 logs video-worker --lines 100
```

### 7.5 重启/停止

```powershell
npx pm2 restart video-web
npx pm2 restart video-worker

npx pm2 stop video-web
npx pm2 stop video-worker
```

## 8. 常见问题排查

## 8.1 `/api/jobs` 或 `/api/runs` 报 `Unable to open the database file`

按顺序检查：

1. 确认数据库存在：`backend\db\biansu.db`
2. 你是否在项目根目录运行命令
3. 执行过初始化：`py -3 backend\db\init_db.py ...`
4. 重启前端进程（dev 或 pm2）

## 8.2 显示 `ffprobe not found`

1. 执行 `ffprobe -version` 验证
2. 若失败，把 FFmpeg `bin` 加入 PATH
3. 重开终端再启动 worker

## 8.3 前端页面空白或没有数据

1. 检查 worker 是否在运行
2. 检查监视目录里是否有可处理文件（非 `_60/_70/_80/_90` 后缀）
3. 打开“监视目录（默认折叠）”确认目录已启用

## 8.4 前端打不开 `http://localhost:3000`

1. `npm run dev` 是否报错
2. PM2 模式下是否先 `npm run build -w web`
3. `npx pm2 logs video-web --lines 100` 查看报错

## 9. 升级数据库字段（不清空数据）

不要直接用 `schema.sql` 手工重建（里面有 `DROP TABLE`）。

例如新增列：

```sql
PRAGMA table_info(runs);
ALTER TABLE runs ADD COLUMN progress_updated_at TEXT;
PRAGMA table_info(runs);
```

本项目部分列也会在 worker/API 启动时自动补齐。

## 10. Windows 建议命令清单

开发模式：

```powershell
# 终端 A
npm run dev

# 终端 B
py -3 backend\apps\worker.py --watch --poll-interval 30
```

生产模式：

```powershell
npm run build -w web
npm run web:pm2:start
npx pm2 start py --name video-worker -- -3 backend\apps\worker.py --watch --poll-interval 30
npx pm2 status
```

## 11. 电脑重启后如何自动继续运行

要做到“重启后继续跑”，建议两层保障：

1. 开机自动启动服务（PM2）
2. 启动时恢复异常中断的 `running` 任务

### 11.1 开机自动启动（任务计划程序）

先确保你平时是用 PM2 运行：

```powershell
cd D:\scripts\video-tempo-studio
npm run pm2:start:all
```

然后创建一个 PowerShell 启动脚本，例如：

`D:\scripts\video-tempo-studio\scripts\start-services.ps1`

内容：

```powershell
Set-Location "D:\scripts\video-tempo-studio"
npm run pm2:start:all
```

在“任务计划程序”中创建任务：

1. 触发器：`启动时`
2. 操作：`启动程序`
3. 程序/脚本：`powershell.exe`
4. 参数：`-ExecutionPolicy Bypass -File "D:\scripts\video-tempo-studio\scripts\start-services.ps1"`
5. 勾选“使用最高权限运行”（建议）

这样电脑每次开机都会自动拉起前后端服务。

### 11.2 恢复重启前中断的任务（避免卡在 running）

如果断电/重启时有任务正在跑，数据库可能残留 `running` 记录。建议开机后先检查：

```powershell
sqlite3 .\backend\db\biansu.db "SELECT id,status,started_at,finished_at FROM jobs WHERE status='running';"
sqlite3 .\backend\db\biansu.db "SELECT id,job_id,status,started_at,finished_at FROM runs WHERE status='running';"
```

如果确认这些是“中断残留”而非真实运行中的任务，可以重置为待处理：

```powershell
sqlite3 .\backend\db\biansu.db "UPDATE jobs SET status='pending', started_at=NULL, finished_at=NULL WHERE status='running';"
sqlite3 .\backend\db\biansu.db "UPDATE runs SET status='failed', finished_at=datetime('now'), error_message='Recovered after host reboot', progress_text='Failed' WHERE status='running';"
```

然后重启 worker：

```powershell
npx pm2 restart video-worker
```

后续 worker 会重新处理这些 `pending` 任务。
