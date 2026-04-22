DROP TABLE IF EXISTS fact_visits;
DROP TABLE IF EXISTS dim_patient;
DROP TABLE IF EXISTS dim_department;

CREATE TABLE dim_patient (
    patient_id INT PRIMARY KEY,
    gender VARCHAR(20),
    age INT,
    city VARCHAR(100),
    insurance_type VARCHAR(50)
);

CREATE TABLE dim_department (
    department_id INT PRIMARY KEY,
    division_name VARCHAR(100),
    doctor_name VARCHAR(100),
    specialty VARCHAR(100)
);

CREATE TABLE fact_visits (
    visit_id INT PRIMARY KEY,
    patient_id INT REFERENCES dim_patient(patient_id),
    department_id INT REFERENCES dim_department(department_id),
    visit_date DATE,
    visit_type VARCHAR(20),
    er_wait_time_min NUMERIC,
    days_stayed NUMERIC,
    treatment_cost NUMERIC,
    charges_per_md NUMERIC,
    satisfaction_category VARCHAR(20),
    year INT,
    month INT,
    month_name VARCHAR(10),
    quarter INT
);