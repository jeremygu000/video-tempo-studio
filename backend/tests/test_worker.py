import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import apps.worker as worker

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BACKEND_ROOT / "db" / "schema.sql"
SCRIPT_PATH = str(BACKEND_ROOT / "apps" / "video_processor.py")


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "biansu.db"
        self.logs_dir = Path(self.tempdir.name) / "logs"
        self.watch_dir = Path(self.tempdir.name) / "watch"
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO watch_targets(directory, enabled) VALUES(?, ?)",
            (str(self.watch_dir), 1),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tempdir.cleanup()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_discover_jobs_enqueues_supported_files_only(self):
        (self.watch_dir / "piece.mp4").write_text("x")
        (self.watch_dir / "piece_60.mp4").write_text("x")
        (self.watch_dir / "notes.txt").write_text("x")

        with self._conn() as conn:
            discovered = worker.discover_jobs(conn)
            self.assertEqual(discovered, 1)
            rows = conn.execute("SELECT file_path, status FROM jobs").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]["file_path"].endswith("piece.mp4"))
            self.assertEqual(rows[0]["status"], "pending")

    def test_discover_jobs_supports_more_video_extensions(self):
        (self.watch_dir / "clip.m4v").write_text("x")
        (self.watch_dir / "clip.webm").write_text("x")
        (self.watch_dir / "clip.MTS").write_text("x")

        with self._conn() as conn:
            discovered = worker.discover_jobs(conn)
            self.assertEqual(discovered, 3)
            rows = conn.execute("SELECT file_path FROM jobs ORDER BY file_path").fetchall()
            paths = [row["file_path"] for row in rows]
            self.assertTrue(any(path.endswith("clip.m4v") for path in paths))
            self.assertTrue(any(path.endswith("clip.webm") for path in paths))
            self.assertTrue(any(path.endswith("clip.MTS") for path in paths))

    def test_run_worker_cycle_processes_pending_job_success(self):
        file_path = self.watch_dir / "piece.mp4"
        file_path.write_text("x")

        process_mock = mock.Mock()
        process_mock.stdout = iter(["PROGRESS 40 Working\n", "ok\n"])
        process_mock.wait.return_value = 0
        process_mock.returncode = 0
        with mock.patch.object(worker.subprocess, "Popen", return_value=process_mock):
            stats = worker.run_worker_cycle(
                db_path=self.db_path,
                script_path=SCRIPT_PATH,
                logs_dir=self.logs_dir,
            )

        self.assertEqual(stats["discovered"], 1)
        self.assertEqual(stats["executed"], 1)

        with self._conn() as conn:
            job = conn.execute("SELECT status FROM jobs LIMIT 1").fetchone()
            run = conn.execute(
                "SELECT status, progress_pct, progress_text, error_message, log_file_path FROM runs LIMIT 1"
            ).fetchone()
            self.assertEqual(job["status"], "success")
            self.assertEqual(run["status"], "success")
            self.assertEqual(run["progress_pct"], 100)
            self.assertEqual(run["progress_text"], "Completed")
            self.assertIsNone(run["error_message"])
            self.assertTrue(Path(run["log_file_path"]).exists())

    def test_run_worker_cycle_processes_pending_job_failure(self):
        file_path = self.watch_dir / "piece.mp4"
        file_path.write_text("x")

        process_mock = mock.Mock()
        process_mock.stdout = iter(["PROGRESS 30 Working\n", "partial\n", "boom\n"])
        process_mock.wait.return_value = 3
        process_mock.returncode = 3
        with mock.patch.object(worker.subprocess, "Popen", return_value=process_mock):
            stats = worker.run_worker_cycle(
                db_path=self.db_path,
                script_path=SCRIPT_PATH,
                logs_dir=self.logs_dir,
            )

        self.assertEqual(stats["discovered"], 1)
        self.assertEqual(stats["executed"], 1)

        with self._conn() as conn:
            job = conn.execute("SELECT status FROM jobs LIMIT 1").fetchone()
            run = conn.execute("SELECT status, progress_text, error_message, log_text FROM runs LIMIT 1").fetchone()
            self.assertEqual(job["status"], "failed")
            self.assertEqual(run["status"], "failed")
            self.assertEqual(run["progress_text"], "Failed")
            self.assertIn("exit code 3", run["error_message"])
            self.assertIn("boom", run["log_text"])

    def test_process_one_job_skips_when_job_is_not_pending(self):
        file_path = self.watch_dir / "piece.mp4"
        file_path.write_text("x")

        with self._conn() as conn:
            worker.discover_jobs(conn)
            job = worker.fetch_pending_jobs(conn)[0]
            conn.execute("UPDATE jobs SET status = 'running' WHERE id = ?", (job["id"],))
            conn.commit()

            run_id = worker.process_one_job(
                conn,
                job,
                script_path=SCRIPT_PATH,
                logs_dir=self.logs_dir,
            )

            self.assertIsNone(run_id)
            runs = conn.execute("SELECT id FROM runs").fetchall()
            self.assertEqual(len(runs), 0)

    def test_run_worker_cycle_does_not_reprocess_running_job(self):
        file_path = self.watch_dir / "piece.mp4"
        file_path.write_text("x")

        with self._conn() as conn:
            worker.discover_jobs(conn)
            job = conn.execute("SELECT id FROM jobs LIMIT 1").fetchone()
            conn.execute("UPDATE jobs SET status = 'running' WHERE id = ?", (job["id"],))
            conn.execute(
                "INSERT INTO runs(job_id, status, started_at) VALUES(?, 'running', ?)",
                (job["id"], "2026-01-01T00:00:00+00:00"),
            )
            conn.commit()

        with mock.patch.object(worker.subprocess, "run") as run_mock:
            stats = worker.run_worker_cycle(
                db_path=self.db_path,
                script_path=SCRIPT_PATH,
                logs_dir=self.logs_dir,
            )

        self.assertEqual(stats["discovered"], 0)
        self.assertEqual(stats["executed"], 0)
        run_mock.assert_not_called()

    def test_parse_progress_line(self):
        self.assertEqual(
            worker.parse_progress_line("PROGRESS 45 phase message"),
            (45, "phase message"),
        )
        self.assertEqual(
            worker.parse_progress_line(" PROGRESS   100   done "),
            (100, "done"),
        )
        self.assertIsNone(worker.parse_progress_line("stretch audio finished"))
        self.assertIsNone(worker.parse_progress_line("PROGRESS bad value"))

    def test_parse_skip_reason_line(self):
        self.assertEqual(
            worker.parse_skip_reason_line("SKIP_REASON missing audio stream"),
            "missing audio stream",
        )
        self.assertEqual(
            worker.parse_skip_reason_line(" SKIP_REASON   ffprobe not found "),
            "ffprobe not found",
        )
        self.assertIsNone(worker.parse_skip_reason_line("Skip not-ready file: a.mp4"))

    def test_process_one_job_updates_running_progress(self):
        file_path = self.watch_dir / "piece.mp4"
        file_path.write_text("x")

        with self._conn() as conn:
            worker.discover_jobs(conn)
            job = worker.fetch_pending_jobs(conn)[0]

            process_mock = mock.Mock()
            process_mock.stdout = iter(
                [
                    "PROGRESS 20 Extracting audio\n",
                    "PROGRESS 55 Combining media\n",
                    "plain log line\n",
                ]
            )
            process_mock.wait.return_value = 0
            process_mock.returncode = 0

            with mock.patch.object(worker.subprocess, "Popen", return_value=process_mock):
                run_id = worker.process_one_job(
                    conn,
                    job,
                    script_path=SCRIPT_PATH,
                    logs_dir=self.logs_dir,
                )

            self.assertIsNotNone(run_id)
            run = conn.execute(
                "SELECT status, progress_pct, progress_text, log_text FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            self.assertEqual(run["status"], "success")
            self.assertEqual(run["progress_pct"], 100)
            self.assertEqual(run["progress_text"], "Completed")
            self.assertIn("plain log line", run["log_text"])

    def test_process_one_job_marks_skipped_when_skip_reason_reported(self):
        file_path = self.watch_dir / "piece.mp4"
        file_path.write_text("x")

        with self._conn() as conn:
            worker.discover_jobs(conn)
            job = worker.fetch_pending_jobs(conn)[0]

            process_mock = mock.Mock()
            process_mock.stdout = iter(
                [
                    "PROGRESS 10 Preparing\n",
                    "SKIP_REASON missing audio stream\n",
                ]
            )
            process_mock.wait.return_value = 0
            process_mock.returncode = 0

            with mock.patch.object(worker.subprocess, "Popen", return_value=process_mock):
                run_id = worker.process_one_job(
                    conn,
                    job,
                    script_path=SCRIPT_PATH,
                    logs_dir=self.logs_dir,
                )

            run = conn.execute(
                "SELECT status, progress_pct, progress_text, error_message FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            job_row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job["id"],)).fetchone()
            self.assertEqual(job_row["status"], "skipped")
            self.assertEqual(run["status"], "skipped")
            self.assertEqual(run["progress_pct"], 100)
            self.assertEqual(run["progress_text"], "Skipped")
            self.assertIn("missing audio stream", run["error_message"])

    def test_main_watch_mode_polls_until_interrupted(self):
        cycle_side_effects = [{"discovered": 1, "executed": 1}, {"discovered": 0, "executed": 0}]

        def cycle_once(**_kwargs):
            if cycle_side_effects:
                return cycle_side_effects.pop(0)
            return {"discovered": 0, "executed": 0}

        with mock.patch.object(worker, "run_worker_cycle", side_effect=cycle_once) as cycle_mock, \
             mock.patch.object(worker.time, "sleep", side_effect=[None, KeyboardInterrupt()]):
            exit_code = worker.main(
                [
                    "--db",
                    str(self.db_path),
                    "--script",
                    SCRIPT_PATH,
                    "--logs-dir",
                    str(self.logs_dir),
                    "--watch",
                    "--poll-interval",
                    "1",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(cycle_mock.call_count, 2)

    def test_main_once_mode_runs_single_cycle(self):
        with mock.patch.object(worker, "run_worker_cycle", return_value={"discovered": 0, "executed": 0}) as cycle_mock:
            exit_code = worker.main(
                [
                    "--db",
                    str(self.db_path),
                    "--script",
                    SCRIPT_PATH,
                    "--logs-dir",
                    str(self.logs_dir),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(cycle_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
