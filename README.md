# Video Tempo Studio

一个用于“视频变速练习素材生成”的项目。

- 后端（Python）：扫描目录、入队、处理视频、写入运行记录
- 前端（Next.js）：查看监视目录、任务进度、运行历史
- 数据库（SQLite）：存储 watch targets / jobs / runs

## 功能
- 自动发现视频并入队
- 实时进度展示（前端可见）
- 文件就绪检测（避免上传未完成就处理）
- `ffprobe` 预检（缺少音频/视频流会跳过并记录原因）
- 支持常见后缀：
  - `.mp4 .m4v .avi .mov .mkv .mpg .mpeg .webm .wmv .flv .ts .m2ts .mts .3gp`

## 目录结构
```text
video-tempo-studio/
  backend/
    apps/
    db/
    tests/
  web/
    app/
    lib/
    prisma/
```

## 环境要求
- Node.js 18+
- Python 3.10+
- FFmpeg + FFprobe（加入 PATH）

## 快速开始
在项目根目录执行：

```bash
npm install
npm run db:init
npm run dev
```

另开终端启动 worker：

```bash
npm run worker:watch
```

## PM2 守护运行（推荐）
后端长期运行建议使用 `pm2`，避免进程意外退出。

```bash
npm run worker:pm2:start
npm run worker:pm2:status
npm run worker:pm2:logs
```

- `worker:pm2:start` 已内置单实例收敛（确保只有 1 个 `video-worker`）
- 手动收敛命令：`npm run worker:pm2:ensure`

前端也可用 pm2 运行（生产模式）：

```bash
npm run build -w web
npm run web:pm2:start
```

一键启动前后端：

```bash
npm run pm2:start:all
```

推荐日常运维命令：

```bash
npm run pm2:start:all    # 先 build 前端，再启动前后端
npm run pm2:stop:all     # 一键停止前后端
npm run pm2:restart:all  # 一键重启前后端
npm run pm2:delete:all   # 清空 pm2 中的前后端进程定义
npm run worker:pm2:status
```

## 防止睡眠（macOS）
如果你需要合盖前后让任务持续运行，可在单独终端执行：

```bash
npm run mac:awake
```

合盖场景建议优先使用 `mac:awake`（更强的防睡眠策略）。

- 停止方式：`Ctrl + C`
- 若只希望“服务运行但屏幕可熄灭”，可用：

```bash
npm run mac:awake:screen-off
```

## 常用命令
```bash
npm run dev
npm run worker:watch
npm run worker:once
npm run worker:pm2:start
npm run worker:pm2:status
npm run worker:pm2:logs
npm run worker:pm2:ensure
npm run web:pm2:start
npm run pm2:start:all
npm run pm2:stop:all
npm run pm2:restart:all
npm run pm2:delete:all
npm run db:init
npm run test:python
npm run test:web
npm run test:all
```

## 配置项（环境变量）
- `VIDEO_SOURCE_DIR`：默认视频目录（`init_db.py` + `video_processor.py`）
- `PYTHON_BIN`：web 调 worker 的 python 命令（Win 默认 `python`，其他默认 `python3`）
- `WORKER_PATH` / `SCRIPT_PATH` / `DB_PATH` / `LOGS_DIR`：覆盖 web 触发 worker 的路径

## Windows 说明
已移除 macOS 绝对路径依赖，Windows 可运行。请确认：
- 已安装 ffmpeg/ffprobe
- 已执行 `npm run db:init`

详细步骤请看：[WINDOWS_SETUP.zh-CN.md](./WINDOWS_SETUP.zh-CN.md)

## 常见问题
- `http://localhost:3000` 打不开且 `video-web` 报错找不到 `.next`：
  - 先执行 `npm run build -w web`，再 `npm run web:pm2:restart`
- `pm2 logs` 看不到 worker 周期日志：
  - 已使用 `python3 -u` 无缓冲运行，重启后会看到 `Watch cycle stats`
- `/api/jobs` 或 `/api/runs` 报 `Unable to open the database file`：
  - 确认已执行 `npm run db:init`
  - 重启 web 进程使 Prisma 重新加载路径配置

## License
Apache License 2.0，见 [LICENSE](./LICENSE)。
