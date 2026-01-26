-- Renovation Project Management Application - Initial Schema

CREATE TABLE projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  start_date TEXT,
  end_date TEXT,
  archived_at TEXT
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  start_datetime TEXT NOT NULL,
  end_datetime TEXT NOT NULL,
  archived_at TEXT,
  CHECK (julianday(end_datetime) > julianday(start_datetime)),
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE vendors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  archived_at TEXT
);

CREATE TABLE material_purchases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  task_id INTEGER,
  vendor_id INTEGER NOT NULL,
  material_description TEXT NOT NULL,
  unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
  quantity REAL NOT NULL CHECK (quantity >= 0),
  total_material_cost REAL NOT NULL DEFAULT 0 CHECK (total_material_cost >= 0),
  delivery_cost REAL DEFAULT 0 CHECK (delivery_cost >= 0),
  purchase_date TEXT NOT NULL,
  archived_at TEXT,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (task_id) REFERENCES tasks(id),
  FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

CREATE TABLE laborers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  hourly_rate REAL CHECK (hourly_rate >= 0),
  daily_rate REAL CHECK (daily_rate >= 0),
  archived_at TEXT
);

CREATE TABLE work_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  task_id INTEGER NOT NULL,
  work_date TEXT NOT NULL,
  archived_at TEXT,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE work_session_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_session_id INTEGER NOT NULL,
  laborer_id INTEGER NOT NULL,
  clock_in_time TEXT NOT NULL,
  clock_out_time TEXT NOT NULL,
  CHECK (
    julianday('2000-01-01 ' || clock_out_time) >
    julianday('2000-01-01 ' || clock_in_time)
  ),
  FOREIGN KEY (work_session_id) REFERENCES work_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (laborer_id) REFERENCES laborers(id)
);

CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_start_datetime ON tasks(start_datetime);
CREATE INDEX idx_tasks_project_start_datetime ON tasks(project_id, start_datetime);
CREATE INDEX idx_material_purchases_project_id ON material_purchases(project_id);
CREATE INDEX idx_material_purchases_vendor_id ON material_purchases(vendor_id);
CREATE INDEX idx_material_purchases_purchase_date ON material_purchases(purchase_date);
CREATE INDEX idx_material_purchases_project_purchase_date ON material_purchases(project_id, purchase_date);
CREATE INDEX idx_work_sessions_project_id ON work_sessions(project_id);
CREATE INDEX idx_work_sessions_work_date ON work_sessions(work_date);
CREATE INDEX idx_work_sessions_project_work_date ON work_sessions(project_id, work_date);

CREATE TRIGGER material_purchases_total_cost_insert
AFTER INSERT ON material_purchases
BEGIN
  UPDATE material_purchases
  SET total_material_cost = unit_cost * quantity
  WHERE id = NEW.id;
END;

CREATE TRIGGER material_purchases_total_cost_update
AFTER UPDATE OF unit_cost, quantity, total_material_cost ON material_purchases
WHEN NEW.total_material_cost != (NEW.unit_cost * NEW.quantity)
BEGIN
  UPDATE material_purchases
  SET total_material_cost = unit_cost * quantity
  WHERE id = NEW.id;
END;
