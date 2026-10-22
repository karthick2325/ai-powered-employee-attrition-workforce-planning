"""
Unit tests for workforce planning calculations and scenario logic.
"""
import unittest
from services.excel_service import ExcelService
from services.workforce_planning_service import WorkforcePlanningService

class TestWorkforcePlanning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()

    def test_summary_kpis(self):
        kpis = WorkforcePlanningService.get_summary_kpis()
        self.assertEqual(kpis["current_headcount"], 50000)
        self.assertEqual(kpis["employees_serving_notice"], 2028)
        self.assertGreater(kpis["expected_additional_exits"], 0)
        self.assertGreater(kpis["target_headcount"], 0)

    def test_scenario_calculation(self):
        calc = WorkforcePlanningService.calculate_scenario(
            current_headcount=50000,
            expected_additional_exits=3412,
            open_positions_to_fill=1200,
            target_headcount=55000
        )
        # Projected = 50000 - 2028 - 3412 + 1200 = 45760
        # Gap = max(0, 55000 - 45760) = 9240
        self.assertEqual(calc["projected_available_staff"], 50000 - 2028 - 3412 + 1200)
        self.assertEqual(calc["new_staffing_gap"], max(0, 55000 - (50000 - 2028 - 3412 + 1200)))

if __name__ == "__main__":
    unittest.main()
