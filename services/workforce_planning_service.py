"""
Workforce Intelligence — Workforce Planning & Exit Analysis Service
Handles notice-period tracking, scenario planning, and department staffing targets.
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from services.excel_service import ExcelService
from services.prediction_service import PredictionService

logger = logging.getLogger(__name__)

class WorkforcePlanningService:
    @classmethod
    def get_summary_kpis(cls) -> Dict[str, Any]:
        """Calculates top KPI cards for Workforce Planning Page."""
        emp_df = ExcelService.get_sheet("Employees")
        notice_df = ExcelService.get_sheet("Notice_Period")
        wp_df = ExcelService.get_sheet("Workforce_Planning")
        pred_kpis = PredictionService.get_prediction_kpis()

        current_headcount = len(emp_df)
        serving_notice = len(notice_df)
        predicted_exits = pred_kpis["predicted_high_risk"]
        
        target_headcount = int(wp_df["Target_Headcount_Illustrative"].sum())
        open_positions = int(wp_df["Open_Requisition_Positions_Estimate"].sum())

        # Formula: Gap = max(0, Target - (Current - Notice - Predicted + Open))
        projected_staff = current_headcount - serving_notice - predicted_exits + open_positions
        staffing_gap = max(0, target_headcount - projected_staff)

        return {
            "current_headcount": current_headcount,
            "employees_serving_notice": serving_notice,
            "expected_additional_exits": predicted_exits,
            "target_headcount": target_headcount,
            "open_requisitions": open_positions,
            "remaining_staffing_gap": staffing_gap,
            "total_expected_exits": serving_notice + predicted_exits
        }

    @classmethod
    def get_headcount_analysis_by_department(cls) -> Dict[str, Any]:
        """Provides current vs target headcount by department for bar chart."""
        wp_df = ExcelService.get_sheet("Workforce_Planning")
        depts = wp_df["Department"].tolist()
        current = wp_df["Total_Employees_In_Snapshot"].tolist()
        target = wp_df["Target_Headcount_Illustrative"].tolist()
        gap = wp_df["Planning_Gap_After_Open_Requisition_Estimate"].tolist()

        return {
            "departments": depts,
            "current_headcount": current,
            "target_headcount": target,
            "gap_after_open": gap
        }

    @classmethod
    def get_expected_exits_breakdown(cls) -> Dict[str, Any]:
        """Provides donut breakdown of confirmed notice vs predicted exits."""
        kpis = cls.get_summary_kpis()
        total_exits = kpis["total_expected_exits"]
        notice_count = kpis["employees_serving_notice"]
        pred_count = kpis["expected_additional_exits"]

        notice_pct = round((notice_count / max(1, total_exits)) * 100, 1)
        pred_pct = round((pred_count / max(1, total_exits)) * 100, 1)

        return {
            "total_expected_exits": total_exits,
            "categories": [
                {"label": "Serving Notice", "count": notice_count, "pct": notice_pct, "color": "#F04452"},
                {"label": "Predicted Additional Exits", "count": pred_count, "pct": pred_pct, "color": "#FFA726"}
            ]
        }

    @classmethod
    def get_monthly_expected_exits(cls) -> Dict[str, Any]:
        """
        Calculates confirmed monthly notice exits from Expected_Last_Working_Day,
        plus defensible scenario allocation of predicted exits over 6-month horizon.
        """
        notice_df = ExcelService.get_sheet("Notice_Period")
        kpis = cls.get_summary_kpis()
        predicted_total = kpis["expected_additional_exits"]

        # Parse months from actual Expected_Last_Working_Day
        dates = pd.to_datetime(notice_df["Expected_Last_Working_Day"])
        monthly_counts = dates.dt.to_period("M").value_counts()

        # Month labels across the 6-month horizon
        month_keys = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
        month_labels = ["Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026"]

        notice_by_month = []
        for mk in month_keys:
            val = int(monthly_counts.get(mk, 0))
            notice_by_month.append(val)

        # Distribute predicted additional exits as a scenario estimate
        # Weighted across the 6 months (higher in Q1 post-appraisal)
        weights = [0.18, 0.24, 0.20, 0.16, 0.12, 0.10]
        pred_by_month = [int(round(predicted_total * w)) for w in weights]
        
        # Adjust rounding difference on first month
        diff = predicted_total - sum(pred_by_month)
        pred_by_month[0] += diff

        return {
            "months": month_labels,
            "notice_exits": notice_by_month,
            "predicted_exits": pred_by_month,
            "total_monthly": [n + p for n, p in zip(notice_by_month, pred_by_month)]
        }

    @classmethod
    def get_department_exit_analysis_table(cls) -> Dict[str, Any]:
        """Computes comprehensive department-wise exit and gap analysis table."""
        wp_df = ExcelService.get_sheet("Workforce_Planning")
        emp_df = ExcelService.get_sheet("Employees")
        pred_df = PredictionService.get_predictions_df()

        rows = []
        for _, wp_row in wp_df.iterrows():
            dept = wp_row["Department"]
            current_hc = int(wp_row["Total_Employees_In_Snapshot"])
            notice_cnt = int(wp_row["Employees_Serving_Notice"])
            
            # Count high risk employees in this department
            dept_preds = pred_df[pred_df["Department"] == dept]
            high_risk_cnt = int((dept_preds["Risk_Level"] == "High").sum())
            total_exits = notice_cnt + high_risk_cnt

            target_hc = int(wp_row["Target_Headcount_Illustrative"])
            open_pos = int(wp_row["Open_Requisition_Positions_Estimate"])

            # Projected staff = current - exits + open
            projected = current_hc - total_exits + open_pos
            rem_gap = max(0, target_hc - projected)

            rows.append({
                "department": dept,
                "current_headcount": current_hc,
                "serving_notice": notice_cnt,
                "predicted_exits": high_risk_cnt,
                "total_expected_exits": total_exits,
                "target_headcount": target_hc,
                "open_positions": open_pos,
                "remaining_gap": rem_gap
            })

        # Calculate Total row
        totals = {
            "department": "Total",
            "current_headcount": sum(r["current_headcount"] for r in rows),
            "serving_notice": sum(r["serving_notice"] for r in rows),
            "predicted_exits": sum(r["predicted_exits"] for r in rows),
            "total_expected_exits": sum(r["total_expected_exits"] for r in rows),
            "target_headcount": sum(r["target_headcount"] for r in rows),
            "open_positions": sum(r["open_positions"] for r in rows),
            "remaining_gap": sum(r["remaining_gap"] for r in rows)
        }

        return {
            "rows": rows,
            "totals": totals
        }

    @classmethod
    def get_open_requisitions_by_department(cls) -> Dict[str, Any]:
        """Calculates open job requisitions per department for bar chart."""
        wp_df = ExcelService.get_sheet("Workforce_Planning")
        return {
            "departments": wp_df["Department"].tolist(),
            "open_positions": wp_df["Open_Requisition_Positions_Estimate"].tolist()
        }

    @classmethod
    def get_notice_period_distribution(cls) -> Dict[str, Any]:
        """Bins days remaining for notice period employees."""
        notice_df = ExcelService.get_sheet("Notice_Period")
        days = notice_df["Days_Remaining_As_Of_Prediction"]

        b0_15 = int(((days >= 0) & (days <= 15)).sum())
        b16_30 = int(((days > 15) & (days <= 30)).sum())
        b31_60 = int(((days > 30) & (days <= 60)).sum())
        b61_90 = int(((days > 60) & (days <= 90)).sum())

        return {
            "labels": ["0-15 days", "16-30 days", "31-60 days", "61-90 days"],
            "values": [b0_15, b16_30, b31_60, b61_90]
        }

    @classmethod
    def filter_and_paginate_notice_employees(
        cls,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """Paginates and enriches employees currently serving notice."""
        notice_df = ExcelService.get_sheet("Notice_Period")
        emp_df = ExcelService.get_sheet("Employees")

        merged = notice_df.merge(
            emp_df[["Employee_ID", "Employee_Name", "Department", "Job_Role"]],
            on="Employee_ID",
            how="left"
        )

        filtered = merged
        if search_query:
            q = str(search_query).strip().lower()
            name_m = filtered["Employee_Name"].str.lower().str.contains(q, na=False)
            id_m = filtered["Employee_ID"].str.lower().str.contains(q, na=False)
            dept_m = filtered["Department"].str.lower().str.contains(q, na=False)
            filtered = filtered[name_m | id_m | dept_m]

        total_records = len(filtered)
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_slice = filtered.iloc[start_idx:end_idx]

        records = []
        for _, row in page_slice.iterrows():
            start_dt = str(row["Notice_Start_Date"])[:10]
            last_dt = str(row["Expected_Last_Working_Day"])[:10]
            records.append({
                "employee_id": row["Employee_ID"],
                "employee_name": row.get("Employee_Name", row["Employee_ID"]),
                "department": row["Department"],
                "job_role": row["Job_Role"],
                "notice_start_date": start_dt,
                "expected_last_working_day": last_dt,
                "days_remaining": int(row["Days_Remaining_As_Of_Prediction"]),
                "notice_status": "Active"
            })

        return {
            "records": records,
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    @classmethod
    def calculate_scenario(
        cls,
        current_headcount: int,
        expected_additional_exits: int,
        open_positions_to_fill: int,
        target_headcount: int
    ) -> Dict[str, int]:
        """
        Interactive scenario planner calculation:
        Projected Available Staff = Current - Serving Notice (2,028) - Expected Additional Exits + Open Positions
        New Staffing Gap = max(0, Target - Projected Available Staff)
        """
        notice_df = ExcelService.get_sheet("Notice_Period")
        known_notice = len(notice_df)

        projected = current_headcount - known_notice - expected_additional_exits + open_positions_to_fill
        new_gap = max(0, target_headcount - projected)

        return {
            "projected_available_staff": projected,
            "new_staffing_gap": new_gap
        }

    @classmethod
    def get_quick_insights(cls) -> List[Dict[str, str]]:
        """Generates dynamic workforce planning insights."""
        kpis = cls.get_summary_kpis()
        table_data = cls.get_department_exit_analysis_table()
        
        # Department with highest expected exits
        sorted_depts = sorted(table_data["rows"], key=lambda x: x["total_expected_exits"], reverse=True)
        top_dept = sorted_depts[0] if sorted_depts else None

        insights = [
            {
                "icon": "bi-graph-up-arrow",
                "color": "danger",
                "text": f"<b>{kpis['total_expected_exits']:,}</b> employees are expected to exit over the next 6-month horizon."
            }
        ]

        if top_dept:
            insights.append({
                "icon": "bi-building-gear",
                "color": "primary",
                "text": f"<b>{top_dept['department']}</b> department has the highest expected exits (<b>{top_dept['total_expected_exits']:,}</b>)."
            })

        insights.extend([
            {
                "icon": "bi-briefcase",
                "color": "success",
                "text": f"<b>{kpis['remaining_staffing_gap']:,}</b> additional positions may be required after filling all open requisitions."
            },
            {
                "icon": "bi-calendar-event",
                "color": "warning",
                "text": "<b>January 2026</b> represents the peak exit month driven by contractual 30-day notice periods."
            },
            {
                "icon": "bi-person-badge",
                "color": "info",
                "text": f"<b>{kpis['open_requisitions']:,}</b> open positions are actively under requisition in the talent acquisition pipeline."
            },
            {
                "icon": "bi-bullseye",
                "color": "purple",
                "text": f"Target headcount is <b>{round((kpis['target_headcount'] - kpis['current_headcount']) / kpis['current_headcount'] * 100, 1)}%</b> above current staffing capacity."
            }
        ])

        return insights
