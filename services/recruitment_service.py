"""
Workforce Intelligence — Recruitment Service
Calculates candidate funnel conversions and recruitment cost breakdowns.
"""
import logging
from typing import Dict, List, Any
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
    # In Indian numbering, commas are placed every 2 digits after the first 3
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

        # Specific stage counts
        applied_raw = stage_counts.get("Applied", 0)
        screening_raw = stage_counts.get("Screening", 0)
        interview_raw = stage_counts.get("Interview", 0)
        offer_raw = stage_counts.get("Offer", 0)
        hired_raw = stage_counts.get("Hired", 0)
        declined_raw = stage_counts.get("Offer Declined", 0)
        withdrawn_raw = stage_counts.get("Withdrawn", 0)
        rejected_raw = stage_counts.get("Rejected", 0)

        # Cumulative funnel stages (everyone applied; candidates who reached screening or beyond)
        cumulative_hired = hired_raw
        cumulative_offer = cumulative_hired + offer_raw + declined_raw
        cumulative_interview = cumulative_offer + interview_raw
        cumulative_screening = cumulative_interview + screening_raw
        cumulative_applied = total_applied

        return {
            "total_candidates": total_applied,
            "stages": [
                {"stage": "Applied", "count": cumulative_applied, "color": "#0D63F3"},
                {"stage": "Screening", "count": cumulative_screening, "color": "#00B4D8"},
                {"stage": "Interview", "count": cumulative_interview, "color": "#22B573"},
                {"stage": "Offer", "count": cumulative_offer, "color": "#FFA726"},
                {"stage": "Hired", "count": cumulative_hired, "color": "#10B981"}
            ],
            "rejected_count": rejected_raw,
            "withdrawn_count": withdrawn_raw,
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
        
        total_cost = float(costs_df["Total_Recruitment_Cost_INR"].sum())
        total_requisitions = len(costs_df)
        avg_cost = total_cost / max(1, total_requisitions)

        recruiter_cost = float(costs_df["Recruiter_Cost_INR"].sum())
        advertising_cost = float(costs_df["Advertising_Cost_INR"].sum())
        agency_cost = float(costs_df["Agency_Cost_INR"].sum())
        assessment_cost = float(costs_df["Assessment_Cost_INR"].sum())

        return {
            "total_cost_numeric": total_cost,
            "total_cost_formatted": format_inr(total_cost),
            "avg_cost_numeric": round(avg_cost),
            "avg_cost_formatted": format_inr(avg_cost),
            "total_requisitions": total_requisitions,
            "categories": {
                "recruiter": {
                    "label": "Recruiter Cost",
                    "numeric": recruiter_cost,
                    "formatted": format_inr(recruiter_cost)
                },
                "advertising": {
                    "label": "Advertising Cost",
                    "numeric": advertising_cost,
                    "formatted": format_inr(advertising_cost)
                },
                "agency": {
                    "label": "Agency Cost",
                    "numeric": agency_cost,
                    "formatted": format_inr(agency_cost)
                },
                "assessment": {
                    "label": "Assessment Cost",
                    "numeric": assessment_cost,
                    "formatted": format_inr(assessment_cost)
                }
            }
        }
