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

The API server is a lightweight HTTP service (no external dependencies) for capturing entries with validation. It uses Python's `ThreadingHTTPServer` to handle concurrent requests, and each request opens its own SQLite connection via `get_db()` to keep database access thread-safe.

```sh
python api.py
```

Environment variables:
- `RENOVATION_DB` to point at a different SQLite file.
- `HOST` to control the bind address (defaults to `127.0.0.1`). Use `HOST=0.0.0.0` to expose the API outside the local machine (for example, inside containers).
- `PORT` to change the listening port (default 8000).
- `LOG_LEVEL` to control logging verbosity (defaults to `INFO`).
- `RENOVATION_API_KEY` to require an API key or bearer token for POST requests.

For production deployments, set `HOST=0.0.0.0` (or an explicit interface) only when you intend to expose the service, and keep it behind a reverse proxy or firewall. The default `127.0.0.1` bind keeps the API limited to local requests for safer development by default.

Example requests:

```sh
curl -X POST http://localhost:8000/projects ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: your-secret-key" ^
  -d "{\"name\":\"Kitchen Refresh\",\"start_date\":\"2025-01-05\"}"
```

```sh
curl -X POST http://localhost:8000/material-purchases ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer your-secret-key" ^
  -d "{\"project_id\":1,\"vendor_id\":1,\"material_description\":\"Tile\",\"unit_cost\":2.4,\"quantity\":180,\"delivery_cost\":45,\"purchase_date\":\"2025-01-11\"}"
```

```sh
curl "http://localhost:8000/projects?limit=10&offset=0"
```

```sh
curl "http://localhost:8000/tasks?limit=10&offset=0"
```

```sh
curl "http://localhost:8000/material-purchases?limit=10&offset=0"
```

```sh
curl "http://localhost:8000/laborers?limit=10&offset=0"
```

```sh
curl "http://localhost:8000/work-sessions?limit=10&offset=0"
```

## Next Steps

- Expand the API with read endpoints and pagination.
- Build exports and dashboards for materials, labor, task analytics, and estimates.
