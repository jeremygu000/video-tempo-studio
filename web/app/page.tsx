"use client";

import { useEffect, useState } from "react";

type Job = {
  id: number;
  directory: string;
  enabled: number;
  created_at: string;
  pending_count: number;
  pending_files: string[];
};

type Run = {
  id: number;
  job_id: number;
  status: "running" | "success" | "failed" | "skipped";
  progress_pct: number;
  progress_text: string | null;
  duration_ms: number | null;
  error_message: string | null;
  log_file_path: string | null;
  created_at: string;
  jobs: {
    file_path: string;
    target_id: number;
  };
};

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [busyJobId, setBusyJobId] = useState<number | null>(null);

  async function refresh() {
    const [jobsResp, runsResp] = await Promise.all([fetch("/api/jobs"), fetch("/api/runs")]);
    const jobsData = (await jobsResp.json()) as { jobs: Job[] };
    const runsData = (await runsResp.json()) as { runs: Run[] };
    setJobs(jobsData.jobs ?? []);
    setRuns(runsData.runs ?? []);
  }

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  async function onToggleJob(job: Job) {
    await fetch(`/api/jobs/${job.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: job.enabled !== 1 }),
    });
    await refresh();
  }

  async function onRunJob(jobId: number) {
    setBusyJobId(jobId);
    try {
      await fetch(`/api/jobs/${jobId}/run`, { method: "POST" });
      await refresh();
    } finally {
      setBusyJobId(null);
    }
  }

  function formatRunStatus(status: Run["status"]) {
    if (status === "running") return "运行中";
    if (status === "success") return "成功";
    if (status === "failed") return "失败";
    if (status === "skipped") return "已跳过";
    return status;
  }

  function formatProgressText(text: string | null) {
    if (!text) return "";
    if (text === "Queued") return "已排队";
    if (text === "Completed") return "已完成";
    if (text === "Failed") return "失败";
    if (text === "Skipped") return "已跳过";
    if (text === "Input file missing") return "源文件不存在";
    if (text.startsWith("Preparing ")) return `准备中：${text.replace("Preparing ", "")}`;
    if (text.includes("separating audio/video")) return text.replace(": separating audio/video", "：拆分音视频");
    if (text.includes("extract-audio")) return text.replace(": extract-audio", "：提取音频");
    if (text.includes("stretch-audio")) return text.replace(": stretch-audio", "：拉伸音频");
    if (text.includes("render-video")) return text.replace(": render-video", "：渲染视频");
    if (text.includes("combining output")) return text.replace(": combining output", "：合成输出");
    if (text.includes("output ready")) return text.replace(": output ready", "：输出完成");
    if (text === "Moving source file") return "移动源文件";
    return text;
  }

  function formatDuration(durationMs: number | null) {
    if (durationMs == null) return "无";
    const totalSeconds = Math.floor(durationMs / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) return `${hours}小时${minutes}分钟${seconds}秒`;
    if (minutes > 0) return `${minutes}分钟${seconds}秒`;
    return `${seconds}秒`;
  }

  const enabledTargets = jobs.filter((job) => job.enabled === 1).length;
  const pendingFiles = jobs.reduce((sum, job) => sum + job.pending_count, 0);
  const runningRuns = runs.filter((run) => run.status === "running").length;
  const failedRuns = runs.filter((run) => run.status === "failed").length;

  return (
    <main className="admin-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">VT</div>
          <div>
            <h1>Video Tempo Studio</h1>
            <p>Admin Console</p>
          </div>
        </div>
        <nav className="menu">
          <button className="menu-item active">仪表盘</button>
          <button className="menu-item">监视目录</button>
          <button className="menu-item">运行记录</button>
        </nav>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <h2>视频变速任务控制台</h2>
            <p>实时查看处理进度与运行状态</p>
          </div>
          <button onClick={() => void refresh()}>手动刷新</button>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <span>监视目录</span>
            <strong>{jobs.length}</strong>
            <em>已启用 {enabledTargets}</em>
          </article>
          <article className="stat-card">
            <span>待处理文件</span>
            <strong>{pendingFiles}</strong>
            <em>跨全部目录</em>
          </article>
          <article className="stat-card">
            <span>运行中任务</span>
            <strong>{runningRuns}</strong>
            <em>实时刷新</em>
          </article>
          <article className="stat-card">
            <span>失败记录</span>
            <strong>{failedRuns}</strong>
            <em>最近 200 条</em>
          </article>
        </section>

        <section className="panel card">
          <details>
            <summary>监视目录（默认折叠）</summary>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>目录</th>
                  <th>状态</th>
                  <th>待处理</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.id}</td>
                    <td>{job.directory}</td>
                    <td>{job.enabled ? "已启用" : "已停用"}</td>
                    <td>
                      <div>{job.pending_count} 个文件</div>
                      {job.pending_files.length > 0 && (
                        <details>
                          <summary>查看文件</summary>
                          <ul>
                            {job.pending_files.map((file) => (
                              <li key={file}>{file}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </td>
                    <td className="actions">
                      <button onClick={() => void onToggleJob(job)}>{job.enabled ? "停用" : "启用"}</button>
                      <button disabled={busyJobId === job.id} onClick={() => void onRunJob(job.id)}>
                        {busyJobId === job.id ? "运行中..." : "立即运行"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </section>

        <section className="panel card">
          <h3>运行记录</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>运行 ID</th>
                <th>任务 ID</th>
                <th>文件</th>
                <th>状态</th>
                <th>进度</th>
                <th>耗时</th>
                <th>错误</th>
                <th>日志文件</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{run.id}</td>
                  <td>{run.job_id}</td>
                  <td>{run.jobs?.file_path ?? "无"}</td>
                  <td>
                    <span className={`status-badge status-${run.status}`}>{formatRunStatus(run.status)}</span>
                  </td>
                  <td>
                    <div className="progress-text">
                      {run.progress_pct ?? 0}% {run.progress_text ? `（${formatProgressText(run.progress_text)}）` : ""}
                    </div>
                    <progress max={100} value={run.progress_pct ?? 0} />
                  </td>
                  <td>{formatDuration(run.duration_ms)}</td>
                  <td>{run.error_message ?? "无"}</td>
                  <td>{run.log_file_path ?? "无"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
