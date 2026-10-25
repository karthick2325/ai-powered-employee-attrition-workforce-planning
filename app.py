"""
Workforce Intelligence — AI-Powered HR Analytics
Main Application Entry Point (Flask & WSGI)
"""
import os
import logging
from flask import Flask, jsonify, render_template

import config
from services.excel_service import ExcelService
from services.model_training_service import ModelTrainingService
from services.prediction_service import PredictionService

from routes.dashboard_routes import dashboard_bp
from routes.analytics_routes import analytics_bp
from routes.prediction_routes import prediction_bp
from routes.workforce_routes import workforce_bp
from routes.model_quality_routes import model_quality_bp
from routes.segmentation_routes import segmentation_bp
from routes.report_routes import report_bp
from routes.recruitment_routes import recruitment_bp
from routes.data_quality_routes import data_quality_bp
from routes.help_routes import help_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = config.SECRET_KEY

    # Register application blueprints across all 10 modules
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(workforce_bp)
    app.register_blueprint(segmentation_bp)
    app.register_blueprint(model_quality_bp)
    app.register_blueprint(recruitment_bp)
    app.register_blueprint(data_quality_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(help_bp)

    @app.route("/health")
    @app.route("/api/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "dataset_loaded": ExcelService.is_loaded(),
            "dataset_path": config.EXCEL_FILE_PATH,
            "snapshot_date": config.DATA_SNAPSHOT_DATE
        })

    @app.route("/api/refresh-data", methods=["POST"])
    def refresh_data():
        try:
            success = ExcelService.reload_data()
            if success:
                # Invalidate prediction cache
                PredictionService.get_predictions_df(force_recompute=True)
                # Invalidate segmentation cache
                from services.segmentation_service import SegmentationService
                SegmentationService.get_pipeline(k=getattr(config, "SEGMENTATION_DEFAULT_K", 5), force_refit=True)
                return jsonify({"success": True, "message": "Dataset successfully refreshed."})
            else:
                return jsonify({"success": False, "error": ExcelService.get_load_error()}), 500
        except Exception as e:
            logger.exception("Dataset refresh failed")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html", error=str(e)), 500

    # Initialize data and models on startup
    with app.app_context():
        logger.info("Initializing Workforce Intelligence data layer...")
        loaded = ExcelService.load_workbook()
        if loaded:
            logger.info("Checking model artifacts...")
            ModelTrainingService.load_artifacts_or_train()
            logger.info("Pre-warming prediction cache...")
            PredictionService.get_predictions_df()
            logger.info("Pre-warming workforce segmentation pipeline...")
            from services.segmentation_service import SegmentationService
            SegmentationService.get_pipeline(k=getattr(config, "SEGMENTATION_DEFAULT_K", 5))
            logger.info("Workforce Intelligence application ready.")
        else:
            logger.error("Initialization warning: %s", ExcelService.get_load_error())

    return app

# WSGI application handle for Gunicorn / production servers
app = create_app()
application = app

if __name__ == "__main__":
    logger.info("Starting development server on %s:%s...", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
