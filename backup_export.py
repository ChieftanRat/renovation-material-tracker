import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path


DEFAULT_DB = "renovation.db"
TABLE_ORDER = [
    "projects",
    "tasks",
    "vendors",
    "laborers",
    "material_purchases",
    "work_sessions",
    "work_session_entries",
]


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    text = str(value).replace("'", "''")
    return f"'{text}'"


def table_columns(conn, table):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def table_rows(conn, table, columns):
    cols = ", ".join(columns)
    return conn.execute(f"SELECT {cols} FROM {table}").fetchall()


def load_seed_db(schema_path, seed_path):
    conn = sqlite3.connect(":memory:")
    conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
    conn.executescript(Path(seed_path).read_text(encoding="utf-8"))
    return conn


def list_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [row[0] for row in rows]


def ordered_tables(tables):
    ordered = [table for table in TABLE_ORDER if table in tables]
    remaining = [table for table in tables if table not in ordered]
    return ordered + remaining


def export_backup(db_path, schema_path, seed_path, output_path, include_seed):
    db_conn = sqlite3.connect(db_path)
    seed_conn = load_seed_db(schema_path, seed_path)
    tables = ordered_tables(list_tables(db_conn))

    lines = [
        "-- Renovation Material Tracker backup",
        f"-- Source DB: {db_path}",
        f"-- Generated: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        "BEGIN TRANSACTION;",
    ]

    for table in tables:
        columns = table_columns(db_conn, table)
        rows = table_rows(db_conn, table, columns)
        seed_rows = table_rows(seed_conn, table, columns)
        seed_set = set(seed_rows)
        for row in rows:
            if not include_seed and row in seed_set:
                continue
            values = ", ".join(sql_literal(value) for value in row)
            cols = ", ".join(columns)
            lines.append(f"INSERT INTO {table} ({cols}) VALUES ({values});")

    lines.append("COMMIT;")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    db_conn.close()
    seed_conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export a backup excluding seeded data by default."
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to the SQLite DB.")
    parser.add_argument(
        "--schema", default="schema.sql", help="Path to schema.sql."
    )
    parser.add_argument("--seed", default="seed.sql", help="Path to seed.sql.")
    parser.add_argument(
        "--out",
        default="",
        help="Output file path. Defaults to backups/backup_YYYYMMDD_HHMMSS.sql",
    )
    parser.add_argument(
        "--include-seed",
        action="store_true",
        help="Include seeded data in the export.",
    )
    args = parser.parse_args()

    if args.out:
        output_path = Path(args.out)
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = Path("backups") / f"backup_{timestamp}.sql"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export_backup(
        db_path=args.db,
        schema_path=args.schema,
        seed_path=args.seed,
        output_path=output_path,
        include_seed=args.include_seed,
    )
    print(f"Backup written to {output_path}")


if __name__ == "__main__":
    main()
