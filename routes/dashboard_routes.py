"""
Workforce Intelligence — Dashboard Routes
Route and API endpoints for Page 1: Dashboard Overview.
"""
from flask import Blueprint, render_template, jsonify
from services.excel_service import ExcelService
from services.analytics_service import AnalyticsService
from services.prediction_service import PredictionService
from services.workforce_planning_service import WorkforcePlanningService
from services.recruitment_service import RecruitmentService
import config

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def dashboard_page():
    return render_template(
        "dashboard.html",
        active_page="dashboard",
        page_title="Dashboard Overview",
        page_subtitle="Employee Attrition & Workforce Planning",
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )

@dashboard_bp.route("/api/dashboard/overview")
def get_dashboard_overview():
    try:
        emp_df = ExcelService.get_sheet("Employees")
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")
        notice_df = ExcelService.get_sheet("Notice_Period")

        # 1. Top 6 KPIs
        total_employees = len(emp_df)
        historical_attrition = int(outcomes_df["Attrition_Within_6M"].sum())
        total_eligible = len(outcomes_df)
        historical_pct = round((historical_attrition / max(1, total_eligible)) * 100, 2)
        serving_notice = len(notice_df)

        pred_kpis = PredictionService.get_prediction_kpis()
        predicted_high_risk = pred_kpis["predicted_high_risk"]
        predicted_high_risk_pct = round((predicted_high_risk / max(1, total_eligible)) * 100, 2)

        wf_kpis = WorkforcePlanningService.get_summary_kpis()
        open_requisitions = wf_kpis["open_requisitions"]
        staffing_gap = wf_kpis["remaining_staffing_gap"]

        kpis = {
            "total_employees": total_employees,
            "historical_attrition": historical_attrition,
            "historical_attrition_pct": historical_pct,
            "total_eligible_outcomes": total_eligible,
            "serving_notice": serving_notice,
            "predicted_high_risk": predicted_high_risk,
            "predicted_high_risk_pct": predicted_high_risk_pct,
            "open_requisitions": open_requisitions,
            "staffing_gap": staffing_gap
        }

        # 2. Charts Data
        dept_charts = AnalyticsService.get_department_charts_data()

        # Attrition outcome distribution (Doughnut)
        stayed_count = total_eligible - historical_attrition
        attrition_distribution = {
            "total": total_eligible,
            "attrition_count": historical_attrition,
            "attrition_pct": historical_pct,
            "stayed_count": stayed_count,
            "stayed_pct": round(100.0 - historical_pct, 2)
        }

        # Employee Risk Distribution (Doughnut)
        risk_distribution = PredictionService.get_risk_distribution()

        # Notice Period monthly exits
        monthly_exits = WorkforcePlanningService.get_monthly_expected_exits()

        # Workforce Planning current vs target
        headcount_comparison = WorkforcePlanningService.get_headcount_analysis_by_department()

        # Candidate Funnel
        recruitment_funnel = RecruitmentService.get_candidate_funnel()

        # Recruitment Costs
        recruitment_costs = RecruitmentService.get_recruitment_costs()

        # Dynamic Quick Insights
        # Department with highest attrition
        highest_attr_dept = dept_charts["attrition_rate"]["departments"][0]
        highest_attr_rate = dept_charts["attrition_rate"]["rates"][0]

        quick_insights = [
            {
                "icon": "bi-graph-up-arrow",
                "color": "danger",
                "text": f"<b>{highest_attr_dept}</b> department has the highest attrition rate (<b>{highest_attr_rate}%</b>)."
            },
            {
                "icon": "bi-cpu-fill",
                "color": "purple",
                "text": f"<b>{predicted_high_risk:,}</b> employees are predicted as high risk. Consider proactive retention actions."
            },
            {
                "icon": "bi-calendar-event",
                "color": "warning",
                "text": f"<b>{serving_notice:,}</b> employees currently serving notice with confirmed exit schedules."
            },
            {
                "icon": "bi-briefcase-fill",
                "color": "success",
                "text": f"<b>{staffing_gap:,}</b> additional positions may be required after filling all open requisitions."
            },
            {
                "icon": "bi-people-fill",
                "color": "primary",
                "text": f"Recruitment pipeline has <b>{recruitment_funnel['total_candidates']:,}</b> active candidates across evaluation stages."
            },
            {
                "icon": "bi-currency-rupee",
                "color": "info",
                "text": f"Average recruitment cost per hire is <b>{recruitment_costs['avg_cost_formatted']}</b> (across 1,617 completed hires)."
            }
        ]

        return jsonify({
            "success": True,
            "kpis": kpis,
            "headcount_by_department": dept_charts["headcount"],
            "attrition_outcome_distribution": attrition_distribution,
            "attrition_rate_by_department": dept_charts["attrition_rate"],
            "attrition_rate_by_department_aligned": dept_charts["attrition_rate_aligned"],
            "risk_distribution": risk_distribution,
            "notice_monthly_exits": monthly_exits,
            "workforce_target_comparison": headcount_comparison,
            "recruitment_funnel": recruitment_funnel,
            "recruitment_costs": recruitment_costs,
            "quick_insights": quick_insights
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
