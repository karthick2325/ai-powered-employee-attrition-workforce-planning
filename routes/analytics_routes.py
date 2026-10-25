"""
Workforce Intelligence — Analytics Routes
Route and API endpoints for Page 2: Employee & Department Analytics.
"""
from flask import Blueprint, render_template, request, jsonify
from services.analytics_service import AnalyticsService
import config

analytics_bp = Blueprint("analytics", __name__)


def _analytics_filters():
    return {
        "department": request.args.get("department"),
        "job_role": request.args.get("job_role"),
        "job_level": request.args.get("job_level"),
        "location": request.args.get("location"),
        "employment_type": request.args.get("employment_type"),
        "min_tenure": request.args.get("min_tenure", type=int),
        "max_tenure": request.args.get("max_tenure", type=int),
    }


@analytics_bp.route("/analytics")
def analytics_page():
    return render_template(
        "analytics.html",
        active_page="analytics",
        page_title="Employee & Department Analytics",
        page_subtitle="Explore employee details, department trends and key workforce metrics",
        snapshot_date=config.DATA_SNAPSHOT_DATE,
    )


@analytics_bp.route("/api/analytics/kpis")
def get_analytics_kpis():
    return jsonify({"success": True, "kpis": AnalyticsService.get_kpis(**_analytics_filters())})


@analytics_bp.route("/api/analytics/charts")
def get_analytics_charts():
    charts = AnalyticsService.get_department_charts_data(**_analytics_filters())
    return jsonify({"success": True, "charts": charts})


@analytics_bp.route("/api/analytics/filters")
def get_filter_options():
    return jsonify({"success": True, "filters": AnalyticsService.get_filter_options()})


@analytics_bp.route("/api/analytics/employees")
def get_employees_table():
    filters = _analytics_filters()
    result = AnalyticsService.filter_and_paginate_employees(
        department=filters["department"],
        job_role=filters["job_role"],
        job_level=filters["job_level"],
        location=filters["location"],
        employment_type=filters["employment_type"],
        min_tenure=filters["min_tenure"],
        max_tenure=filters["max_tenure"],
        search_query=request.args.get("search"),
        page=request.args.get("page", default=1, type=int),
        page_size=request.args.get("page_size", default=10, type=int),
        sort_by=request.args.get("sort_by", default="Employee_ID"),
        ascending=request.args.get("ascending", default="true").lower() == "true",
    )
    return jsonify({"success": True, **result})


@analytics_bp.route("/api/analytics/compare")
def compare_departments():
    dept1 = request.args.get("dept1", "Technology")
    dept2 = request.args.get("dept2", "Sales")
    comparison = AnalyticsService.compare_departments(dept1, dept2)
    return jsonify({"success": True, "comparison": comparison})
