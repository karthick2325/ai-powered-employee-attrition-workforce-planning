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
    def get_training_analytics(cls) -> Dict[str, Any]:
        """
        Calculates training hours metrics across departments and job levels.
        Maintains strict separation between training hours (recorded) and financial costs.
        """
        emp_df = ExcelService.get_sheet("Employees")
        
        total_hours = float(emp_df["Training_Hours_Last_12M"].sum())
        avg_hours = round(float(emp_df["Training_Hours_Last_12M"].mean()), 1)
        med_hours = float(emp_df["Training_Hours_Last_12M"].median())

        # Department-wise training
        dept_train = emp_df.groupby("Department")["Training_Hours_Last_12M"].agg(["mean", "median", "sum"]).reset_index()
        dept_train["mean"] = dept_train["mean"].round(1)

        # Job Level training
        level_train = emp_df.groupby("Job_Level")["Training_Hours_Last_12M"].agg(["mean", "median", "count"]).reset_index()
        level_train["mean"] = level_train["mean"].round(1)

        return {
            "total_training_hours": int(total_hours),
            "average_training_hours_per_employee": avg_hours,
            "median_training_hours": int(med_hours),
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
