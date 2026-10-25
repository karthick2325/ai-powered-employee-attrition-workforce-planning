"""Workforce Intelligence — Segmentation API Routes.

This blueprint exposes the workforce segmentation service to the dashboard.
Supported K values are integers from 2 through 10.
"""

import logging
from io import BytesIO

import numpy as np
from flask import Blueprint, jsonify, request, send_file, render_template

from services.segmentation_service import SegmentationService
from services.excel_service import ExcelService
import config

logger = logging.getLogger(__name__)

# Keep a stable blueprint name for app.py registration.
segmentation_bp = Blueprint("segmentation", __name__)
# Compatibility alias for projects that import this name instead.
segmentation_routes_bp = segmentation_bp


@segmentation_bp.get("/segmentation")
def segmentation_page():
    """Render the Workforce Segmentation page and its department filter options."""
    departments = []
    try:
        if ExcelService.is_loaded():
            employees = ExcelService.get_sheet("Employees")
            if employees is not None and "Department" in employees.columns:
                departments = sorted(employees["Department"].dropna().astype(str).unique().tolist())
    except Exception:
        logger.exception("Could not load departments for segmentation page")

    return render_template(
        "segmentation.html",
        active_page="segmentation",
        departments=departments,
        current_date=config.DATA_SNAPSHOT_DATE,
        disclaimer=config.DISCLAIMER_TEXT,
    )


class SegmentationRequestError(ValueError):
    """Raised when a request contains invalid segmentation parameters."""


def _json_safe(value):
    """Convert numpy/pandas scalar values and non-finite numbers to JSON-safe data."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    return value


def _get_int_arg(name, default=None, minimum=None, maximum=None):
    """Read and validate an integer query parameter or JSON body field."""
    raw = request.args.get(name)
    if raw is None and request.is_json:
        body = request.get_json(silent=True) or {}
        raw = body.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        # Reject values such as 3.5 instead of silently truncating them.
        parsed = int(str(raw).strip())
        if str(raw).strip() not in (str(parsed), f"+{parsed}"):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise SegmentationRequestError(f"'{name}' must be an integer.") from exc
    if minimum is not None and parsed < minimum:
        raise SegmentationRequestError(f"'{name}' must be at least {minimum}.")
    if maximum is not None and parsed > maximum:
        raise SegmentationRequestError(f"'{name}' must be no greater than {maximum}.")
    return parsed


def _get_k(default=5):
    return _get_int_arg("k", default=default, minimum=2, maximum=10)


def _success(data, status=200, **extra):
    payload = {"success": True, "data": _json_safe(data)}
    payload.update(_json_safe(extra))
    return jsonify(payload), status


def _error(message, status=400):
    return jsonify({"success": False, "error": str(message)}), status


def _run_service(callback):
    """Execute a service call and convert predictable failures into API responses."""
    try:
        return callback()
    except SegmentationRequestError as exc:
        return _error(exc, 400)
    except ValueError as exc:
        return _error(exc, 400)
    except FileNotFoundError as exc:
        logger.exception("Segmentation data file was not found")
        return _error("The workforce dataset could not be found. Check the configured Excel path.", 500)
    except Exception:
        logger.exception("Segmentation API request failed: %s %s", request.method, request.path)
        return _error("The segmentation request could not be completed. Check the application logs for details.", 500)


@segmentation_bp.get("/api/segmentation/health")
def segmentation_health():
    """Lightweight health endpoint; does not trigger model training."""
    return jsonify({"success": True, "module": "workforce_segmentation", "status": "available", "supported_k": list(range(2, 11))})


@segmentation_bp.get("/api/segmentation/overview")
def segmentation_overview():
    """Executive KPI cards for the selected cluster count."""
    def action():
        k = _get_k()
        data = SegmentationService.get_overview_kpis(k=k)
        return _success(data, k=k)
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/summary")
def segmentation_summary():
    """Unified segmentation response with KPIs, profiles, benchmark and data quality."""
    def action():
        k = _get_k()
        data = SegmentationService.get_full_summary(k=k)
        return jsonify(_json_safe(data))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/profiles")
def segmentation_profiles():
    """Segment archetypes and HR recommendations for selected K."""
    def action():
        k = _get_k()
        data = SegmentationService.get_segment_profiles_data(k=k)
        return _success(data, k=k, count=len(data))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/pca")
def segmentation_pca():
    """Two-dimensional PCA projection for the selected K assignment."""
    def action():
        k = _get_k()
        data = SegmentationService.get_pca_projection(k=k)
        return _success(data, k=k)
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/k-evaluation")
def segmentation_k_evaluation():
    """Evaluation scores for candidate K values 2–10."""
    def action():
        selected_k = _get_int_arg("selected_k", default=None, minimum=2, maximum=10)
        data = SegmentationService.get_k_evaluation_data(selected_k=selected_k)
        return _success(data, selected_k=selected_k, count=len(data))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/benchmark")
def segmentation_benchmark():
    """Compare the five configured unsupervised clustering algorithms."""
    def action():
        k = _get_k()
        data = SegmentationService.get_five_algorithm_benchmark(k=k)
        return _success(data, k=k)
    return _run_service(action)


@segmentation_bp.post("/api/segmentation/refit")
def segmentation_refit():
    """Re-cluster the workforce using a requested K from 2 through 10."""
    def action():
        k = _get_int_arg("k", default=None, minimum=2, maximum=10)
        if k is None:
            raise SegmentationRequestError("Provide 'k' in the query string or JSON body.")
        data = SegmentationService.refit_k(k)
        return jsonify(_json_safe(data))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/employees")
def segmentation_employees():
    """Search, filter and paginate employee cluster assignments."""
    def action():
        k = _get_k()
        segment_id = _get_int_arg("segment_id", default=None, minimum=-1, maximum=1000000)
        page = _get_int_arg("page", default=1, minimum=1, maximum=100000000)
        page_size = _get_int_arg("page_size", default=10, minimum=1, maximum=100)
        department = request.args.get("department")
        job_role = request.args.get("job_role")
        search = request.args.get("search", request.args.get("q", ""))
        data = SegmentationService.get_segmented_employees(
            segment_id=segment_id,
            department=department,
            job_role=job_role,
            search=search,
            page=page,
            page_size=page_size,
            k=k,
        )
        return _success(data, k=k, count=data.get("total_records", 0))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/role-pressure")
def segmentation_role_pressure():
    """Role staffing pressure, optionally filtered by department and pressure tier."""
    def action():
        department = request.args.get("department")
        pressure_tier = request.args.get("pressure_tier", request.args.get("tier"))
        data = SegmentationService.get_role_pressure_data(
            department=department,
            pressure_tier=pressure_tier,
        )
        return _success(data, count=len(data))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/anomalies")
def segmentation_anomalies():
    """Paginated workload/pay anomaly records."""
    def action():
        page = _get_int_arg("page", default=1, minimum=1, maximum=100000000)
        page_size = _get_int_arg("page_size", default=10, minimum=1, maximum=100)
        search = request.args.get("search", request.args.get("q", ""))
        anomaly_type = request.args.get("anomaly_type", request.args.get("type"))
        data = SegmentationService.get_anomalies_data(
            search_query=search,
            anomaly_type=anomaly_type,
            page=page,
            page_size=page_size,
        )
        return _success(data, count=data.get("total_records", 0))
    return _run_service(action)


@segmentation_bp.get("/api/segmentation/data-quality")
def segmentation_data_quality():
    """Data coverage, missing-feature, duplicate-ID and fairness-exclusion summary."""
    return _run_service(lambda: _success(SegmentationService.get_data_quality_summary()))


@segmentation_bp.get("/api/segmentation/export")
def segmentation_export():
    """Download segmentation outputs as CSV or XLSX.

    Query parameters:
      format=csv|xlsx
      dataset=profiles|role_pressure|anomalies|benchmark
      k=2..10
    """
    def action():
        k = _get_k()
        export_format = request.args.get("format", "csv").strip().lower()
        dataset = request.args.get("dataset", "profiles").strip().lower()
        if export_format not in {"csv", "xlsx", "excel"}:
            raise SegmentationRequestError("'format' must be csv or xlsx.")
        if dataset not in {"profiles", "role_pressure", "anomalies", "benchmark"}:
            raise SegmentationRequestError("'dataset' must be profiles, role_pressure, anomalies, or benchmark.")
        content, mimetype, filename = SegmentationService.export_data(
            k=k,
            export_format=export_format,
            dataset=dataset,
        )
        return send_file(
            BytesIO(content),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
            max_age=0,
        )
    return _run_service(action)


# Older frontend versions used this alias for the employee table.
segmentation_bp.add_url_rule(
    "/api/segmentation/segment-employees",
    endpoint="segmentation_segment_employees_alias",
    view_func=segmentation_employees,
    methods=["GET"],
)

# Older frontend versions used this alias for the staffing-pressure table.
segmentation_bp.add_url_rule(
    "/api/segmentation/role-staffing-pressure",
    endpoint="segmentation_role_staffing_pressure_alias",
    view_func=segmentation_role_pressure,
    methods=["GET"],
)
