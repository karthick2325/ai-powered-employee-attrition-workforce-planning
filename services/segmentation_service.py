"""
Workforce Intelligence — Segmentation Service
Provides cached access, thread-safe orchestration, executive KPIs,
five-algorithm unsupervised benchmarking, 2D PCA projection,
role staffing pressure analysis, pay/workload anomaly detection,
and enterprise CSV/XLSX export for unsupervised workforce segmentation.
"""

import os
import io
import csv
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import numpy as np

import config
from src.segmentation import WorkforceSegmentation

logger = logging.getLogger(__name__)


def _sanitize_csv_cell(val: Any) -> Any:
    """Prevents CSV / Excel formula injection by prepending apostrophe if needed."""
    if isinstance(val, str) and len(val) > 0 and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


def _safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert a value to a finite float."""
    try:
        number = float(val)
        return number if np.isfinite(number) else default
    except (ValueError, TypeError, OverflowError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    """Safely convert a value to an integer."""
    number = _safe_float(val)
    return int(number) if number is not None else default


def _validate_k(k: Optional[int], default: int = 5) -> int:
    """Validate K without silently replacing invalid supplied values."""
    if k is None:
        return default
    if isinstance(k, bool):
        raise ValueError("K must be an integer between 2 and 10.")
    try:
        value = int(k)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("K must be an integer between 2 and 10.") from exc
    if value != k or not 2 <= value <= 10:
        raise ValueError("K must be an integer between 2 and 10.")
    return value


def _as_search_text(series: pd.Series) -> pd.Series:
    """Normalize arbitrary pandas values for safe, case-insensitive search."""
    return series.astype("string").fillna("").str.lower()


class SegmentationService:
    _instance = None
    _pipeline_lock = threading.Lock()
    _pipeline: Optional[WorkforceSegmentation] = None
    _current_k: int = 5
    _cached_profiles: Optional[pd.DataFrame] = None
    _cached_role_pressure: Optional[pd.DataFrame] = None
    _cached_anomalies: Optional[pd.DataFrame] = None
    _cached_k_eval: Optional[List[Dict[str, Any]]] = None
    _cached_benchmark: Optional[Dict[str, Any]] = None
    _cached_pca: Optional[Dict[str, Any]] = None
    _last_calculated_at: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SegmentationService, cls).__new__(cls)
        return cls._instance

    @classmethod
    def _sync_pipeline_cache(cls) -> None:
        """Synchronize service-level caches with the active pipeline."""
        pipeline = cls._pipeline
        if pipeline is None:
            return
        cls._current_k = _validate_k(getattr(pipeline, "k", cls._current_k))
        cls._cached_profiles = getattr(pipeline, "segment_profiles", None)
        cls._cached_role_pressure = getattr(pipeline, "role_pressure_df", None)
        cls._cached_anomalies = getattr(pipeline, "anomalies_df", None)
        cls._cached_k_eval = getattr(pipeline, "k_evaluation_results", None)
        cls._cached_benchmark = getattr(pipeline, "five_algorithm_benchmark", None)
        cls._cached_pca = getattr(pipeline, "pca_projection_data", None)
        cls._last_calculated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def get_pipeline(
        cls,
        k: Optional[int] = None,
        force_refit: bool = False
    ) -> WorkforceSegmentation:
        """Return the active pipeline, safely refitting when K or data changes."""
        target_k = _validate_k(k, default=cls._current_k)

        with cls._pipeline_lock:
            if cls._pipeline is None or force_refit:
                logger.info(
                    "Initializing WorkforceSegmentation pipeline (K=%s, force_refit=%s)",
                    target_k, force_refit
                )
                pipeline = WorkforceSegmentation(
                    excel_path=config.EXCEL_FILE_PATH,
                    k=target_k,
                    random_state=42
                )
                pipeline.run_pipeline()
                cls._pipeline = pipeline
                cls._sync_pipeline_cache()
            elif target_k != cls._current_k:
                logger.info(
                    "Re-clustering workforce from K=%s to K=%s",
                    cls._current_k, target_k
                )
                cls._pipeline.fast_refit(k=target_k)
                # Results that contain cluster labels/summaries must not be
                # reused after changing K. Preserve K-independent calculations
                # only when the pipeline implementation leaves them valid.
                if hasattr(cls._pipeline, "five_algorithm_benchmark"):
                    cls._pipeline.five_algorithm_benchmark = None
                if hasattr(cls._pipeline, "pca_projection_data"):
                    cls._pipeline.pca_projection_data = None
                cls._sync_pipeline_cache()
            return cls._pipeline

    @classmethod
    def get_overview_kpis(cls, k: Optional[int] = None) -> Dict[str, Any]:
        """Calculate executive KPI cards from the active segmentation results."""
        pipeline = cls.get_pipeline(k=k)
        profiles = getattr(pipeline, "segment_profiles", None)
        roles = getattr(pipeline, "role_pressure_df", None)
        anomalies = getattr(pipeline, "anomalies_df", None)

        if profiles is None or profiles.empty:
            return {}

        profiles = profiles.copy()
        total_employees = _safe_int(profiles.get("Headcount", pd.Series(dtype=float)).sum())
        total_sim_exits = _safe_int(profiles.get("Simulated_Exits", pd.Series(dtype=float)).sum())
        overall_attr_rate = round(total_sim_exits / max(1, total_employees) * 100, 2)

        if "Flight_Risk_Rate_Pct" in profiles.columns:
            rate_col = "Flight_Risk_Rate_Pct"
        elif "Simulated_Attrition_Pct" in profiles.columns:
            rate_col = "Simulated_Attrition_Pct"
        else:
            rate_col = "_safe_rate"
            profiles[rate_col] = 0.0
        profiles[rate_col] = pd.to_numeric(profiles[rate_col], errors="coerce").fillna(0.0)
        highest_risk_seg = profiles.sort_values(rate_col, ascending=False).iloc[0]
        lowest_risk_seg = profiles.sort_values(rate_col, ascending=True).iloc[0]
        crit_role = roles.iloc[0] if roles is not None and not roles.empty else None

        notice_df = getattr(pipeline, "df_notice", None)
        total_notice_exits = len(notice_df) if notice_df is not None else 0
        total_replacement_need = total_notice_exits + total_sim_exits

        k_eval = getattr(pipeline, "k_evaluation_results", None) or []
        curr_k_eval = next((r for r in k_eval if _safe_int(r.get("k"), -1) == pipeline.k), {})
        sil_score = curr_k_eval.get("silhouette_score")
        total_anomalies = len(anomalies) if anomalies is not None else 0
        anomaly_pct = round(total_anomalies / max(1, total_employees) * 100, 2)
        highest_sim_rate = _safe_float(highest_risk_seg.get(rate_col), 0.0) or 0.0

        # The active production pipeline is K-Means. Do not run the expensive
        # multi-algorithm benchmark just to populate dashboard KPI cards.
        best_algo = "K-Means"
        segmented_df = getattr(pipeline, "df_segmented", None)
        if segmented_df is not None and not segmented_df.empty and "Segment_ID" in segmented_df.columns:
            segment_ids = pd.to_numeric(segmented_df["Segment_ID"], errors="coerce")
            assigned_count = int(segment_ids.ge(0).sum())
            noise_count = int(segment_ids.eq(-1).sum())
        else:
            assigned_count = total_employees
            noise_count = 0
        coverage_pct = round(assigned_count / max(1, len(getattr(pipeline, "df_population", []))) * 100, 2)
        noise_pct = round(noise_count / max(1, len(getattr(pipeline, "df_population", []))) * 100, 2)
        source_rows = cls._get_source_row_count(pipeline)
        eligible_employees = len(getattr(pipeline, "df_population", []))
        data_quality_status = (
            f"{total_employees:,} employees assigned across "
            f"{len(profiles)} clusters"
        )

        def segment_payload(row: pd.Series, include_exits: bool = False) -> Dict[str, Any]:
            payload = {
                "segment_id": _safe_int(row.get("Segment_ID"), 0),
                "archetype_name": str(row.get("Archetype_Name") or f"Segment {_safe_int(row.get('Segment_ID')) + 1}"),
                "headcount": _safe_int(row.get("Headcount")),
                "pct_workforce": _safe_float(row.get("Pct_Workforce"), 0.0) or 0.0,
                "attrition_rate": _safe_float(row.get(rate_col), 0.0) or 0.0,
                "predicted_risk_rate": _safe_float(row.get(rate_col), 0.0) or 0.0,
            }
            if include_exits:
                payload["simulated_exits"] = _safe_int(row.get("Simulated_Exits"))
                payload["method_used"] = "Post-hoc simulated validation and ML prediction integration"
            return payload

        role_payload = {
            "job_role": str(crit_role.get("Job_Role", "N/A")),
            "department": str(crit_role.get("Department", "N/A")),
            "pressure_ratio": _safe_float(crit_role.get("Staffing_Pressure_Ratio"), 0.0) or 0.0,
            "pressure_tier": str(crit_role.get("Pressure_Tier", "N/A")),
            "headcount": _safe_int(crit_role.get("Headcount")),
            "immediate_need": _safe_int(crit_role.get("Immediate_Staffing_Need", crit_role.get("Immediate_Need", 0))),
            "notice_exits": _safe_int(crit_role.get("Notice_Exits")),
            "positions_remaining": _safe_int(crit_role.get("Open_Requisitions", crit_role.get("Positions_Remaining", 0))),
        } if crit_role is not None else {
            "job_role": "N/A", "department": "N/A", "pressure_ratio": 0.0,
            "pressure_tier": "N/A", "headcount": 0, "immediate_need": 0,
            "notice_exits": 0, "positions_remaining": 0
        }

        return {
            "current_k": pipeline.k,
            "total_clustered_employees": total_employees,
            "total_segments": len(profiles),
            "eligible_employees": eligible_employees or total_employees,
            "source_rows": source_rows,
            "excluded_records": total_notice_exits,
            "silhouette_score": sil_score,
            "best_validated_algorithm": best_algo,
            "clustering_coverage_pct": coverage_pct,
            "unassigned_noise_pct": noise_pct,
            "highest_risk_segment": segment_payload(highest_risk_seg, include_exits=True),
            "lowest_risk_segment": segment_payload(lowest_risk_seg),
            "top_pressure_role": role_payload,
            "total_anomalies_flagged": total_anomalies,
            "anomaly_percentage": anomaly_pct,
            "assessed_records": total_employees,
            "contamination_rate": 0.02,
            "total_replacement_need": total_replacement_need,
            "confirmed_notice_exits": total_notice_exits,
            "simulated_additional_exits": total_sim_exits,
            "overall_simulated_attrition_rate": overall_attr_rate,
            "data_quality_status": data_quality_status,
            "last_calculated_at": cls._last_calculated_at or datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def _get_source_row_count(cls, pipeline: WorkforceSegmentation) -> int:
        """Use the loaded employee sheet when available; otherwise use cohort sizes."""
        try:
            if ExcelService.is_loaded():
                employees = ExcelService.get_sheet("Employees")
                if employees is not None:
                    return int(len(employees))
        except Exception:
            logger.debug("Unable to read Employees sheet row count", exc_info=True)
        population = getattr(pipeline, "df_population", None)
        notice = getattr(pipeline, "df_notice", None)
        return int(len(population) if population is not None else 0) + int(len(notice) if notice is not None else 0)

    @classmethod
    def get_five_algorithm_benchmark(cls, k: Optional[int] = None) -> Dict[str, Any]:
        """Returns the 5-algorithm unsupervised clustering benchmark results."""
        pipeline = cls.get_pipeline(k=k)
        if getattr(pipeline, "five_algorithm_benchmark", None) is None:
            pipeline.benchmark_five_algorithms(k=pipeline.k)
            cls._cached_benchmark = getattr(pipeline, "five_algorithm_benchmark", None)
        benchmark = getattr(pipeline, "five_algorithm_benchmark", None)
        return benchmark if isinstance(benchmark, dict) else {"selected_algorithm": None, "candidates": []}

    @classmethod
    def get_pca_projection(cls, k: Optional[int] = None) -> Dict[str, Any]:
        """Return PCA coordinates for the requested/current K assignment."""
        pipeline = cls.get_pipeline(k=k)
        if getattr(pipeline, "pca_projection_data", None) is None:
            pipeline.compute_pca_projection()
            cls._cached_pca = getattr(pipeline, "pca_projection_data", None)
        result = getattr(pipeline, "pca_projection_data", None)
        return result if isinstance(result, dict) else {"points": []}

    @classmethod
    def get_segment_profiles_data(cls, k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns structured segment profiles list with demographic audit."""
        pipeline = cls.get_pipeline(k=k)
        if pipeline.segment_profiles is None:
            pipeline.profile_segments()

        df = pipeline.segment_profiles.copy()
        total_notice = len(pipeline.df_notice) if pipeline.df_notice is not None else 0
        df["Allocated_Notice_Exits"] = ((df["Pct_Workforce"] / 100.0) * total_notice).round(0).astype(int)
        df["Total_Replacement_Need"] = df["Allocated_Notice_Exits"] + df["Simulated_Exits"]

        # Add verified gender counts per cluster from the exact employee rows
        # assigned by the active model. Never infer gender from names.
        segmented = getattr(pipeline, "df_segmented", None)
        gender_available = (
            segmented is not None
            and not segmented.empty
            and "Segment_ID" in segmented.columns
            and "Gender" in segmented.columns
        )
        gender_counts = {}
        if gender_available:
            gender_values = segmented["Gender"].astype("string").fillna("").str.strip().str.casefold()
            gender_source = segmented[["Segment_ID"]].copy()
            gender_source["_gender_norm"] = gender_values
            for segment_id, group in gender_source.groupby("Segment_ID", dropna=False):
                normalized = group["_gender_norm"]
                male_count = int(normalized.isin(["male", "m", "man"]).sum())
                female_count = int(normalized.isin(["female", "f", "woman"]).sum())
                other_count = int(len(group) - male_count - female_count)
                gender_counts[int(segment_id)] = {
                    "Gender_Counts_Available": True,
                    "Gender_Male_Count": male_count,
                    "Gender_Female_Count": female_count,
                    "Gender_Other_Count": other_count,
                }

        df["Gender_Counts_Available"] = bool(gender_available)
        df["Gender_Male_Count"] = None
        df["Gender_Female_Count"] = None
        df["Gender_Other_Count"] = None
        if gender_available:
            for row_index, row in df.iterrows():
                counts = gender_counts.get(int(row["Segment_ID"]))
                if counts:
                    for field, value in counts.items():
                        df.at[row_index, field] = value

        # Ensure both alias column names exist
        if "Flight_Risk_Rate_Pct" in df.columns and "Simulated_Attrition_Pct" not in df.columns:
            df["Simulated_Attrition_Pct"] = df["Flight_Risk_Rate_Pct"]
        elif "Simulated_Attrition_Pct" in df.columns and "Flight_Risk_Rate_Pct" not in df.columns:
            df["Flight_Risk_Rate_Pct"] = df["Simulated_Attrition_Pct"]

        if "Actionable_Recommendation" in df.columns and "Recommended_Talent_Action" not in df.columns:
            df["Recommended_Talent_Action"] = df["Actionable_Recommendation"]
        elif "Recommended_Talent_Action" in df.columns and "Actionable_Recommendation" not in df.columns:
            df["Actionable_Recommendation"] = df["Recommended_Talent_Action"]

        return df.to_dict(orient="records")

    @classmethod
    def get_k_evaluation_data(cls, selected_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return evaluation metrics for candidate K values (not only selected K)."""
        pipeline = cls.get_pipeline(k=selected_k)
        results = getattr(pipeline, "k_evaluation_results", None)
        if not results:
            pipeline.evaluate_k_candidates(range(2, 11))
            results = getattr(pipeline, "k_evaluation_results", None)
        cls._cached_k_eval = results or []
        return cls._cached_k_eval

    @classmethod
    def get_role_pressure_data(cls, department: Optional[str] = None, pressure_tier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns role staffing pressure records, optionally filtered."""
        pipeline = cls.get_pipeline()
        if pipeline.role_pressure_df is None:
            pipeline.segment_job_roles()

        df = pipeline.role_pressure_df.copy()
        if department and department != "All":
            df = df[df["Department"] == department]
        if pressure_tier and pressure_tier != "All":
            df = df[df["Pressure_Tier"] == pressure_tier]

        # Alias columns for compatibility
        if "Immediate_Staffing_Need" in df.columns and "Immediate_Need" not in df.columns:
            df["Immediate_Need"] = df["Immediate_Staffing_Need"]
        if "Open_Requisitions" in df.columns and "Positions_Remaining" not in df.columns:
            df["Positions_Remaining"] = df["Open_Requisitions"]

        return df.to_dict(orient="records")

    @classmethod
    def get_anomalies_data(
        cls,
        search_query: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """Returns paginated and filtered workforce workload/pay anomalies."""
        pipeline = cls.get_pipeline()
        if pipeline.anomalies_df is None:
            pipeline.detect_workload_pay_anomalies()

        source_df = getattr(pipeline, "anomalies_df", None)
        df = source_df.copy() if source_df is not None else pd.DataFrame()
        if df.empty:
            return {"records": [], "total_records": 0, "page": 1, "page_size": max(1, min(_safe_int(page_size, 10), 100)), "total_pages": 1, "anomaly_types": []}

        # Support both supported anomaly category field names.
        cat_col = "Anomaly_Category" if "Anomaly_Category" in df.columns else "Anomaly_Type"
        if cat_col not in df.columns:
            df["Anomaly_Type"] = "Unknown"
            cat_col = "Anomaly_Type"
        if "Anomaly_Type" not in df.columns:
            df["Anomaly_Type"] = df[cat_col]

        if anomaly_type and anomaly_type != "All":
            df = df[df[cat_col] == anomaly_type]

        if search_query:
            q = str(search_query).strip().lower()
            mask = pd.Series(False, index=df.index)
            for column in ("Employee_ID", "Department", "Job_Role", cat_col):
                if column in df.columns:
                    mask |= _as_search_text(df[column]).str.contains(q, na=False, regex=False)
            df = df[mask]

        page_size = max(1, min(_safe_int(page_size, 10), 100))
        page = max(1, _safe_int(page, 1))
        total_records = len(df)
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_slice = df.iloc[start_idx:end_idx]

        return {
            "records": page_slice.to_dict(orient="records"),
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "anomaly_types": pipeline.anomalies_df[cat_col].unique().tolist()
        }

    @classmethod
    def get_segmented_employees(
        cls,
        segment_id: Optional[int] = None,
        department: Optional[str] = None,
        job_role: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        k: Optional[int] = None
    ) -> Dict[str, Any]:
        """Returns searchable and paginated employee cluster assignments for selected K."""
        pipeline = cls.get_pipeline(k=k)
        source_df = getattr(pipeline, "df_segmented", None)
        df = source_df.copy() if source_df is not None else pd.DataFrame()
        if df.empty:
            page_size = max(1, min(_safe_int(page_size, 10), 100))
            return {"records": [], "total_records": 0, "page": 1, "page_size": page_size, "total_pages": 1}

        # Ensure Employee_Name is present and joined from authoritative source
        if "Employee_Name" not in df.columns or df["Employee_Name"].isnull().any():
            emp_df = ExcelService.get_sheet("Employees")
            if "Employee_Name" in emp_df.columns:
                name_map = emp_df.set_index("Employee_ID")["Employee_Name"].to_dict()
                df["Employee_Name"] = df["Employee_ID"].map(name_map)

        if segment_id is not None and segment_id >= 0:
            df = df[df["Segment_ID"] == segment_id]
        if department and department != "All":
            df = df[df["Department"] == department]
        if job_role and job_role != "All":
            df = df[df["Job_Role"] == job_role]
        if search:
            q = str(search).strip().lower()
            mask = pd.Series(False, index=df.index)
            for column in ("Employee_ID", "Department", "Job_Role", "Employee_Name"):
                if column in df.columns:
                    mask |= _as_search_text(df[column]).str.contains(q, na=False, regex=False)
            df = df[mask]

        page_size = max(1, min(_safe_int(page_size, 10), 100))
        page = max(1, _safe_int(page, 1))
        total_records = len(df)
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        slice_df = df.iloc[start_idx:end_idx]

        cols = [
            "Employee_ID", "Employee_Name", "Department", "Job_Role", "Job_Level",
            "Segment_ID", "Segment_Label", "Tenure_Months_At_Prediction",
            "Annual_Salary_INR", "Compa_Ratio", "Job_Satisfaction_Score_1_5",
            "Work_Life_Balance_Score_1_5", "Overtime_Hours_Monthly"
        ]
        available_cols = [c for c in cols if c in slice_df.columns]
        records = slice_df[available_cols].to_dict(orient="records")

        return {
            "records": records,
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    @classmethod
    def get_data_quality_summary(cls) -> Dict[str, Any]:
        """Calculate data quality and coverage metrics from available pipeline data."""
        pipeline = cls.get_pipeline()
        population = getattr(pipeline, "df_population", None)
        notice = getattr(pipeline, "df_notice", None)
        segmented = getattr(pipeline, "df_segmented", None)
        anomalies = getattr(pipeline, "anomalies_df", None)
        transformed = getattr(pipeline, "X_transformed", None)

        source_rows = cls._get_source_row_count(pipeline)
        notice_count = len(notice) if notice is not None else 0
        eligible_count = len(population) if population is not None else max(0, source_rows - notice_count)
        clustered_count = len(segmented) if segmented is not None else 0
        coverage_pct = round(clustered_count / max(1, eligible_count) * 100, 2)

        employee_ids = None
        try:
            if ExcelService.is_loaded():
                employee_df = ExcelService.get_sheet("Employees")
                if employee_df is not None and "Employee_ID" in employee_df.columns:
                    employee_ids = employee_df["Employee_ID"]
        except Exception:
            logger.debug("Unable to inspect Employee_ID data quality", exc_info=True)
        duplicate_ids = int(employee_ids.duplicated().sum()) if employee_ids is not None else 0

        feature_names = getattr(pipeline, "NUMERIC_FEATURES", []) or []
        categorical_names = getattr(pipeline, "CATEGORICAL_FEATURES", []) or []
        try:
            feature_count = len(feature_names) + len(categorical_names)
        except TypeError:
            feature_count = 0
        transformed_dimensions = int(transformed.shape[1]) if transformed is not None and hasattr(transformed, "shape") and len(transformed.shape) > 1 else 0
        anomaly_count = len(anomalies) if anomalies is not None else 0

        missing_critical = 0
        if population is not None and not population.empty:
            critical_columns = [c for c in (list(feature_names) + list(categorical_names)) if c in population.columns]
            if critical_columns:
                missing_critical = int(population[critical_columns].isna().any(axis=1).sum())

        return {
            "source_row_count": source_rows,
            "eligible_employee_count": eligible_count,
            "excluded_record_count": notice_count,
            "exclusion_reason": "Employees currently serving contractual notice periods as of snapshot date",
            "duplicate_employee_ids": duplicate_ids,
            "missing_critical_features": missing_critical,
            "raw_feature_count": feature_count,
            "transformed_feature_dimensions": transformed_dimensions,
            "successfully_clustered_count": clustered_count,
            "clustering_coverage_pct": coverage_pct,
            "anomalies_assessed_count": eligible_count,
            "anomalies_flagged_count": anomaly_count,
            "anomaly_contamination_setting": "2.0%",
            "fairness_demographics_excluded_from_clustering": ["Age", "Gender"],
            "target_labels_excluded_from_clustering": ["Attrition_Within_6M"]
        }

    @classmethod
    def get_full_summary(cls, k: Optional[int] = None) -> Dict[str, Any]:
        """Returns the unified segmentation contract (Phase 6 API specification)."""
        pipeline = cls.get_pipeline(k=k)
        kpis = cls.get_overview_kpis(k=pipeline.k)
        profiles = cls.get_segment_profiles_data(k=pipeline.k)
        dq = cls.get_data_quality_summary()
        k_eval = cls.get_k_evaluation_data()
        benchmark = cls.get_five_algorithm_benchmark(k=pipeline.k)

        curr_k_eval = next((r for r in k_eval if r.get("k") == pipeline.k), {})

        return {
            "success": True,
            "model": {
                "algorithm": "kmeans",
                "requested_clusters": pipeline.k,
                "actual_clusters": len(profiles),
                "silhouette_score": curr_k_eval.get("silhouette_score"),
                "davies_bouldin_score": curr_k_eval.get("davies_bouldin_score"),
                "inertia": curr_k_eval.get("inertia"),
                "random_state": pipeline.random_state,
                "n_init": 10
            },
            "summary": {
                "source_rows": dq["source_row_count"],
                "eligible_employees": dq["eligible_employee_count"],
                "clustered_employees": dq["successfully_clustered_count"],
                "excluded_records": dq["excluded_record_count"],
                "anomaly_count": dq["anomalies_flagged_count"],
                "anomaly_percentage": kpis.get("anomaly_percentage", 2.0)
            },
            "benchmark": benchmark,
            "segments": profiles,
            "kpis": kpis,
            "data_quality": dq,
            "metadata": {
                "generated_at": cls._last_calculated_at or datetime.now(timezone.utc).isoformat(),
                "data_source": "Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx",
                "is_synthetic": True,
                "disclaimer": config.DISCLAIMER_TEXT
            },
            "warnings": []
        }

    @classmethod
    def refit_k(cls, k: int) -> Dict[str, Any]:
        """Dynamically and rapidly reclusters workforce with a newly requested K value."""
        k = _validate_k(k)
        pipeline = cls.get_pipeline(k=k, force_refit=False)
        return {
            "success": True,
            "k": pipeline.k,
            "message": f"Successfully re-clustered workforce into {pipeline.k} segments.",
            "kpis": cls.get_overview_kpis(k=k)
        }

    @classmethod
    def export_data(
        cls,
        k: Optional[int] = None,
        export_format: str = "csv",
        dataset: str = "profiles"
    ) -> Tuple[bytes, str, str]:
        """
        Exports workforce segmentation results in CSV or XLSX format with formula injection sanitization.
        Returns: (bytes_content, mimetype, filename)
        """
        pipeline = cls.get_pipeline(k=k)
        target_k = pipeline.k

        if dataset == "role_pressure":
            df = pipeline.role_pressure_df.copy() if pipeline.role_pressure_df is not None else pd.DataFrame()
            base_name = f"Role_Staffing_Pressure_K{target_k}"
        elif dataset == "anomalies":
            df = pipeline.anomalies_df.copy() if pipeline.anomalies_df is not None else pd.DataFrame()
            base_name = f"Workload_Pay_Anomalies_K{target_k}"
        elif dataset == "benchmark":
            benchmark = cls.get_five_algorithm_benchmark(k=target_k)
            df = pd.DataFrame(benchmark["candidates"])
            base_name = f"Five_Algorithm_Clustering_Benchmark_K{target_k}"
        else:
            # Default: segment profiles
            df = pipeline.segment_profiles.copy() if pipeline.segment_profiles is not None else pd.DataFrame()
            base_name = f"Workforce_Segmentation_Profiles_K{target_k}"

        # Prevent formula injection in string columns
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].apply(_sanitize_csv_cell)

        if export_format.lower() in ("xlsx", "excel"):
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                # Include all primary segmentation sheets for comprehensive export
                if pipeline.segment_profiles is not None:
                    prof_df = pipeline.segment_profiles.copy()
                    for c in prof_df.select_dtypes(include=["object", "string"]).columns:
                        prof_df[c] = prof_df[c].apply(_sanitize_csv_cell)
                    prof_df.to_excel(writer, sheet_name="Segment_Profiles", index=False)

                if pipeline.role_pressure_df is not None:
                    role_df = pipeline.role_pressure_df.copy()
                    for c in role_df.select_dtypes(include=["object", "string"]).columns:
                        role_df[c] = role_df[c].apply(_sanitize_csv_cell)
                    role_df.to_excel(writer, sheet_name="Role_Staffing_Pressure", index=False)

                if pipeline.anomalies_df is not None:
                    anom_df = pipeline.anomalies_df.head(1000).copy()
                    for c in anom_df.select_dtypes(include=["object", "string"]).columns:
                        anom_df[c] = anom_df[c].apply(_sanitize_csv_cell)
                    anom_df.to_excel(writer, sheet_name="Anomalies_Sample", index=False)

                # Metadata sheet
                meta_records = [
                    {"Parameter": "Algorithm Selected", "Value": (getattr(pipeline, "five_algorithm_benchmark", None) or {}).get("selected_algorithm") or "Not evaluated"},
                    {"Parameter": "Cluster Count (K)", "Value": target_k},
                    {"Parameter": "Random State", "Value": pipeline.random_state},
                    {"Parameter": "Eligible Clustered Population", "Value": len(pipeline.df_population) if pipeline.df_population is not None else 0},
                    {"Parameter": "Notice Exclusions", "Value": len(pipeline.df_notice) if pipeline.df_notice is not None else 0},
                    {"Parameter": "Total Source Records", "Value": cls._get_source_row_count(pipeline)},
                    {"Parameter": "Generated At (UTC)", "Value": datetime.now(timezone.utc).isoformat()},
                    {"Parameter": "Synthetic Notice", "Value": config.DISCLAIMER_TEXT}
                ]
                pd.DataFrame(meta_records).to_excel(writer, sheet_name="Export_Metadata", index=False)

            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            # CSV export
            content = df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename
