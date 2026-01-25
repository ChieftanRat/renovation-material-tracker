import json
import os
import sqlite3
from datetime import date, datetime, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DB_PATH = os.environ.get("RENOVATION_DB", "renovation.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
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


class RenovationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            send_json(self, 200, {"status": "ok"})
            return
        send_json(self, 404, {"error": "Not found."})

    def do_POST(self):
        routes = {
            "/projects": self.handle_projects,
            "/tasks": self.handle_tasks,
            "/vendors": self.handle_vendors,
            "/material-purchases": self.handle_material_purchases,
            "/laborers": self.handle_laborers,
            "/work-sessions": self.handle_work_sessions,
        }
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
            ["laborer_id", "project_id", "work_date", "clock_in_time", "clock_out_time"],
        )
        if error:
            raise ValueError(error)
        work_date = parse_date(data["work_date"], "work_date")
        clock_in = parse_time(data["clock_in_time"], "clock_in_time")
        clock_out = parse_time(data["clock_out_time"], "clock_out_time")
        start_dt = datetime.combine(work_date, clock_in)
        end_dt = datetime.combine(work_date, clock_out)
        if end_dt <= start_dt:
            raise ValueError("clock_out_time must be after clock_in_time.")
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO work_sessions (
                  laborer_id,
                  project_id,
                  task_id,
                  work_date,
                  clock_in_time,
                  clock_out_time
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data["laborer_id"],
                    data["project_id"],
                    data.get("task_id"),
                    data["work_date"],
                    data["clock_in_time"],
                    data["clock_out_time"],
                ),
            )
        send_json(self, 201, {"id": cursor.lastrowid})

    def log_message(self, format, *args):
        return


def run():
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), RenovationHandler)
    print(f"API listening on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
