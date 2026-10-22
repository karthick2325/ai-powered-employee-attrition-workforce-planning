"""
Unit tests for analytics calculations and department metrics.
"""
import unittest
from services.excel_service import ExcelService
from services.analytics_service import AnalyticsService

class TestAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()

    def test_kpis_calculation(self):
        kpis = AnalyticsService.get_kpis()
        self.assertEqual(kpis["total_employees"], 50000)
        self.assertGreater(kpis["total_departments"], 0)
        self.assertGreater(kpis["unique_job_roles"], 0)
        self.assertGreater(kpis["average_tenure_months"], 0)
        self.assertGreater(kpis["average_job_satisfaction"], 0)

    def test_department_charts_data(self):
        charts = AnalyticsService.get_department_charts_data()
        self.assertIn("headcount", charts)
        self.assertIn("attrition_rate", charts)
        self.assertIn("tenure", charts)
        self.assertIn("satisfaction", charts)
        self.assertIn("overtime", charts)
        self.assertIn("training", charts)

        # Headcount total must equal 50000
        self.assertEqual(sum(charts["headcount"]["values"]), 50000)

    def test_department_comparison(self):
        res = AnalyticsService.compare_departments("Technology", "Sales")
        self.assertIn("dept1", res)
        self.assertIn("dept2", res)
        self.assertEqual(res["dept1"]["name"], "Technology")
        self.assertEqual(res["dept2"]["name"], "Sales")
        self.assertIn("headcount", res["dept1"]["metrics"])

if __name__ == "__main__":
    unittest.main()
