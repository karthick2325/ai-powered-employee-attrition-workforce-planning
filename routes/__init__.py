"""
Routes package initialization.
"""
from routes.dashboard_routes import dashboard_bp
from routes.analytics_routes import analytics_bp
from routes.prediction_routes import prediction_bp
from routes.workforce_routes import workforce_bp
from routes.model_quality_routes import model_quality_bp
from routes.segmentation_routes import segmentation_bp

__all__ = [
    "dashboard_bp",
    "analytics_bp",
    "prediction_bp",
    "workforce_bp",
    "model_quality_bp",
    "segmentation_bp"
]
