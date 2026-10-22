"""
Unit tests for model training, metrics, and persistence.
"""
import unittest
import os
from services.excel_service import ExcelService
from services.model_training_service import ModelTrainingService
import config

class TestModelTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ExcelService.load_workbook()

    def test_artifacts_exist_or_train(self):
        artifacts = ModelTrainingService.load_artifacts_or_train()
        self.assertIsNotNone(artifacts)
        self.assertIn("model_comparison", artifacts)
        self.assertIn("selected_model", artifacts)
        self.assertIn("confusion_matrix", artifacts)
        self.assertIn("roc_curve", artifacts)
        self.assertIn("pr_curve", artifacts)
        self.assertIn("feature_importance", artifacts)

    def test_five_models_evaluated(self):
        artifacts = ModelTrainingService.load_artifacts_or_train()
        comparison = artifacts["model_comparison"]
        self.assertEqual(len(comparison), 5, "Expected all 5 candidate models in comparison")
        model_names = [m["model_name"] for m in comparison]
        self.assertIn("Logistic Regression", model_names)
        self.assertIn("Decision Tree", model_names)
        self.assertIn("Random Forest", model_names)
        self.assertIn("Gradient Boosting", model_names)
        self.assertIn("XGBoost", model_names)

    def test_held_out_metrics_valid(self):
        artifacts = ModelTrainingService.load_artifacts_or_train()
        for m in artifacts["model_comparison"]:
            self.assertGreater(m["accuracy"], 0.5, f"Accuracy too low for {m['model_name']}")
            self.assertGreater(m["roc_auc"], 0.5, f"ROC-AUC too low for {m['model_name']}")

if __name__ == "__main__":
    unittest.main()
