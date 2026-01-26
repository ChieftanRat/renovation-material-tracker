import argparse
import sqlite3
from datetime import datetime


MIGRATIONS = []


def migration(name):
    def wrapper(func):
        MIGRATIONS.append((name, func))
        return func
    return wrapper


def ensure_migrations_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          name TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )


def has_column(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def has_table(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


@migration("001_add_archived_at")
def add_archived_at(conn):
    targets = [
        ("projects", "archived_at"),
        ("tasks", "archived_at"),
        ("vendors", "archived_at"),
        ("material_purchases", "archived_at"),
        ("laborers", "archived_at"),
        ("work_sessions", "archived_at"),
    ]
    for table, column in targets:
        if not has_column(conn, table, column):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


@migration("002_work_session_entries")
def migrate_work_sessions(conn):
    if has_table(conn, "work_session_entries"):
        return
    conn.execute(
        """
        CREATE TABLE work_sessions_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          task_id INTEGER NOT NULL,
          work_date TEXT NOT NULL,
          archived_at TEXT,
          FOREIGN KEY (project_id) REFERENCES projects(id),
          FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO work_sessions_new (id, project_id, task_id, work_date, archived_at)
        SELECT id, project_id, task_id, work_date, archived_at
        FROM work_sessions
        """
    )
    conn.execute(
        """
        CREATE TABLE work_session_entries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          work_session_id INTEGER NOT NULL,
          laborer_id INTEGER NOT NULL,
          clock_in_time TEXT NOT NULL,
          clock_out_time TEXT NOT NULL,
          CHECK (
            julianday('2000-01-01 ' || clock_out_time) >
            julianday('2000-01-01 ' || clock_in_time)
          ),
          FOREIGN KEY (work_session_id) REFERENCES work_sessions(id) ON DELETE CASCADE,
          FOREIGN KEY (laborer_id) REFERENCES laborers(id)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO work_session_entries (
          work_session_id,
          laborer_id,
          clock_in_time,
          clock_out_time
        )
        SELECT id, laborer_id, clock_in_time, clock_out_time
        FROM work_sessions
        """
    )
    conn.execute("DROP TABLE work_sessions")
    conn.execute("ALTER TABLE work_sessions_new RENAME TO work_sessions")
    conn.execute("CREATE INDEX idx_work_sessions_project_id ON work_sessions(project_id)")
    conn.execute("CREATE INDEX idx_work_sessions_task_id ON work_sessions(task_id)")
    conn.execute(
        "CREATE INDEX idx_work_session_entries_session_id ON work_session_entries(work_session_id)"
    )
    conn.execute(
        "CREATE INDEX idx_work_session_entries_laborer_id ON work_session_entries(laborer_id)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Apply schema migrations without wiping data."
    )
    parser.add_argument("--db", default="renovation.db")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        ensure_migrations_table(conn)
        applied = {
            row[0]
            for row in conn.execute("SELECT name FROM schema_migrations").fetchall()
        }
        for name, func in MIGRATIONS:
            if name in applied:
                continue
            func(conn)
            conn.execute(
                "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
                (name, datetime.utcnow().isoformat(timespec="seconds")),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
