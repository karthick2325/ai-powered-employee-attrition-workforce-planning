"""
Workforce Intelligence — AI-Powered HR Analytics
Configuration Module
"""
import os
import glob
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

# Ensure runtime directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

def discover_dataset_path() -> str:
    """
    Discovers the Excel dataset file path dynamically with environment variable support
    and fallback candidates.
    """
    env_path = os.getenv("DATASET_PATH") or os.getenv("EXCEL_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    candidate_names = [
        "Employee_Attrition_Workforce_Planning_Expert_Dataset(3).xlsx",
        "Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx",
        "Employee_Attrition_Workforce_Planning.xlsx"
    ]
    
    # Check data/ and root directories for candidate names
    for name in candidate_names:
        data_candidate = DATA_DIR / name
        if data_candidate.exists():
            return str(data_candidate)
        root_candidate = BASE_DIR / name
        if root_candidate.exists():
            return str(root_candidate)

    # Glob search for any matching pattern
    glob_patterns = [
        str(DATA_DIR / "*Attrition*.xlsx"),
        str(BASE_DIR / "*Attrition*.xlsx"),
        str(DATA_DIR / "*.xlsx"),
        str(BASE_DIR / "*.xlsx"),
    ]
    for pattern in glob_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    # Return default path if not yet found
    return str(DATA_DIR / "Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx")

EXCEL_FILE_PATH = discover_dataset_path()

# Target and Feature sets for ML modeling
TARGET_COLUMN = "Attrition_Within_6M"

CATEGORICAL_FEATURES = [
    "Department",
    "Job_Role",
    "Job_Level",
    "Location",
    "Employment_Type"
]

NUMERICAL_FEATURES = [
    "Tenure_Months_At_Prediction",
    "Annual_Salary_INR",
    "Overtime_Hours_Monthly",
    "Job_Satisfaction_Score_1_5",
    "Work_Life_Balance_Score_1_5",
    "Months_Since_Last_Promotion",
    "Training_Hours_Last_12M",
    "Manager_Tenure_Months",
    "Commute_Distance_KM",
    "Performance_Rating_1_5",
    "Last_Salary_Hike_Pct"
]

# Audited fairness features excluded from default predictive model
FAIRNESS_AUDIT_FEATURES = ["Age", "Gender"]

# Explicit data leakage and non-feature exclusions
EXCLUDED_FEATURES = [
    "Employee_ID",
    "Prediction_Date",
    "Joining_Date",
    "Serving_Notice_As_Of_Prediction",
    "Outcome_Window_End",
    "Actual_Exit_Date_Within_Window"
]

# Risk classification thresholds
RISK_THRESHOLDS = {
    "LOW_MAX": 0.30,       # Below 0.30 -> Low Risk
    "MEDIUM_MAX": 0.60,    # 0.30 to 0.60 -> Medium Risk
    # >= 0.60 -> High Risk
}

# Synthetic dataset disclaimer
DISCLAIMER_TEXT = (
    "Demonstration application using synthetic workforce data. "
    "Predictions and planning estimates are illustrative and must not be treated as actual employee outcomes."
)

DATA_SNAPSHOT_DATE = "01 Jan 2026"

# Server configuration
SECRET_KEY = os.getenv("SECRET_KEY", "workforce-intelligence-secret-key-2026")
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "127.0.0.1")
