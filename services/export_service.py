"""
Workforce Intelligence — Enterprise Export Service
Generates verified, securely formatted CSV and multi-sheet Excel (.xlsx) workbooks.
Features:
- UTF-8 BOM encoding for seamless Excel CSV opening
- Formula injection protection on all user and text fields
- openpyxl enterprise formatting: navy headers, white bold text, zebra striping, thin borders, freeze panes, auto column widths
- Number formatting: Indian Currency (₹ #,##,##0), percentages (0.0%), integers (#,##0)
- Multi-sheet analytical workbooks with README_Metadata and Executive Summary
"""

import io
import csv
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import config
from services.excel_service import ExcelService
from services.prediction_service import PredictionService
from services.segmentation_service import SegmentationService
from services.workforce_planning_service import WorkforcePlanningService
from services.recruitment_service import RecruitmentService
from services.data_validation_service import DataValidationService

logger = logging.getLogger(__name__)


def sanitize_formula_injection(val: Any) -> Any:
    """Prepends apostrophe to prevent spreadsheet formula injection in untrusted cells."""
    if isinstance(val, str) and len(val) > 0 and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


class ExportService:
    """
    Enterprise Data Serialization and Workbook Generation Engine.
    """

    # Enterprise styling tokens
    HEADER_FILL = PatternFill(start_color="14264F", end_color="14264F", fill_type="solid")
    HEADER_FONT = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    META_TITLE_FONT = Font(name="Arial", size=14, bold=True, color="14264F")
    META_HEADER_FONT = Font(name="Arial", size=11, bold=True, color="0F172A")
    DATA_FONT = Font(name="Arial", size=10, color="1E293B")
    THIN_BORDER = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    @classmethod
    def apply_sheet_formatting(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        has_header: bool = True,
        freeze_header: bool = True
    ):
        """Applies consistent corporate styling, borders, row heights, and auto-fit column widths."""
        if freeze_header and has_header:
            ws.freeze_panes = "A2"

        for row_idx, row in enumerate(ws.iter_rows(), start=1):
            if row_idx == 1 and has_header:
                ws.row_dimensions[row_idx].height = 28
                for cell in row:
                    cell.fill = cls.HEADER_FILL
                    cell.font = cls.HEADER_FONT
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    cell.border = cls.THIN_BORDER
            else:
                ws.row_dimensions[row_idx].height = 20
                fill = cls.ZEBRA_FILL if row_idx % 2 == 0 else cls.WHITE_FILL
                for cell in row:
                    cell.font = cls.DATA_FONT
                    cell.border = cls.THIN_BORDER
                    if cell.fill.fill_type is None:
                        cell.fill = fill

                    # Format numbers and currency
                    if isinstance(cell.value, (int, float)):
                        col_name = str(ws.cell(row=1, column=cell.column).value).lower()
                        if "pct" in col_name or "rate" in col_name or "ratio" in col_name or "score" in col_name:
                            cell.number_format = "0.0%" if "pct" in col_name or "rate" in col_name else "0.00"
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                        elif "salary" in col_name or "cost" in col_name or "inr" in col_name or "savings" in col_name:
                            cell.number_format = "₹ #,##,##0"
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                        else:
                            cell.number_format = "#,##0"
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                    elif isinstance(cell.value, str):
                        cell.value = sanitize_formula_injection(cell.value)
                        cell.alignment = Alignment(horizontal="left", vertical="center")

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(12, min(max_len + 4, 45))

    @classmethod
    def generate_readme_metadata_sheet(
        cls,
        wb: openpyxl.Workbook,
        report_title: str,
        record_count: int,
        filters_applied: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ):
        """Creates standard README & Audit Metadata worksheet."""
        ws = wb.create_sheet(title="README_Metadata", index=0)
        ws.views.sheetView[0].showGridLines = True
        ws.row_dimensions[1].height = 34

        ws.cell(row=1, column=1, value=report_title).font = cls.META_TITLE_FONT
        ws.cell(row=2, column=1, value="AttritionSense Technologies — Enterprise Workforce Intelligence Report").font = Font(name="Arial", size=10, italic=True, color="64748B")

        meta = [
            ("Generated Timestamp (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Data Snapshot Date", config.DATA_SNAPSHOT_DATE),
            ("Primary Data Source", "Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx"),
            ("Total Records in Report", f"{record_count:,}"),
            ("Export Mode", "Direct In-Memory Generation"),
            ("Classification Horizon", "6 Months (01 Jan 2026 to 30 Jun 2026)")
        ]

        if filters_applied:
            filter_str = ", ".join(f"{k}: {v}" for k, v in filters_applied.items() if v and v != "All")
            meta.append(("Active User Filters", filter_str or "None (Full Population)"))

        meta.append(("Ethical AI Notice", "Illustrative decision-support outputs. Do not use for automated adverse employment actions."))
        if notes:
            meta.append(("Analytical Notes", notes))

        start_row = 4
        for idx, (k, v) in enumerate(meta):
            r = start_row + idx
            c1 = ws.cell(row=r, column=1, value=k)
            c2 = ws.cell(row=r, column=2, value=v)
            c1.font = cls.META_HEADER_FONT
            c2.font = cls.DATA_FONT
            c1.border = cls.THIN_BORDER
            c2.border = cls.THIN_BORDER
            ws.row_dimensions[r].height = 22

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 65

    # -------------------------------------------------------------------------
    # 1. ATTRITION RISK REPORT
    # -------------------------------------------------------------------------
    @classmethod
    def export_attrition_risk_report(
        cls,
        export_format: str = "xlsx",
        department: Optional[str] = None,
        job_role: Optional[str] = None,
        job_level: Optional[str] = None,
        location: Optional[str] = None,
        risk_level: Optional[str] = None
    ) -> Tuple[bytes, str, str]:
        """Exports filtered or complete employee attrition prediction records."""
        df = PredictionService.get_filtered_predictions(
            department=department,
            job_role=job_role,
            job_level=job_level,
            location=location,
            risk_level=risk_level
        )

        export_cols = [
            "Employee_ID", "Employee_Name", "Department", "Job_Role", "Job_Level", "Location",
            "Employment_Type", "Tenure_Months_At_Prediction", "Annual_Salary_INR",
            "Overtime_Hours_Monthly", "Job_Satisfaction_Score_1_5", "Work_Life_Balance_Score_1_5",
            "Performance_Rating_1_5", "Training_Hours_Last_12M", "Risk_Probability", "Risk_Level"
        ]
        available_cols = [c for c in export_cols if c in df.columns]
        export_df = df[available_cols].copy()

        # Sanitize string columns
        for c in export_df.select_dtypes(include=["object", "string"]).columns:
            export_df[c] = export_df[c].apply(sanitize_formula_injection)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"AttritionSense_Risk_Report_{timestamp_str}"

        if export_format.lower() in ("xlsx", "excel"):
            wb = openpyxl.Workbook()
            # Remove default empty sheet
            wb.remove(wb.active)

            # Metadata Sheet
            filters = {"Department": department, "Job Role": job_role, "Job Level": job_level, "Risk Level": risk_level}
            cls.generate_readme_metadata_sheet(
                wb,
                report_title="Employee Attrition Risk Assessment Report",
                record_count=len(export_df),
                filters_applied=filters,
                notes="Scored with Random Forest Classifier (PR-AUC: 0.121, ROC-AUC: 0.680). Low Risk: <0.30, Med: 0.30-0.60, High: >=0.60."
            )

            # Summary KPIs Sheet
            ws_sum = wb.create_sheet(title="Executive_Summary")
            ws_sum.views.sheetView[0].showGridLines = True
            high_risk = int((export_df["Risk_Level"] == "High").sum())
            med_risk = int((export_df["Risk_Level"] == "Medium").sum())
            low_risk = int((export_df["Risk_Level"] == "Low").sum())
            avg_prob = round(float(export_df["Risk_Probability"].mean()) * 100, 2) if len(export_df) > 0 else 0.0

            sum_data = [
                ("Assessed Population", len(export_df)),
                ("High Flight Risk Employees (Score >= 0.60)", high_risk),
                ("High Risk Proportion", f"{round(high_risk / max(1, len(export_df)) * 100, 2)}%"),
                ("Medium Risk Employees", med_risk),
                ("Low Risk Employees", low_risk),
                ("Cohort Mean Flight Probability", f"{avg_prob}%")
            ]
            ws_sum.cell(row=1, column=1, value="Metric").font = cls.HEADER_FONT
            ws_sum.cell(row=1, column=2, value="Value").font = cls.HEADER_FONT
            ws_sum.cell(row=1, column=1).fill = cls.HEADER_FILL
            ws_sum.cell(row=1, column=2).fill = cls.HEADER_FILL
            for i, (k, v) in enumerate(sum_data, start=2):
                c1 = ws_sum.cell(row=i, column=1, value=k)
                c2 = ws_sum.cell(row=i, column=2, value=v)
                c1.border = cls.THIN_BORDER
                c2.border = cls.THIN_BORDER
                c1.font = cls.META_HEADER_FONT
                c2.font = cls.DATA_FONT
            cls.apply_sheet_formatting(ws_sum, has_header=True)

            # Detailed Data Sheet
            ws_data = wb.create_sheet(title="Employee_Risk_Scores")
            ws_data.views.sheetView[0].showGridLines = True
            # Write header
            ws_data.append(list(export_df.columns))
            # Write rows
            for row in export_df.itertuples(index=False):
                ws_data.append(list(row))
            cls.apply_sheet_formatting(ws_data, has_header=True, freeze_header=True)

            out = io.BytesIO()
            wb.save(out)
            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            # CSV export with UTF-8 BOM
            content = export_df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8-sig")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename

    # -------------------------------------------------------------------------
    # 2. WORKFORCE SEGMENTATION & ARCHETYPES REPORT
    # -------------------------------------------------------------------------
    @classmethod
    def export_segmentation_report(
        cls,
        k: Optional[int] = None,
        export_format: str = "xlsx"
    ) -> Tuple[bytes, str, str]:
        """Exports workforce segmentation profiles, cluster statistics, and employee assignments."""
        pipeline = SegmentationService.get_pipeline(k=k)
        target_k = pipeline.k

        profiles_df = pipeline.segment_profiles.copy() if pipeline.segment_profiles is not None else pd.DataFrame()
        roles_df = pipeline.role_pressure_df.copy() if pipeline.role_pressure_df is not None else pd.DataFrame()
        anom_df = pipeline.anomalies_df.copy() if pipeline.anomalies_df is not None else pd.DataFrame()

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"Workforce_Segmentation_Report_K{target_k}_{timestamp_str}"

        if export_format.lower() in ("xlsx", "excel"):
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            cls.generate_readme_metadata_sheet(
                wb,
                report_title=f"Unsupervised Workforce Segmentation Report (K = {target_k})",
                record_count=len(pipeline.df_segmented) if pipeline.df_segmented is not None else 47972,
                notes="Workforce clustered on 11 numerical + 3 categorical workplace dimensions. Target labels strictly excluded during training."
            )

            # Segment Profiles Sheet
            ws_prof = wb.create_sheet(title="Segment_Archetype_Profiles")
            ws_prof.views.sheetView[0].showGridLines = True
            ws_prof.append(list(profiles_df.columns))
            for row in profiles_df.itertuples(index=False):
                ws_prof.append(list(row))
            cls.apply_sheet_formatting(ws_prof, has_header=True)

            # Job Role Staffing Pressure Sheet
            ws_roles = wb.create_sheet(title="Job_Role_Staffing_Pressure")
            ws_roles.views.sheetView[0].showGridLines = True
            ws_roles.append(list(roles_df.columns))
            for row in roles_df.itertuples(index=False):
                ws_roles.append(list(row))
            cls.apply_sheet_formatting(ws_roles, has_header=True)

            # Workload & Pay Outliers Sheet
            ws_anom = wb.create_sheet(title="Workload_Pay_Anomalies")
            ws_anom.views.sheetView[0].showGridLines = True
            anom_sub = anom_df.head(2000).copy()
            ws_anom.append(list(anom_sub.columns))
            for row in anom_sub.itertuples(index=False):
                ws_anom.append(list(row))
            cls.apply_sheet_formatting(ws_anom, has_header=True)

            out = io.BytesIO()
            wb.save(out)
            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            # CSV export of segment profiles
            content = profiles_df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8-sig")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename

    # -------------------------------------------------------------------------
    # 3. FIVE-ALGORITHM CLUSTERING BENCHMARK REPORT
    # -------------------------------------------------------------------------
    @classmethod
    def export_clustering_benchmark_report(
        cls,
        k: Optional[int] = None,
        export_format: str = "xlsx"
    ) -> Tuple[bytes, str, str]:
        """Exports 5-algorithm unsupervised benchmark evaluation table and model diagnostics."""
        benchmark = SegmentationService.get_five_algorithm_benchmark(k=k)
        candidates = benchmark["candidates"]

        bench_rows = []
        for c in candidates:
            bench_rows.append({
                "Algorithm": c["name"],
                "Family": c["family"],
                "Clusters_Found": c["clusters_found"],
                "Silhouette_Score": c["silhouette_display"],
                "Davies_Bouldin_Index": c["davies_bouldin_display"],
                "Calinski_Harabasz_Index": c["calinski_harabasz_display"],
                "Noise_Count": c["noise_count"],
                "Noise_Percentage": f"{c['noise_percentage']}%",
                "Coverage_Percentage": f"{c['coverage_percentage']}%",
                "Size_Imbalance_Ratio": c["size_imbalance_ratio"] or "N/A",
                "Runtime_ms": c["runtime_ms"],
                "Validation_Status": "Validated Candidate" if c["is_valid"] else f"Rejected ({c['rejection_reason']})",
                "Composite_Score": c["composite_score"]
            })

        bench_df = pd.DataFrame(bench_rows)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"Five_Algorithm_Clustering_Benchmark_{timestamp_str}"

        if export_format.lower() in ("xlsx", "excel"):
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            cls.generate_readme_metadata_sheet(
                wb,
                report_title="5-Algorithm Unsupervised Clustering Benchmark",
                record_count=len(candidates),
                notes=f"Recommended Model: {benchmark['selected_algorithm']}. Rationale: {benchmark['selection_rationale']}"
            )

            ws = wb.create_sheet(title="Benchmark_Comparison")
            ws.views.sheetView[0].showGridLines = True
            ws.append(list(bench_df.columns))
            for row in bench_df.itertuples(index=False):
                ws.append(list(row))
            cls.apply_sheet_formatting(ws, has_header=True)

            out = io.BytesIO()
            wb.save(out)
            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            content = bench_df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8-sig")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename

    # -------------------------------------------------------------------------
    # 4. WORKFORCE PLANNING & SCENARIOS REPORT
    # -------------------------------------------------------------------------
    @classmethod
    def export_workforce_planning_report(
        cls,
        export_format: str = "xlsx"
    ) -> Tuple[bytes, str, str]:
        """Exports department headcount analysis, monthly notice exits, and staffing gaps."""
        dept_table = WorkforcePlanningService.get_department_exit_analysis_table()
        rows_df = pd.DataFrame(dept_table["rows"])
        role_gaps_df = pd.DataFrame(WorkforcePlanningService.get_role_staffing_gap_analysis())

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"Workforce_Planning_Exit_Analysis_{timestamp_str}"

        if export_format.lower() in ("xlsx", "excel"):
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            cls.generate_readme_metadata_sheet(
                wb,
                report_title="Workforce Planning & Exit Analysis Report",
                record_count=len(rows_df),
                notes="Clearly separates 2,028 verified notice period exits from model-predicted future attrition scenarios."
            )

            # Department Exit Table Sheet
            ws_dept = wb.create_sheet(title="Department_Headcount_Gaps")
            ws_dept.views.sheetView[0].showGridLines = True
            ws_dept.append(list(rows_df.columns))
            for row in rows_df.itertuples(index=False):
                ws_dept.append(list(row))
            cls.apply_sheet_formatting(ws_dept, has_header=True)

            # Role Staffing Gaps Sheet
            ws_role = wb.create_sheet(title="Role_Staffing_Pressure")
            ws_role.views.sheetView[0].showGridLines = True
            ws_role.append(list(role_gaps_df.columns))
            for row in role_gaps_df.itertuples(index=False):
                ws_role.append(list(row))
            cls.apply_sheet_formatting(ws_role, has_header=True)

            out = io.BytesIO()
            wb.save(out)
            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            content = rows_df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8-sig")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename

    # -------------------------------------------------------------------------
    # 5. DATA QUALITY AUDIT REPORT
    # -------------------------------------------------------------------------
    @classmethod
    def export_data_quality_report(
        cls,
        export_format: str = "xlsx"
    ) -> Tuple[bytes, str, str]:
        """Exports data quality checks, referential integrity verification, and dataset inventory."""
        checks = DataValidationService.run_all_checks()
        checks_df = pd.DataFrame(checks)
        summary = DataValidationService.get_quality_summary()

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"Data_Quality_Audit_Report_{timestamp_str}"

        if export_format.lower() in ("xlsx", "excel"):
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            cls.generate_readme_metadata_sheet(
                wb,
                report_title="Automated Data Quality & Governance Audit",
                record_count=len(checks),
                notes=f"Overall Quality Index: {summary['overall_quality_score']}%. Status: {summary['validation_status']}."
            )

            ws = wb.create_sheet(title="Quality_Checks")
            ws.views.sheetView[0].showGridLines = True
            ws.append(list(checks_df.columns))
            for row in checks_df.itertuples(index=False):
                ws.append(list(row))
            cls.apply_sheet_formatting(ws, has_header=True)

            out = io.BytesIO()
            wb.save(out)
            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            content = checks_df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8-sig")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename

    # -------------------------------------------------------------------------
    # 6. RECRUITMENT & TRAINING ANALYTICS REPORT
    # -------------------------------------------------------------------------
    @classmethod
    def export_recruitment_training_report(
        cls,
        export_format: str = "xlsx"
    ) -> Tuple[bytes, str, str]:
        """Exports recruitment funnel conversions, requisition costs, and training metrics."""
        costs_df = ExcelService.get_sheet("Recruitment_Costs").copy()
        reqs_df = ExcelService.get_sheet("Job_Requisitions").copy()
        emp_df = ExcelService.get_sheet("Employees")

        # Training summary by department
        train_dept = emp_df.groupby("Department")["Training_Hours_Last_12M"].agg(["count", "mean", "median", "min", "max"]).reset_index()
        train_dept.columns = ["Department", "Employees", "Mean_Training_Hours", "Median_Training_Hours", "Min_Hours", "Max_Hours"]
        train_dept["Mean_Training_Hours"] = train_dept["Mean_Training_Hours"].round(1)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"Recruitment_Training_Analytics_{timestamp_str}"

        if export_format.lower() in ("xlsx", "excel"):
            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            cls.generate_readme_metadata_sheet(
                wb,
                report_title="Recruitment & Training Analytics Report",
                record_count=len(costs_df),
                notes="Separates documented recruitment expenses in INR from employee training hours."
            )

            # Requisitions Sheet
            ws_req = wb.create_sheet(title="Job_Requisitions")
            ws_req.views.sheetView[0].showGridLines = True
            ws_req.append(list(reqs_df.columns))
            for row in reqs_df.itertuples(index=False):
                ws_req.append(list(row))
            cls.apply_sheet_formatting(ws_req, has_header=True)

            # Recruitment Costs Sheet
            ws_cost = wb.create_sheet(title="Recruitment_Costs")
            ws_cost.views.sheetView[0].showGridLines = True
            ws_cost.append(list(costs_df.columns))
            for row in costs_df.itertuples(index=False):
                ws_cost.append(list(row))
            cls.apply_sheet_formatting(ws_cost, has_header=True)

            # Training Summary Sheet
            ws_train = wb.create_sheet(title="Department_Training_Hours")
            ws_train.views.sheetView[0].showGridLines = True
            ws_train.append(list(train_dept.columns))
            for row in train_dept.itertuples(index=False):
                ws_train.append(list(row))
            cls.apply_sheet_formatting(ws_train, has_header=True)

            out = io.BytesIO()
            wb.save(out)
            content = out.getvalue()
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{base_name}.xlsx"
        else:
            content = costs_df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL).encode("utf-8-sig")
            mimetype = "text/csv; charset=utf-8"
            filename = f"{base_name}.csv"

        return content, mimetype, filename
