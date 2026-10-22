"""
Workforce Intelligence — Preprocessing Service
Prepares feature matrices, handles scaling, encoding, and train/test splitting.
"""
from typing import Tuple, List
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib

import config
from services.excel_service import ExcelService

class PreprocessingService:
    _preprocessor: ColumnTransformer = None
    _feature_names: List[str] = []

    @classmethod
    def get_modeling_data(cls) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """
        Merges Employees with Attrition_Outcomes on Employee_ID.
        Ensures employees serving notice are excluded (47,972 records).
        Returns X, y, and the full merged DataFrame.
        """
        emp_df = ExcelService.get_sheet("Employees")
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")

        # Exclude employees currently serving notice from training population
        if "Serving_Notice_As_Of_Prediction" in emp_df.columns:
            eligible_emp = emp_df[emp_df["Serving_Notice_As_Of_Prediction"] == False].copy()
        else:
            eligible_emp = emp_df.copy()

        # Merge on Employee_ID
        merged = eligible_emp.merge(
            outcomes_df[["Employee_ID", config.TARGET_COLUMN]],
            on="Employee_ID",
            how="inner"
        )

        feature_cols = config.CATEGORICAL_FEATURES + config.NUMERICAL_FEATURES
        X = merged[feature_cols].copy()
        y = merged[config.TARGET_COLUMN].copy()

        return X, y, merged

    @classmethod
    def build_preprocessor(cls) -> ColumnTransformer:
        """Constructs a ColumnTransformer pipeline for categorical and numerical features."""
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), config.NUMERICAL_FEATURES),
                ("cat", OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore"), config.CATEGORICAL_FEATURES)
            ]
        )
        return preprocessor

    @classmethod
    def get_train_test_split(cls, test_size: float = 0.2, random_state: int = 42):
        """Generates stratified train and test splits."""
        X, y, merged = cls.get_modeling_data()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y
        )
        return X_train, X_test, y_train, y_test, merged
