# Renovation Material Tracker

This repository contains the initial implementation artifacts for a small-scale renovation project management application. The first implementation step is a normalized relational schema that captures projects, tasks, materials, labor, and work sessions.

## Database Schema

The initial schema lives in [`schema.sql`](schema.sql) and targets SQLite-compatible syntax. To apply it locally:

```sh
sqlite3 renovation.db < schema.sql
```

## Next Steps

- Add seed data and reference queries for reports.
- Implement application services (API or CLI) to capture entries.
- Build report queries for materials, labor, task analytics, and estimates.
