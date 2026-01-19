-- Reference report queries for analytics and exports.

-- Material spend per project (materials + delivery).
SELECT
  p.id AS project_id,
  p.name AS project_name,
  SUM(mp.total_material_cost + mp.delivery_cost) AS total_material_spend
FROM material_purchases mp
JOIN projects p ON p.id = mp.project_id
GROUP BY p.id, p.name
ORDER BY total_material_spend DESC;

-- Vendor spend summary.
SELECT
  v.id AS vendor_id,
  v.name AS vendor_name,
  SUM(mp.total_material_cost + mp.delivery_cost) AS vendor_spend
FROM material_purchases mp
JOIN vendors v ON v.id = mp.vendor_id
GROUP BY v.id, v.name
ORDER BY vendor_spend DESC;

-- Labor payroll report (hourly vs daily rate).
SELECT
  l.id AS laborer_id,
  l.name AS laborer_name,
  COUNT(ws.id) AS work_sessions,
  ROUND(SUM(
    (julianday(ws.work_date || ' ' || ws.clock_out_time) -
     julianday(ws.work_date || ' ' || ws.clock_in_time)) * 24
  ), 2) AS hours_worked,
  ROUND(SUM(
    CASE
      WHEN l.hourly_rate IS NOT NULL THEN
        (julianday(ws.work_date || ' ' || ws.clock_out_time) -
         julianday(ws.work_date || ' ' || ws.clock_in_time)) * 24 * l.hourly_rate
      WHEN l.daily_rate IS NOT NULL THEN
        l.daily_rate
      ELSE 0
    END
  ), 2) AS gross_pay
FROM work_sessions ws
JOIN laborers l ON l.id = ws.laborer_id
GROUP BY l.id, l.name
ORDER BY gross_pay DESC;

-- Labor cost per project.
SELECT
  p.id AS project_id,
  p.name AS project_name,
  ROUND(SUM(
    CASE
      WHEN l.hourly_rate IS NOT NULL THEN
        (julianday(ws.work_date || ' ' || ws.clock_out_time) -
         julianday(ws.work_date || ' ' || ws.clock_in_time)) * 24 * l.hourly_rate
      WHEN l.daily_rate IS NOT NULL THEN
        l.daily_rate
      ELSE 0
    END
  ), 2) AS labor_cost
FROM work_sessions ws
JOIN laborers l ON l.id = ws.laborer_id
JOIN projects p ON p.id = ws.project_id
GROUP BY p.id, p.name
ORDER BY labor_cost DESC;

-- Average task duration in hours.
SELECT
  t.name AS task_name,
  ROUND(AVG((julianday(t.end_datetime) - julianday(t.start_datetime)) * 24), 2) AS avg_hours
FROM tasks t
GROUP BY t.name
ORDER BY avg_hours DESC;

-- Average material cost per material description (for estimation inputs).
SELECT
  mp.material_description,
  ROUND(AVG(mp.unit_cost), 2) AS avg_unit_cost,
  ROUND(AVG(mp.quantity), 2) AS avg_quantity,
  ROUND(AVG(mp.delivery_cost), 2) AS avg_delivery_cost
FROM material_purchases mp
GROUP BY mp.material_description
ORDER BY mp.material_description;
