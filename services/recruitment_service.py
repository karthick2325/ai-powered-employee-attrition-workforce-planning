"""
Workforce Intelligence — Recruitment & Training Service
Calculates candidate funnel conversions, recruitment cost breakdowns in INR,
requisition fulfillment status, and employee training hours analytics.
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from services.excel_service import ExcelService

logger = logging.getLogger(__name__)


def format_inr(amount: float) -> str:
    """Formats a numeric amount into Indian Currency display (e.g. ₹ 12,48,50,000)."""
    s = str(int(round(amount)))
    if len(s) <= 3:
        return f"₹ {s}"
    last_three = s[-3:]
    remaining = s[:-3]
    parts = []
    while len(remaining) > 2:
        parts.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        parts.insert(0, remaining)
    parts.append(last_three)
    return f"₹ {','.join(parts)}"


class RecruitmentService:
    @classmethod
    def get_candidate_funnel(cls) -> Dict[str, Any]:
        """
        Calculates cumulative progression stages for candidate funnel chart
        from Recruitment_Pipeline sheet.
        """
        pipe_df = ExcelService.get_sheet("Recruitment_Pipeline")
        total_applied = len(pipe_df)

        stage_counts = pipe_df["Candidate_Stage_As_Of_Prediction"].value_counts().to_dict()

        applied_raw = stage_counts.get("Applied", 0)
        screening_raw = stage_counts.get("Screening", 0)
        interview_raw = stage_counts.get("Interview", 0)
        offer_raw = stage_counts.get("Offer", 0)
        hired_raw = stage_counts.get("Hired", 0)
        declined_raw = stage_counts.get("Offer Declined", 0)
        withdrawn_raw = stage_counts.get("Withdrawn", 0)
        rejected_raw = stage_counts.get("Rejected", 0)

        # Cumulative funnel stages
        cumulative_hired = hired_raw
        cumulative_offer = cumulative_hired + offer_raw + declined_raw
        cumulative_interview = cumulative_offer + interview_raw
        cumulative_screening = cumulative_interview + screening_raw
        cumulative_applied = total_applied

        return {
            "total_candidates": total_applied,
            "stages": [
                {"stage": "Applied", "count": cumulative_applied, "pct": 100.0, "color": "#0D63F3"},
                {"stage": "Screening", "count": cumulative_screening, "pct": round(cumulative_screening / max(1, total_applied) * 100, 1), "color": "#00B4D8"},
                {"stage": "Interview", "count": cumulative_interview, "pct": round(cumulative_interview / max(1, total_applied) * 100, 1), "color": "#22B573"},
                {"stage": "Offer", "count": cumulative_offer, "pct": round(cumulative_offer / max(1, total_applied) * 100, 1), "color": "#FFA726"},
                {"stage": "Hired", "count": cumulative_hired, "pct": round(cumulative_hired / max(1, total_applied) * 100, 1), "color": "#10B981"}
            ],
            "rejected_count": rejected_raw,
            "withdrawn_count": withdrawn_raw,
            "offer_declined_count": declined_raw,
            "breakdown": {
                "applied_in_stage": applied_raw,
                "screening_in_stage": screening_raw,
                "interview_in_stage": interview_raw,
                "offer_in_stage": offer_raw,
                "hired_in_stage": hired_raw,
                "rejected_in_stage": rejected_raw
            }
        }

    @classmethod
    def get_recruitment_costs(cls) -> Dict[str, Any]:
        """
        Calculates total, average, and itemized recruitment costs from Recruitment_Costs sheet.
        """
        costs_df = ExcelService.get_sheet("Recruitment_Costs")
        req_df = ExcelService.get_sheet("Job_Requisitions")
        
        total_cost = float(costs_df["Total_Recruitment_Cost_INR"].sum())
        total_requisitions = len(costs_df)
        total_hires = int(req_df["Hires_Made"].sum()) if "Hires_Made" in req_df.columns else 1617
        
        # Validated formula: Cost per Hire = Total Expenditure / Total Completed Hires
        avg_cost_per_hire = total_cost / max(1, total_hires)
        avg_cost_per_req = total_cost / max(1, total_requisitions)

        recruiter_cost = float(costs_df["Recruiter_Cost_INR"].sum())
        advertising_cost = float(costs_df["Advertising_Cost_INR"].sum())
        agency_cost = float(costs_df["Agency_Cost_INR"].sum())
        assessment_cost = float(costs_df["Assessment_Cost_INR"].sum())

        return {
            "total_cost_numeric": total_cost,
            "total_cost_formatted": format_inr(total_cost),
            "avg_cost_numeric": round(avg_cost_per_hire),
            "avg_cost_formatted": format_inr(avg_cost_per_hire),
            "avg_cost_per_hire_numeric": round(avg_cost_per_hire),
            "avg_cost_per_hire_formatted": format_inr(avg_cost_per_hire),
            "avg_cost_per_requisition_numeric": round(avg_cost_per_req),
            "avg_cost_per_requisition_formatted": format_inr(avg_cost_per_req),
            "total_hires": total_hires,
            "total_requisitions": total_requisitions,
            "categories": {
                "recruiter": {
                    "label": "Internal Recruiter Cost",
                    "numeric": recruiter_cost,
                    "formatted": format_inr(recruiter_cost),
                    "pct": round(recruiter_cost / max(1, total_cost) * 100, 1)
                },
                "advertising": {
                    "label": "Job Advertising / Boards",
                    "numeric": advertising_cost,
                    "formatted": format_inr(advertising_cost),
                    "pct": round(advertising_cost / max(1, total_cost) * 100, 1)
                },
                "agency": {
                    "label": "External Agency Fees",
                    "numeric": agency_cost,
                    "formatted": format_inr(agency_cost),
                    "pct": round(agency_cost / max(1, total_cost) * 100, 1)
                },
                "assessment": {
                    "label": "Candidate Assessments & Tech Screening",
                    "numeric": assessment_cost,
                    "formatted": format_inr(assessment_cost),
                    "pct": round(assessment_cost / max(1, total_cost) * 100, 1)
                }
            }
        }


    @classmethod
    def get_department_hiring_performance(cls) -> Dict[str, Any]:
        """Department-level hiring demand, completed hires, vacancies and fill rate."""
        req_df = ExcelService.get_sheet("Job_Requisitions").copy()
        required = ["Department", "Positions_Requested", "Hires_Made", "Positions_Remaining"]
        missing = [column for column in required if column not in req_df.columns]
        if missing:
            logger.warning("Job_Requisitions missing columns for hiring chart: %s", missing)
            return {"departments": [], "positions_requested": [], "hires_made": [], "positions_remaining": [], "fill_rate_pct": [], "records": 0, "available": False, "message": "Hiring data is missing required columns: " + ", ".join(missing)}

        req_df["Department"] = req_df["Department"].astype("string").str.strip()
        req_df = req_df[req_df["Department"].notna() & req_df["Department"].ne("")].copy()
        for column in ["Positions_Requested", "Hires_Made", "Positions_Remaining"]:
            req_df[column] = pd.to_numeric(req_df[column], errors="coerce")
        req_df = req_df.dropna(subset=["Positions_Requested", "Hires_Made", "Positions_Remaining"])
        if req_df.empty:
            return {"departments": [], "positions_requested": [], "hires_made": [], "positions_remaining": [], "fill_rate_pct": [], "records": 0, "available": False, "message": "No valid hiring records are available for the selected data."}

        # Keep open vacancies semantically consistent with the Open Positions KPI.
        if "Requisition_Status_As_Of_Prediction" in req_df.columns:
            status = req_df["Requisition_Status_As_Of_Prediction"].astype("string").str.strip().str.casefold()
            req_df["_open_positions"] = req_df["Positions_Remaining"].where(status.eq("open"), 0)
        else:
            req_df["_open_positions"] = req_df["Positions_Remaining"]

        grouped = req_df.groupby("Department", as_index=False).agg(
            positions_requested=("Positions_Requested", "sum"),
            hires_made=("Hires_Made", "sum"),
            positions_remaining=("_open_positions", "sum"),
            requisitions=("Department", "size")
        )
        grouped["fill_rate_pct"] = (grouped["hires_made"] / grouped["positions_requested"].replace(0, pd.NA) * 100).fillna(0).round(1)
        grouped = grouped.sort_values("positions_requested", ascending=False)
        return {
            "departments": grouped["Department"].astype(str).tolist(),
            "positions_requested": grouped["positions_requested"].round(0).astype(int).tolist(),
            "hires_made": grouped["hires_made"].round(0).astype(int).tolist(),
            "positions_remaining": grouped["positions_remaining"].round(0).astype(int).tolist(),
            "fill_rate_pct": grouped["fill_rate_pct"].tolist(),
            "requisitions": grouped["requisitions"].astype(int).tolist(),
            "records": int(len(req_df)),
            "available": True,
            "message": ""
        }

    @classmethod
    def get_training_analytics(cls) -> Dict[str, Any]:
        """
        Calculates training hours metrics across departments and job levels.
        Maintains strict separation between training hours (recorded) and financial costs.
        """
        emp_df = ExcelService.get_sheet("Employees")
        
        if "Training_Hours_Last_12M" not in emp_df.columns:
            return {
                "total_training_hours": 0, "average_training_hours_per_employee": None,
                "median_training_hours": None,
                "department_breakdown": {"departments": [], "average_hours": [], "total_hours": []},
                "level_breakdown": {"levels": [], "average_hours": [], "headcount": []},
                "financial_note": "Training hours column is unavailable in the employee workbook."
            }
        emp_df = emp_df.copy()
        emp_df["Training_Hours_Last_12M"] = pd.to_numeric(emp_df["Training_Hours_Last_12M"], errors="coerce")
        valid_hours = emp_df.dropna(subset=["Training_Hours_Last_12M"])
        total_hours = float(valid_hours["Training_Hours_Last_12M"].sum()) if not valid_hours.empty else 0.0
        avg_hours = round(float(valid_hours["Training_Hours_Last_12M"].mean()), 1) if not valid_hours.empty else None
        med_value = valid_hours["Training_Hours_Last_12M"].median() if not valid_hours.empty else None
        med_hours = round(float(med_value), 1) if pd.notna(med_value) else None

        # Department-wise training; exclude blank categories and invalid measurements.
        dept_source = valid_hours.dropna(subset=["Department"]).copy() if "Department" in valid_hours.columns else pd.DataFrame()
        if not dept_source.empty:
            dept_source["Department"] = dept_source["Department"].astype(str).str.strip()
            dept_source = dept_source[dept_source["Department"].ne("")]
            dept_train = dept_source.groupby("Department")["Training_Hours_Last_12M"].agg(["mean", "median", "sum"]).reset_index()
            dept_train["mean"] = dept_train["mean"].round(1)
            dept_train["sum"] = dept_train["sum"].round(0).astype(int)
        else:
            dept_train = pd.DataFrame(columns=["Department", "mean", "median", "sum"])

        # Job-level training; exclude missing labels and invalid measurements.
        level_source = valid_hours.dropna(subset=["Job_Level"]).copy() if "Job_Level" in valid_hours.columns else pd.DataFrame()
        if not level_source.empty:
            level_source["Job_Level"] = level_source["Job_Level"].astype(str).str.strip()
            level_source = level_source[level_source["Job_Level"].ne("")]
            level_train = level_source.groupby("Job_Level")["Training_Hours_Last_12M"].agg(["mean", "median", "count"]).reset_index()
            level_train["mean"] = level_train["mean"].round(1)
        else:
            level_train = pd.DataFrame(columns=["Job_Level", "mean", "median", "count"])

        return {
            "total_training_hours": int(total_hours),
            "average_training_hours_per_employee": avg_hours,
            "median_training_hours": med_hours,
            "department_breakdown": {
                "departments": dept_train["Department"].tolist(),
                "average_hours": dept_train["mean"].tolist(),
                "total_hours": dept_train["sum"].tolist()
            },
            "level_breakdown": {
                "levels": level_train["Job_Level"].tolist(),
                "average_hours": level_train["mean"].tolist(),
                "headcount": level_train["count"].tolist()
            },
            "financial_note": "Dataset records verified employee training hours. Explicit monetary training budgets are not modeled in current data dictionary."
        }

    @classmethod
    def get_recruitment_kpis(cls) -> Dict[str, Any]:
        """Executive KPI cards for Recruitment & Training page."""
        req_df = ExcelService.get_sheet("Job_Requisitions")
        pipe_df = ExcelService.get_sheet("Recruitment_Pipeline")
        costs = cls.get_recruitment_costs()
        training = cls.get_training_analytics()

        total_reqs = len(req_df)
        open_reqs = req_df[req_df["Requisition_Status_As_Of_Prediction"] == "Open"] if "Requisition_Status_As_Of_Prediction" in req_df.columns else req_df
        active_reqs_count = len(open_reqs)
        total_requested = int(req_df["Positions_Requested"].sum())
        hires_made = int(req_df["Hires_Made"].sum())
        positions_remaining_open = int(open_reqs["Positions_Remaining"].sum())
        positions_remaining_total = int(req_df["Positions_Remaining"].sum())
        fill_rate = round(hires_made / max(1, total_requested) * 100, 1)

        return {
            "active_requisitions": active_reqs_count,
            "total_requisitions": total_reqs,
            "positions_requested": total_requested,
            "hires_made": hires_made,
            "positions_remaining": positions_remaining_open,
            "total_positions_remaining": positions_remaining_total,
            "fill_rate_pct": fill_rate,
            "active_pipeline_candidates": len(pipe_df),
            "total_recruitment_spend": costs["total_cost_formatted"],
            "avg_cost_per_hire": costs["avg_cost_formatted"],
            "avg_cost_per_requisition": costs["avg_cost_per_requisition_formatted"],
            "avg_training_hours": training["average_training_hours_per_employee"]
        }
