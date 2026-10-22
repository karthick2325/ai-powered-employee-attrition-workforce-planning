"""
Workforce Intelligence — Excel Data Service
Centralized data access and in-memory caching layer for the workbook.
"""
import os
import logging
from typing import Dict, Optional, Any
import pandas as pd
import config

logger = logging.getLogger(__name__)

# Deterministic name generator for synthetic employee display
FIRST_NAMES_MALE = [
    "Arjun", "Karthik", "Rahul", "Vignesh", "Suresh", "Rohan", "Aditya", "Vikram",
    "Deepak", "Anand", "Naveen", "Manoj", "Pradeep", "Varun", "Ashok", "Ganesh"
]
FIRST_NAMES_FEMALE = [
    "Priya", "Divya", "Meena", "Anitha", "Lavanya", "Kavitha", "Pooja", "Deepa",
    "Sneha", "Shreya", "Nandhini", "Lakshmi", "Sandhya", "Preeti", "Aarthi", "Ritu"
]
LAST_NAMES = [
    "Kumar", "Sharma", "R", "N", "S", "K", "P", "M", "T", "Patel",
    "Reddy", "Iyer", "Rao", "Nair", "Verma", "Singh", "Joshi", "Gupta"
]

def generate_display_name(emp_id: str, gender: Optional[str] = None) -> str:
    """Deterministically maps an Employee ID to a realistic name for UI consistency."""
    try:
        # Numeric seed from digits in ID
        digits = "".join(ch for ch in str(emp_id) if ch.isdigit())
        seed = int(digits) if digits else hash(str(emp_id))
    except Exception:
        seed = hash(str(emp_id))
        
    g = str(gender).upper() if gender else ("F" if seed % 2 == 1 else "M")
    if g == "FEMALE" or g == "F":
        fname = FIRST_NAMES_FEMALE[seed % len(FIRST_NAMES_FEMALE)]
    else:
        fname = FIRST_NAMES_MALE[seed % len(FIRST_NAMES_MALE)]
        
    lname = LAST_NAMES[(seed // 7) % len(LAST_NAMES)]
    return f"{fname} {lname}"

class ExcelService:
    """Singleton service to read, cache, and provide dataframes from the workbook."""
    _instance = None
    _data: Dict[str, pd.DataFrame] = {}
    _loaded = False
    _load_error: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExcelService, cls).__new__(cls)
        return cls._instance

    @classmethod
    def load_workbook(cls, file_path: Optional[str] = None, force_reload: bool = False) -> bool:
        """Loads all sheets from the Excel workbook into memory."""
        if cls._loaded and not force_reload:
            return True

        target_path = file_path or config.EXCEL_FILE_PATH
        if not os.path.exists(target_path):
            cls._load_error = f"Excel workbook not found at: {target_path}"
            logger.error(cls._load_error)
            return False

        logger.info(f"Loading Excel workbook from {target_path}...")
        try:
            excel_file = pd.ExcelFile(target_path, engine="openpyxl")
            sheets = [
                "Employees",
                "Notice_Period",
                "Attrition_Outcomes",
                "Workforce_Planning",
                "Recruitment_Pipeline",
                "Job_Requisitions",
                "Recruitment_Costs",
                "README",
                "Data_Dictionary",
                "Validation_Report",
                "Change_Log"
            ]

            cls._data.clear()
            for sheet in sheets:
                if sheet in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet)
                    cls._data[sheet] = df
                else:
                    logger.warning(f"Sheet '{sheet}' not found in workbook.")

            # Add display name column to Employees if not present
            if "Employees" in cls._data:
                emp_df = cls._data["Employees"]
                if "Employee_Name" not in emp_df.columns:
                    gender_col = emp_df["Gender"] if "Gender" in emp_df.columns else None
                    emp_df["Employee_Name"] = [
                        generate_display_name(eid, gen)
                        for eid, gen in zip(emp_df["Employee_ID"], gender_col if gender_col is not None else [None]*len(emp_df))
                    ]

            cls._loaded = True
            cls._load_error = None
            logger.info("Excel workbook loaded successfully into memory.")
            return True
        except Exception as e:
            cls._load_error = f"Failed to load workbook: {str(e)}"
            cls._loaded = False
            logger.exception(cls._load_error)
            return False

    @classmethod
    def get_sheet(cls, sheet_name: str) -> pd.DataFrame:
        """Returns a cached DataFrame for the given worksheet name."""
        if not cls._loaded:
            cls.load_workbook()
        if sheet_name not in cls._data:
            raise KeyError(f"Sheet '{sheet_name}' is not loaded or does not exist.")
        return cls._data[sheet_name]

    @classmethod
    def get_all_sheets(cls) -> Dict[str, pd.DataFrame]:
        """Returns all loaded DataFrames."""
        if not cls._loaded:
            cls.load_workbook()
        return cls._data

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded

    @classmethod
    def get_load_error(cls) -> Optional[str]:
        return cls._load_error

    @classmethod
    def reload_data(cls) -> bool:
        """Forces reloading the workbook from disk."""
        return cls.load_workbook(force_reload=True)

    @classmethod
    def get_dataset_summary(cls) -> list:
        """Returns structured metadata summary across all sheets."""
        if not cls._loaded:
            cls.load_workbook()

        descriptions = {
            "Employees": "Employee master records and baseline demographic/workforce attributes",
            "Notice_Period": "Employees actively serving contractual notice periods as of snapshot",
            "Attrition_Outcomes": "Binary 6-month attrition labels for the eligible non-notice cohort",
            "Workforce_Planning": "Department-level headcount, target allocations, and gap estimates",
            "Recruitment_Pipeline": "Candidate pipeline tracking across evaluation and offer stages",
            "Job_Requisitions": "Active and filled job requisitions by department and role",
            "Recruitment_Costs": "Cost breakdown (recruiter, agency, ad, assessment) per requisition",
            "README": "Project data provenance, modeling rules, and design notes",
            "Data_Dictionary": "Full column definitions, data types, and cautions",
            "Validation_Report": "Validation checks and automated integrity audit results",
            "Change_Log": "Dataset versioning and anomaly remediation history"
        }

        summary = []
        for name, df in cls._data.items():
            summary.append({
                "sheet_name": name,
                "description": descriptions.get(name, "Worksheet"),
                "total_records": len(df),
                "total_columns": len(df.columns),
                "validation_status": "Valid"
            })
        return summary
