import json
import os
import sqlite3
from datetime import date, datetime, time, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("RENOVATION_DB", os.path.join(BASE_DIR, "renovation.db"))
STATIC_DIR = os.path.join(BASE_DIR, "static")
BACKUP_DIR = os.environ.get("RENOVATION_BACKUPS", os.path.join(BASE_DIR, "backups"))
BACKUP_INTERVAL = timedelta(minutes=10)
BACKUP_RETENTION_DAYS = int(os.environ.get("RENOVATION_BACKUP_RETENTION_DAYS", "30"))
_LAST_BACKUP_AT = None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def read_json(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length <= 0:
        return None, "Request body required."
    try:
        payload = handler.rfile.read(length)
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            return None, "JSON body must be an object."
        return data, None
    except json.JSONDecodeError:
        return None, "Invalid JSON payload."


def send_json(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


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


def parse_positive_int(value, field, default, minimum=1, maximum=200):
    if value is None:
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer.")
    if number < minimum or number > maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}.")
    return number


def parse_optional_int(value, field):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be an integer.")


def parse_optional_date(value, field):
    if value is None:
        return None
    parse_date(value, field)
    return value


def parse_bool(value):
    if value is None:
        return False
    return str(value).lower() in ("1", "true", "yes", "on")


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def get_query_value(query, key):
    return query.get(key, [None])[0]


def build_filters(query, filters):
    clauses = []
    params = []
    for param, column, value_type in filters:
        raw_value = get_query_value(query, param)
        if value_type == "int":
            value = parse_optional_int(raw_value, param)
        elif value_type == "date":
            value = parse_optional_date(raw_value, param)
        else:
            value = raw_value
        if value is None:
            continue
        if value_type == "date":
            if param == "start_date":
                clauses.append(f"{column} >= ?")
            elif param == "end_date":
                clauses.append(f"{column} <= ?")
            else:
                clauses.append(f"{column} = ?")
        else:
            clauses.append(f"{column} = ?")
        params.append(value)
    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params


def maybe_backup_db(force=False):
    global _LAST_BACKUP_AT
    now = datetime.utcnow()
    if not force and _LAST_BACKUP_AT and now - _LAST_BACKUP_AT < BACKUP_INTERVAL:
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
    with sqlite3.connect(DB_PATH) as source:
        with sqlite3.connect(backup_path) as dest:
            source.backup(dest)
    _LAST_BACKUP_AT = now
    purge_old_backups(now)


def purge_old_backups(now):
    cutoff = now - timedelta(days=BACKUP_RETENTION_DAYS)
    for name in os.listdir(BACKUP_DIR):
        if not name.startswith("backup_") or not name.endswith(".db"):
            continue
        path = os.path.join(BACKUP_DIR, name)
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
        except OSError:
            continue
        if mtime < cutoff:
            try:
                os.remove(path)
            except OSError:
                continue


class RenovationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as file_handle:
                    content = file_handle.read()
                send_file(self, 200, content, "text/html; charset=utf-8")
                return
        if parsed.path == "/health":
            send_json(self, 200, {"status": "ok"})
            return
        if parsed.path == "/backups":
            send_json(
                self,
                200,
                {
                    "directory": BACKUP_DIR,
                    "retention_days": BACKUP_RETENTION_DAYS,
                    "last_backup_at": _LAST_BACKUP_AT.isoformat(timespec="seconds")
                    if _LAST_BACKUP_AT
                    else None,
                },
            )
            return
        if parsed.path.startswith("/static/"):
            relative = os.path.normpath(parsed.path.lstrip("/"))
            if ".." in relative or relative.startswith("\\") or relative.startswith("/"):
                send_json(self, 400, {"error": "Invalid path."})
                return
            file_path = os.path.join(BASE_DIR, relative)
            if not file_path.startswith(STATIC_DIR):
                send_json(self, 404, {"error": "Not found."})
                return
            if not os.path.isfile(file_path):
                send_json(self, 404, {"error": "Not found."})
                return
            ext = os.path.splitext(file_path)[1].lower()
            content_type = {
                ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".svg": "image/svg+xml",
            }.get(ext, "application/octet-stream")
            with open(file_path, "rb") as file_handle:
                content = file_handle.read()
            send_file(self, 200, content, content_type)
            return
        list_routes = {
            "/projects": {
                "table": "projects",
                "order_by": "id",
                "archivable": True,
                "filters": [
                    ("start_date", "start_date", "date"),
                    ("end_date", "end_date", "date"),
                ],
            },
            "/tasks": {
                "table": "tasks",
                "order_by": "id",
                "archivable": True,
                "filters": [
                    ("project_id", "project_id", "int"),
                    ("start_date", "date(start_datetime)", "date"),
                    ("end_date", "date(start_datetime)", "date"),
                ],
            },
            "/vendors": {
                "table": "vendors",
                "order_by": "id",
                "archivable": True,
                "filters": [],
            },
            "/material-purchases": {
                "table": "material_purchases",
                "order_by": "id",
                "archivable": True,
                "filters": [
                    ("project_id", "project_id", "int"),
                    ("vendor_id", "vendor_id", "int"),
                    ("task_id", "task_id", "int"),
                    ("start_date", "purchase_date", "date"),
                    ("end_date", "purchase_date", "date"),
                ],
            },
            "/laborers": {
                "table": "laborers",
                "order_by": "id",
                "archivable": True,
                "filters": [],
            },
            "/work-sessions": {
                "table": "work_sessions",
                "order_by": "id",
                "archivable": True,
                "filters": [
                    ("project_id", "project_id", "int"),
                    ("laborer_id", "laborer_id", "int"),
                    ("task_id", "task_id", "int"),
                    ("start_date", "work_date", "date"),
                    ("end_date", "work_date", "date"),
                ],
            },
        }
        route = list_routes.get(parsed.path)
        if not route:
            send_json(self, 404, {"error": "Not found."})
            return
        try:
            query = parse_qs(parsed.query)
            page = parse_positive_int(query.get("page", [None])[0], "page", 1, minimum=1)
            page_size = parse_positive_int(
                query.get("page_size", [None])[0], "page_size", 25, minimum=1, maximum=200
            )
            if parsed.path == "/work-sessions":
                include_archived = parse_bool(query.get("include_archived", [None])[0])
                self.handle_work_sessions_list(query, page, page_size, include_archived)
                return
            table = route["table"]
            order_by = route["order_by"]
            include_archived = parse_bool(query.get("include_archived", [None])[0])
            offset = (page - 1) * page_size
            with get_db() as conn:
                where_sql, params = build_filters(query, route["filters"])
                if route.get("archivable") and not include_archived:
                    if where_sql:
                        where_sql += " AND archived_at IS NULL"
                    else:
                        where_sql = " WHERE archived_at IS NULL"
                total = conn.execute(
                    f"SELECT COUNT(*) FROM {table}{where_sql}",
                    params,
                ).fetchone()[0]
                rows = conn.execute(
                    f"SELECT * FROM {table}{where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?",
                    params + [page_size, offset],
                ).fetchall()
            total_pages = (total + page_size - 1) // page_size if page_size else 0
            send_json(
                self,
                200,
                {
                    "data": rows_to_dicts(rows),
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
            )
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})

    def do_PUT(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2:
            send_json(self, 404, {"error": "Not found."})
            return
        resource, raw_id = parts
        try:
            record_id = int(raw_id)
        except ValueError:
            send_json(self, 400, {"error": "Invalid id."})
            return
        routes = {
            "projects": self.update_project,
            "tasks": self.update_task,
            "material-purchases": self.update_material_purchase,
            "work-sessions": self.update_work_session,
            "vendors": self.update_vendor,
            "laborers": self.update_laborer,
        }
        handler = routes.get(resource)
        if not handler:
            send_json(self, 404, {"error": "Not found."})
            return
        data, error = read_json(self)
        if error:
            send_json(self, 400, {"error": error})
            return
        try:
            handler(record_id, data)
            maybe_backup_db()
        except sqlite3.IntegrityError as exc:
            send_json(self, 400, {"error": str(exc)})
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception:
            send_json(self, 500, {"error": "Unexpected server error."})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2:
            send_json(self, 404, {"error": "Not found."})
            return
        resource, raw_id = parts
        try:
            record_id = int(raw_id)
        except ValueError:
            send_json(self, 400, {"error": "Invalid id."})
            return
        tables = {
            "projects": "projects",
            "tasks": "tasks",
            "material-purchases": "material_purchases",
            "work-sessions": "work_sessions",
            "vendors": "vendors",
            "laborers": "laborers",
        }
        table = tables.get(resource)
        if not table:
            send_json(self, 404, {"error": "Not found."})
            return
        with get_db() as conn:
            cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            send_json(self, 404, {"error": "Not found."})
            return
        maybe_backup_db()
        send_json(self, 200, {"id": record_id})

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
        data, error = read_json(self)
        if error:
            send_json(self, 400, {"error": error})
            return
        try:
            handler(data)
            maybe_backup_db()
        except sqlite3.IntegrityError as exc:
            send_json(self, 400, {"error": str(exc)})
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception:
            send_json(self, 500, {"error": "Unexpected server error."})

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
        return


def run():
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), RenovationHandler)
    print(f"API listening on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
