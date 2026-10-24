"""
Workforce Intelligence — Reports & Exports Routes
Blueprint for Page: Reports & Exports Center.
Provides verified, formatted Excel and CSV exports with preview and filter controls.
"""

import logging
from flask import Blueprint, render_template, request, Response, jsonify
from services.export_service import ExportService
from services.excel_service import ExcelService
import config

logger = logging.getLogger(__name__)

report_bp = Blueprint("reports", __name__)


@report_bp.route("/reports")
def reports_page():
    """Renders the Reports & Exports Management Center."""
    departments = []
    if ExcelService.is_loaded():
        emp_df = ExcelService.get_sheet("Employees")
        departments = sorted(emp_df["Department"].dropna().unique().tolist())

    return render_template(
        "reports.html",
        active_page="reports",
        page_title="Reports & Exports Center",
        page_subtitle="Generate verified enterprise CSV and multi-sheet Excel analytical reports",
        departments=departments,
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )


@report_bp.route("/api/reports/download")
def download_report():
    """Universal export handler for all report types and formats."""
    try:
        report_type = request.args.get("type", "attrition_risk").lower()
        export_format = request.args.get("format", "xlsx").lower()

        # Optional filters
        department = request.args.get("department")
        job_role = request.args.get("job_role")
        risk_level = request.args.get("risk_level")
        k = request.args.get("k", type=int)

        if report_type == "attrition_risk":
            content, mimetype, filename = ExportService.export_attrition_risk_report(
                export_format=export_format,
                department=department,
                job_role=job_role,
                risk_level=risk_level
            )
        elif report_type in ("workforce_segmentation", "segmentation"):
            content, mimetype, filename = ExportService.export_segmentation_report(
                k=k,
                export_format=export_format
            )
        elif report_type in ("clustering_benchmark", "benchmark", "model_benchmark"):
            content, mimetype, filename = ExportService.export_clustering_benchmark_report(
                k=k,
                export_format=export_format
            )
        elif report_type in ("workforce_planning", "planning"):
            content, mimetype, filename = ExportService.export_workforce_planning_report(
                export_format=export_format
            )
        elif report_type in ("data_quality", "quality"):
            content, mimetype, filename = ExportService.export_data_quality_report(
                export_format=export_format
            )
        elif report_type in ("recruitment_training", "recruitment"):
            content, mimetype, filename = ExportService.export_recruitment_training_report(
                export_format=export_format
            )
        else:
            return jsonify({"success": False, "error": f"Unknown report type: {report_type}"}), 400

        response = Response(content, mimetype=mimetype)
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.exception("Error generating report export")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route("/api/reports/available")
def get_available_reports():
    """Returns directory of available export reports with descriptions and sheet structures."""
    return jsonify({
        "success": True,
        "reports": [
            {
                "id": "attrition_risk",
                "title": "Employee Attrition Risk Assessment",
                "description": "Risk probability scores, contributing factors, and retention actions for active employees.",
                "supported_formats": ["xlsx", "csv"],
                "default_format": "xlsx",
                "sheets": ["README_Metadata", "Executive_Summary", "Employee_Risk_Scores"],
                "records_scope": "Eligible Active Non-Notice Cohort (47,972 Records)"
            },
            {
                "id": "workforce_segmentation",
                "title": "Workforce Segmentation & Profiles",
                "description": "Segment archetypes, cluster profiles, job role staffing pressure, and pay/workload anomalies.",
                "supported_formats": ["xlsx", "csv"],
                "default_format": "xlsx",
                "sheets": ["README_Metadata", "Segment_Archetype_Profiles", "Job_Role_Staffing_Pressure", "Workload_Pay_Anomalies"],
                "records_scope": "Clustered Active Cohort (K = 5 Archetypes)"
            },
            {
                "id": "clustering_benchmark",
                "title": "5-Algorithm Unsupervised Clustering Benchmark",
                "description": "Comparative benchmark of K-Means, Agglomerative, GMM, DBSCAN, and BIRCH with validation metrics.",
                "supported_formats": ["xlsx", "csv"],
                "default_format": "xlsx",
                "sheets": ["README_Metadata", "Benchmark_Comparison"],
                "records_scope": "5 Evaluated Machine Learning Clustering Algorithms"
            },
            {
                "id": "workforce_planning",
                "title": "Workforce Planning & Exit Analysis",
                "description": "Confirmed notice period departures, target headcount gaps, and role-level staffing pressure.",
                "supported_formats": ["xlsx", "csv"],
                "default_format": "xlsx",
                "sheets": ["README_Metadata", "Department_Headcount_Gaps", "Role_Staffing_Pressure"],
                "records_scope": "8 Departments and 26 Job Roles"
            },
            {
                "id": "data_quality",
                "title": "Automated Data Quality & Governance Audit",
                "description": "12 automated integrity audits, referential key verification, and population reconciliation.",
                "supported_formats": ["xlsx", "csv"],
                "default_format": "xlsx",
                "sheets": ["README_Metadata", "Quality_Checks"],
                "records_scope": "Full Multi-Sheet Workbook Health Audit"
            },
            {
                "id": "recruitment_training",
                "title": "Recruitment Funnel & Training Analytics",
                "description": "Requisitions, cost breakdown in INR, candidate pipeline stages, and employee training hours.",
                "supported_formats": ["xlsx", "csv"],
                "default_format": "xlsx",
                "sheets": ["README_Metadata", "Job_Requisitions", "Recruitment_Costs", "Department_Training_Hours"],
                "records_scope": "1,200 Requisitions and 20,000 Pipeline Candidates"
            }
        ]
    })
