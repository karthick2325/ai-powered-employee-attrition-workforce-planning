"""
Workforce Intelligence — Workforce Planning Routes
Route and API endpoints for Page 4: Workforce Planning & Exit Analysis.
"""
from flask import Blueprint, render_template, request, jsonify
from services.workforce_planning_service import WorkforcePlanningService
import config

workforce_bp = Blueprint("workforce", __name__)


@workforce_bp.route("/workforce")
def workforce_page():
    return render_template(
        "workforce.html",
        active_page="workforce",
        page_title="Workforce Planning & Exit Analysis",
        page_subtitle="Plan future staffing, track notice period exits and identify hiring requirements",
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )


@workforce_bp.route("/api/workforce/kpis")
def get_workforce_kpis():
    kpis = WorkforcePlanningService.get_summary_kpis()
    return jsonify({"success": True, "kpis": kpis})


@workforce_bp.route("/api/workforce/headcount-analysis")
def get_headcount_analysis():
    data = WorkforcePlanningService.get_headcount_analysis_by_department()
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/expected-exits-breakdown")
def get_expected_exits_breakdown():
    data = WorkforcePlanningService.get_expected_exits_breakdown()
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/monthly-exits")
def get_monthly_exits():
    data = WorkforcePlanningService.get_monthly_expected_exits()
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/department-table")
def get_department_table():
    data = WorkforcePlanningService.get_department_exit_analysis_table()
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/role-gaps")
def get_role_gaps():
    data = WorkforcePlanningService.get_role_staffing_gap_analysis()
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/open-requisitions")
def get_open_requisitions():
    data = WorkforcePlanningService.get_open_requisitions_by_department()
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/notice-distribution")
def get_notice_distribution():
    ref_date = request.args.get("reference_date", default="2026-01-01")
    data = WorkforcePlanningService.get_notice_period_distribution(reference_date=ref_date)
    return jsonify({"success": True, "data": data})


@workforce_bp.route("/api/workforce/notice-employees")
def get_notice_employees():
    search = request.args.get("search")
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=10, type=int)
    ref_date = request.args.get("reference_date", default="2026-01-01")
    
    result = WorkforcePlanningService.filter_and_paginate_notice_employees(
        search_query=search,
        page=page,
        page_size=page_size,
        reference_date=ref_date
    )
    return jsonify({"success": True, **result})


@workforce_bp.route("/api/workforce/scenario-planner", methods=["POST"])
def post_scenario_planner():
    data = request.get_json(silent=True) or {}
    current = int(data.get("current_headcount", 50000))
    additional_exits = int(data.get("expected_additional_exits", 3412))
    open_to_fill = int(data.get("open_positions_to_fill", 1200))
    target = int(data.get("target_headcount", 55000))
    retention_pct = float(data.get("retention_success_pct", 0.0))

    calc = WorkforcePlanningService.calculate_scenario(
        current_headcount=current,
        expected_additional_exits=additional_exits,
        open_positions_to_fill=open_to_fill,
        target_headcount=target,
        retention_success_pct=retention_pct
    )
    return jsonify({"success": True, **calc})


@workforce_bp.route("/api/workforce/insights")
def get_workforce_insights():
    insights = WorkforcePlanningService.get_quick_insights()
    return jsonify({"success": True, "insights": insights})
