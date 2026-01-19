-- Renovation Project Management Application - Initial Schema

CREATE TABLE projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  start_date TEXT,
  end_date TEXT
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  start_datetime TEXT NOT NULL,
  end_datetime TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE vendors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL
);

CREATE TABLE material_purchases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  task_id INTEGER,
  vendor_id INTEGER NOT NULL,
  material_description TEXT NOT NULL,
  unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
  quantity REAL NOT NULL CHECK (quantity >= 0),
  total_material_cost REAL NOT NULL CHECK (total_material_cost >= 0),
  delivery_cost REAL DEFAULT 0 CHECK (delivery_cost >= 0),
  purchase_date TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (task_id) REFERENCES tasks(id),
  FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

CREATE TABLE laborers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  hourly_rate REAL CHECK (hourly_rate >= 0),
  daily_rate REAL CHECK (daily_rate >= 0)
);

CREATE TABLE work_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  laborer_id INTEGER NOT NULL,
  project_id INTEGER NOT NULL,
  task_id INTEGER,
  work_date TEXT NOT NULL,
  clock_in_time TEXT NOT NULL,
  clock_out_time TEXT NOT NULL,
  FOREIGN KEY (laborer_id) REFERENCES laborers(id),
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);
