import argparse
import sqlite3
import sys
from pathlib import Path


DEFAULT_DB = "renovation.db"


def confirm(prompt):
    response = input(f"{prompt} [y/N]: ").strip().lower()
    return response in ("y", "yes")


def apply_backup(db_path, backup_path):
    backup_sql = Path(backup_path).read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")
        conn.executescript(backup_sql)
        conn.commit()
    except sqlite3.DatabaseError as exc:
        conn.rollback()
        raise RuntimeError(f"Restore failed: {exc}") from exc
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Apply a SQL backup file to the SQLite database."
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to the SQLite DB.")
    parser.add_argument(
        "--backup", required=True, help="Path to the backup SQL file."
    )
    parser.add_argument(
        "--yes", action="store_true", help="Apply without confirmation prompt."
    )
    args = parser.parse_args()

    if not args.yes:
        if not confirm(f"Apply backup {args.backup} to {args.db}?"):
            print("Restore cancelled.")
            sys.exit(1)

    try:
        apply_backup(args.db, args.backup)
    except RuntimeError as exc:
        print(str(exc))
        sys.exit(1)
    print(f"Backup applied to {args.db}")


if __name__ == "__main__":
    main()
