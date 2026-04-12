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

## 常用命令
```bash
npm run dev
npm run worker:watch
npm run worker:once
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

## License
Apache License 2.0，见 [LICENSE](./LICENSE)。
