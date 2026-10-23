"""
Automated tests for filter functionality across Analytics, Prediction, and Workforce components.
Verifies that charts, KPIs, and tables update consistently when filters are applied.
"""
import unittest
from app import create_app
from services.excel_service import ExcelService
from services.analytics_service import AnalyticsService
from services.prediction_service import PredictionService
from services.model_training_service import ModelTrainingService

class TestFilterFunctionality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        ExcelService.load_workbook()

    def test_analytics_single_department_filter(self):
        """Test applying Department filter updates KPIs, charts, and table consistently."""
        dept = "Technology"
        
        # 1. KPIs
        res_kpi = self.client.get(f"/api/analytics/kpis?department={dept}")
        self.assertEqual(res_kpi.status_code, 200)
        kpis = res_kpi.get_json()["kpis"]
        self.assertLess(kpis["total_employees"], 50000)
        self.assertEqual(kpis["total_departments"], 1)

        # 2. Charts
        res_charts = self.client.get(f"/api/analytics/charts?department={dept}")
        self.assertEqual(res_charts.status_code, 200)
        charts = res_charts.get_json()["charts"]
        self.assertEqual(charts["headcount"]["departments"], [dept])
        self.assertEqual(charts["headcount"]["total"], kpis["total_employees"])
        self.assertEqual(sum(charts["headcount"]["values"]), kpis["total_employees"])
        self.assertEqual(charts["attrition_rate"]["departments"], [dept])
        self.assertEqual(charts["tenure"]["departments"], [dept])
        self.assertEqual(charts["satisfaction"]["departments"], [dept])
        self.assertEqual(charts["overtime"]["departments"], [dept])
        self.assertEqual(charts["training"]["departments"], [dept])

        # 3. Employee Table
        res_table = self.client.get(f"/api/analytics/employees?department={dept}")
        self.assertEqual(res_table.status_code, 200)
        table_data = res_table.get_json()
        self.assertEqual(table_data["total_records"], kpis["total_employees"])
        for rec in table_data["records"]:
            self.assertEqual(rec["department"], dept)

    def test_analytics_job_role_and_location_filters(self):
        """Test applying job_role and location filters together."""
        role = "Software Engineer"
        loc = "Bengaluru"

        # KPIs
        res_kpi = self.client.get(f"/api/analytics/kpis?job_role={role}&location={loc}")
        self.assertEqual(res_kpi.status_code, 200)
        kpis = res_kpi.get_json()["kpis"]
        self.assertGreater(kpis["total_employees"], 0)
        self.assertEqual(kpis["unique_job_roles"], 1)

        # Charts
        res_charts = self.client.get(f"/api/analytics/charts?job_role={role}&location={loc}")
        self.assertEqual(res_charts.status_code, 200)
        charts = res_charts.get_json()["charts"]
        self.assertEqual(charts["headcount"]["total"], kpis["total_employees"])

        # Table
        res_table = self.client.get(f"/api/analytics/employees?job_role={role}&location={loc}")
        self.assertEqual(res_table.status_code, 200)
        table_data = res_table.get_json()
        self.assertEqual(table_data["total_records"], kpis["total_employees"])
        for rec in table_data["records"]:
            self.assertEqual(rec["job_role"], role)
            self.assertEqual(rec["location"], loc)

    def test_analytics_multiple_simultaneous_filters(self):
        """Test department, job_role, job_level, location, employment_type, and tenure."""
        dept = "Sales"
        role = "Sales Analyst"
        level = "Junior"
        loc = "Chennai"
        emp_type = "Full-time"
        max_tenure = 200

        res_kpi = self.client.get(
            f"/api/analytics/kpis?department={dept}&job_role={role}&job_level={level}&location={loc}&employment_type={emp_type}&max_tenure={max_tenure}"
        )
        self.assertEqual(res_kpi.status_code, 200)
        kpis = res_kpi.get_json()["kpis"]
        self.assertGreater(kpis["total_employees"], 0)

        res_charts = self.client.get(
            f"/api/analytics/charts?department={dept}&job_role={role}&job_level={level}&location={loc}&employment_type={emp_type}&max_tenure={max_tenure}"
        )
        self.assertEqual(res_charts.status_code, 200)
        charts = res_charts.get_json()["charts"]

        res_table = self.client.get(
            f"/api/analytics/employees?department={dept}&job_role={role}&job_level={level}&location={loc}&employment_type={emp_type}&max_tenure={max_tenure}"
        )
        self.assertEqual(res_table.status_code, 200)
        table_data = res_table.get_json()

        self.assertEqual(kpis["total_employees"], charts["headcount"]["total"])
        self.assertEqual(kpis["total_employees"], table_data["total_records"])

    def test_analytics_reset_restores_original_data(self):
        """Test reset / calling with All restores total 50,000 employees and all depts."""
        res_kpi = self.client.get("/api/analytics/kpis?department=All&job_role=All&job_level=All&location=All&employment_type=All")
        kpis = res_kpi.get_json()["kpis"]
        self.assertEqual(kpis["total_employees"], 50000)

        res_charts = self.client.get("/api/analytics/charts?department=All")
        charts = res_charts.get_json()["charts"]
        self.assertEqual(charts["headcount"]["total"], 50000)
        self.assertEqual(sum(charts["headcount"]["values"]), 50000)

    def test_analytics_empty_result_graceful_handling(self):
        """Test that filters matching 0 records return empty structures gracefully without error."""
        res_kpi = self.client.get("/api/analytics/kpis?department=NonexistentDept")
        self.assertEqual(res_kpi.status_code, 200)
        kpis = res_kpi.get_json()["kpis"]
        self.assertEqual(kpis["total_employees"], 0)
        self.assertEqual(kpis["average_tenure_months"], 0.0)

        res_charts = self.client.get("/api/analytics/charts?department=NonexistentDept")
        self.assertEqual(res_charts.status_code, 200)
        charts = res_charts.get_json()["charts"]
        self.assertEqual(charts["headcount"]["total"], 0)
        self.assertEqual(charts["headcount"]["departments"], [])

    def test_prediction_single_filter(self):
        """Test applying Department filter to prediction KPIs, charts, and table."""
        dept = "Sales"
        
        # 1. KPIs
        res_kpi = self.client.get(f"/api/prediction/kpis?department={dept}")
        self.assertEqual(res_kpi.status_code, 200)
        kpis = res_kpi.get_json()["kpis"]
        self.assertLess(kpis["eligible_employees"], 47972)
        self.assertEqual(
            kpis["eligible_employees"],
            kpis["predicted_high_risk"] + kpis["predicted_medium_risk"] + kpis["predicted_low_risk"]
        )

        # 2. Risk Distribution Chart
        res_dist = self.client.get(f"/api/prediction/risk-distribution?department={dept}")
        self.assertEqual(res_dist.status_code, 200)
        dist = res_dist.get_json()["risk_distribution"]
        self.assertEqual(dist["total"], kpis["eligible_employees"])
        self.assertEqual(
            sum(c["count"] for c in dist["categories"]),
            kpis["eligible_employees"]
        )

        # 3. Department Risk Chart
        res_dept_risk = self.client.get(f"/api/prediction/department-risk?department={dept}")
        self.assertEqual(res_dept_risk.status_code, 200)
        dept_risk = res_dept_risk.get_json()["department_risk"]
        self.assertEqual(len(dept_risk), 1)
        self.assertEqual(dept_risk[0]["department"], dept)

        # 4. Predictions Table
        res_table = self.client.get(f"/api/prediction/employees?department={dept}")
        self.assertEqual(res_table.status_code, 200)
        table_data = res_table.get_json()
        self.assertEqual(table_data["total_records"], kpis["eligible_employees"])

    def test_prediction_multiple_filters(self):
        """Test Department, Job Role, and Risk Level filters applied together."""
        dept = "Technology"
        role = "Software Engineer"
        risk = "High"

        res_kpi = self.client.get(f"/api/prediction/kpis?department={dept}&job_role={role}&risk_level={risk}")
        self.assertEqual(res_kpi.status_code, 200)
        kpis = res_kpi.get_json()["kpis"]

        res_table = self.client.get(f"/api/prediction/employees?department={dept}&job_role={role}&risk_level={risk}")
        self.assertEqual(res_table.status_code, 200)
        table_data = res_table.get_json()

        self.assertEqual(kpis["eligible_employees"], table_data["total_records"])
        self.assertEqual(kpis["predicted_high_risk"], table_data["total_records"])
        self.assertEqual(kpis["predicted_medium_risk"], 0)
        self.assertEqual(kpis["predicted_low_risk"], 0)

        for rec in table_data["records"]:
            self.assertEqual(rec["department"], dept)
            self.assertEqual(rec["job_role"], role)
            self.assertEqual(rec["risk_level"], risk)

    def test_prediction_reset_restores_original_data(self):
        """Test resetting prediction filters returns full eligible cohort (47,972)."""
        res_kpi = self.client.get("/api/prediction/kpis?department=All&risk_level=All")
        kpis = res_kpi.get_json()["kpis"]
        self.assertEqual(kpis["eligible_employees"], 47972)

        res_dist = self.client.get("/api/prediction/risk-distribution?department=All")
        dist = res_dist.get_json()["risk_distribution"]
        self.assertEqual(dist["total"], 47972)

    def test_filtering_does_not_modify_evaluation_metrics_or_retrain(self):
        """Confirming that filtering does not retrain models or modify model evaluation metrics."""
        # Get baseline evaluation
        artifacts = ModelTrainingService.load_artifacts_or_train()
        original_rf = next(m for m in artifacts["model_comparison"] if m["model_name"] == "Random Forest")
        original_acc = original_rf["accuracy"]
        original_roc = original_rf["roc_auc"]

        # Apply several filters on analytics and prediction
        self.client.get("/api/analytics/kpis?department=Sales")
        self.client.get("/api/analytics/charts?department=Sales")
        self.client.get("/api/prediction/kpis?department=Technology&risk_level=High")
        self.client.get("/api/prediction/department-risk?department=Technology")

        # Check model evaluation endpoint
        res_eval = self.client.get("/api/model-quality/summary")
        self.assertEqual(res_eval.status_code, 200)
        eval_data = res_eval.get_json()["evaluation"]
        rf_after = next(m for m in eval_data["model_comparison"] if m["model_name"] == "Random Forest")

        self.assertEqual(rf_after["accuracy"], original_acc)
        self.assertEqual(rf_after["roc_auc"], original_roc)

    def test_search_and_pagination_preserved(self):
        """Verify search query filters down records and pagination slices correctly."""
        # Search by ID
        res = self.client.get("/api/analytics/employees?search=EMP000001")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data["total_records"], 1)
        self.assertEqual(data["records"][0]["employee_id"], "EMP000001")

        # Pagination: Page 2 with page_size=5
        res_p2 = self.client.get("/api/analytics/employees?page=2&page_size=5")
        self.assertEqual(res_p2.status_code, 200)
        data_p2 = res_p2.get_json()
        self.assertEqual(data_p2["page"], 2)
        self.assertEqual(len(data_p2["records"]), 5)

if __name__ == "__main__":
    unittest.main()
