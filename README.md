# Renovation Material Tracker

This repository contains the initial implementation artifacts for a small-scale renovation project management application. The first implementation step is a normalized relational schema that captures projects, tasks, materials, labor, and work sessions.

## Database Schema

The initial schema lives in [`schema.sql`](schema.sql) and targets SQLite-compatible syntax. To apply it locally:

```sh
sqlite3 renovation.db < schema.sql
```

## Seed Data

Reference data lives in [`seed.sql`](seed.sql). After creating the schema:

```sh
sqlite3 renovation.db < seed.sql
```

## Reports and Queries

Reference report queries live in [`reports.sql`](reports.sql). You can run them in a SQLite shell:

```sh
sqlite3 renovation.db
.read reports.sql
```

## API Layer

The API server is a lightweight HTTP service (no external dependencies) for capturing entries with validation.

```sh
python api.py
```

Environment variables:
- `RENOVATION_DB` to point at a different SQLite file.
- `PORT` to change the listening port (default 8000).
- `RENOVATION_BACKUPS` to set the backup folder (default `backups/`).
- `RENOVATION_BACKUP_RETENTION_DAYS` to set how long backups are kept (default 30 days).

Example requests:

```sh
curl -X POST http://localhost:8000/projects ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Kitchen Refresh\",\"start_date\":\"2025-01-05\"}"
```

```sh
curl -X POST http://localhost:8000/material-purchases ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":1,\"vendor_id\":1,\"material_description\":\"Tile\",\"unit_cost\":2.4,\"quantity\":180,\"delivery_cost\":45,\"purchase_date\":\"2025-01-11\"}"
```

## Next Steps

- Expand the API with read endpoints and pagination.
- Build exports and dashboards for materials, labor, task analytics, and estimates.

## Quick Start (Windows)

Double-click `start.bat` to launch the API and open the UI in your browser.

## Backup Export

Use `backup_export.py` to export a SQL backup. By default, it excludes seeded data
from `seed.sql` and only exports user-entered rows.

```sh
py backup_export.py
```

Optional flags:
- `--db` to point at a different SQLite file.
- `--out` to choose an output path.
- `--include-seed` to include seeded data.

## Backup Restore

Apply a backup SQL file to the database:

```sh
py backup_restore.py --backup backups/backup_YYYYMMDD_HHMMSS.sql
```

Optional flags:
- `--db` to point at a different SQLite file.
- `--yes` to skip the confirmation prompt.

## Migrations

Apply schema migrations without wiping data:

```sh
py migrate.py
```

Optional flags:
- `--db` to point at a different SQLite file.
