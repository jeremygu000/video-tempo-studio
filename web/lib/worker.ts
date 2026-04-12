import { promisify } from "node:util";
import { execFile } from "node:child_process";
import path from "node:path";
import fs from "node:fs";

const execFileAsync = promisify(execFile);

function resolveProjectRoot(): string {
  const cwd = process.cwd();
  const candidates = [cwd, path.resolve(cwd, "..")];
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, "backend", "apps", "worker.py"))) {
      return candidate;
    }
  }
  return candidates[0];
}

const PROJECT_ROOT = resolveProjectRoot();
const WORKER_PATH = process.env.WORKER_PATH ?? path.join(PROJECT_ROOT, "backend", "apps", "worker.py");
const DB_PATH = process.env.DB_PATH ?? path.join(PROJECT_ROOT, "backend", "db", "biansu.db");
const SCRIPT_PATH = process.env.SCRIPT_PATH ?? path.join(PROJECT_ROOT, "backend", "apps", "video_processor.py");
const LOGS_DIR = process.env.LOGS_DIR ?? path.join(PROJECT_ROOT, "backend", "logs");
const PYTHON_BIN = process.env.PYTHON_BIN ?? (process.platform === "win32" ? "python" : "python3");

export async function triggerWorkerForTarget(targetId: number): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync(PYTHON_BIN, [
    WORKER_PATH,
    "--db",
    DB_PATH,
    "--script",
    SCRIPT_PATH,
    "--logs-dir",
    LOGS_DIR,
    "--target-id",
    String(targetId),
  ]);
}
