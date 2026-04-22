import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

DIVISIONS = [
    "Cardiology",
    "Dermatology",
    "Gynaecology",
    "Neurology",
    "Oncology",
    "Orthopaedics",
    "Surgery",
    "Pediatrics",
    "Radiology",
    "Emergency Medicine",
]

INSURANCE_TYPES = ["Private", "Medicare", "Medicaid", "Self-pay"]
VISIT_TYPES = ["Inpatient", "Outpatient"]
SATISFACTION_LEVELS = ["Excellent", "Good", "Neutral"]

DIVISION_RULES = {
    "Cardiology": {"cost_min": 4000, "cost_max": 18000, "wait_mean": 50},
    "Dermatology": {"cost_min": 500, "cost_max": 4000, "wait_mean": 30},
    "Gynaecology": {"cost_min": 2000, "cost_max": 10000, "wait_mean": 40},
    "Neurology": {"cost_min": 3500, "cost_max": 16000, "wait_mean": 55},
    "Oncology": {"cost_min": 7000, "cost_max": 25000, "wait_mean": 60},
    "Orthopaedics": {"cost_min": 3000, "cost_max": 15000, "wait_mean": 45},
    "Surgery": {"cost_min": 5000, "cost_max": 22000, "wait_mean": 70},
    "Pediatrics": {"cost_min": 1000, "cost_max": 8000, "wait_mean": 35},
    "Radiology": {"cost_min": 800, "cost_max": 5000, "wait_mean": 25},
    "Emergency Medicine": {"cost_min": 2500, "cost_max": 12000, "wait_mean": 75},
}


def generate_patients(n: int = 3000) -> pd.DataFrame:
    patients = []
    for pid in range(1, n + 1):
        patients.append(
            {
                "patient_id": pid,
                "gender": random.choice(["Male", "Female"]),
                "age": random.randint(18, 90),
                "city": fake.city(),
                "insurance_type": random.choice(INSURANCE_TYPES),
            }
        )
    return pd.DataFrame(patients)


def generate_departments(doctors_per_division: int = 3) -> pd.DataFrame:
    rows = []
    department_id = 1

    for division in DIVISIONS:
        for _ in range(doctors_per_division):
            rows.append(
                {
                    "department_id": department_id,
                    "division_name": division,
                    "doctor_name": f"Dr. {fake.last_name()}",
                    "specialty": division,
                }
            )
            department_id += 1

    return pd.DataFrame(rows)


def random_date(start_date: datetime, end_date: datetime) -> datetime:
    delta = end_date - start_date
    return start_date + timedelta(days=random.randint(0, delta.days))


def generate_visits(
    patients_df: pd.DataFrame,
    departments_df: pd.DataFrame,
    n: int = 20000,
) -> pd.DataFrame:
    visits = []
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)

    patient_ids = patients_df["patient_id"].tolist()

    for vid in range(1, n + 1):
        visit_type = random.choices(VISIT_TYPES, weights=[0.45, 0.55])[0]
        dept_row = departments_df.sample(1).iloc[0]
        division_name = dept_row["division_name"]
        rules = DIVISION_RULES[division_name]

        visit_date = random_date(start_date, end_date)

        er_wait = max(5, int(np.random.normal(rules["wait_mean"], 12)))
        days_stayed = max(1, int(np.random.normal(5, 3))) if visit_type == "Inpatient" else 0

        treatment_cost = round(
            np.random.uniform(rules["cost_min"], rules["cost_max"]),
            2,
        )
        charges_per_md = round(treatment_cost * np.random.uniform(1.05, 1.25), 2)

        satisfaction = random.choices(
            SATISFACTION_LEVELS, weights=[0.35, 0.45, 0.20]
        )[0]

        visits.append(
            {
                "visit_id": vid,
                "patient_id": random.choice(patient_ids),
                "department_id": int(dept_row["department_id"]),
                "visit_date": visit_date.date(),
                "visit_type": visit_type,
                "er_wait_time_min": er_wait,
                "days_stayed": days_stayed,
                "treatment_cost": treatment_cost,
                "charges_per_md": charges_per_md,
                "satisfaction_category": satisfaction,
            }
        )

    return pd.DataFrame(visits)


def main() -> None:
    patients_df = generate_patients()
    departments_df = generate_departments(doctors_per_division=4)
    visits_df = generate_visits(patients_df, departments_df)

    patients_df.to_csv(os.path.join(RAW_DIR, "patients.csv"), index=False)
    departments_df.to_csv(os.path.join(RAW_DIR, "departments.csv"), index=False)
    visits_df.to_csv(os.path.join(RAW_DIR, "visits.csv"), index=False)

    print("Synthetic raw data generated successfully.")


if __name__ == "__main__":
    main()