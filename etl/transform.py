import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
os.makedirs(CLEAN_DIR, exist_ok=True)


def clean_patients(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["patient_id"]).copy()
    df["age"] = df["age"].fillna(df["age"].median()).astype(int)
    df["gender"] = df["gender"].fillna("Unknown")
    df["insurance_type"] = df["insurance_type"].fillna("Unknown")
    return df


def clean_departments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["department_id"]).copy()
    df["division_name"] = df["division_name"].str.strip()
    df["doctor_name"] = df["doctor_name"].str.strip()
    return df


def clean_visits(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["visit_id"]).copy()
    df["visit_date"] = pd.to_datetime(df["visit_date"], errors="coerce")
    df = df.dropna(subset=["visit_date"])

    df["er_wait_time_min"] = df["er_wait_time_min"].clip(lower=0)
    df["days_stayed"] = df["days_stayed"].clip(lower=0)
    df["treatment_cost"] = df["treatment_cost"].clip(lower=0)
    df["charges_per_md"] = df["charges_per_md"].clip(lower=0)

    df["year"] = df["visit_date"].dt.year
    df["month"] = df["visit_date"].dt.month
    df["month_name"] = df["visit_date"].dt.strftime("%b")
    df["quarter"] = df["visit_date"].dt.quarter

    return df


def main() -> None:
    patients = pd.read_csv(os.path.join(RAW_DIR, "patients.csv"))
    departments = pd.read_csv(os.path.join(RAW_DIR, "departments.csv"))
    visits = pd.read_csv(os.path.join(RAW_DIR, "visits.csv"))

    patients_clean = clean_patients(patients)
    departments_clean = clean_departments(departments)
    visits_clean = clean_visits(visits)

    patients_clean.to_csv(os.path.join(CLEAN_DIR, "patients_clean.csv"), index=False)
    departments_clean.to_csv(os.path.join(CLEAN_DIR, "departments_clean.csv"), index=False)
    visits_clean.to_csv(os.path.join(CLEAN_DIR, "visits_clean.csv"), index=False)

    print("Cleaned data written successfully.")


if __name__ == "__main__":
    main()