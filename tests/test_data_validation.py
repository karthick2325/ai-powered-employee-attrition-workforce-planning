"""
Unit tests for data quality and integrity checks.
"""
import unittest
from services.excel_service import ExcelService
from services.data_validation_service import DataValidationService

class TestDataValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()

    def test_run_all_checks(self):
        checks = DataValidationService.run_all_checks()
        self.assertGreaterEqual(len(checks), 8, "Expected at least 8 validation checks")

        for c in checks:
            self.assertIn("check_type", c)
            self.assertIn("status", c)
            self.assertIn("result", c)
            # Ensure no check failed
            self.assertNotEqual(c["status"], "FAIL", f"Check '{c['check_type']}' failed: {c['details']}")

    def test_referential_integrity(self):
        emp_df = ExcelService.get_sheet("Employees")
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")
        notice_df = ExcelService.get_sheet("Notice_Period")

        emp_ids = set(emp_df["Employee_ID"])
        notice_ids = set(notice_df["Employee_ID"])
        outcome_ids = set(outcomes_df["Employee_ID"])

        # All notice employees must exist in master
        self.assertTrue(notice_ids.issubset(emp_ids), "Notice IDs missing from Employees master")
        # All outcome employees must exist in master
        self.assertTrue(outcome_ids.issubset(emp_ids), "Outcome IDs missing from Employees master")
        # Outcome set and notice set must be mutually disjoint
        self.assertEqual(len(notice_ids.intersection(outcome_ids)), 0, "Notice employees must not overlap with eligible outcomes")

if __name__ == "__main__":
    unittest.main()
