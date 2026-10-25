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
    def get_filtered_employees(
        cls,
        department: Optional[str] = None,
        job_role: Optional[str] = None,
        job_level: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        min_tenure: Optional[int] = None,
        max_tenure: Optional[int] = None,
    ) -> pd.DataFrame:
        """Centralized helper to filter master employee records consistently."""
        emp_df = ExcelService.get_sheet("Employees")
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
            try:
                min_t = int(min_tenure)
                filtered = filtered[filtered["Tenure_Months_At_Prediction"] >= min_t]
            except (ValueError, TypeError):
                pass
        if max_tenure is not None:
            try:
                max_t = int(max_tenure)
                filtered = filtered[filtered["Tenure_Months_At_Prediction"] <= max_t]
            except (ValueError, TypeError):
                pass
        return filtered

    @classmethod
    def get_kpis(
        cls,
        department: Optional[str] = None,
        job_role: Optional[str] = None,
        job_level: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        min_tenure: Optional[int] = None,
        max_tenure: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculates top KPI cards for Analytics Page using applied filters."""
        filtered = cls.get_filtered_employees(
            department=department,
            job_role=job_role,
            job_level=job_level,
            location=location,
            employment_type=employment_type,
            min_tenure=min_tenure,
            max_tenure=max_tenure
        )

        total_emp = len(filtered)
        depts_count = int(filtered["Department"].nunique()) if total_emp > 0 else 0
        roles_count = int(filtered["Job_Role"].nunique()) if total_emp > 0 else 0
        avg_tenure = round(float(filtered["Tenure_Months_At_Prediction"].mean()), 1) if total_emp > 0 else 0.0
        avg_satisfaction = round(float(filtered["Job_Satisfaction_Score_1_5"].mean()), 1) if total_emp > 0 else 0.0
        avg_training = round(float(filtered["Training_Hours_Last_12M"].mean()), 1) if total_emp > 0 else 0.0
        avg_overtime = round(float(filtered["Overtime_Hours_Monthly"].mean()), 1) if total_emp > 0 else 0.0

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
    def get_department_charts_data(
        cls,
        department: Optional[str] = None,
        job_role: Optional[str] = None,
        job_level: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        min_tenure: Optional[int] = None,
        max_tenure: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculates department-level metrics for the four decision-focused Employee Analytics charts.
        Accurately joins eligible outcomes for attrition rates using applied filters.
        """
        outcomes_df = ExcelService.get_sheet("Attrition_Outcomes")
        filtered_emp = cls.get_filtered_employees(
            department=department,
            job_role=job_role,
            job_level=job_level,
            location=location,
            employment_type=employment_type,
            min_tenure=min_tenure,
            max_tenure=max_tenure
        )

        if len(filtered_emp) == 0:
            return {
                "headcount": {"departments": [], "values": [], "total": 0},
                "gender_by_department": {
                    "departments": [], "male": [], "female": [],
                    "non_disclosed": [], "unknown": [], "available": "Gender" in filtered_emp.columns
                },
                "attrition_rate": {"departments": [], "rates": []},
                "attrition_rate_aligned": {"departments": [], "rates": []},
                "tenure": {"departments": [], "values": []},
                "satisfaction": {"departments": [], "values": []},
                "performance": {"departments": [], "values": []},
                "work_life_balance": {"departments": [], "values": []},
                "overtime": {"departments": [], "values": []},
                "training": {"departments": [], "values": []}
            }

        # Headcount by department
        headcount_series = filtered_emp["Department"].value_counts().sort_values(ascending=False)
        departments = headcount_series.index.tolist()
        headcounts = [int(value) for value in headcount_series.values.tolist()]

        # Gender breakdown is returned for chart tooltips only (not KPI cards).
        # Never infer gender from employee names; use the workbook's Gender field.
        gender_counts = {"male": [], "female": [], "non_disclosed": [], "unknown": []}
        gender_available = "Gender" in filtered_emp.columns
        if gender_available:
            normalized_gender = filtered_emp["Gender"].astype("string").str.strip().str.casefold()
            for dept in departments:
                dept_gender = normalized_gender[filtered_emp["Department"] == dept]
                gender_counts["male"].append(int(dept_gender.isin(["male", "m"]).sum()))
                gender_counts["female"].append(int(dept_gender.isin(["female", "f"]).sum()))
                gender_counts["non_disclosed"].append(int(dept_gender.isin([
                    "non-disclosed", "non disclosed", "not disclosed", "prefer not to say", "undisclosed"
                ]).sum()))
                gender_counts["unknown"].append(int((dept_gender.isna() | ~dept_gender.isin([
                    "male", "m", "female", "f", "non-disclosed", "non disclosed",
                    "not disclosed", "prefer not to say", "undisclosed"
                ])).sum()))
        else:
            for key in gender_counts:
                gender_counts[key] = [None for _ in departments]

        gender_by_department = {
            "departments": departments,
            **gender_counts,
            "available": gender_available
        }

        # Attrition rate by department
        # Merge eligible employees with outcomes
        eligible_emp = filtered_emp[filtered_emp["Serving_Notice_As_Of_Prediction"] == False]
        merged_outcomes = eligible_emp.merge(outcomes_df, on="Employee_ID", how="inner")
        
        dept_attr_rates = []
        for dept in departments:
            dept_cohort = merged_outcomes[merged_outcomes["Department"] == dept]
            if len(dept_cohort) > 0:
                pos = pd.to_numeric(dept_cohort["Attrition_Within_6M"], errors="coerce").sum()
                rate = round((float(pos) / len(dept_cohort)) * 100, 1)
            else:
                # No eligible outcome records means unavailable, not a real 0% rate.
                rate = None
            dept_attr_rates.append({"department": dept, "attrition_rate": rate})

        # Sort attrition rate descending
        dept_attr_rates_sorted = sorted(
            dept_attr_rates,
            key=lambda x: (x["attrition_rate"] is not None, x["attrition_rate"] if x["attrition_rate"] is not None else -1),
            reverse=True
        )

        # Null-safe aggregation shared by all department-level metrics.
        # Missing metric data is returned as null (displayed as N/A), not a false zero.
        def safe_group_mean(column: str) -> List[Optional[float]]:
            if column not in filtered_emp.columns:
                return [None for _ in departments]
            numeric = pd.to_numeric(filtered_emp[column], errors="coerce")
            grouped = numeric.groupby(filtered_emp["Department"]).mean()
            result = []
            for dept in departments:
                value = grouped.get(dept)
                result.append(round(float(value), 2) if pd.notna(value) else None)
            return result

        # Average tenure by department
        tenure_values = safe_group_mean("Tenure_Months_At_Prediction")

        # Job satisfaction, performance and work-life balance by department.
        sat_values = safe_group_mean("Job_Satisfaction_Score_1_5")
        performance_values = safe_group_mean("Performance_Rating_1_5")
        work_life_balance_values = safe_group_mean("Work_Life_Balance_Score_1_5")

        # Average overtime hours by department
        overtime_values = safe_group_mean("Overtime_Hours_Monthly")

        # Training hours by department
        training_values = safe_group_mean("Training_Hours_Last_12M")

        return {
            "headcount": {
                "departments": departments,
                "values": headcounts,
                "total": sum(headcounts)
            },
            "gender_by_department": gender_by_department,
            "attrition_rate": {
                "departments": [item["department"] for item in dept_attr_rates_sorted],
                "rates": [item["attrition_rate"] for item in dept_attr_rates_sorted]
            },
            # Same department order as headcount, specifically for combo charts.
            "attrition_rate_aligned": {
                "departments": departments,
                "rates": [
                    next(
                        (item["attrition_rate"] for item in dept_attr_rates
                         if item["department"] == dept),
                        None
                    )
                    for dept in departments
                ]
            },
            "tenure": {
                "departments": departments,
                "values": tenure_values
            },
            "satisfaction": {
                "departments": departments,
                "values": sat_values
            },
            "performance": {
                "departments": departments,
                "values": performance_values
            },
            "work_life_balance": {
                "departments": departments,
                "values": work_life_balance_values
            },
            "overtime": {
                "departments": departments,
                "values": overtime_values
            },
            "training": {
                "departments": departments,
                "values": training_values
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

        filtered = cls.get_filtered_employees(
            department=department,
            job_role=job_role,
            job_level=job_level,
            location=location,
            employment_type=employment_type,
            min_tenure=min_tenure,
            max_tenure=max_tenure
        )

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
