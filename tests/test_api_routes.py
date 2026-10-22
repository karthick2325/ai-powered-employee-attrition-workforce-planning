"""
Integration tests for Flask API and frontend routes.
"""
import unittest
from app import create_app

class TestApiRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_all_five_dashboard_pages(self):
        pages = ["/", "/analytics", "/prediction", "/workforce", "/model-quality"]
        for p in pages:
            res = self.client.get(p)
            self.assertEqual(res.status_code, 200, f"Page {p} returned {res.status_code}")

    def test_overview_api(self):
        res = self.client.get("/api/dashboard/overview")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["kpis"]["total_employees"], 50000)

    def test_prediction_api(self):
        res = self.client.get("/api/prediction/kpis")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["kpis"]["eligible_employees"], 47972)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

if __name__ == "__main__":
    unittest.main()
