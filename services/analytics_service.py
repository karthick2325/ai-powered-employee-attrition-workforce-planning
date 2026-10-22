"""
Workforce Intelligence — Analytics Service
Calculates department-level workforce metrics, employee filtering, and comparisons.
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from services.excel_service import ExcelService
from services.prediction_service import PredictionService

logger = logging.getLogger(__name__)

class AnalyticsService:
    @classmethod
    def get_kpis(cls, department: Optional[str] = None) -> Dict[str, Any]:
        """Calculates top KPI cards for Analytics Page."""
        emp_df = ExcelService.get_sheet("Employees")
        
        filtered = emp_df
        if department and department != "All":
            filtered = filtered[filtered["Department"] == department]

        total_emp = len(filtered)
        depts_count = int(filtered["Department"].nunique())
        roles_count = int(filtered["Job_Role"].nunique())
        avg_tenure = round(float(filtered["Tenure_Months_At_Prediction"].mean()), 1) if total_emp > 0 else 0
        avg_satisfaction = round(float(filtered["Job_Satisfaction_Score_1_5"].mean()), 1) if total_emp > 0 else 0
        avg_training = round(float(filtered["Training_Hours_Last_12M"].mean()), 1) if total_emp > 0 else 0
        avg_overtime = round(float(filtered["Overtime_Hours_Monthly"].mean()), 1) if total_emp > 0 else 0

        return {
            "total_employees": total_emp,
            "total_departments": depts_count,
            "unique_job_roles": roles_count,
            "average_tenure_months": avg_tenure,
            "average_job_satisfaction": avg_satisfaction,
            "average_training_hours": avg_training,
            "average_overtime_hours": avg_overtime
        }

    @classmethod
    def get_department_charts_data(cls) -> Dict[str, Any]:
        """
        Calculates all 6 department-level charts for Analytics & Overview dashboards.
        Accurately joins eligible outcomes for attrition rates.
        """
        emp_df = ExcelService.get_sheet("Employees")
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")

        # Headcount by department
        headcount_series = emp_df["Department"].value_counts().sort_values(ascending=False)
        departments = headcount_series.index.tolist()
        headcounts = headcount_series.values.tolist()

        # Attrition rate by department
        # Merge eligible employees with outcomes
        eligible_emp = emp_df[emp_df["Serving_Notice_As_Of_Prediction"] == False]
        merged_outcomes = eligible_emp.merge(outcomes_df, on="Employee_ID", how="inner")
        
        dept_attr_rates = []
        for dept in departments:
            dept_cohort = merged_outcomes[merged_outcomes["Department"] == dept]
            if len(dept_cohort) > 0:
                pos = dept_cohort["Attrition_Within_6M"].sum()
                rate = round((pos / len(dept_cohort)) * 100, 1)
            else:
                rate = 0.0
            dept_attr_rates.append({"department": dept, "attrition_rate": rate})

        # Sort attrition rate descending
        dept_attr_rates_sorted = sorted(dept_attr_rates, key=lambda x: x["attrition_rate"], reverse=True)

        # Average tenure by department
        tenure_df = emp_df.groupby("Department")["Tenure_Months_At_Prediction"].mean().loc[departments].round(1)

        # Job satisfaction by department
        sat_df = emp_df.groupby("Department")["Job_Satisfaction_Score_1_5"].mean().loc[departments].round(1)

        # Average overtime hours by department
        overtime_df = emp_df.groupby("Department")["Overtime_Hours_Monthly"].mean().loc[departments].round(1)

        # Training hours by department
        training_df = emp_df.groupby("Department")["Training_Hours_Last_12M"].mean().loc[departments].round(1)

        return {
            "headcount": {
                "departments": departments,
                "values": headcounts,
                "total": sum(headcounts)
            },
            "attrition_rate": {
                "departments": [item["department"] for item in dept_attr_rates_sorted],
                "rates": [item["attrition_rate"] for item in dept_attr_rates_sorted]
            },
            "tenure": {
                "departments": departments,
                "values": tenure_df.values.tolist()
            },
            "satisfaction": {
                "departments": departments,
                "values": sat_df.values.tolist()
            },
            "overtime": {
                "departments": departments,
                "values": overtime_df.values.tolist()
            },
            "training": {
                "departments": departments,
                "values": training_df.values.tolist()
            }
        }

    @classmethod
    def get_filter_options(cls) -> Dict[str, Any]:
        """Provides dynamic distinct values for frontend filter controls."""
        emp_df = ExcelService.get_sheet("Employees")
        return {
            "departments": sorted(emp_df["Department"].unique().tolist()),
            "job_roles": sorted(emp_df["Job_Role"].unique().tolist()),
            "job_levels": sorted(emp_df["Job_Level"].unique().tolist()),
            "locations": sorted(emp_df["Location"].unique().tolist()),
            "employment_types": sorted(emp_df["Employment_Type"].unique().tolist()),
            "tenure_range": {
                "min": int(emp_df["Tenure_Months_At_Prediction"].min()),
                "max": int(emp_df["Tenure_Months_At_Prediction"].max())
            }
        }

    @classmethod
    def filter_and_paginate_employees(
        cls,
        department: Optional[str] = None,
        job_role: Optional[str] = None,
        job_level: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        min_tenure: Optional[int] = None,
        max_tenure: Optional[int] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "Employee_ID",
        ascending: bool = True
    ) -> Dict[str, Any]:
        """Filters, sorts, and paginates employees for the Employee Details table."""
        emp_df = ExcelService.get_sheet("Employees")
        pred_df = PredictionService.get_predictions_df()

        # Build risk lookup dict for fast enrichment
        risk_map = dict(zip(pred_df["Employee_ID"], pred_df["Risk_Level"]))

        filtered = emp_df
        if department and department != "All":
            filtered = filtered[filtered["Department"] == department]
        if job_role and job_role != "All":
            filtered = filtered[filtered["Job_Role"] == job_role]
        if job_level and job_level != "All":
            filtered = filtered[filtered["Job_Level"] == job_level]
        if location and location != "All":
            filtered = filtered[filtered["Location"] == location]
        if employment_type and employment_type != "All":
            filtered = filtered[filtered["Employment_Type"] == employment_type]
        if min_tenure is not None:
            filtered = filtered[filtered["Tenure_Months_At_Prediction"] >= min_tenure]
        if max_tenure is not None:
            filtered = filtered[filtered["Tenure_Months_At_Prediction"] <= max_tenure]

        if search_query:
            q = str(search_query).strip().lower()
            name_match = filtered["Employee_Name"].str.lower().str.contains(q, na=False)
            id_match = filtered["Employee_ID"].str.lower().str.contains(q, na=False)
            filtered = filtered[name_match | id_match]

        if sort_by in filtered.columns:
            filtered = filtered.sort_values(by=sort_by, ascending=ascending)

        total_records = len(filtered)
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_slice = filtered.iloc[start_idx:end_idx]

        records = []
        for _, row in page_slice.iterrows():
            eid = row["Employee_ID"]
            serving_notice = bool(row.get("Serving_Notice_As_Of_Prediction", False))
            risk_level = "Notice" if serving_notice else risk_map.get(eid, "Low")

            records.append({
                "employee_id": eid,
                "employee_name": row.get("Employee_Name", eid),
                "department": row["Department"],
                "job_role": row["Job_Role"],
                "job_level": row["Job_Level"],
                "location": row["Location"],
                "employment_type": row["Employment_Type"],
                "tenure_months": int(row["Tenure_Months_At_Prediction"]),
                "overtime_hours": int(row["Overtime_Hours_Monthly"]),
                "job_satisfaction": int(row["Job_Satisfaction_Score_1_5"]),
                "work_life_balance": int(row["Work_Life_Balance_Score_1_5"]),
                "training_hours": int(row["Training_Hours_Last_12M"]),
                "risk_level": risk_level,
                "notice_status": "Yes" if serving_notice else "No"
            })

        return {
            "records": records,
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    @classmethod
    def compare_departments(cls, dept1: str, dept2: str) -> Dict[str, Any]:
        """Calculates side-by-side comparative workforce metrics for two departments."""
        emp_df = ExcelService.get_sheet("Employees")
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")
        pred_df = PredictionService.get_predictions_df()

        eligible_emp = emp_df[emp_df["Serving_Notice_As_Of_Prediction"] == False]
        merged_outcomes = eligible_emp.merge(outcomes_df, on="Employee_ID", how="inner")

        def get_dept_stats(dept_name: str) -> Dict[str, Any]:
            dept_emp = emp_df[emp_df["Department"] == dept_name]
            count = len(dept_emp)
            if count == 0:
                return {}

            # Attrition rate
            cohort = merged_outcomes[merged_outcomes["Department"] == dept_name]
            attr_rate = round((cohort["Attrition_Within_6M"].sum() / max(1, len(cohort))) * 100, 1)

            # High risk employees
            dept_preds = pred_df[pred_df["Department"] == dept_name]
            high_risk_count = int((dept_preds["Risk_Level"] == "High").sum())

            # Notice employees
            notice_count = int(dept_emp["Serving_Notice_As_Of_Prediction"].sum())

            return {
                "headcount": count,
                "attrition_rate": f"{attr_rate}%",
                "avg_tenure": f"{round(float(dept_emp['Tenure_Months_At_Prediction'].mean()), 1)} months",
                "avg_overtime": f"{round(float(dept_emp['Overtime_Hours_Monthly'].mean()), 1)} hrs",
                "job_satisfaction": f"{round(float(dept_emp['Job_Satisfaction_Score_1_5'].mean()), 1)} / 5",
                "training_hours": f"{round(float(dept_emp['Training_Hours_Last_12M'].mean()), 1)} hrs",
                "high_risk_employees": high_risk_count,
                "employees_serving_notice": notice_count
            }

        return {
            "dept1": {"name": dept1, "metrics": get_dept_stats(dept1)},
            "dept2": {"name": dept2, "metrics": get_dept_stats(dept2)}
        }
