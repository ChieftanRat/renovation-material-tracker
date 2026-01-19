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

## Next Steps

- Implement application services (API or CLI) to capture entries.
- Build exports and dashboards for materials, labor, task analytics, and estimates.
