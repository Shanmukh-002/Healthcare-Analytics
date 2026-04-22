DROP VIEW IF EXISTS vw_kpis;
DROP VIEW IF EXISTS vw_patients_by_division;
DROP VIEW IF EXISTS vw_wait_time_by_division;
DROP VIEW IF EXISTS vw_satisfaction_by_division;
DROP VIEW IF EXISTS vw_inpatients_outpatients_monthly;
DROP VIEW IF EXISTS vw_cost_vs_charges_monthly;

CREATE VIEW vw_kpis AS
SELECT
    COUNT(*) FILTER (WHERE visit_type = 'Inpatient') AS number_of_inpatients,
    COUNT(*) FILTER (WHERE visit_type = 'Outpatient') AS number_of_outpatients,
    ROUND(AVG(er_wait_time_min), 2) AS average_er_wait_time_min,
    ROUND(AVG(NULLIF(days_stayed, 0)), 2) AS average_days_stayed
FROM fact_visits;

CREATE VIEW vw_patients_by_division AS
SELECT
    d.division_name,
    COUNT(*) AS patient_count
FROM fact_visits f
JOIN dim_department d ON f.department_id = d.department_id
GROUP BY d.division_name
ORDER BY patient_count DESC;

CREATE VIEW vw_wait_time_by_division AS
SELECT
    d.division_name,
    ROUND(AVG(f.er_wait_time_min), 2) AS avg_wait_time
FROM fact_visits f
JOIN dim_department d ON f.department_id = d.department_id
GROUP BY d.division_name
ORDER BY avg_wait_time DESC;

CREATE VIEW vw_satisfaction_by_division AS
SELECT
    d.division_name,
    f.satisfaction_category,
    COUNT(*) AS satisfaction_count
FROM fact_visits f
JOIN dim_department d ON f.department_id = d.department_id
GROUP BY d.division_name, f.satisfaction_category
ORDER BY d.division_name, satisfaction_category;

CREATE VIEW vw_inpatients_outpatients_monthly AS
SELECT
    year,
    month,
    MIN(month_name) AS month_name,
    COUNT(*) FILTER (WHERE visit_type = 'Inpatient') AS number_of_inpatients,
    COUNT(*) FILTER (WHERE visit_type = 'Outpatient') AS number_of_outpatients
FROM fact_visits
GROUP BY year, month
ORDER BY year, month;

CREATE VIEW vw_cost_vs_charges_monthly AS
SELECT
    year,
    month,
    MIN(month_name) AS month_name,
    ROUND(SUM(treatment_cost), 2) AS total_treatment_cost,
    ROUND(SUM(charges_per_md), 2) AS total_charges
FROM fact_visits
GROUP BY year, month
ORDER BY year, month;