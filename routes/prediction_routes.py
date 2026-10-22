"""
Workforce Intelligence — Prediction Routes
Route and API endpoints for Page 3: AI Attrition Prediction.
"""
from flask import Blueprint, render_template, request, jsonify
from services.prediction_service import PredictionService
from services.model_training_service import ModelTrainingService
import config

prediction_bp = Blueprint("prediction", __name__)

@prediction_bp.route("/prediction")
def prediction_page():
    return render_template(
        "prediction.html",
        active_page="prediction",
        page_title="AI Attrition Prediction",
        page_subtitle="Predict next 6 months attrition risk and take proactive actions",
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )

@prediction_bp.route("/api/prediction/kpis")
def get_prediction_kpis():
    kpis = PredictionService.get_prediction_kpis()
    return jsonify({"success": True, "kpis": kpis})

@prediction_bp.route("/api/prediction/employees")
def get_predicted_employees():
    department = request.args.get("department")
    job_role = request.args.get("job_role")
    job_level = request.args.get("job_level")
    location = request.args.get("location")
    risk_level = request.args.get("risk_level")
    search_query = request.args.get("search")

    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=10, type=int)
    sort_by = request.args.get("sort_by", default="Risk_Probability")
    ascending = request.args.get("ascending", default="false").lower() == "true"

    result = PredictionService.filter_and_paginate_predictions(
        department=department,
        job_role=job_role,
        job_level=job_level,
        location=location,
        risk_level=risk_level,
        search_query=search_query,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        ascending=ascending
    )

    return jsonify({"success": True, **result})

@prediction_bp.route("/api/prediction/employee/<emp_id>")
def get_employee_prediction_detail(emp_id):
    detail = PredictionService.get_employee_detail(emp_id)
    if detail is None:
        return jsonify({"success": False, "error": f"Employee {emp_id} not found"}), 404
    return jsonify({"success": True, "employee": detail})

@prediction_bp.route("/api/prediction/risk-distribution")
def get_risk_distribution():
    dist = PredictionService.get_risk_distribution()
    return jsonify({"success": True, "risk_distribution": dist})

@prediction_bp.route("/api/prediction/department-risk")
def get_department_risk():
    dept_risk = PredictionService.get_department_average_risk()
    return jsonify({"success": True, "department_risk": dept_risk})

@prediction_bp.route("/api/prediction/feature-importance")
def get_feature_importance():
    artifacts = ModelTrainingService.load_artifacts_or_train()
    importance = artifacts.get("feature_importance", [])
    return jsonify({"success": True, "feature_importance": importance[:8]})
