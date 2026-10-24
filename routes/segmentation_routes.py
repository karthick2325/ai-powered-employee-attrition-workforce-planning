"""
Workforce Intelligence — Segmentation Routes
Blueprint for unsupervised workforce segmentation, 5-algorithm benchmark,
2D PCA projection, role staffing pressure, workload/pay anomalies, and export endpoints.
"""

import logging
from flask import Blueprint, render_template, jsonify, request, Response
from services.segmentation_service import SegmentationService
from services.excel_service import ExcelService
import config

logger = logging.getLogger(__name__)

segmentation_bp = Blueprint("segmentation_bp", __name__)


@segmentation_bp.route("/segmentation")
def segmentation_page():
    """Renders the Workforce Segmentation & Talent Intelligence page."""
    departments = []
    if ExcelService.is_loaded():
        emp_df = ExcelService.get_sheet("Employees")
        departments = sorted(emp_df["Department"].dropna().unique().tolist())

    return render_template(
        "segmentation.html",
        active_page="segmentation",
        page_title="Workforce Segmentation & Talent Intelligence",
        page_subtitle="5-Algorithm Unsupervised Benchmark, PCA Projection, and Archetype Profiling",
        departments=departments,
        current_date=config.DATA_SNAPSHOT_DATE,
        disclaimer=config.DISCLAIMER_TEXT
    )


@segmentation_bp.route("/api/segmentation/overview")
def api_segmentation_overview():
    """Returns top KPI summary for the segmentation dashboard."""
    try:
        k = request.args.get("k", type=int)
        data = SegmentationService.get_overview_kpis(k=k)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.exception("Error in /api/segmentation/overview")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/benchmark")
def api_segmentation_benchmark():
    """Returns the comprehensive 5-algorithm unsupervised clustering benchmark."""
    try:
        k = request.args.get("k", type=int)
        benchmark = SegmentationService.get_five_algorithm_benchmark(k=k)
        return jsonify({"success": True, "data": benchmark})
    except Exception as e:
        logger.exception("Error in /api/segmentation/benchmark")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/pca")
def api_segmentation_pca():
    """Returns 2D PCA projection coordinates with explained variance."""
    try:
        pca_data = SegmentationService.get_pca_projection()
        return jsonify({"success": True, "data": pca_data})
    except Exception as e:
        logger.exception("Error in /api/segmentation/pca")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/profiles")
def api_segmentation_profiles():
    """Returns detailed profiles of workforce clusters."""
    try:
        k = request.args.get("k", type=int)
        profiles = SegmentationService.get_segment_profiles_data(k=k)
        return jsonify({"success": True, "data": profiles})
    except Exception as e:
        logger.exception("Error in /api/segmentation/profiles")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/employees")
def api_segmentation_employees():
    """Returns paginated list of employee cluster assignments."""
    try:
        seg_id = request.args.get("segment_id", type=int)
        dept = request.args.get("department")
        role = request.args.get("job_role")
        search = request.args.get("search")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)

        data = SegmentationService.get_segmented_employees(
            segment_id=seg_id,
            department=dept,
            job_role=role,
            search=search,
            page=page,
            page_size=page_size
        )
        return jsonify({"success": True, **data})
    except Exception as e:
        logger.exception("Error in /api/segmentation/employees")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/k-evaluation")
def api_segmentation_k_evaluation():
    """Returns evaluation scores across candidate K values."""
    try:
        eval_data = SegmentationService.get_k_evaluation_data()
        return jsonify({"success": True, "data": eval_data})
    except Exception as e:
        logger.exception("Error in /api/segmentation/k-evaluation")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/role-pressure")
def api_segmentation_role_pressure():
    """Returns role staffing pressure segmentation."""
    try:
        dept = request.args.get("department")
        tier = request.args.get("pressure_tier")
        roles = SegmentationService.get_role_pressure_data(department=dept, pressure_tier=tier)
        return jsonify({"success": True, "data": roles})
    except Exception as e:
        logger.exception("Error in /api/segmentation/role-pressure")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/anomalies")
def api_segmentation_anomalies():
    """Returns paginated list of workload and compensation anomalies."""
    try:
        q = request.args.get("q")
        anom_type = request.args.get("type")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)

        result = SegmentationService.get_anomalies_data(
            search_query=q,
            anomaly_type=anom_type,
            page=page,
            page_size=page_size
        )
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.exception("Error in /api/segmentation/anomalies")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/refit", methods=["POST"])
def api_segmentation_refit():
    """Reclusters the workforce with a newly requested K value."""
    try:
        payload = request.get_json(silent=True) or {}
        k = int(payload.get("k", 5))
        result = SegmentationService.refit_k(k=k)
        return jsonify(result)
    except Exception as e:
        logger.exception("Error in /api/segmentation/refit")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/export")
def api_segmentation_export():
    """Exports workforce segmentation results in CSV or Excel format."""
    try:
        k = request.args.get("k", type=int)
        export_format = request.args.get("format", "csv").lower()
        dataset = request.args.get("dataset", "profiles")

        content, mimetype, filename = SegmentationService.export_data(
            k=k,
            export_format=export_format,
            dataset=dataset
        )

        response = Response(content, mimetype=mimetype)
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.exception("Error in /api/segmentation/export")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/summary")
def api_segmentation_summary():
    """Returns the comprehensive, unified segmentation contract (Phase 6 API specification)."""
    try:
        k = request.args.get("k", type=int)
        summary = SegmentationService.get_full_summary(k=k)
        return jsonify(summary)
    except Exception as e:
        logger.exception("Error in /api/segmentation/summary")
        return jsonify({
            "success": False,
            "error": {
                "code": "SEGMENTATION_FAILED",
                "message": "Failed to calculate workforce segmentation summary",
                "details": [str(e)]
            }
        }), 500


@segmentation_bp.route("/api/segmentation/data-quality")
def api_segmentation_data_quality():
    """Returns data quality and population audit metrics."""
    try:
        dq = SegmentationService.get_data_quality_summary()
        return jsonify({"success": True, "data": dq})
    except Exception as e:
        logger.exception("Error in /api/segmentation/data-quality")
        return jsonify({"success": False, "error": str(e)}), 500


@segmentation_bp.route("/api/segmentation/model-comparison")
def api_segmentation_model_comparison():
    """Returns unsupervised model comparison (wraps 5-algorithm benchmark)."""
    try:
        pipeline = SegmentationService.get_pipeline()
        comp = pipeline.compare_clustering_models(sample_size=2000)
        return jsonify({"success": True, "data": comp})
    except Exception as e:
        logger.exception("Error in /api/segmentation/model-comparison")
        return jsonify({"success": False, "error": str(e)}), 500
