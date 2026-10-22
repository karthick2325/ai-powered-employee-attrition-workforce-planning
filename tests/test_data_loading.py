"""
Unit tests for Excel data loading and schema integrity.
"""
import unittest
from services.excel_service import ExcelService
import config

class TestDataLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loaded = ExcelService.load_workbook()

    def test_workbook_loaded_successfully(self):
        self.assertTrue(self.loaded, "Failed to load Excel workbook")
        self.assertTrue(ExcelService.is_loaded(), "ExcelService reports not loaded")

    def test_required_sheets_present(self):
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
        for s in sheets:
            df = ExcelService.get_sheet(s)
            self.assertIsNotNone(df, f"Sheet '{s}' missing or None")
            self.assertGreater(len(df), 0, f"Sheet '{s}' is empty")

    def test_employees_row_count(self):
        emp_df = ExcelService.get_sheet("Employees")
        self.assertEqual(len(emp_df), 50000, "Employees sheet count mismatch")

    def test_attrition_outcomes_row_count(self):
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")
        self.assertEqual(len(outcomes_df), 47972, "Attrition outcomes count mismatch")

    def test_notice_period_row_count(self):
        notice_df = ExcelService.get_sheet("Notice_Period")
        self.assertEqual(len(notice_df), 2028, "Notice period count mismatch")

if __name__ == "__main__":
    unittest.main()
