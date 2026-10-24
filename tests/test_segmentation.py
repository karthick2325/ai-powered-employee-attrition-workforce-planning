"""
Workforce Intelligence — Unsupervised Learning & Segmentation Automated Test Suite
Tests:
  1. Data preparation, Compa_Ratio calculation, and exclusion rules.
  2. K-Means clustering with configurable K, post-hoc validation, and demographic audit.
  3. Job role staffing pressure segmentation.
  4. Workload and compensation anomaly detection via Isolation Forest.
  5. Flask Blueprint API routes and JSON contracts.
  6. CSV & Excel Export endpoints with formula sanitization.
  7. Unified API summary contract (Phase 6 specification).
  8. Data quality governance and model comparison endpoints.
"""

import unittest
import json
from app import create_app
from src.segmentation import WorkforceSegmentation
from services.segmentation_service import SegmentationService
from services.excel_service import ExcelService
import config


class TestSegmentationModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_population_and_compa_ratio(self):
        """Verifies eligible cohort population (47,972) and Compa_Ratio calculation."""
        seg = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=5, random_state=42)
        df = seg.load_data()

        # Cohort verification
        self.assertEqual(len(df), 47972, "Population must be exactly 47,972 non-notice employees.")
        self.assertNotIn(True, df["Serving_Notice_As_Of_Prediction"].values, "Notice employees must be excluded.")

        # Compa_Ratio derivation
        self.assertIn("Compa_Ratio", df.columns, "Compa_Ratio must be derived.")
        self.assertTrue(df["Compa_Ratio"].min() >= 0.60, "Compa_Ratio min should be around 0.66.")
        self.assertTrue(df["Compa_Ratio"].max() <= 1.40, "Compa_Ratio max should be around 1.34.")
        self.assertAlmostEqual(df["Compa_Ratio"].mean(), 1.00, delta=0.05, msg="Mean Compa_Ratio should be ~1.0.")

    def test_02_feature_exclusions_from_clustering(self):
        """Verifies that target label, IDs, and demographics are excluded from clustering."""
        seg = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=5, random_state=42)
        seg.load_data()
        preprocessor = seg.build_preprocessor()

        X = seg.df_population[seg.NUMERIC_FEATURES + seg.CATEGORICAL_FEATURES]
        transformed = preprocessor.fit_transform(X)

        # 11 numeric + 8 Dept + 4 Level + 3 Type = 26 one-hot / scaled columns
        self.assertEqual(transformed.shape[0], 47972)
        self.assertEqual(transformed.shape[1], 26)

        # Ensure excluded columns never enter features
        for excluded in seg.EXCLUDED_FROM_CLUSTERING:
            self.assertNotIn(excluded, seg.NUMERIC_FEATURES)
            self.assertNotIn(excluded, seg.CATEGORICAL_FEATURES)

    def test_03_configurable_k_and_post_hoc_validation(self):
        """Tests K-Means fitting with configurable K and post-hoc validation."""
        for test_k in [4, 5]:
            seg = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=test_k, random_state=42)
            seg.fit()
            profiles = seg.profile_segments()

            self.assertEqual(len(profiles), test_k, f"Must produce exactly {test_k} segment profiles.")
            self.assertEqual(profiles["Headcount"].sum(), 47972, "Total headcount across segments must sum to 47,972.")
            self.assertAlmostEqual(profiles["Pct_Workforce"].sum(), 100.0, delta=0.2)

            # Post-hoc validation: sum of simulated exits must equal total positive simulated labels (2,779)
            self.assertEqual(profiles["Simulated_Exits"].sum(), 2779, "Simulated exits across segments must equal 2,779.")

            # Demographic audit check
            self.assertTrue((profiles["Audit_Pct_Female"] > 35.0).all(), "Female % should be ~42-43%.")
            self.assertTrue((profiles["Audit_Mean_Age"] > 30.0).all(), "Mean age should be ~33-35.")

    def test_04_job_role_staffing_pressure(self):
        """Tests job role staffing pressure clustering across all 26 roles."""
        seg = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=5, random_state=42)
        seg.fit()
        roles_df = seg.segment_job_roles(n_clusters=3)

        self.assertEqual(len(roles_df), 26, "Must contain all 26 job roles.")
        self.assertIn("Staffing_Pressure_Ratio", roles_df.columns)
        self.assertIn("Pressure_Tier", roles_df.columns)

        # Notice exits across roles should equal 2,028
        total_notice_in_roles = roles_df["Notice_Exits"].sum()
        self.assertEqual(total_notice_in_roles, 2028, "Total notice exits allocated across roles must equal 2,028.")

        # Tiers present
        unique_tiers = roles_df["Pressure_Tier"].unique()
        self.assertTrue(len(unique_tiers) >= 2, "Must cluster roles into distinct pressure tiers.")

    def test_05_workload_pay_anomaly_detection(self):
        """Tests Isolation Forest anomaly detection on workload and compensation."""
        seg = WorkforceSegmentation(excel_path=config.EXCEL_FILE_PATH, k=5, random_state=42)
        seg.fit()
        anom_df = seg.detect_anomalies(contamination=0.02)

        # 2% of 47,972 is ~960 anomalies
        self.assertAlmostEqual(len(anom_df), 960, delta=10)
        self.assertIn("Anomaly_Type", anom_df.columns)
        self.assertIn("Anomaly_Score", anom_df.columns)

    def test_06_api_routes(self):
        """Tests Flask web and API routes for segmentation."""
        # 1. Page view
        res = self.client.get("/segmentation")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Workforce Segmentation", res.data)
        self.assertIn(b"Synthetic Data Notice", res.data)

        # 2. Overview API
        res = self.client.get("/api/segmentation/overview?k=5")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["total_clustered_employees"], 47972)
        self.assertEqual(data["data"]["total_segments"], 5)

        # 3. Profiles API
        res = self.client.get("/api/segmentation/profiles?k=5")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 5)

        # 4. K-Evaluation API
        res = self.client.get("/api/segmentation/k-evaluation")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertTrue(len(data["data"]) >= 4)

        # 5. Role Pressure API
        res = self.client.get("/api/segmentation/role-pressure")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 26)

        # 6. Anomalies API
        res = self.client.get("/api/segmentation/anomalies?page=1&page_size=10")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]["records"]), 10)

        # 7. Dynamic Refit API
        res = self.client.post(
            "/api/segmentation/refit",
            data=json.dumps({"k": 4}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["k"], 4)

    def test_07_export_csv_and_xlsx_routes(self):
        """Tests export endpoint for CSV and XLSX formats with sanitization."""
        # CSV Export
        res_csv = self.client.get("/api/segmentation/export?k=5&format=csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv.headers.get("Content-Type", ""))
        self.assertIn("attachment;", res_csv.headers.get("Content-Disposition", ""))
        self.assertIn(b"Segment_ID", res_csv.data)

        # XLSX Export
        res_xlsx = self.client.get("/api/segmentation/export?k=5&format=xlsx")
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn("spreadsheetml", res_xlsx.headers.get("Content-Type", ""))
        self.assertIn("attachment;", res_xlsx.headers.get("Content-Disposition", ""))
        self.assertTrue(len(res_xlsx.data) > 1000)

    def test_08_unified_summary_contract(self):
        """Tests unified contract endpoint /api/segmentation/summary (Phase 6)."""
        res = self.client.get("/api/segmentation/summary?k=5")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)

        self.assertTrue(data["success"])
        self.assertIn("model", data)
        self.assertEqual(data["model"]["algorithm"], "kmeans")
        self.assertEqual(data["model"]["requested_clusters"], 5)
        self.assertEqual(data["model"]["actual_clusters"], 5)

        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["eligible_employees"], 47972)
        self.assertEqual(data["summary"]["clustered_employees"], 47972)
        self.assertEqual(data["summary"]["excluded_records"], 2028)
        self.assertEqual(data["summary"]["anomaly_count"], 960)

        self.assertIn("segments", data)
        self.assertEqual(len(data["segments"]), 5)
        self.assertIn("kpis", data)
        self.assertIn("data_quality", data)
        self.assertIn("metadata", data)
        self.assertTrue(data["metadata"]["is_synthetic"])

    def test_09_data_quality_and_model_comparison(self):
        """Tests data quality endpoint and optional unsupervised model comparison."""
        res_dq = self.client.get("/api/segmentation/data-quality")
        self.assertEqual(res_dq.status_code, 200)
        dq_data = json.loads(res_dq.data)
        self.assertTrue(dq_data["success"])
        self.assertEqual(dq_data["data"]["source_row_count"], 50000)
        self.assertEqual(dq_data["data"]["eligible_employee_count"], 47972)

        res_comp = self.client.get("/api/segmentation/model-comparison")
        self.assertEqual(res_comp.status_code, 200)
        comp_data = json.loads(res_comp.data)
        self.assertTrue(comp_data["success"])
        self.assertIn("kmeans", comp_data["data"]["models"])
        self.assertIn("agglomerative", comp_data["data"]["models"])


if __name__ == "__main__":
    unittest.main()
