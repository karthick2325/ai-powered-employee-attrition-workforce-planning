"""
Workforce Intelligence — Data Quality & Integrity Routes
Blueprint for Page: Data Quality & Governance Audit.
"""
from flask import Blueprint, render_template, jsonify
from services.data_validation_service import DataValidationService
from services.excel_service import ExcelService
import config

data_quality_bp = Blueprint("data_quality", __name__)


@data_quality_bp.route("/data-quality")
def data_quality_page():
    return render_template(
        "data_quality.html",
        active_page="data_quality",
        page_title="Data Quality & Governance Audit",
        page_subtitle="12 automated integrity checks, referential key verification, and population audit",
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )


@data_quality_bp.route("/api/data-quality/summary")
def get_data_quality_summary():
    summary = DataValidationService.get_quality_summary()
    return jsonify({"success": True, "summary": summary})


@data_quality_bp.route("/api/data-quality/checks")
def get_data_quality_checks():
    checks = DataValidationService.run_all_checks()
    return jsonify({"success": True, "checks": checks})


@data_quality_bp.route("/api/data-quality/excluded")
def get_excluded_population():
    data = DataValidationService.get_excluded_population_report()
    return jsonify({"success": True, "excluded": data})


@data_quality_bp.route("/api/data-quality/sheets")
def get_sheets_inventory():
    summary = ExcelService.get_dataset_summary()
    return jsonify({"success": True, "sheets": summary})
