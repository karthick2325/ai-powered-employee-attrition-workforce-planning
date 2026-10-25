"""
Workforce Intelligence — Recruitment & Training Routes
Route and API endpoints for Recruitment Funnel, Costs, and Training Analytics.
"""
from flask import Blueprint, render_template, jsonify
from services.recruitment_service import RecruitmentService
from services.excel_service import ExcelService
import config

recruitment_bp = Blueprint("recruitment", __name__)


@recruitment_bp.route("/recruitment-training")
def recruitment_page():
    return render_template(
        "recruitment_training.html",
        active_page="recruitment",
        page_title="Recruitment & Training Analytics",
        page_subtitle="Talent acquisition pipeline, verified cost breakdown, and learning hours",
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )


@recruitment_bp.route("/api/recruitment/kpis")
def get_recruitment_kpis():
    data = RecruitmentService.get_recruitment_kpis()
    return jsonify({"success": True, "kpis": data})


@recruitment_bp.route("/api/recruitment/funnel")
def get_recruitment_funnel():
    data = RecruitmentService.get_candidate_funnel()
    return jsonify({"success": True, "funnel": data})


@recruitment_bp.route("/api/recruitment/costs")
def get_recruitment_costs():
    data = RecruitmentService.get_recruitment_costs()
    return jsonify({"success": True, "costs": data})


@recruitment_bp.route("/api/recruitment/training")
def get_training_analytics():
    data = RecruitmentService.get_training_analytics()
    return jsonify({"success": True, "training": data})


@recruitment_bp.route("/api/recruitment/hiring-by-department")
def get_hiring_by_department():
    data = RecruitmentService.get_department_hiring_performance()
    return jsonify({"success": True, "hiring": data})


@recruitment_bp.route("/api/recruitment/requisitions")
def get_requisitions_table():
    req_df = ExcelService.get_sheet("Job_Requisitions")
    records = req_df.to_dict(orient="records")
    return jsonify({"success": True, "requisitions": records[:100], "total": len(records)})
