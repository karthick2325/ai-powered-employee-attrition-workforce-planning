"""
Comprehensive Automated Verification Suite for AttritionSense Technologies Audit
Validates:
- Single Source of Truth population equations
- Accurate Cost-per-Hire and Requisition formulas
- Dynamic notice calculation relative to reference date
- Brand identity ('AttritionSense Technologies') and logo placeholders
- AI Model Intelligence supervised & unsupervised endpoints
- Enterprise Reports & Exports generation (CSV & XLSX)
"""
import unittest
import pandas as pd
from app import create_app
from services.excel_service import ExcelService
from services.recruitment_service import RecruitmentService
from services.workforce_planning_service import WorkforcePlanningService
from services.prediction_service import PredictionService
from services.export_service import ExportService
import config


class TestAuditCorrections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # ---------------------------------------------------------
    # 1. Single Source of Truth & Population Rules
    # ---------------------------------------------------------
    def test_single_source_of_truth_headcounts(self):
        emp_df = ExcelService.get_sheet("Employees")
        notice_df = ExcelService.get_sheet("Notice_Period")
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")

        total_employees = len(emp_df)
        notice_count = len(notice_df)
        outcomes_count = len(outcomes_df)

        # 50,000 total snapshot records
        self.assertEqual(total_employees, 50000, "Master headcount must equal 50,000")
        # 2,028 confirmed notice period records
        self.assertEqual(notice_count, 2028, "Confirmed notice exits must equal 2,028")
        # 47,972 active eligible non-notice cohort
        self.assertEqual(outcomes_count, 47972, "Attrition outcomes cohort must equal 47,972")
        self.assertEqual(total_employees - notice_count, outcomes_count, "Master - Notice must strictly equal 47,972")

        # Distinct employee IDs
        self.assertEqual(emp_df["Employee_ID"].nunique(), 50000, "Employee_IDs must be strictly unique")
        self.assertEqual(notice_df["Employee_ID"].nunique(), 2028, "Notice Employee_IDs must be unique")

    def test_historical_vs_predicted_attrition_separation(self):
        # Historical realised attrition
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")
        historical_exits = int((outcomes_df["Attrition_Within_6M"] == 1).sum())
        historical_rate = round(historical_exits / len(outcomes_df) * 100, 2)
        
        self.assertEqual(historical_exits, 2779, "Realised 6M historical exits must equal 2,779")
        self.assertAlmostEqual(historical_rate, 5.79, places=2, msg="Historical attrition rate must be 5.79%")

        # Predicted attrition risk on active cohort
        pred_df = PredictionService.get_predictions_df()
        self.assertEqual(len(pred_df), 47972, "Predictions must run on 47,972 active non-notice employees")
        high_risk_count = int((pred_df["Risk_Level"] == "High").sum())
        self.assertEqual(high_risk_count, 2694, "Predicted high-risk employees must equal 2,694")
        
        # Ensure predicted exits are not conflated with historical exits
        self.assertNotEqual(historical_exits, high_risk_count, "Predicted high-risk exits must be distinct from realised historical exits")

    # ---------------------------------------------------------
    # 2. Recruitment KPI & Financial Math
    # ---------------------------------------------------------
    def test_recruitment_kpis_and_cost_per_hire(self):
        kpis = RecruitmentService.get_recruitment_kpis()
        costs = RecruitmentService.get_recruitment_costs()

        # Cost per hire = Total Spend (12,62,32,510) / Total Hires (1,617) = INR 78,066
        self.assertEqual(costs["total_cost_numeric"], 126232510.0)
        self.assertEqual(costs["total_hires"], 1617)
        self.assertEqual(costs["total_requisitions"], 1200)
        self.assertEqual(costs["avg_cost_per_hire_numeric"], 78066)
        # Cost per requisition = Total Spend / 1,200 requisitions = INR 1,05,194
        self.assertEqual(costs["avg_cost_per_requisition_numeric"], 105194)

        # Active Requisitions = 463 open (NOT 1,200 total)
        self.assertEqual(kpis["active_requisitions"], 463)
        self.assertEqual(kpis["total_requisitions"], 1200)
        self.assertEqual(kpis["positions_remaining"], 730)
        self.assertEqual(kpis["total_positions_remaining"], 785)
        self.assertEqual(kpis["fill_rate_pct"], 67.3)
        self.assertEqual(kpis["active_pipeline_candidates"], 20000)

    # ---------------------------------------------------------
    # 3. Dynamic Date Calculation for Notice Periods
    # ---------------------------------------------------------
    def test_dynamic_notice_period_calculation(self):
        # As of snapshot date 2026-01-01
        res_jan = WorkforcePlanningService.filter_and_paginate_notice_employees(
            reference_date="2026-01-01", page=1, page_size=10
        )
        self.assertEqual(res_jan["total_records"], 2028)
        self.assertTrue(all(r["days_remaining"] >= 0 for r in res_jan["records"]))

        # As of 2026-06-01 (when all notice employees should have departed)
        res_jun = WorkforcePlanningService.filter_and_paginate_notice_employees(
            reference_date="2026-06-01", page=1, page_size=10
        )
        self.assertTrue(all(r["days_remaining"] <= 0 for r in res_jun["records"]))
        self.assertTrue(all(r["notice_status"] == "Notice Completed / Departed" for r in res_jun["records"]))

    # ---------------------------------------------------------
    # 4. Brand Identity & Rebranding
    # ---------------------------------------------------------
    def test_branding_identity_and_logo_placeholder(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        
        # Verify brand name
        self.assertIn("AttritionSense Technologies", html)
        self.assertIn("Detect Risks. Retain Talent.", html)
        # Verify replaceable logo image slot
        self.assertIn("attritionsense-technologies-logo.png", html)
        # Verify synthetic data notice
        self.assertIn("HR Decision-Support &amp; Synthetic Data Notice", html)

    # ---------------------------------------------------------
    # 5. AI Model Intelligence Dashboard Routes & APIs
    # ---------------------------------------------------------
    def test_ai_model_intelligence_pages_and_apis(self):
        # Both URLs work
        res1 = self.client.get("/model-quality")
        self.assertEqual(res1.status_code, 200)
        res2 = self.client.get("/ai-model-intelligence")
        self.assertEqual(res2.status_code, 200)

        # Supervised model summary API
        res_summary = self.client.get("/api/model-quality/summary")
        self.assertEqual(res_summary.status_code, 200)
        data = res_summary.get_json()
        self.assertTrue(data["success"])
        self.assertIn("evaluation", data)
        self.assertIn("dataset_summary", data)
        self.assertIn("data_quality_checks", data)
        
        # Check supervised models present
        models = [m["model_name"] for m in data["evaluation"]["model_comparison"]]
        self.assertIn("Random Forest", models)
        self.assertIn("Logistic Regression", models)
        self.assertIn("Gradient Boosting", models)
        self.assertIn("Decision Tree", models)
        self.assertIn("XGBoost", models)

        # Unsupervised 5-algorithm benchmark API
        res_bench = self.client.get("/api/segmentation/benchmark")
        self.assertEqual(res_bench.status_code, 200)
        bench_data = res_bench.get_json()
        self.assertTrue(bench_data["success"])
        candidates = [c["name"] for c in bench_data["data"]["candidates"]]
        self.assertIn("K-Means", candidates)
        self.assertIn("Agglomerative Clustering", candidates)
        self.assertIn("Gaussian Mixture Model (GMM)", candidates)
        self.assertIn("DBSCAN", candidates)
        self.assertIn("BIRCH", candidates)

        # K-evaluation curve API
        res_keval = self.client.get("/api/segmentation/k-evaluation")
        self.assertEqual(res_keval.status_code, 200)
        keval_data = res_keval.get_json()
        self.assertTrue(keval_data["success"])
        self.assertTrue(len(keval_data["data"]) >= 5)

    # ---------------------------------------------------------
    # 6. Reports & Data Exports
    # ---------------------------------------------------------
    def test_reports_page_and_export_generation(self):
        # Reports UI page
        res = self.client.get("/reports")
        self.assertEqual(res.status_code, 200)

        # Available reports directory
        res_avail = self.client.get("/api/reports/available")
        self.assertEqual(res_avail.status_code, 200)
        avail_data = res_avail.get_json()
        self.assertTrue(avail_data["success"])
        self.assertGreaterEqual(len(avail_data["reports"]), 6)

        # CSV Download
        res_csv = self.client.get("/api/reports/download?type=attrition_risk&format=csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, "text/csv")
        self.assertIn(b"Employee_ID", res_csv.data)

        # Excel Download
        res_xlsx = self.client.get("/api/reports/download?type=workforce_planning&format=xlsx")
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn(
            res_xlsx.mimetype,
            [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/octet-stream"
            ]
        )
        self.assertGreater(len(res_xlsx.data), 1000)

    # ---------------------------------------------------------
    # 7. Non-Technical HR Dashboard Check (Segmentation)
    # ---------------------------------------------------------
    def test_segmentation_hr_friendliness(self):
        res = self.client.get("/segmentation")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        
        # Verify technical benchmark table is NOT on the HR segmentation page
        self.assertNotIn("Run 5-Model Benchmark", html)
        self.assertNotIn("Candidate Algorithm", html)
        self.assertNotIn("Female Audit", html)
        # Verify action-oriented talent actions and distribution chart are present
        self.assertIn("Strategic HR Action", html)
        self.assertIn("Workforce Segment Distribution", html)

        # Verify API provides Recommended_Talent_Action contract field
        res_prof = self.client.get("/api/segmentation/profiles")
        self.assertEqual(res_prof.status_code, 200)
        prof_data = res_prof.get_json()
        self.assertTrue(prof_data["success"])
        self.assertIn("Recommended_Talent_Action", prof_data["data"][0])

    # ---------------------------------------------------------
    # 8. Targeted Audit Corrections Tests
    # ---------------------------------------------------------
    def test_ai_model_intelligence_multi_model_details(self):
        """Verifies multi-model evaluation details for all 5 algorithms."""
        res = self.client.get("/api/model-quality/summary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        ev = data["evaluation"]
        self.assertIn("model_details", ev)
        
        expected_models = ["Random Forest", "Logistic Regression", "Decision Tree", "Gradient Boosting", "XGBoost"]
        for m_name in expected_models:
            self.assertIn(m_name, ev["model_details"], f"Model {m_name} must have detailed metrics")
            m_info = ev["model_details"][m_name]
            self.assertIn("confusion_matrix", m_info)
            self.assertIn("roc_curve", m_info)
            self.assertIn("pr_curve", m_info)
            self.assertIn("feature_importance", m_info)
            self.assertGreater(len(m_info["feature_importance"]), 0)

    def test_segmentation_employee_names(self):
        """Verifies Employee Name column in cluster exploration contains genuine names, not Employee_ID."""
        res = self.client.get("/api/segmentation/employees?page=1&page_size=20")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        employees = data.get("records") or data.get("data")
        self.assertIsNotNone(employees)
        self.assertGreater(len(employees), 0)
        
        for emp in employees:
            self.assertIn("Employee_ID", emp)
            self.assertIn("Employee_Name", emp)
            # Employee_Name must not just be the Employee_ID
            self.assertNotEqual(emp["Employee_Name"], emp["Employee_ID"], "Employee_Name must not duplicate Employee_ID")
            self.assertTrue(len(emp["Employee_Name"]) > 0)

    def test_workforce_planning_headcount_separation(self):
        """Verifies active headcount (47,972) vs snapshot records (50,000) separation."""
        kpis = WorkforcePlanningService.get_summary_kpis()
        self.assertEqual(kpis["active_headcount"], 47972)
        self.assertEqual(kpis["total_snapshot_records"], 50000)
        self.assertEqual(kpis["employees_serving_notice"], 2028)
        self.assertEqual(kpis["expected_additional_exits"], 2694)
        self.assertEqual(kpis["confirmed_completed_departures"], 2779)
        self.assertEqual(kpis["projected_headcount"], 46008)
        self.assertEqual(kpis["remaining_staffing_gap"], 6230)

    def test_data_quality_kpis_and_domain_completeness(self):
        """Verifies HR Data Quality KPIs, domain completeness, and category counts."""
        res = self.client.get("/api/data-quality/summary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        s = data["summary"]

        self.assertEqual(s["total_records_audited"], 50000)
        self.assertEqual(s["unique_employees"], 50000)
        self.assertEqual(s["duplicate_employee_ids"], 0)
        self.assertEqual(s["missing_required_values"], 0)
        self.assertEqual(s["data_completeness_pct"], 100.0)
        self.assertEqual(s["data_quality_issues"], 0)
        self.assertEqual(s["records_requiring_review"], 0)

        # Domain completeness
        self.assertIn("domain_completeness", s)
        self.assertEqual(len(s["domain_completeness"]), 4)
        for d in s["domain_completeness"]:
            self.assertEqual(d["completeness_pct"], 100.0)

        # Checks by category
        self.assertIn("checks_by_category", s)
        self.assertGreaterEqual(len(s["checks_by_category"]), 4)


if __name__ == "__main__":
    unittest.main()
