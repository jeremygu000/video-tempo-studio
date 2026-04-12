#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path


def default_watch_directory() -> str:
    env_value = os.environ.get("VIDEO_SOURCE_DIR", "").strip()
    if env_value:
        return env_value
    return str(Path.home() / "Videos")


def seed_default_watch_target(conn: sqlite3.Connection, directory: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO watch_targets(directory, enabled)
        VALUES(?, 1)
        """,
        (directory,),
    )


def initialize_database(db_path: Path, schema_path: Path, watch_directory: str | None = None) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    seed_directory = watch_directory or default_watch_directory()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        seed_default_watch_target(conn, seed_directory)
        conn.commit()


def main() -> None:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Initialize SQLite database for video processing jobs.")
    parser.add_argument(
        "--db",
        default=str(script_dir / "biansu.db"),
        help="Path to SQLite database file.",
    )
    parser.add_argument(
        "--schema",
        default=str(script_dir / "schema.sql"),
        help="Path to SQL schema file.",
    )
    parser.add_argument(
        "--watch-directory",
        default=None,
        help="Default watch directory to insert into watch_targets.",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    schema_path = Path(args.schema).resolve()

    initialize_database(db_path, schema_path, watch_directory=args.watch_directory)
    print(f"Database initialized: {db_path}")


if __name__ == "__main__":
    main()
