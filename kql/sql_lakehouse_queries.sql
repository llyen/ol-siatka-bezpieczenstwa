-- sql_lakehouse_queries.sql
-- Wersje SQL dla Lakehouse SQL endpoint / Warehouse.

-- Readiness by division
SELECT admin_division, status, COUNT(*) AS declarations
FROM fact_readiness_declaration
GROUP BY admin_division, status
ORDER BY admin_division, status;

-- Active plan enriched with admin names
SELECT p.hazard_code, p.phase, p.task_module_id, p.task_module_name,
       p.admin_division, a.admin_name, p.role, p.criticality, p.sla_hours
FROM activation_plan p
LEFT JOIN dim_admin_division a ON p.admin_division = a.admin_division
ORDER BY p.dependency_order, p.role, p.admin_division;

-- SPO-1 participants from active plan
SELECT DISTINCT p.admin_division, a.admin_name, a.ministry, c.email, c.duty_phone
FROM activation_plan p
LEFT JOIN dim_admin_division a ON p.admin_division = a.admin_division
LEFT JOIN dim_contact_point c ON p.admin_division = c.admin_division
WHERE p.role IN ('wiodący', 'współpracujący')
ORDER BY p.admin_division;
