import sqlite3
import tempfile
import unittest
from pathlib import Path

from db.init_db import initialize_database

TEST_WATCH_DIRECTORY = "/tmp/video-input-test"


class InitDbTests(unittest.TestCase):
    def test_initialize_database_inserts_default_watch_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "biansu.db"
            schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

            initialize_database(db_path, schema_path, watch_directory=TEST_WATCH_DIRECTORY)

            with sqlite3.connect(db_path) as conn:
                rows = conn.execute("SELECT directory FROM watch_targets ORDER BY id").fetchall()
                self.assertEqual(rows, [(TEST_WATCH_DIRECTORY,)])

    def test_initialize_database_is_idempotent_for_default_watch_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "biansu.db"
            schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

            initialize_database(db_path, schema_path, watch_directory=TEST_WATCH_DIRECTORY)
            initialize_database(db_path, schema_path, watch_directory=TEST_WATCH_DIRECTORY)

            with sqlite3.connect(db_path) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM watch_targets WHERE directory = ?",
                    (TEST_WATCH_DIRECTORY,),
                ).fetchone()[0]
                self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
