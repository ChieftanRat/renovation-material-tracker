import json
import logging
import mimetypes
import os
import sqlite3
from datetime import date, datetime, time, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DB_PATH = os.environ.get("RENOVATION_DB", "renovation.db")
API_AUTH_SECRET = os.environ.get("RENOVATION_API_KEY")
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
MAX_PAGE_SIZE = int(os.environ.get("MAX_PAGE_SIZE", "100"))
SERVER_TIMEOUT = float(os.environ.get("SERVER_TIMEOUT", "10"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def parse_env_int(name, default):
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


BACKUP_RETENTION_DAYS = parse_env_int("BACKUP_RETENTION_DAYS", 30)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("renovation.api")
BASE_DIR = os.path.dirname(__file__)
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
SEED_PATH = os.path.join(BASE_DIR, "seed.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def read_json(handler):
    length_header = handler.headers.get("Content-Length")
    if length_header is None:
        return None, "Request body required.", 400
    try:
        length = int(length_header)
    except ValueError:
        return None, "Invalid Content-Length header.", 400
    if length <= 0:
        return None, "Request body required.", 400
    if length > MAX_CONTENT_LENGTH:
        return (
            None,
            f"Request body must be {MAX_CONTENT_LENGTH} bytes or less.",
            413,
        )
    try:
        payload = handler.rfile.read(length)
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            return None, "JSON body must be an object.", 400
        return data, None, 200
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Invalid JSON payload.", 400


def send_json(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    LOGGER.info("%s %s -> %s", handler.command, handler.path, status)


def require_auth(handler):
    if not API_AUTH_SECRET:
        LOGGER.error("RENOVATION_API_KEY is not configured.")
        send_json(handler, 403, {"error": "API key not configured."})
        return False
    api_key = handler.headers.get("X-API-Key")
    auth_header = handler.headers.get("Authorization", "")
    bearer = None
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
    if not api_key and not bearer:
        send_json(handler, 401, {"error": "Authentication required."})
        return False
    if api_key == API_AUTH_SECRET or bearer == API_AUTH_SECRET:
        return True
    send_json(handler, 403, {"error": "Invalid credentials."})
    return False


def require_mutation_auth(handler):
    return require_auth(handler)


def send_file(handler, status, content, content_type):
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def require_fields(data, fields):
    missing = []
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    if missing:
        return f"Missing required fields: {', '.join(missing)}."
    return None


def parse_date(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be YYYY-MM-DD.")


def parse_datetime(value, field):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be ISO datetime (YYYY-MM-DD HH:MM).")


def parse_time(value, field):
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be HH:MM or HH:MM:SS.")


def ensure_non_negative(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if number < 0:
        raise ValueError(f"{field} must be non-negative.")
    return number


def parse_pagination(query):
    params = parse_qs(query)

    def parse_int(name, default, minimum, maximum=None):
        if name not in params:
            return default
        values = params[name]
        if len(values) != 1 or not values[0]:
            raise ValueError(build_pagination_error(name, minimum, maximum))
        try:
            number = int(values[0])
        except ValueError:
            raise ValueError(build_pagination_error(name, minimum, maximum))
        if number < minimum:
            raise ValueError(build_pagination_error(name, minimum, maximum))
        if maximum is not None and number > maximum:
            raise ValueError(build_pagination_error(name, minimum, maximum))
        return number

    def build_pagination_error(name, minimum, maximum):
        if maximum is None:
            return f"{name} must be an integer of at least {minimum}."
        return f"{name} must be between {minimum} and {maximum}."

    page = parse_int("page", 1, 1)
    page_size = parse_int("page_size", 25, 1, MAX_PAGE_SIZE)
    limit = page_size
    offset = (page - 1) * page_size
    return page, page_size, limit, offset


def get_query_value(query, name):
    params = parse_qs(query, keep_blank_values=True)
    if name not in params:
        return None
    values = params[name]
    if len(values) != 1:
        raise ValueError(f"{name} must be provided once.")
    value = values[0].strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


def parse_optional_int(value, field):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer.")


def parse_optional_bool(value, field):
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes", "y"):
        return True
    if normalized in ("false", "0", "no", "n"):
        return False
    raise ValueError(f"{field} must be true or false.")


def build_filters(query, filters):
    clauses = []
    params = []
    for name, column, value_type in filters:
        raw_value = get_query_value(query, name)
        if raw_value is None:
            continue
        if value_type == "int":
            value = parse_optional_int(raw_value, name)
        elif value_type == "date":
            value = parse_date(raw_value, name).isoformat()
        elif value_type == "datetime":
            value = parse_datetime(raw_value, name).isoformat()
        else:
            raise ValueError(f"Unsupported filter type: {value_type}")
        if name.startswith("start_"):
            operator = ">="
        elif name.startswith("end_"):
            operator = "<="
        else:
            operator = "="
        clauses.append(f"{column} {operator} ?")
        params.append(value)
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def rows_to_dicts(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_latest_backup_timestamp():
    try:
        entries = [os.path.join(BACKUP_DIR, name) for name in os.listdir(BACKUP_DIR)]
    except FileNotFoundError:
        return None
    newest_mtime = None
    for path in entries:
        if not os.path.isfile(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if newest_mtime is None or mtime > newest_mtime:
            newest_mtime = mtime
    if newest_mtime is None:
        return None
    return datetime.utcfromtimestamp(newest_mtime).isoformat(timespec="seconds")


def get_latest_backup_mtime():
    try:
        entries = [os.path.join(BACKUP_DIR, name) for name in os.listdir(BACKUP_DIR)]
    except FileNotFoundError:
        return None
    newest_mtime = None
    for path in entries:
        if not os.path.isfile(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if newest_mtime is None or mtime > newest_mtime:
            newest_mtime = mtime
    if newest_mtime is None:
        return None
    return datetime.utcfromtimestamp(newest_mtime)


def prune_old_backups():
    if BACKUP_RETENTION_DAYS <= 0:
        return
    try:
        entries = [os.path.join(BACKUP_DIR, name) for name in os.listdir(BACKUP_DIR)]
    except FileNotFoundError:
        return
    cutoff = datetime.utcnow() - timedelta(days=BACKUP_RETENTION_DAYS)
    for path in entries:
        if not os.path.isfile(path):
            continue
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                os.remove(path)
        except OSError:
            LOGGER.warning("Failed to prune backup %s", path)


def write_backup(output_path):
    from backup_export import export_backup

    export_backup(
        db_path=DB_PATH,
        schema_path=SCHEMA_PATH,
        seed_path=SEED_PATH,
        output_path=output_path,
        include_seed=False,
    )


def maybe_backup_db(force=False):
    if BACKUP_RETENTION_DAYS <= 0:
        return
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        prune_old_backups()
        last_backup = get_latest_backup_mtime()
        if not force and last_backup:
            if datetime.utcnow() - last_backup < timedelta(days=1):
                return
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = Path(BACKUP_DIR) / f"backup_{timestamp}.sql"
        write_backup(output_path)
    except Exception:
        LOGGER.exception("Failed to write backup")
        if force:
            raise


def get_migration_count():
    with get_db() as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if not table:
            return 0
        return conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]


class RenovationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.serve_static_file("index.html")
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if parsed.path.startswith("/static/"):
            relative_path = parsed.path.removeprefix("/static/").lstrip("/")
            self.serve_static_file(relative_path)
            return
        if parsed.path == "/health":
            send_json(self, 200, {"status": "ok"})
            return
        if parsed.path == "/backups":
            payload = {
                "last_backup_at": get_latest_backup_timestamp(),
                "retention_days": BACKUP_RETENTION_DAYS,
            }
            send_json(self, 200, payload)
            return
        if parsed.path == "/migrations":
            send_json(self, 200, {"count": get_migration_count()})
            return
        if parsed.path.startswith("/projects/") and parsed.path.endswith("/summary"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) != 3 or parts[2] != "summary":
                send_json(self, 404, {"error": "Not found."})
                return
            try:
                project_id = int(parts[1])
            except ValueError:
                send_json(self, 400, {"error": "Invalid id."})
                return
            self.handle_project_summary(project_id)
            return
        routes = {
            "/projects": self.handle_get_projects,
            "/tasks": self.handle_get_tasks,
            "/vendors": self.handle_get_vendors,
            "/material-purchases": self.handle_get_material_purchases,
            "/laborers": self.handle_get_laborers,
            "/work-sessions": self.handle_get_work_sessions,
        }
        handler = routes.get(parsed.path)
        if not handler:
            send_json(self, 404, {"error": "Not found."})
            return
        try:
            page, page_size, limit, offset = parse_pagination(parsed.query)
            handler(page, page_size, limit, offset)
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception:
            LOGGER.exception("Unhandled error handling %s %s", self.command, self.path)
            send_json(self, 500, {"error": "Unexpected server error."})

    def serve_static_file(self, relative_path):
        static_root = os.path.join(os.path.dirname(__file__), "static")
        requested_path = os.path.normpath(os.path.join(static_root, relative_path))
        if os.path.commonpath([static_root, requested_path]) != static_root:
            send_json(self, 404, {"error": "Not found."})
            return
        if not os.path.isfile(requested_path):
            send_json(self, 404, {"error": "Not found."})
            return
        content_type, _ = mimetypes.guess_type(requested_path)
        if not content_type:
            content_type = "application/octet-stream"
        try:
            with open(requested_path, "rb") as handle:
                content = handle.read()
            send_file(self, 200, content, content_type)
            LOGGER.info("%s %s -> %s", self.command, self.path, 200)
        except OSError:
            LOGGER.exception("Failed to read static file %s", requested_path)
            send_json(self, 500, {"error": "Unexpected server error."})

    def do_POST(self):
        routes = {
            "/projects": self.handle_projects,
            "/tasks": self.handle_tasks,
            "/vendors": self.handle_vendors,
            "/material-purchases": self.handle_material_purchases,
            "/laborers": self.handle_laborers,
            "/work-sessions": self.handle_work_sessions,
        }
        if self.path == "/backups":
            if not require_mutation_auth(self):
                return
            try:
                maybe_backup_db(force=True)
                send_json(self, 200, {"status": "ok"})
            except Exception:
                send_json(self, 500, {"error": "Backup failed."})
            return
        archive_routes = {
            "/projects": "projects",
            "/tasks": "tasks",
            "/vendors": "vendors",
            "/material-purchases": "material_purchases",
            "/laborers": "laborers",
            "/work-sessions": "work_sessions",
        }
        if self.path.endswith("/archive") or self.path.endswith("/restore"):
            parts = self.path.strip("/").split("/")
            if len(parts) != 3:
                send_json(self, 404, {"error": "Not found."})
                return
            resource, raw_id, action = parts
            table = archive_routes.get(f"/{resource}")
            if not table or action not in ("archive", "restore"):
                send_json(self, 404, {"error": "Not found."})
                return
            try:
                record_id = int(raw_id)
            except ValueError:
                send_json(self, 400, {"error": "Invalid id."})
                return
            if not require_mutation_auth(self):
                return
            archived_at = None
            if action == "archive":
                archived_at = datetime.utcnow().isoformat(timespec="seconds")
            with get_db() as conn:
                cursor = conn.execute(
                    f"UPDATE {table} SET archived_at = ? WHERE id = ?",
                    (archived_at, record_id),
                )
            if cursor.rowcount == 0:
                send_json(self, 404, {"error": "Not found."})
                return
            maybe_backup_db()
            send_json(self, 200, {"id": record_id, "archived": action == "archive"})
            return
        handler = routes.get(self.path)
        if not handler:
            send_json(self, 404, {"error": "Not found."})
            return
        if not require_auth(self):
            return
        data, error, status = read_json(self)
        if error:
            send_json(self, status, {"error": error})
            return
        try:
            handler(data)
            maybe_backup_db()
        except sqlite3.IntegrityError as exc:
            send_json(self, 400, {"error": str(exc)})
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception:
            LOGGER.exception("Unhandled error handling %s %s", self.command, self.path)
            send_json(self, 500, {"error": "Unexpected server error."})

    def do_PUT(self):
        parsed = urlparse(self.path)
        resource, record_id = self.parse_resource_id(parsed.path)
        if not resource:
            return
        routes = {
            "projects": self.update_project,
            "tasks": self.update_task,
            "vendors": self.update_vendor,
            "material-purchases": self.update_material_purchase,
            "laborers": self.update_laborer,
            "work-sessions": self.update_work_session,
        }
        handler = routes.get(resource)
        if not handler:
            send_json(self, 404, {"error": "Not found."})
            return
        if not require_mutation_auth(self):
            return
        data, error, status = read_json(self)
        if error:
            send_json(self, status, {"error": error})
            return
        try:
            handler(record_id, data)
            maybe_backup_db()
        except sqlite3.IntegrityError as exc:
            send_json(self, 400, {"error": str(exc)})
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception:
            LOGGER.exception("Unhandled error handling %s %s", self.command, self.path)
            send_json(self, 500, {"error": "Unexpected server error."})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        resource, record_id = self.parse_resource_id(parsed.path)
        if not resource:
            return
        routes = {
            "projects": self.delete_project,
            "tasks": self.delete_task,
            "vendors": self.delete_vendor,
            "material-purchases": self.delete_material_purchase,
            "laborers": self.delete_laborer,
            "work-sessions": self.delete_work_session,
        }
        handler = routes.get(resource)
        if not handler:
            send_json(self, 404, {"error": "Not found."})
            return
        if not require_mutation_auth(self):
            return
        try:
            handler(record_id)
            maybe_backup_db()
        except sqlite3.IntegrityError as exc:
            send_json(self, 400, {"error": str(exc)})
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception:
            LOGGER.exception("Unhandled error handling %s %s", self.command, self.path)
            send_json(self, 500, {"error": "Unexpected server error."})

    def handle_get_projects(self, page, page_size, limit, offset):
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            cursor = conn.execute(
                """
                SELECT id, name, description, start_date, end_date
                FROM projects
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            items = rows_to_dicts(cursor)
        total_pages = (total + page_size - 1) // page_size if total else 0
        send_json(
            self,
            200,
            {
                "data": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    def handle_get_tasks(self, page, page_size, limit, offset):
        query = urlparse(self.path).query
        include_archived = parse_optional_bool(
            get_query_value(query, "include_archived"),
            "include_archived",
        )
        filters = [
            ("project_id", "t.project_id", "int"),
            ("start_date", "date(t.start_datetime)", "date"),
            ("end_date", "date(t.end_datetime)", "date"),
        ]
        where_sql, params = build_filters(query, filters)
        if not include_archived:
            if where_sql:
                where_sql += " AND t.archived_at IS NULL"
            else:
                where_sql = " WHERE t.archived_at IS NULL"
        with get_db() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM tasks t{where_sql}", params).fetchone()[
                0
            ]
            cursor = conn.execute(
                f"""
                SELECT id, project_id, name, start_datetime, end_datetime, archived_at
                FROM tasks t
                {where_sql}
                ORDER BY t.id
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            )
            items = rows_to_dicts(cursor)
        total_pages = (total + page_size - 1) // page_size if total else 0
        send_json(
            self,
            200,
            {
                "data": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    def handle_get_vendors(self, page, page_size, limit, offset):
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
            cursor = conn.execute(
                """
                SELECT id, name
                FROM vendors
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            items = rows_to_dicts(cursor)
        total_pages = (total + page_size - 1) // page_size if total else 0
        send_json(
            self,
            200,
            {
                "data": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    def handle_get_material_purchases(self, page, page_size, limit, offset):
        query = urlparse(self.path).query
        include_archived = parse_optional_bool(
            get_query_value(query, "include_archived"),
            "include_archived",
        )
        project_id = get_query_value(query, "project_id")
        if project_id is None:
            raise ValueError("project_id is required.")
        filters = [
            ("project_id", "mp.project_id", "int"),
            ("task_id", "mp.task_id", "int"),
            ("vendor_id", "mp.vendor_id", "int"),
            ("start_date", "mp.purchase_date", "date"),
            ("end_date", "mp.purchase_date", "date"),
        ]
        where_sql, params = build_filters(query, filters)
        if not include_archived:
            if where_sql:
                where_sql += " AND mp.archived_at IS NULL"
            else:
                where_sql = " WHERE mp.archived_at IS NULL"
        with get_db() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM material_purchases mp{where_sql}",
                params,
            ).fetchone()[0]
            cursor = conn.execute(
                f"""
                SELECT
                  id,
                  project_id,
                  task_id,
                  vendor_id,
                  material_description,
                  unit_cost,
                  quantity,
                  total_material_cost,
                  delivery_cost,
                  purchase_date,
                  archived_at
                FROM material_purchases mp
                {where_sql}
                ORDER BY mp.id
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            )
            items = rows_to_dicts(cursor)
        total_pages = (total + page_size - 1) // page_size if total else 0
        send_json(
            self,
            200,
            {
                "data": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    def handle_get_laborers(self, page, page_size, limit, offset):
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM laborers").fetchone()[0]
            cursor = conn.execute(
                """
                SELECT id, name, hourly_rate, daily_rate
                FROM laborers
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            items = rows_to_dicts(cursor)
        total_pages = (total + page_size - 1) // page_size if total else 0
        send_json(
            self,
            200,
            {
                "data": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    def handle_get_work_sessions(self, page, page_size, limit, offset):
        query = urlparse(self.path).query
        include_archived = parse_optional_bool(
            get_query_value(query, "include_archived"),
            "include_archived",
        )
        project_id = get_query_value(query, "project_id")
        if project_id is None:
            raise ValueError("project_id is required.")
        self.handle_work_sessions_list(query, page, page_size, include_archived)

    def handle_project_summary(self, project_id):
        with get_db() as conn:
            exists = conn.execute(
                "SELECT 1 FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            if not exists:
                send_json(self, 404, {"error": "Not found."})
                return
            row = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*)
                   FROM tasks
                   WHERE project_id = ? AND archived_at IS NULL) AS tasks_count,
                  (SELECT COUNT(*)
                   FROM material_purchases
                   WHERE project_id = ? AND archived_at IS NULL) AS purchases_count,
                  (SELECT COALESCE(SUM(total_material_cost + delivery_cost), 0)
                   FROM material_purchases
                   WHERE project_id = ? AND archived_at IS NULL) AS material_total,
                  (SELECT COUNT(*)
                   FROM work_sessions
                   WHERE project_id = ? AND archived_at IS NULL) AS sessions_count,
                  (SELECT COALESCE(SUM(
                    CASE
                      WHEN l.hourly_rate IS NOT NULL THEN
                        (julianday('2000-01-01 ' || e.clock_out_time) -
                         julianday('2000-01-01 ' || e.clock_in_time)) * 24 * l.hourly_rate
                      WHEN l.daily_rate IS NOT NULL THEN l.daily_rate
                      ELSE 0
                    END
                  ), 0)
                   FROM work_sessions ws
                   JOIN work_session_entries e ON e.work_session_id = ws.id
                   JOIN laborers l ON l.id = e.laborer_id
                   WHERE ws.project_id = ? AND ws.archived_at IS NULL) AS labor_total,
                  (SELECT CASE
                    WHEN EXISTS (
                      SELECT 1
                      FROM work_sessions ws
                      JOIN work_session_entries e ON e.work_session_id = ws.id
                      JOIN laborers l ON l.id = e.laborer_id
                      WHERE ws.project_id = ?
                        AND ws.archived_at IS NULL
                        AND (l.hourly_rate IS NOT NULL OR l.daily_rate IS NOT NULL)
                    ) THEN 1
                    ELSE 0
                   END) AS has_labor_rates
                """,
                (
                    project_id,
                    project_id,
                    project_id,
                    project_id,
                    project_id,
                    project_id,
                ),
            ).fetchone()
        material_total = row["material_total"] or 0
        labor_total = row["labor_total"] or 0
        send_json(
            self,
            200,
            {
                "project_id": project_id,
                "material_total": material_total,
                "labor_total": labor_total,
                "combined_total": material_total + labor_total,
                "tasks_count": row["tasks_count"] or 0,
                "purchases_count": row["purchases_count"] or 0,
                "sessions_count": row["sessions_count"] or 0,
                "has_labor_rates": bool(row["has_labor_rates"]),
            },
        )

    def handle_projects(self, data):
        error = require_fields(data, ["name"])
        if error:
            raise ValueError(error)
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date:
            start_value = parse_date(start_date, "start_date")
        else:
            start_value = None
        if end_date:
            end_value = parse_date(end_date, "end_date")
        else:
            end_value = None
        if start_value and end_value and end_value < start_value:
            raise ValueError("end_date must be on or after start_date.")
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (name, description, start_date, end_date)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data["name"].strip(),
                    data.get("description"),
                    start_date,
                    end_date,
                ),
            )
        send_json(self, 201, {"id": cursor.lastrowid})

    def handle_tasks(self, data):
        error = require_fields(data, ["project_id", "name", "start_datetime", "end_datetime"])
        if error:
            raise ValueError(error)
        start_dt = parse_datetime(data["start_datetime"], "start_datetime")
        end_dt = parse_datetime(data["end_datetime"], "end_datetime")
        if end_dt <= start_dt:
            raise ValueError("end_datetime must be after start_datetime.")
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (project_id, name, start_datetime, end_datetime)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data["project_id"],
                    data["name"].strip(),
                    data["start_datetime"],
                    data["end_datetime"],
                ),
            )
        send_json(self, 201, {"id": cursor.lastrowid})

    def handle_vendors(self, data):
        error = require_fields(data, ["name"])
        if error:
            raise ValueError(error)
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO vendors (name) VALUES (?)",
                (data["name"].strip(),),
            )
        send_json(self, 201, {"id": cursor.lastrowid})

    def handle_material_purchases(self, data):
        error = require_fields(
            data,
            [
                "project_id",
                "vendor_id",
                "material_description",
                "unit_cost",
                "quantity",
                "purchase_date",
            ],
        )
        if error:
            raise ValueError(error)
        unit_cost = ensure_non_negative(data["unit_cost"], "unit_cost")
        quantity = ensure_non_negative(data["quantity"], "quantity")
        delivery_cost = ensure_non_negative(data.get("delivery_cost", 0), "delivery_cost")
        purchase_date = parse_date(data["purchase_date"], "purchase_date")
        if purchase_date > date.today():
            raise ValueError("purchase_date cannot be in the future.")
        total_material_cost = unit_cost * quantity
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO material_purchases (
                  project_id,
                  task_id,
                  vendor_id,
                  material_description,
                  unit_cost,
                  quantity,
                  total_material_cost,
                  delivery_cost,
                  purchase_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["project_id"],
                    data.get("task_id"),
                    data["vendor_id"],
                    data["material_description"].strip(),
                    unit_cost,
                    quantity,
                    total_material_cost,
                    delivery_cost,
                    data["purchase_date"],
                ),
            )
        send_json(self, 201, {"id": cursor.lastrowid})

    def handle_laborers(self, data):
        error = require_fields(data, ["name"])
        if error:
            raise ValueError(error)
        hourly_rate = data.get("hourly_rate")
        daily_rate = data.get("daily_rate")
        if hourly_rate is None and daily_rate is None:
            raise ValueError("Provide hourly_rate or daily_rate.")
        hourly_value = None
        daily_value = None
        if hourly_rate is not None:
            hourly_value = ensure_non_negative(hourly_rate, "hourly_rate")
        if daily_rate is not None:
            daily_value = ensure_non_negative(daily_rate, "daily_rate")
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO laborers (name, hourly_rate, daily_rate)
                VALUES (?, ?, ?)
                """,
                (data["name"].strip(), hourly_value, daily_value),
            )
        send_json(self, 201, {"id": cursor.lastrowid})

    def handle_work_sessions(self, data):
        error = require_fields(
            data,
            [
                "project_id",
                "task_id",
                "work_date",
                "entries",
            ],
        )
        if error:
            raise ValueError(error)
        work_date = parse_date(data["work_date"], "work_date")
        entries = data["entries"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("entries must be a non-empty list.")
        cleaned_entries = []
        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise ValueError("entries must contain objects.")
            for field in ("laborer_id", "clock_in_time", "clock_out_time"):
                if entry.get(field) in (None, ""):
                    raise ValueError(f"Entry {idx}: {field} is required.")
            clock_in = parse_time(entry["clock_in_time"], "clock_in_time")
            clock_out = parse_time(entry["clock_out_time"], "clock_out_time")
            start_dt = datetime.combine(work_date, clock_in)
            end_dt = datetime.combine(work_date, clock_out)
            if end_dt <= start_dt:
                raise ValueError("clock_out_time must be after clock_in_time.")
            cleaned_entries.append(
                (
                    entry["laborer_id"],
                    entry["clock_in_time"],
                    entry["clock_out_time"],
                )
            )
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO work_sessions (project_id, task_id, work_date)
                VALUES (?, ?, ?)
                """,
                (
                    data["project_id"],
                    data["task_id"],
                    data["work_date"],
                ),
            )
            session_id = cursor.lastrowid
            conn.executemany(
                """
                INSERT INTO work_session_entries (
                  work_session_id,
                  laborer_id,
                  clock_in_time,
                  clock_out_time
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (session_id, laborer_id, clock_in_time, clock_out_time)
                    for laborer_id, clock_in_time, clock_out_time in cleaned_entries
                ],
            )
        send_json(self, 201, {"id": session_id})

    def update_project(self, record_id, data):
        error = require_fields(data, ["name"])
        if error:
            raise ValueError(error)
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date:
            start_value = parse_date(start_date, "start_date")
        else:
            start_value = None
        if end_date:
            end_value = parse_date(end_date, "end_date")
        else:
            end_value = None
        if start_value and end_value and end_value < start_value:
            raise ValueError("end_date must be on or after start_date.")
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE projects
                SET name = ?, description = ?, start_date = ?, end_date = ?
                WHERE id = ?
                """,
                (
                    data["name"].strip(),
                    data.get("description"),
                    start_date,
                    end_date,
                    record_id,
                ),
            )
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id})

    def update_task(self, record_id, data):
        error = require_fields(data, ["project_id", "name", "start_datetime", "end_datetime"])
        if error:
            raise ValueError(error)
        start_dt = parse_datetime(data["start_datetime"], "start_datetime")
        end_dt = parse_datetime(data["end_datetime"], "end_datetime")
        if end_dt <= start_dt:
            raise ValueError("end_datetime must be after start_datetime.")
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET project_id = ?, name = ?, start_datetime = ?, end_datetime = ?
                WHERE id = ?
                """,
                (
                    data["project_id"],
                    data["name"].strip(),
                    data["start_datetime"],
                    data["end_datetime"],
                    record_id,
                ),
            )
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id})

    def update_material_purchase(self, record_id, data):
        error = require_fields(
            data,
            [
                "project_id",
                "task_id",
                "vendor_id",
                "material_description",
                "unit_cost",
                "quantity",
                "purchase_date",
            ],
        )
        if error:
            raise ValueError(error)
        unit_cost = ensure_non_negative(data["unit_cost"], "unit_cost")
        quantity = ensure_non_negative(data["quantity"], "quantity")
        delivery_cost = ensure_non_negative(data.get("delivery_cost", 0), "delivery_cost")
        purchase_date = parse_date(data["purchase_date"], "purchase_date")
        if purchase_date > date.today():
            raise ValueError("purchase_date cannot be in the future.")
        total_material_cost = unit_cost * quantity
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE material_purchases
                SET project_id = ?,
                    task_id = ?,
                    vendor_id = ?,
                    material_description = ?,
                    unit_cost = ?,
                    quantity = ?,
                    total_material_cost = ?,
                    delivery_cost = ?,
                    purchase_date = ?
                WHERE id = ?
                """,
                (
                    data["project_id"],
                    data["task_id"],
                    data["vendor_id"],
                    data["material_description"].strip(),
                    unit_cost,
                    quantity,
                    total_material_cost,
                    delivery_cost,
                    data["purchase_date"],
                    record_id,
                ),
            )
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id})

    def update_work_session(self, record_id, data):
        error = require_fields(data, ["project_id", "task_id", "work_date", "entries"])
        if error:
            raise ValueError(error)
        work_date = parse_date(data["work_date"], "work_date")
        entries = data["entries"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("entries must be a non-empty list.")
        cleaned_entries = []
        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise ValueError("entries must contain objects.")
            for field in ("laborer_id", "clock_in_time", "clock_out_time"):
                if entry.get(field) in (None, ""):
                    raise ValueError(f"Entry {idx}: {field} is required.")
            clock_in = parse_time(entry["clock_in_time"], "clock_in_time")
            clock_out = parse_time(entry["clock_out_time"], "clock_out_time")
            start_dt = datetime.combine(work_date, clock_in)
            end_dt = datetime.combine(work_date, clock_out)
            if end_dt <= start_dt:
                raise ValueError("clock_out_time must be after clock_in_time.")
            cleaned_entries.append(
                (
                    entry["laborer_id"],
                    entry["clock_in_time"],
                    entry["clock_out_time"],
                )
            )
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE work_sessions
                SET project_id = ?, task_id = ?, work_date = ?
                WHERE id = ?
                """,
                (data["project_id"], data["task_id"], data["work_date"], record_id),
            )
            if cursor.rowcount == 0:
                send_json(self, 404, {"error": "Not found."})
                return
            conn.execute(
                "DELETE FROM work_session_entries WHERE work_session_id = ?",
                (record_id,),
            )
            conn.executemany(
                """
                INSERT INTO work_session_entries (
                  work_session_id,
                  laborer_id,
                  clock_in_time,
                  clock_out_time
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (record_id, laborer_id, clock_in_time, clock_out_time)
                    for laborer_id, clock_in_time, clock_out_time in cleaned_entries
                ],
            )
        send_json(self, 200, {"id": record_id})

    def update_vendor(self, record_id, data):
        error = require_fields(data, ["name"])
        if error:
            raise ValueError(error)
        with get_db() as conn:
            cursor = conn.execute(
                "UPDATE vendors SET name = ? WHERE id = ?",
                (data["name"].strip(), record_id),
            )
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id})

    def update_laborer(self, record_id, data):
        error = require_fields(data, ["name"])
        if error:
            raise ValueError(error)
        hourly_rate = data.get("hourly_rate")
        daily_rate = data.get("daily_rate")
        if hourly_rate is None and daily_rate is None:
            raise ValueError("Provide hourly_rate or daily_rate.")
        hourly_value = None
        daily_value = None
        if hourly_rate is not None:
            hourly_value = ensure_non_negative(hourly_rate, "hourly_rate")
        if daily_rate is not None:
            daily_value = ensure_non_negative(daily_rate, "daily_rate")
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE laborers
                SET name = ?, hourly_rate = ?, daily_rate = ?
                WHERE id = ?
                """,
                (data["name"].strip(), hourly_value, daily_value, record_id),
            )
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id})

    def delete_project(self, record_id):
        archived_at = datetime.utcnow().isoformat(timespec="seconds")
        with get_db() as conn:
            has_tasks = conn.execute(
                "SELECT 1 FROM tasks WHERE project_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            has_purchases = conn.execute(
                "SELECT 1 FROM material_purchases WHERE project_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            has_sessions = conn.execute(
                "SELECT 1 FROM work_sessions WHERE project_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            if has_tasks or has_purchases or has_sessions:
                cursor = conn.execute(
                    "UPDATE projects SET archived_at = ? WHERE id = ?",
                    (archived_at, record_id),
                )
                if cursor.rowcount == 0:
                    send_json(self, 404, {"error": "Not found."})
                    return
                send_json(self, 200, {"id": record_id, "archived": True})
                return
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id, "deleted": True})

    def delete_task(self, record_id):
        archived_at = datetime.utcnow().isoformat(timespec="seconds")
        with get_db() as conn:
            has_purchases = conn.execute(
                "SELECT 1 FROM material_purchases WHERE task_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            has_sessions = conn.execute(
                "SELECT 1 FROM work_sessions WHERE task_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            if has_purchases or has_sessions:
                cursor = conn.execute(
                    "UPDATE tasks SET archived_at = ? WHERE id = ?",
                    (archived_at, record_id),
                )
                if cursor.rowcount == 0:
                    send_json(self, 404, {"error": "Not found."})
                    return
                send_json(self, 200, {"id": record_id, "archived": True})
                return
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id, "deleted": True})

    def delete_vendor(self, record_id):
        archived_at = datetime.utcnow().isoformat(timespec="seconds")
        with get_db() as conn:
            has_purchases = conn.execute(
                "SELECT 1 FROM material_purchases WHERE vendor_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            if has_purchases:
                cursor = conn.execute(
                    "UPDATE vendors SET archived_at = ? WHERE id = ?",
                    (archived_at, record_id),
                )
                if cursor.rowcount == 0:
                    send_json(self, 404, {"error": "Not found."})
                    return
                send_json(self, 200, {"id": record_id, "archived": True})
                return
            cursor = conn.execute("DELETE FROM vendors WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id, "deleted": True})

    def delete_material_purchase(self, record_id):
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM material_purchases WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id, "deleted": True})

    def delete_laborer(self, record_id):
        archived_at = datetime.utcnow().isoformat(timespec="seconds")
        with get_db() as conn:
            has_entries = conn.execute(
                "SELECT 1 FROM work_session_entries WHERE laborer_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            if has_entries:
                cursor = conn.execute(
                    "UPDATE laborers SET archived_at = ? WHERE id = ?",
                    (archived_at, record_id),
                )
                if cursor.rowcount == 0:
                    send_json(self, 404, {"error": "Not found."})
                    return
                send_json(self, 200, {"id": record_id, "archived": True})
                return
            cursor = conn.execute("DELETE FROM laborers WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id, "deleted": True})

    def delete_work_session(self, record_id):
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM work_sessions WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        send_json(self, 200, {"id": record_id, "deleted": True})

    def handle_work_sessions_list(self, query, page, page_size, include_archived):
        filters = [
            ("project_id", "ws.project_id", "int"),
            ("task_id", "ws.task_id", "int"),
            ("start_date", "ws.work_date", "date"),
            ("end_date", "ws.work_date", "date"),
        ]
        laborer_id = get_query_value(query, "laborer_id")
        if laborer_id is not None:
            laborer_id = parse_optional_int(laborer_id, "laborer_id")
        where_sql, params = build_filters(query, filters)
        if not include_archived:
            if where_sql:
                where_sql += " AND ws.archived_at IS NULL"
            else:
                where_sql = " WHERE ws.archived_at IS NULL"
        if laborer_id is not None:
            clause = "EXISTS (SELECT 1 FROM work_session_entries wse WHERE wse.work_session_id = ws.id AND wse.laborer_id = ?)"
            where_sql = f"{where_sql} AND {clause}" if where_sql else f" WHERE {clause}"
            params.append(laborer_id)
        offset = (page - 1) * page_size
        with get_db() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM work_sessions ws{where_sql}",
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                WITH paged_sessions AS (
                    SELECT ws.id, ws.project_id, ws.task_id, ws.work_date, ws.archived_at
                    FROM work_sessions ws
                    {where_sql}
                    ORDER BY ws.id
                    LIMIT ? OFFSET ?
                )
                SELECT
                    ps.id,
                    ps.project_id,
                    ps.task_id,
                    ps.work_date,
                    ps.archived_at,
                    wse.id AS entry_id,
                    wse.laborer_id,
                    wse.clock_in_time,
                    wse.clock_out_time
                FROM paged_sessions ps
                LEFT JOIN work_session_entries wse ON wse.work_session_id = ps.id
                ORDER BY ps.id, wse.id
                """,
                params + [page_size, offset],
            ).fetchall()
        sessions = {}
        ordered_ids = []
        for row in rows:
            session_id = row["id"]
            if session_id not in sessions:
                sessions[session_id] = {
                    "id": session_id,
                    "project_id": row["project_id"],
                    "task_id": row["task_id"],
                    "work_date": row["work_date"],
                    "archived_at": row["archived_at"],
                    "entries": [],
                }
                ordered_ids.append(session_id)
            if row["entry_id"] is not None:
                sessions[session_id]["entries"].append(
                    {
                        "id": row["entry_id"],
                        "laborer_id": row["laborer_id"],
                        "clock_in_time": row["clock_in_time"],
                        "clock_out_time": row["clock_out_time"],
                    }
                )
        payload_rows = [sessions[session_id] for session_id in ordered_ids]
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        send_json(
            self,
            200,
            {
                "data": payload_rows,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    def parse_resource_id(self, path):
        parts = path.strip("/").split("/")
        if len(parts) != 2:
            send_json(self, 404, {"error": "Not found."})
            return None, None
        resource, raw_id = parts
        if not resource:
            send_json(self, 404, {"error": "Not found."})
            return None, None
        try:
            record_id = int(raw_id)
        except ValueError:
            send_json(self, 400, {"error": "Invalid id."})
            return None, None
        return resource, record_id

    def log_message(self, format, *args):
        LOGGER.info(
            "%s - - [%s] %s",
            self.client_address[0],
            self.log_date_time_string(),
            format % args,
        )


def run():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), RenovationHandler)
    server.timeout = SERVER_TIMEOUT
    server.socket.settimeout(SERVER_TIMEOUT)
    print(f"API listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
