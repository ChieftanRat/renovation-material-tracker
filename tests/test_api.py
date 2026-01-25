import json
import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, timedelta
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import api


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "renovation.db")
        os.environ["RENOVATION_DB"] = self.db_path
        api.DB_PATH = self.db_path
        self._load_schema_and_seed()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), api.RenovationHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def _load_schema_and_seed(self):
        repo_root = Path(__file__).resolve().parents[1]
        schema_sql = (repo_root / "schema.sql").read_text(encoding="utf-8")
        seed_sql = (repo_root / "seed.sql").read_text(encoding="utf-8")
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema_sql)
            conn.executescript(seed_sql)

    def _request_json(self, method, path, payload):
        body = json.dumps(payload).encode("utf-8")
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            data = response.read().decode("utf-8")
            return response.status, json.loads(data)
        finally:
            conn.close()

    def test_create_project_success(self):
        status, payload = self._request_json(
            "POST",
            "/projects",
            {"name": "Deck Refinish", "start_date": "2025-04-01"},
        )
        self.assertEqual(status, 201)
        self.assertIn("id", payload)

    def test_create_project_missing_name(self):
        status, payload = self._request_json(
            "POST",
            "/projects",
            {"start_date": "2025-04-01"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "Missing required fields: name.")

    def test_material_purchase_future_date_rejected(self):
        future_date = (date.today() + timedelta(days=1)).isoformat()
        status, payload = self._request_json(
            "POST",
            "/material-purchases",
            {
                "project_id": 1,
                "vendor_id": 1,
                "material_description": "Drywall",
                "unit_cost": 12.5,
                "quantity": 8,
                "purchase_date": future_date,
            },
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "purchase_date cannot be in the future.")

    def test_material_purchase_success(self):
        status, payload = self._request_json(
            "POST",
            "/material-purchases",
            {
                "project_id": 1,
                "vendor_id": 1,
                "material_description": "Paint",
                "unit_cost": 29.0,
                "quantity": 3,
                "delivery_cost": 5,
                "purchase_date": date.today().isoformat(),
            },
        )
        self.assertEqual(status, 201)
        self.assertIn("id", payload)


if __name__ == "__main__":
    unittest.main()
