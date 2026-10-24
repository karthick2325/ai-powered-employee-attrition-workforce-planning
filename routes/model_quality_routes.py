"""
Workforce Intelligence — Model Performance & Data Quality Routes
Route and API endpoints for Page 5: Model Performance & Data Quality.
"""
import logging
from flask import Blueprint, render_template, jsonify
from services.excel_service import ExcelService
from services.data_validation_service import DataValidationService
from services.model_training_service import ModelTrainingService
from services.prediction_service import PredictionService
import config

logger = logging.getLogger(__name__)

model_quality_bp = Blueprint("model_quality", __name__)

@model_quality_bp.route("/model-quality")
@model_quality_bp.route("/ai-model-intelligence")
def model_quality_page():
    return render_template(
        "model_quality.html",
        active_page="model_quality",
        page_title="AI Model Intelligence",
        page_subtitle="Comprehensive supervised attrition models & unsupervised workforce segmentation benchmarks",
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )

@model_quality_bp.route("/api/model-quality/summary")
def get_model_quality_summary():
    try:
        # Load or train evaluation artifacts
        artifacts = ModelTrainingService.load_artifacts_or_train()
        
        # Dataset summary from loaded sheets
        dataset_summary = ExcelService.get_dataset_summary()

        # Data quality checks
        quality_checks = DataValidationService.run_all_checks()

        # Model information
        model_info = {
            "selected_model": "Random Forest Classifier",
            "target_column": "Attrition_Within_6M",
            "prediction_horizon": "6 Months",
            "training_records": artifacts.get("training_records", 38377),
            "test_records": artifacts.get("test_records", 9595),
            "training_date": config.DATA_SNAPSHOT_DATE,
            "model_version": artifacts.get("model_version", "v1.0"),
            "key_features": "Overtime, Satisfaction, Work-Life Balance, Tenure, Training, Job Level, Department",
            "notes": "Synthetic dataset for demonstration only. Not for real HR decision-making."
        }

        return jsonify({
            "success": True,
            "evaluation": artifacts,
            "dataset_summary": dataset_summary,
            "data_quality_checks": quality_checks,
            "model_info": model_info
        })
    except Exception as e:
        logger.exception("Failed to load model quality summary")
        return jsonify({"success": False, "error": str(e)}), 500

@model_quality_bp.route("/api/model-quality/retrain", methods=["POST"])
def retrain_models():
    try:
        logger.info("Retraining models requested via API...")
        results = ModelTrainingService.train_and_evaluate_all()
        # Force recomputing cached predictions
        PredictionService.get_predictions_df(force_recompute=True)
        return jsonify({
            "success": True,
            "message": "Models successfully retrained and evaluation artifacts updated.",
            "evaluation": results
        })
    except Exception as e:
        logger.exception("Model retraining failed")
        return jsonify({"success": False, "error": str(e)}), 500
