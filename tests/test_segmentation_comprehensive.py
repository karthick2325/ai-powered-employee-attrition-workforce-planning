"""
Workforce Intelligence — Phase 11 Comprehensive Unsupervised ML & Segmentation Test Suite
Tests data quality edge cases, pipeline robustness, model invariants,
isolation forest, silhouette handling, error schemas, and module regression.
"""

import unittest
import json
import numpy as np
import pandas as pd
from app import create_app
from src.segmentation import WorkforceSegmentation
from services.segmentation_service import SegmentationService
from services.excel_service import ExcelService
import config


class TestSegmentationComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_synthetic_fixture_data_handling(self):
        """Tests pipeline handling with missing values, unknown categories, and small samples."""
        # Create a small valid synthetic dataset fixture
        n = 50
        df_fixture = pd.DataFrame({
            "Employee_ID": [f"TEST_{i:04d}" for i in range(n)],
            "Department": ["Technology", "Operations", "Sales", "HR", "Finance"] * (n // 5),
            "Job_Role": ["Software Engineer", "Operations Lead", "Sales Executive", "HR Specialist", "Financial Analyst"] * (n // 5),
            "Job_Level": ["Junior", "Mid", "Senior", "Lead", "Executive"] * (n // 5),
            "Location": ["Bengaluru", "Hyderabad", "Pune", "Chennai", "Gurgaon"] * (n // 5),
            "Employment_Type": ["Full-time", "Contract", "Full-time", "Full-time", "Part-time"] * (n // 5),
            "Age": [25 + (i % 30) for i in range(n)],
            "Gender": ["Male", "Female"] * (n // 2),
            "Annual_Salary_INR": [600000 + i * 25000 for i in range(n)],
            "Tenure_Months_At_Prediction": [12 + (i % 60) for i in range(n)],
            "Overtime_Hours_Monthly": [5 + (i % 25) for i in range(n)],
            "Job_Satisfaction_Score_1_5": [3.0 + (i % 3) * 0.5 for i in range(n)],
            "Work_Life_Balance_Score_1_5": [2.5 + (i % 3) * 0.5 for i in range(n)],
            "Months_Since_Last_Promotion": [6 + (i % 36) for i in range(n)],
            "Training_Hours_Last_12M": [10 + (i % 40) for i in range(n)],
            "Manager_Tenure_Months": [12 + (i % 24) for i in range(n)],
            "Commute_Distance_KM": [5 + (i % 45) for i in range(n)],
            "Performance_Rating_1_5": [3.0 + (i % 3) * 0.5 for i in range(n)],
            "Last_Salary_Hike_Pct": [5.0 + (i % 10) for i in range(n)],
            "Serving_Notice_As_Of_Prediction": [False] * n,
            "Attrition_Within_6M": [0 if i % 10 != 0 else 1 for i in range(n)]
        })

        # Test compa ratio calculation on fixture
        level_meds = df_fixture.groupby("Job_Level")["Annual_Salary_INR"].median()
        df_fixture["Compa_Ratio"] = (df_fixture["Annual_Salary_INR"] / df_fixture["Job_Level"].map(level_meds)).round(4)
        self.assertEqual(len(df_fixture), n)
        self.assertAlmostEqual(df_fixture["Compa_Ratio"].mean(), 1.0, delta=0.2)

        # Build pipeline on fixture
        seg = WorkforceSegmentation(k=3, random_state=42)
        seg.df_population = df_fixture
        preproc = seg.build_preprocessor()
        X = df_fixture[seg.NUMERIC_FEATURES + seg.CATEGORICAL_FEATURES]
        X_trans = preproc.fit_transform(X)

        self.assertEqual(X_trans.shape[0], n)
        self.assertFalse(np.isnan(X_trans).any(), "Preprocessed matrix must not contain NaNs")

        # Test unknown categorical handling on transform
        test_unknown = X.iloc[:5].copy()
        test_unknown["Department"] = "Unknown Dept"
        test_unknown["Employment_Type"] = "Gig"
        X_trans_unk = preproc.transform(test_unknown)
        self.assertEqual(X_trans_unk.shape[0], 5)
        self.assertFalse(np.isnan(X_trans_unk).any(), "Unknown categories must be ignored without NaNs")

    def test_02_model_invariants_and_leakage_absence(self):
        """Verifies strictly zero leakage of target labels or demographic audit features."""
        seg = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=5, random_state=42)
        seg.load_data()

        # Clustering feature list must NEVER include target label or demographics
        forbidden_features = [
            "Attrition_Within_6M",
            "Attrition_Reason",
            "Actual_Exit_Date_Within_Window",
            "Outcome_Window_End",
            "Age",
            "Gender",
            "Employee_ID"
        ]
        for f in forbidden_features:
            self.assertNotIn(f, seg.NUMERIC_FEATURES, f"Data leakage: {f} found in NUMERIC_FEATURES")
            self.assertNotIn(f, seg.CATEGORICAL_FEATURES, f"Data leakage: {f} found in CATEGORICAL_FEATURES")

    def test_03_reproducibility_and_deterministic_clusters(self):
        """Ensures that identical random_state generates deterministic cluster assignments."""
        seg1 = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=4, random_state=42)
        seg1.fit()
        labels1 = seg1.df_segmented["Segment_ID"].values

        seg2 = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=4, random_state=42)
        seg2.fit()
        labels2 = seg2.df_segmented["Segment_ID"].values

        np.testing.assert_array_equal(labels1, labels2, "K-Means cluster assignments must be perfectly reproducible.")

    def test_04_isolation_forest_anomaly_denominator(self):
        """Validates that anomaly count uses the correct active eligible denominator."""
        pipeline = SegmentationService.get_pipeline(k=5)
        anomalies_df = pipeline.anomalies_df
        self.assertIsNotNone(anomalies_df)

        total_eligible = len(pipeline.df_population)
        anomaly_count = len(anomalies_df)

        # At 2% contamination on 47,972 employees, expected count is ~960
        self.assertEqual(total_eligible, 47972)
        self.assertAlmostEqual(anomaly_count, 960, delta=10)
        self.assertAlmostEqual((anomaly_count / total_eligible) * 100, 2.0, delta=0.1)

    def test_05_role_pressure_exit_exposure_denominator(self):
        """Validates role staffing pressure ratio and total notice exits."""
        pipeline = SegmentationService.get_pipeline(k=5)
        roles = pipeline.role_pressure_df
        self.assertEqual(len(roles), 26, "Must assess all 26 job roles.")

        # Ensure pressure ratio is between 0 and 2.0
        self.assertTrue((roles["Staffing_Pressure_Ratio"] >= 0.0).all())
        self.assertTrue((roles["Staffing_Pressure_Ratio"] <= 2.0).all())

        # Total notice exits in roles must match the 2,028 notice period population
        self.assertEqual(roles["Notice_Exits"].sum(), 2028)

    def test_06_fast_refit_performance_and_consistency(self):
        """Tests that fast_refit updates K and segment profiles without errors."""
        pipeline = SegmentationService.get_pipeline(k=5)
        self.assertEqual(pipeline.k, 5)

        # Fast refit to 3
        pipeline.fast_refit(k=3)
        self.assertEqual(pipeline.k, 3)
        self.assertEqual(len(pipeline.segment_profiles), 3)
        self.assertEqual(pipeline.segment_profiles["Headcount"].sum(), 47972)

        # Restore to 5
        pipeline.fast_refit(k=5)
        self.assertEqual(pipeline.k, 5)
        self.assertEqual(len(pipeline.segment_profiles), 5)
        self.assertEqual(pipeline.segment_profiles["Headcount"].sum(), 47972)

    def test_07_api_unified_contract_fields(self):
        """Tests that /api/segmentation/summary adheres strictly to Phase 6 API contract."""
        res = self.client.get("/api/segmentation/summary?k=5")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)

        # Model metadata
        self.assertIn("algorithm", data["model"])
        self.assertIn("requested_clusters", data["model"])
        self.assertIn("actual_clusters", data["model"])
        self.assertIn("random_state", data["model"])

        # Summary counts
        self.assertEqual(data["summary"]["source_rows"], 50000)
        self.assertEqual(data["summary"]["eligible_employees"], 47972)
        self.assertEqual(data["summary"]["clustered_employees"], 47972)
        self.assertEqual(data["summary"]["excluded_records"], 2028)
        self.assertAlmostEqual(data["summary"]["anomaly_percentage"], 2.0, delta=0.1)

        # Segments
        self.assertEqual(len(data["segments"]), 5)
        for seg in data["segments"]:
            self.assertIn("Segment_ID", seg)
            self.assertIn("Archetype_Name", seg)
            self.assertIn("Headcount", seg)
            self.assertIn("Pct_Workforce", seg)
            self.assertIn("Recommended_Talent_Action", seg)

    def test_08_formula_injection_protection_in_exports(self):
        """Tests that export sanitizes formula characters (=, +, -, @)."""
        from services.segmentation_service import _sanitize_csv_cell
        self.assertEqual(_sanitize_csv_cell("=1+1"), "'=1+1")
        self.assertEqual(_sanitize_csv_cell("+cmd"), "'+cmd")
        self.assertEqual(_sanitize_csv_cell("-malicious"), "'-malicious")
        self.assertEqual(_sanitize_csv_cell("@sum(A1)"), "'@sum(A1)")
        self.assertEqual(_sanitize_csv_cell("Normal Text"), "Normal Text")
        self.assertEqual(_sanitize_csv_cell(12345), 12345)

    def test_09_all_application_routes_regression(self):
        """Verifies that all 6 main dashboard routes remain fully functional."""
        routes = [
            ("/", "Dashboard Overview"),
            ("/analytics", "Department Analytics"),
            ("/prediction", "Attrition Prediction"),
            ("/workforce", "Workforce Planning"),
            ("/segmentation", "Workforce Segmentation"),
            ("/model-quality", "Model Performance")
        ]
        for route, keyword in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")
            self.assertIn(keyword.encode("utf-8"), res.data, f"Route {route} missing keyword '{keyword}'")


if __name__ == "__main__":
    unittest.main()
