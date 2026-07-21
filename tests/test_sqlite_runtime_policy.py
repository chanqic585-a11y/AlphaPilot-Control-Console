from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.sqlite_runtime_policy import (
    apply_migration,
    ensure_migration_ledger,
    get_user_version,
    integrity_check,
    online_backup,
    open_sqlite,
)


class SqliteRuntimePolicyTests(unittest.TestCase):
    def test_runtime_pragmas_and_migration_ledger_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            connection = open_sqlite(Path(directory) / "source.sqlite")
            try:
                ensure_migration_ledger(connection)
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                self.assertEqual(connection.execute("PRAGMA busy_timeout").fetchone()[0], 5_000)

                applied = apply_migration(
                    connection,
                    migration_id="001-example",
                    description="create example table",
                    statements=("CREATE TABLE Example (id TEXT PRIMARY KEY)",),
                    target_user_version=1,
                )
                self.assertTrue(applied)
                self.assertEqual(get_user_version(connection), 1)
                self.assertFalse(
                    apply_migration(
                        connection,
                        migration_id="001-example",
                        description="create example table",
                        statements=("CREATE TABLE Example (id TEXT PRIMARY KEY)",),
                        target_user_version=1,
                    )
                )
            finally:
                connection.close()

    def test_changed_migration_checksum_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            connection = open_sqlite(Path(directory) / "source.sqlite")
            try:
                apply_migration(
                    connection,
                    migration_id="001-example",
                    description="first",
                    statements=("CREATE TABLE Example (id TEXT PRIMARY KEY)",),
                    target_user_version=1,
                )
                with self.assertRaises(RuntimeError):
                    apply_migration(
                        connection,
                        migration_id="001-example",
                        description="changed",
                        statements=("CREATE TABLE Example (id INTEGER PRIMARY KEY)",),
                        target_user_version=1,
                    )
            finally:
                connection.close()

    def test_online_backup_is_integrity_checked_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.sqlite"
            backup_path = root / "backup.sqlite"
            connection = open_sqlite(source_path)
            try:
                connection.execute("CREATE TABLE Example (id TEXT PRIMARY KEY)")
                connection.execute("INSERT INTO Example VALUES ('one')")
                connection.commit()
                receipt = online_backup(connection, backup_path)
            finally:
                connection.close()

            self.assertTrue(receipt["integrityPassed"])
            self.assertEqual(receipt["sha256"], hashlib.sha256(backup_path.read_bytes()).hexdigest())
            backup = open_sqlite(backup_path, wal=False)
            try:
                self.assertEqual(backup.execute("SELECT COUNT(*) FROM Example").fetchone()[0], 1)
                self.assertTrue(integrity_check(backup)["passed"])
            finally:
                backup.close()


if __name__ == "__main__":
    unittest.main()
