-- Sample data for local development and reference queries.

INSERT INTO projects (name, description, start_date, end_date)
VALUES
  ('Kitchen Refresh', 'Cabinet refacing and tile upgrade', '2025-01-05', '2025-02-10'),
  ('Bathroom Remodel', 'Shower rebuild and fixture replacement', '2025-02-15', '2025-03-20');

INSERT INTO tasks (project_id, name, start_datetime, end_datetime)
VALUES
  (1, 'Cabinet Refacing', '2025-01-06 08:00', '2025-01-10 17:30'),
  (1, 'Backsplash Tile', '2025-01-12 09:00', '2025-01-14 16:00'),
  (2, 'Demo and Prep', '2025-02-16 08:30', '2025-02-17 15:30'),
  (2, 'Shower Waterproofing', '2025-02-19 09:00', '2025-02-20 18:00');

INSERT INTO vendors (name)
VALUES
  ('Brightline Supply'),
  ('Stone & Tile Depot'),
  ('QuickFix Hardware');

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
VALUES
  (1, 1, 1, 'Cabinet veneer sheets', 45.00, 18, 810.00, 60.00, '2025-01-06'),
  (1, 2, 2, 'Subway tile 3x6', 2.40, 180, 432.00, 45.00, '2025-01-11'),
  (2, 3, 3, 'Demo bags and liners', 1.20, 90, 108.00, 0.00, '2025-02-16'),
  (2, 4, 2, 'Waterproofing membrane', 4.80, 95, 456.00, 35.00, '2025-02-19');

INSERT INTO laborers (name, hourly_rate, daily_rate)
VALUES
  ('Amir Jones', 32.50, NULL),
  ('Lucia Perez', 28.00, NULL),
  ('Team Zenith', NULL, 420.00);

INSERT INTO work_sessions (
  laborer_id,
  project_id,
  task_id,
  work_date,
  clock_in_time,
  clock_out_time
)
VALUES
  (1, 1, 1, '2025-01-06', '08:05', '16:45'),
  (2, 1, 2, '2025-01-12', '09:10', '16:20'),
  (3, 2, 3, '2025-02-16', '08:30', '15:30'),
  (1, 2, 4, '2025-02-19', '09:00', '18:00');
