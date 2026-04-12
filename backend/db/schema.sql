PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS runs;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS watch_targets;

CREATE TABLE IF NOT EXISTS watch_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  directory TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_id INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'success', 'failed', 'skipped')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  started_at TEXT,
  finished_at TEXT,
  FOREIGN KEY (target_id) REFERENCES watch_targets(id) ON DELETE CASCADE,
  UNIQUE(target_id, file_path)
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'skipped')),
  progress_pct INTEGER NOT NULL DEFAULT 0,
  progress_text TEXT,
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER,
  log_text TEXT,
  error_message TEXT,
  error_trace TEXT,
  log_file_path TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_watch_targets_enabled ON watch_targets(enabled);
CREATE INDEX IF NOT EXISTS idx_jobs_target_id ON jobs(target_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_runs_job_id ON runs(job_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);
