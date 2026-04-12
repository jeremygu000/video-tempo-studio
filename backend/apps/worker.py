#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".avi",
    ".mov",
    ".mkv",
    ".mpg",
    ".mpeg",
    ".webm",
    ".wmv",
    ".flv",
    ".ts",
    ".m2ts",
    ".mts",
    ".3gp",
}
GENERATED_SUFFIXES = ("_60", "_70", "_80", "_90")
PROGRESS_LINE_RE = re.compile(r"^\s*PROGRESS\s+(\d{1,3})\s+(.+?)\s*$")
SKIP_REASON_RE = re.compile(r"^\s*SKIP_REASON\s+(.+?)\s*$")


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def build_command(script_path: str, directory: str, file_path: str) -> list[str]:
    return [sys.executable, script_path, "--directory", directory, "--file", file_path]


def parse_progress_line(line: str) -> tuple[int, str] | None:
    match = PROGRESS_LINE_RE.match(line)
    if match is None:
        return None
    pct = int(match.group(1))
    if pct < 0 or pct > 100:
        return None
    text = match.group(2).strip()
    return (pct, text)


def parse_skip_reason_line(line: str) -> str | None:
    match = SKIP_REASON_RE.match(line)
    if match is None:
        return None
    reason = match.group(1).strip()
    return reason if reason else None


def ensure_runs_progress_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    if "progress_pct" not in columns:
        conn.execute("ALTER TABLE runs ADD COLUMN progress_pct INTEGER NOT NULL DEFAULT 0")
    if "progress_text" not in columns:
        conn.execute("ALTER TABLE runs ADD COLUMN progress_text TEXT")
    conn.commit()


def scan_target_files(directory: str) -> list[str]:
    target_dir = Path(directory)
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    files: list[Path] = []
    for item in target_dir.iterdir():
        if not item.is_file():
            continue
        if item.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if item.stem.endswith(GENERATED_SUFFIXES):
            continue
        files.append(item)

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(path.resolve()) for path in files]


def fetch_targets(conn: sqlite3.Connection, target_id: int | None = None) -> list[sqlite3.Row]:
    if target_id is None:
        return conn.execute(
            "SELECT id, directory, enabled, created_at FROM watch_targets WHERE enabled = 1 ORDER BY id"
        ).fetchall()
    return conn.execute(
        "SELECT id, directory, enabled, created_at FROM watch_targets WHERE enabled = 1 AND id = ?",
        (target_id,),
    ).fetchall()


def enqueue_jobs_for_target(conn: sqlite3.Connection, target: sqlite3.Row) -> int:
    count = 0
    for file_path in scan_target_files(target["directory"]):
        result = conn.execute(
            """
            INSERT OR IGNORE INTO jobs(target_id, file_path, status)
            VALUES(?, ?, 'pending')
            """,
            (target["id"], file_path),
        )
        if result.rowcount == 1:
            count += 1
    conn.commit()
    return count


def discover_jobs(conn: sqlite3.Connection, target_id: int | None = None) -> int:
    discovered = 0
    for target in fetch_targets(conn, target_id=target_id):
        discovered += enqueue_jobs_for_target(conn, target)
    return discovered


def fetch_pending_jobs(conn: sqlite3.Connection, target_id: int | None = None) -> list[sqlite3.Row]:
    sql = """
        SELECT j.id, j.target_id, j.file_path, j.status, t.directory AS target_directory
          FROM jobs j
          JOIN watch_targets t ON t.id = j.target_id
         WHERE j.status = 'pending'
           AND t.enabled = 1
    """
    params: list[int] = []
    if target_id is not None:
        sql += " AND j.target_id = ?"
        params.append(target_id)
    sql += " ORDER BY j.id"
    return conn.execute(sql, tuple(params)).fetchall()


def claim_pending_job(conn: sqlite3.Connection, job_id: int, started_at: str) -> bool:
    result = conn.execute(
        """
        UPDATE jobs
           SET status = 'running', started_at = ?, finished_at = NULL
         WHERE id = ? AND status = 'pending'
        """,
        (started_at, job_id),
    )
    conn.commit()
    return result.rowcount == 1


def update_run_progress(conn: sqlite3.Connection, run_id: int, pct: int, text: str) -> None:
    conn.execute(
        "UPDATE runs SET progress_pct = ?, progress_text = ? WHERE id = ?",
        (pct, text, run_id),
    )
    conn.commit()


def process_one_job(
    conn: sqlite3.Connection,
    job: sqlite3.Row,
    script_path: str,
    logs_dir: str | Path,
) -> int | None:
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    started_at = utc_now_iso()
    if not claim_pending_job(conn, job["id"], started_at):
        return None

    run_id = conn.execute(
        "INSERT INTO runs(job_id, status, started_at, progress_pct, progress_text) VALUES(?, 'running', ?, 0, ?)",
        (job["id"], started_at, "Queued"),
    ).lastrowid
    conn.commit()

    start_perf = time.perf_counter()
    final_status = "success"
    error_message: str | None = None
    error_trace: str | None = None
    output_log = ""
    progress_pct = 0
    progress_text = "Queued"
    skip_reason: str | None = None

    file_path = Path(job["file_path"])
    if not file_path.exists():
        final_status = "skipped"
        error_message = "Input file not found."
        progress_text = "Input file missing"
    else:
        try:
            process = subprocess.Popen(
                build_command(script_path, job["target_directory"], str(file_path)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_lines: list[str] = []
            if process.stdout is not None:
                stdout_stream = process.stdout
                for line in stdout_stream:
                    output_lines.append(line.rstrip("\n"))
                    parsed = parse_progress_line(line)
                    if parsed is not None:
                        progress_pct, progress_text = parsed
                        update_run_progress(conn, int(run_id), progress_pct, progress_text)
                    parsed_skip_reason = parse_skip_reason_line(line)
                    if parsed_skip_reason is not None:
                        skip_reason = parsed_skip_reason
                close_stdout = getattr(stdout_stream, "close", None)
                if callable(close_stdout):
                    close_stdout()

            return_code = process.wait()
            output_log = "\n".join(output_lines).strip()
            if return_code != 0:
                final_status = "failed"
                error_message = f"Worker command failed with exit code {return_code}"
                progress_text = "Failed"
        except Exception as exc:
            final_status = "failed"
            error_message = f"{type(exc).__name__}: {exc}"
            error_trace = traceback.format_exc()
            output_log = error_trace
            progress_text = "Failed"

    if final_status == "success":
        if skip_reason is not None:
            final_status = "skipped"
            error_message = skip_reason
            progress_pct = 100
            progress_text = "Skipped"
        else:
            progress_pct = 100
            progress_text = "Completed"

    duration_ms = int((time.perf_counter() - start_perf) * 1000)
    finished_at = utc_now_iso()
    log_file_path = logs_dir / f"run_{run_id}.log"
    log_file_path.write_text(output_log, encoding="utf-8")

    conn.execute(
        "UPDATE jobs SET status = ?, finished_at = ? WHERE id = ?",
        (final_status, finished_at, job["id"]),
    )
    conn.execute(
        """
        UPDATE runs
           SET status = ?,
               finished_at = ?,
               duration_ms = ?,
               log_text = ?,
               error_message = ?,
               error_trace = ?,
               log_file_path = ?,
               progress_pct = ?,
               progress_text = ?
         WHERE id = ?
        """,
        (
            final_status,
            finished_at,
            duration_ms,
            output_log,
            error_message,
            error_trace,
            str(log_file_path),
            progress_pct,
            progress_text,
            run_id,
        ),
    )
    conn.commit()
    return int(run_id)


def run_worker_cycle(
    db_path: str | Path,
    script_path: str,
    logs_dir: str | Path,
    target_id: int | None = None,
) -> dict[str, int]:
    discovered = 0
    executed = 0
    db_path = Path(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_runs_progress_columns(conn)
        discovered = discover_jobs(conn, target_id=target_id)
        for pending_job in fetch_pending_jobs(conn, target_id=target_id):
            run_id = process_one_job(conn, pending_job, script_path=script_path, logs_dir=logs_dir)
            if run_id is not None:
                executed += 1

    return {"discovered": discovered, "executed": executed}


def main(argv: list[str] | None = None) -> int:
    script_dir = Path(__file__).resolve().parent
    backend_root = script_dir.parent
    parser = argparse.ArgumentParser(description="Discover and process video jobs from watch targets.")
    parser.add_argument(
        "--db",
        default=str(backend_root / "db" / "biansu.db"),
        help="Path to SQLite database file.",
    )
    parser.add_argument(
        "--script",
        default=str(script_dir / "video_processor.py"),
        help="Path to processing script.",
    )
    parser.add_argument(
        "--logs-dir",
        default=str(backend_root / "logs"),
        help="Directory to store run logs.",
    )
    parser.add_argument(
        "--target-id",
        type=int,
        default=None,
        help="Run only one enabled watch target by id.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep polling and execute newly discovered jobs continuously.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=30.0,
        help="Polling interval in seconds for --watch mode.",
    )
    args = parser.parse_args(argv)

    if not args.watch:
        stats = run_worker_cycle(
            db_path=args.db,
            script_path=args.script,
            logs_dir=args.logs_dir,
            target_id=args.target_id,
        )
        print(f"Cycle stats: {stats}")
        return 0

    try:
        while True:
            stats = run_worker_cycle(
                db_path=args.db,
                script_path=args.script,
                logs_dir=args.logs_dir,
                target_id=args.target_id,
            )
            print(f"Watch cycle stats: {stats}")
            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        print("Worker stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
