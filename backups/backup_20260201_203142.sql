-- Renovation Material Tracker backup
-- Source DB: renovation.db
-- Generated: 2026-02-01T20:31:42Z
BEGIN TRANSACTION;
INSERT INTO projects (id, name, description, start_date, end_date, archived_at) VALUES (3, 'Madre Bdrm Floor', 'Turning wooden floor to concrete', '2026-01-20', '2026-02-13', NULL);
INSERT INTO tasks (id, project_id, name, start_datetime, end_datetime, archived_at) VALUES (1, 1, 'Cabinet Refacing', '2025-01-06 08:00', '2025-01-10 17:30', '2026-01-20T01:11:58');
INSERT INTO tasks (id, project_id, name, start_datetime, end_datetime, archived_at) VALUES (5, 3, 'Foundation Blockwork', '2026-01-20 08:00', '2026-01-25 17:00', NULL);
INSERT INTO vendors (id, name, archived_at) VALUES (4, 'Carters & Co', NULL);
INSERT INTO vendors (id, name, archived_at) VALUES (5, 'Exodus Trucking', NULL);
INSERT INTO laborers (id, name, hourly_rate, daily_rate, archived_at) VALUES (4, 'Gregory', NULL, 100.0, NULL);
INSERT INTO material_purchases (id, project_id, task_id, vendor_id, material_description, unit_cost, quantity, total_material_cost, delivery_cost, purchase_date, archived_at) VALUES (5, 3, 5, 4, 'Arawak Grey Cement 42.5KG', 19.27, 3.0, 57.81, 3.0, '2026-01-17', NULL);
INSERT INTO material_purchases (id, project_id, task_id, vendor_id, material_description, unit_cost, quantity, total_material_cost, delivery_cost, purchase_date, archived_at) VALUES (6, 3, 5, 4, 'High Tension Steel 12i 12MMx6MT', 15.44, 3.0, 46.32, 0.0, '2026-01-17', NULL);
INSERT INTO material_purchases (id, project_id, task_id, vendor_id, material_description, unit_cost, quantity, total_material_cost, delivery_cost, purchase_date, archived_at) VALUES (7, 3, 5, 4, 'Concrete Blocks 8 inch', 5.66, 50.0, 283.0, 15.0, '2026-01-17', NULL);
INSERT INTO material_purchases (id, project_id, task_id, vendor_id, material_description, unit_cost, quantity, total_material_cost, delivery_cost, purchase_date, archived_at) VALUES (8, 3, 5, 5, '1/2i Stone 1M', 100.0, 1.0, 100.0, 120.0, '2026-01-19', NULL);
INSERT INTO work_sessions (id, project_id, task_id, work_date, archived_at) VALUES (1, 1, 1, '2025-01-06', '2026-01-20T01:12:00');
INSERT INTO work_sessions (id, project_id, task_id, work_date, archived_at) VALUES (5, 1, 1, '2025-01-08', NULL);
INSERT INTO work_sessions (id, project_id, task_id, work_date, archived_at) VALUES (6, 3, 5, '2026-01-25', NULL);
INSERT INTO work_sessions (id, project_id, task_id, work_date, archived_at) VALUES (7, 3, 5, '2026-01-26', NULL);
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (5, 5, 1, '08:00', '11:00');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (6, 5, 2, '10:00', '14:30');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (7, 1, 1, '08:05', '16:45');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (8, 1, 2, '09:00', '12:00');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (9, 2, 2, '09:10', '16:20');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (10, 2, 3, '06:20', '17:00');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (11, 6, 4, '10:00', '15:00');
INSERT INTO work_session_entries (id, work_session_id, laborer_id, clock_in_time, clock_out_time) VALUES (12, 7, 4, '09:00', '15:00');
COMMIT;
