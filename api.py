import json
import logging
import mimetypes
import os
import sqlite3
from datetime import date, datetime, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


DB_PATH = os.environ.get("RENOVATION_DB", "renovation.db")
API_AUTH_SECRET = os.environ.get("RENOVATION_API_KEY")
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
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

    def parse_int(name, default, minimum):
        if name not in params:
            return default
        values = params[name]
        if len(values) != 1 or not values[0]:
            raise ValueError(f"{name} must be an integer of at least {minimum}.")
        try:
            number = int(values[0])
        except ValueError:
            raise ValueError(f"{name} must be an integer of at least {minimum}.")
        if number < minimum:
            raise ValueError(f"{name} must be an integer of at least {minimum}.")
        return number

    page = parse_int("page", 1, 1)
    page_size = parse_int("page_size", 25, 1)
    limit = page_size
    offset = (page - 1) * page_size
    return page, page_size, limit, offset


def rows_to_dicts(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_latest_backup_timestamp():
    backup_dir = os.path.join(os.path.dirname(__file__), "backups")
    try:
        entries = [os.path.join(backup_dir, name) for name in os.listdir(backup_dir)]
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
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            cursor = conn.execute(
                """
                SELECT id, project_id, name, start_datetime, end_datetime
                FROM tasks
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
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM material_purchases").fetchone()[0]
            cursor = conn.execute(
                """
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
                  purchase_date
                FROM material_purchases
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
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM work_sessions").fetchone()[0]
            cursor = conn.execute(
                """
                SELECT
                  id,
                  laborer_id,
                  project_id,
                  task_id,
                  work_date,
                  clock_in_time,
                  clock_out_time
                FROM work_sessions
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
                SELECT ws.id, ws.project_id, ws.task_id, ws.work_date
                FROM work_sessions ws
                {where_sql}
                ORDER BY ws.id
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()
            session_ids = [row["id"] for row in rows]
            entries = []
            if session_ids:
                placeholders = ",".join("?" for _ in session_ids)
                entries = conn.execute(
                    f"""
                    SELECT work_session_id, laborer_id, clock_in_time, clock_out_time
                    FROM work_session_entries
                    WHERE work_session_id IN ({placeholders})
                    ORDER BY id
                    """,
                    session_ids,
                ).fetchall()
        entries_by_session = {}
        for entry in entries:
            entries_by_session.setdefault(entry["work_session_id"], []).append(dict(entry))
        payload_rows = []
        for row in rows:
            data = dict(row)
            data["entries"] = entries_by_session.get(row["id"], [])
            payload_rows.append(data)
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
