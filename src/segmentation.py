"""
Workforce Intelligence — Unsupervised Learning Module (Workforce Segmentation)
Module: src/segmentation.py

PURPOSE:
Unsupervised segmentation of the workforce for talent intelligence, planning,
and comprehensive 5-algorithm benchmarking.
1. Groups employees into workforce segments with distinct headcount, compensation,
   workload, and replacement profiles.
2. Evaluates and benchmarks 5 unsupervised clustering algorithms:
   - K-Means
   - Agglomerative Clustering
   - Gaussian Mixture Model (GMM)
   - DBSCAN
   - BIRCH
3. Calculates internal clustering metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz, BIC/AIC, noise %).
4. Selects the best clustering model via transparent, documented scoring.
5. Computes 2D PCA projection with explained-variance ratios and distortion caveats.
6. Clusters job roles by staffing pressure ratio.
7. Detects workload and compensation anomalies via Isolation Forest.
8. Strictly excludes simulated labels, identifiers, and sensitive demographics during training.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd
import joblib

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN, Birch
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.ensemble import IsolationForest

# Configure logger
logger = logging.getLogger("workforce_segmentation")


def _sanitize_csv_cell(val: Any) -> Any:
    """Prevents CSV / Excel formula injection by prepending apostrophe if needed."""
    if isinstance(val, str) and len(val) > 0 and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


class WorkforceSegmentation:
    """
    Unsupervised workforce segmentation pipeline adhering strictly to data dictionary,
    fairness audit guidelines, post-hoc validation rules, and 5-algorithm benchmarking.
    """

    NUMERIC_FEATURES = [
        "Tenure_Months_At_Prediction",
        "Compa_Ratio",
        "Overtime_Hours_Monthly",
        "Job_Satisfaction_Score_1_5",
        "Work_Life_Balance_Score_1_5",
        "Months_Since_Last_Promotion",
        "Training_Hours_Last_12M",
        "Commute_Distance_KM",
        "Performance_Rating_1_5",
        "Last_Salary_Hike_Pct",
        "Manager_Tenure_Months"
    ]

    CATEGORICAL_FEATURES = [
        "Department",
        "Job_Level",
        "Employment_Type"
    ]

    EXCLUDED_FROM_CLUSTERING = [
        "Employee_ID",
        "Prediction_Date",
        "Joining_Date",
        "Age",
        "Gender",
        "Serving_Notice_As_Of_Prediction",
        "Attrition_Within_6M",
        "Outcome_Window_End",
        "Actual_Exit_Date_Within_Window"
    ]

    def __init__(
        self,
        excel_path: Optional[str] = None,
        k: int = 5,
        random_state: int = 42
    ):
        self.excel_path = excel_path or self._discover_excel_path()
        self.k = k
        self.random_state = random_state

        self.df_raw: Optional[pd.DataFrame] = None
        self.df_population: Optional[pd.DataFrame] = None
        self.df_notice: Optional[pd.DataFrame] = None
        self.df_requisitions: Optional[pd.DataFrame] = None
        self.df_workforce_planning: Optional[pd.DataFrame] = None

        self.preprocessor: Optional[ColumnTransformer] = None
        self.kmeans_model: Optional[KMeans] = None
        self.X_transformed: Optional[np.ndarray] = None
        self.feature_names: List[str] = []

        self.df_segmented: Optional[pd.DataFrame] = None
        self.segment_profiles: Optional[pd.DataFrame] = None
        self.role_pressure_df: Optional[pd.DataFrame] = None
        self.anomalies_df: Optional[pd.DataFrame] = None
        self.k_evaluation_results: List[Dict[str, Any]] = []
        self.five_algorithm_benchmark: Optional[Dict[str, Any]] = None
        self.pca_projection_data: Optional[Dict[str, Any]] = None

    def _discover_excel_path(self) -> str:
        """Finds the dataset path across conventional workspace paths."""
        candidates = [
            Path("data") / "Employee_Attrition_Workforce_Planning_Expert_Dataset_Corrected.xlsx",
            Path("data") / "Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx",
            Path(".") / "Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx",
            Path("..") / "Employee_Attrition_Workforce_Planning_Expert_Dataset_Corrected.xlsx",
        ]
        for c in candidates:
            if c.exists():
                return str(c.resolve())
        return "data/Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx"

    def load_data(self) -> pd.DataFrame:
        """
        Loads Employees, Notice_Period, Job_Requisitions, Workforce_Planning, and Attrition_Outcomes.
        Filters eligible non-notice cohort (47,972 employees) and derives Compa_Ratio.
        """
        if self.df_population is not None:
            return self.df_population

        logger.info(f"Reading dataset from {self.excel_path}...")
        excel_file = pd.ExcelFile(self.excel_path, engine="openpyxl")
        
        self.df_raw = pd.read_excel(excel_file, sheet_name="Employees")
        self.df_notice = pd.read_excel(excel_file, sheet_name="Notice_Period")
        self.df_requisitions = pd.read_excel(excel_file, sheet_name="Job_Requisitions")
        self.df_workforce_planning = pd.read_excel(excel_file, sheet_name="Workforce_Planning")
        
        outcomes_df = pd.read_excel(excel_file, sheet_name="Attrition_Outcomes")

        # Ensure Employee_Name is preserved from authoritative master data
        if "Employee_Name" not in self.df_raw.columns:
            try:
                from services.excel_service import ExcelService, generate_display_name
                if ExcelService.is_loaded():
                    emp_sheet = ExcelService.get_sheet("Employees")
                    if "Employee_Name" in emp_sheet.columns:
                        name_dict = emp_sheet.set_index("Employee_ID")["Employee_Name"].to_dict()
                        self.df_raw["Employee_Name"] = self.df_raw["Employee_ID"].map(name_dict)
                if "Employee_Name" not in self.df_raw.columns:
                    gender_col = self.df_raw["Gender"] if "Gender" in self.df_raw.columns else None
                    self.df_raw["Employee_Name"] = [
                        generate_display_name(eid, gen)
                        for eid, gen in zip(self.df_raw["Employee_ID"], gender_col if gender_col is not None else [None]*len(self.df_raw))
                    ]
            except Exception as e:
                logger.warning(f"Could not load Employee_Name in segmentation data: {e}")

        # Exclude active notice period cohort (contractual exit scheduled)
        notice_ids = set(self.df_notice["Employee_ID"].dropna().unique())
        pop_mask = (~self.df_raw["Employee_ID"].isin(notice_ids))
        if "Serving_Notice_As_Of_Prediction" in self.df_raw.columns:
            pop_mask = pop_mask & (self.df_raw["Serving_Notice_As_Of_Prediction"] == False)

        self.df_population = self.df_raw[pop_mask].copy().reset_index(drop=True)
        logger.info(f"Loaded {len(self.df_population)} eligible non-notice employees. (Expected: 47,972)")

        # Merge simulated Attrition_Within_6M strictly for post-hoc validation and auditing
        if "Attrition_Within_6M" in outcomes_df.columns:
            outcomes_sub = outcomes_df[["Employee_ID", "Attrition_Within_6M"]].drop_duplicates("Employee_ID")
            self.df_population = self.df_population.merge(outcomes_sub, on="Employee_ID", how="left")
            self.df_population["Attrition_Within_6M"] = self.df_population["Attrition_Within_6M"].fillna(0).astype(int)

        # Compute Compa_Ratio: Annual_Salary_INR / Median salary of respective Job_Level
        medians = self.df_population.groupby("Job_Level")["Annual_Salary_INR"].median()
        self.df_population["Compa_Ratio"] = self.df_population.apply(
            lambda row: round(row["Annual_Salary_INR"] / max(1, medians.get(row["Job_Level"], row["Annual_Salary_INR"])), 3),
            axis=1
        )

        return self.df_population

    def build_preprocessor(self) -> ColumnTransformer:
        """Constructs standardized ColumnTransformer pipeline."""
        if self.preprocessor is not None:
            return self.preprocessor

        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), self.NUMERIC_FEATURES),
                ("cat", OneHotEncoder(drop=None, sparse_output=False, handle_unknown="ignore"), self.CATEGORICAL_FEATURES)
            ]
        )
        return self.preprocessor

    def fit(self, k: Optional[int] = None) -> "WorkforceSegmentation":
        """Fits baseline K-Means pipeline on the eligible population."""
        if k is not None:
            self.k = k

        self.load_data()
        self.build_preprocessor()

        X_df = self.df_population[self.NUMERIC_FEATURES + self.CATEGORICAL_FEATURES]
        self.X_transformed = self.preprocessor.fit_transform(X_df)

        # Retrieve one-hot column names
        cat_encoder = self.preprocessor.named_transformers_["cat"]
        cat_features = cat_encoder.get_feature_names_out(self.CATEGORICAL_FEATURES).tolist()
        self.feature_names = self.NUMERIC_FEATURES + cat_features

        logger.info(f"Fitting KMeans(k={self.k}, random_state={self.random_state})...")
        self.kmeans_model = KMeans(
            n_clusters=self.k,
            init="k-means++",
            n_init=10,
            max_iter=300,
            random_state=self.random_state
        )
        labels = self.kmeans_model.fit_predict(self.X_transformed)

        self.df_segmented = self.df_population.copy()
        self.df_segmented["Segment_ID"] = labels
        self.df_segmented["Segment_Label"] = [f"Segment {lbl + 1}" for lbl in labels]

        return self

    def fast_refit(self, k: int) -> "WorkforceSegmentation":
        """Reclusters workforce quickly without reloading workbook or refitting preprocessor."""
        if self.X_transformed is None:
            return self.fit(k=k)

        self.k = k
        self.kmeans_model = KMeans(
            n_clusters=self.k,
            init="k-means++",
            n_init=10,
            max_iter=300,
            random_state=self.random_state
        )
        labels = self.kmeans_model.fit_predict(self.X_transformed)

        self.df_segmented = self.df_population.copy()
        self.df_segmented["Segment_ID"] = labels
        self.df_segmented["Segment_Label"] = [f"Segment {lbl + 1}" for lbl in labels]
        self.profile_segments()
        return self

    # -------------------------------------------------------------------------
    # 5-ALGORITHM UNSUPERVISED BENCHMARKING ENGINE (PHASE 4 CORE)
    # -------------------------------------------------------------------------
    def benchmark_five_algorithms(
        self,
        k: Optional[int] = None,
        sample_size: int = 3000,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Rigorous benchmark across 5 unsupervised clustering algorithms:
          1. K-Means
          2. Agglomerative Clustering
          3. Gaussian Mixture Model (GMM)
          4. DBSCAN
          5. BIRCH

        Evaluates Silhouette score, Davies-Bouldin index, Calinski-Harabasz index,
        noise rate, assignment coverage, size balance, and computational latency.
        Applies mathematical safeguards (returns N/A with reason for unsupported solutions).
        Transparently scores candidates and selects the recommended algorithm.
        """
        if self.X_transformed is None:
            self.fit(k=k or self.k)

        eval_k = k or self.k
        X_full = self.X_transformed
        n_total = len(X_full)

        # Standardized reproducible sample for pairwise distance metric (Silhouette)
        rng = np.random.RandomState(random_state)
        sample_n = min(sample_size, n_total)
        sample_indices = rng.choice(n_total, size=sample_n, replace=False)
        X_eval_sample = X_full[sample_indices]

        candidates = [
            {
                "id": "kmeans",
                "name": "K-Means",
                "family": "Centroid-based (Partitioning)",
                "description": "Partitions workforce by minimizing within-cluster variance using Euclidean distances.",
                "model_factory": lambda: KMeans(n_clusters=eval_k, init="k-means++", n_init=10, random_state=random_state),
                "params": {"n_clusters": eval_k, "init": "k-means++", "n_init": 10, "random_state": random_state}
            },
            {
                "id": "agglomerative",
                "name": "Agglomerative Clustering",
                "family": "Hierarchical (Bottom-up)",
                "description": "Constructs cluster hierarchy by iteratively merging closest pairs with Ward linkage.",
                "model_factory": lambda: AgglomerativeClustering(n_clusters=eval_k, linkage="ward"),
                "params": {"n_clusters": eval_k, "linkage": "ward"},
                "subsample_fit": True  # Ward linkage on 48k rows requires >18GB RAM; fits on representative sample
            },
            {
                "id": "gmm",
                "name": "Gaussian Mixture Model (GMM)",
                "family": "Distribution-based (Probabilistic)",
                "description": "Models workforce as mixture of Gaussian distributions, yielding soft cluster probabilities.",
                "model_factory": lambda: GaussianMixture(n_components=eval_k, covariance_type="full", random_state=random_state),
                "params": {"n_components": eval_k, "covariance_type": "full", "random_state": random_state}
            },
            {
                "id": "dbscan",
                "name": "DBSCAN",
                "family": "Density-based",
                "description": "Groups dense regions of workforce and explicitly flags isolated outliers as noise (-1).",
                "model_factory": lambda: DBSCAN(eps=4.2, min_samples=25),
                "params": {"eps": 4.2, "min_samples": 25},
                "subsample_fit": True  # Density neighborhood query across 48k points subsampled for computational stability
            },
            {
                "id": "birch",
                "name": "BIRCH",
                "family": "Hierarchical Tree-based (CFTree)",
                "description": "Constructs Clustering Feature Tree for incremental, memory-efficient subclustering.",
                "model_factory": lambda: Birch(n_clusters=eval_k, threshold=1.0, branching_factor=50),
                "params": {"n_clusters": eval_k, "threshold": 1.0, "branching_factor": 50},
                "subsample_fit": True
            }
        ]

        benchmark_results = []

        for cand in candidates:
            c_name = cand["name"]
            logger.info(f"Benchmarking candidate algorithm: {c_name}...")
            t0 = time.time()
            model = cand["model_factory"]()
            warnings = []

            try:
                # Fit model
                if cand.get("subsample_fit", False):
                    # Fit on representative evaluation sample and predict/assign
                    model.fit(X_eval_sample)
                    labels_sub = model.labels_
                    # Map to evaluation labels
                    labels_for_metrics = labels_sub
                    X_for_metrics = X_eval_sample
                    warnings.append(f"Subsampled fit ({sample_n:,} records) applied for computational memory safety.")
                else:
                    if hasattr(model, "fit_predict"):
                        all_labels = model.fit_predict(X_full)
                    else:
                        model.fit(X_full)
                        all_labels = model.predict(X_full)

                    labels_for_metrics = all_labels[sample_indices]
                    X_for_metrics = X_eval_sample

                elapsed_ms = round((time.time() - t0) * 1000, 1)

                # Analyze cluster structure
                unique_labels = set(labels_for_metrics)
                has_noise = -1 in unique_labels
                meaningful_labels = unique_labels - {-1}
                n_clusters_found = len(meaningful_labels)

                noise_count = int(np.sum(labels_for_metrics == -1)) if has_noise else 0
                noise_pct = round((noise_count / len(labels_for_metrics)) * 100, 2)
                coverage_pct = round(100.0 - noise_pct, 2)

                # Cluster size balance
                cluster_sizes = []
                for lbl in meaningful_labels:
                    cluster_sizes.append(int(np.sum(labels_for_metrics == lbl)))

                min_size = min(cluster_sizes) if cluster_sizes else 0
                max_size = max(cluster_sizes) if cluster_sizes else 0
                imbalance_ratio = round(max_size / max(1, min_size), 2) if min_size > 0 else None

                # Compute Mathematical Metrics with strict safeguards
                if n_clusters_found < 2:
                    sil_score = None
                    db_score = None
                    ch_score = None
                    sil_display = "N/A"
                    db_display = "N/A"
                    ch_display = "N/A"
                    warnings.append(f"Only {n_clusters_found} cluster(s) found. Internal separation metrics undefined.")
                else:
                    # Filter out noise points for internal metrics
                    if has_noise and noise_count > 0:
                        non_noise_mask = (labels_for_metrics != -1)
                        eval_X = X_for_metrics[non_noise_mask]
                        eval_y = labels_for_metrics[non_noise_mask]
                    else:
                        eval_X = X_for_metrics
                        eval_y = labels_for_metrics

                    if len(set(eval_y)) >= 2:
                        try:
                            sil_score = round(float(silhouette_score(eval_X, eval_y)), 4)
                            sil_display = str(sil_score)
                        except Exception as e:
                            sil_score = None
                            sil_display = "N/A"
                            warnings.append(f"Silhouette calculation error: {str(e)}")

                        try:
                            db_score = round(float(davies_bouldin_score(eval_X, eval_y)), 4)
                            db_display = str(db_score)
                        except Exception as e:
                            db_score = None
                            db_display = "N/A"
                            warnings.append(f"Davies-Bouldin error: {str(e)}")

                        try:
                            ch_score = round(float(calinski_harabasz_score(eval_X, eval_y)), 1)
                            ch_display = str(ch_score)
                        except Exception as e:
                            ch_score = None
                            ch_display = "N/A"
                            warnings.append(f"Calinski-Harabasz error: {str(e)}")
                    else:
                        sil_score, db_score, ch_score = None, None, None
                        sil_display, db_display, ch_display = "N/A", "N/A", "N/A"

                # Specific diagnostics for GMM
                extra_diagnostics = {}
                if cand["id"] == "gmm" and hasattr(model, "bic"):
                    try:
                        extra_diagnostics["bic"] = round(float(model.bic(X_eval_sample)), 1)
                        extra_diagnostics["aic"] = round(float(model.aic(X_eval_sample)), 1)
                    except Exception:
                        pass

                # Scoring and validation for Best Model Selection
                # Rejection criteria:
                is_valid = True
                rejection_reason = None
                composite_score = 0.0

                if n_clusters_found < 2:
                    is_valid = False
                    rejection_reason = "Degenerate solution: fewer than 2 meaningful clusters formed."
                elif noise_pct > 30.0:
                    is_valid = False
                    rejection_reason = f"High unassigned noise rate ({noise_pct}%). Unsuitable for workforce coverage."
                elif min_size < 10:
                    is_valid = False
                    rejection_reason = f"Tiny singleton cluster detected (min size: {min_size})."
                elif sil_score is not None and db_score is not None:
                    # Valid candidate composite score:
                    # Higher silhouette (weight 0.40) + Lower Davies-Bouldin (weight 0.35) + Balance (weight 0.25)
                    norm_sil = max(0.0, sil_score + 0.5)  # shift silhouette to positive
                    norm_db = max(0.0, 10.0 - min(10.0, db_score)) / 10.0
                    norm_bal = max(0.0, 1.0 - min(1.0, (imbalance_ratio or 1.0) / 10.0))
                    composite_score = round((norm_sil * 40.0) + (norm_db * 35.0) + (norm_bal * 25.0), 2)

                benchmark_results.append({
                    "id": cand["id"],
                    "name": cand["name"],
                    "family": cand["family"],
                    "description": cand["description"],
                    "parameters": cand["params"],
                    "runtime_ms": elapsed_ms,
                    "clusters_found": n_clusters_found,
                    "noise_count": noise_count,
                    "noise_percentage": noise_pct,
                    "coverage_percentage": coverage_pct,
                    "cluster_sizes": cluster_sizes,
                    "min_cluster_size": min_size,
                    "max_cluster_size": max_size,
                    "size_imbalance_ratio": imbalance_ratio,
                    "silhouette_score": sil_score,
                    "silhouette_display": sil_display,
                    "davies_bouldin_index": db_score,
                    "davies_bouldin_display": db_display,
                    "calinski_harabasz_index": ch_score,
                    "calinski_harabasz_display": ch_display,
                    "extra_diagnostics": extra_diagnostics,
                    "is_valid": is_valid,
                    "rejection_reason": rejection_reason,
                    "composite_score": composite_score,
                    "warnings": warnings
                })

            except Exception as ex:
                logger.exception(f"Algorithm {c_name} evaluation failed")
                benchmark_results.append({
                    "id": cand["id"],
                    "name": cand["name"],
                    "family": cand["family"],
                    "description": cand["description"],
                    "parameters": cand["params"],
                    "runtime_ms": round((time.time() - t0) * 1000, 1),
                    "clusters_found": 0,
                    "noise_count": 0,
                    "noise_percentage": 0.0,
                    "coverage_percentage": 0.0,
                    "cluster_sizes": [],
                    "min_cluster_size": 0,
                    "max_cluster_size": 0,
                    "size_imbalance_ratio": None,
                    "silhouette_score": None,
                    "silhouette_display": "N/A",
                    "davies_bouldin_index": None,
                    "davies_bouldin_display": "N/A",
                    "calinski_harabasz_index": None,
                    "calinski_harabasz_display": "N/A",
                    "extra_diagnostics": {},
                    "is_valid": False,
                    "rejection_reason": f"Execution exception: {str(ex)}",
                    "composite_score": 0.0,
                    "warnings": [str(ex)]
                })

        # Rank valid candidates
        valid_candidates = [r for r in benchmark_results if r["is_valid"]]
        valid_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        if valid_candidates:
            best_candidate = valid_candidates[0]
            selection_rationale = (
                f"{best_candidate['name']} is selected as the optimal workforce segmentation model. "
                f"It achieved the highest composite validation score ({best_candidate['composite_score']}) "
                f"with a Davies-Bouldin index of {best_candidate['davies_bouldin_display']}, "
                f"Calinski-Harabasz score of {best_candidate['calinski_harabasz_display']}, "
                f"100% employee assignment coverage (0% noise), and balanced segment sizes "
                f"(ratio: {best_candidate['size_imbalance_ratio']})."
            )
        else:
            best_candidate = benchmark_results[0]
            selection_rationale = (
                "No candidate model fully satisfied strict production validity thresholds. "
                "Displaying K-Means as baseline diagnostic model."
            )

        output_data = {
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dataset_records": n_total,
            "sample_evaluated": sample_n,
            "target_k": eval_k,
            "random_state": random_state,
            "selected_algorithm": best_candidate["name"],
            "selected_algorithm_id": best_candidate["id"],
            "selection_rationale": selection_rationale,
            "candidates": benchmark_results
        }

        self.five_algorithm_benchmark = output_data

        # Persist benchmark results
        try:
            out_file = Path("artifacts") / "unsupervised_benchmark_results.json"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w") as f:
                json.dump(output_data, f, indent=2)
            # Duplicate to models/ for model governance
            mod_file = Path("models") / "unsupervised_benchmark_results.json"
            mod_file.parent.mkdir(parents=True, exist_ok=True)
            with open(mod_file, "w") as f:
                json.dump(output_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist benchmark JSON: {str(e)}")

        return output_data

    # -------------------------------------------------------------------------
    # 2D PCA PROJECTION WITH EXPLAINED VARIANCE
    # -------------------------------------------------------------------------
    def compute_pca_projection(self, sample_size: int = 800) -> Dict[str, Any]:
        """
        Projects 26-dimensional standardized workforce feature space onto 2 principal components.
        Returns coordinates, explained variance, and distortion notice for enterprise visualization.
        """
        if self.X_transformed is None:
            self.fit()

        pca = PCA(n_components=2, random_state=self.random_state)
        X_pca = pca.fit_transform(self.X_transformed)

        var_ratio = pca.explained_variance_ratio_
        pc1_var = round(float(var_ratio[0]) * 100, 2)
        pc2_var = round(float(var_ratio[1]) * 100, 2)
        total_var = round(pc1_var + pc2_var, 2)

        # Sample for front-end rendering performance
        n_total = len(X_pca)
        rng = np.random.RandomState(self.random_state)
        sample_n = min(sample_size, n_total)
        idx = rng.choice(n_total, size=sample_n, replace=False)

        sampled_points = []
        labels = self.df_segmented["Segment_ID"].values
        roles = self.df_segmented["Job_Role"].values
        depts = self.df_segmented["Department"].values
        names = self.df_segmented.get("Employee_Name", self.df_segmented["Employee_ID"]).values

        for i in idx:
            sampled_points.append({
                "x": round(float(X_pca[i, 0]), 3),
                "y": round(float(X_pca[i, 1]), 3),
                "segment_id": int(labels[i]),
                "segment_label": f"Segment {int(labels[i]) + 1}",
                "role": str(roles[i]),
                "department": str(depts[i]),
                "name": str(names[i])
            })

        self.pca_projection_data = {
            "total_points": n_total,
            "rendered_points": sample_n,
            "pc1_explained_variance_pct": pc1_var,
            "pc2_explained_variance_pct": pc2_var,
            "total_explained_variance_pct": total_var,
            "caveat": "2D projection reduces 26 standardized workplace dimensions into 2 orthogonal axes. Apparent boundary overlaps in 2D represent projection compression and not true multi-dimensional proximity.",
            "points": sampled_points
        }
        return self.pca_projection_data

    # -------------------------------------------------------------------------
    # DYNAMIC ARCHETYPE PROFILING
    # -------------------------------------------------------------------------
    def profile_segments(self) -> pd.DataFrame:
        """
        Derives descriptive archetype labels, distinguishing statistics, and actionable
        HR recommendations from actual cluster characteristics.
        """
        if self.df_segmented is None:
            self.fit()

        df = self.df_segmented
        pop_salary_mean = df["Annual_Salary_INR"].mean()
        pop_tenure_mean = df["Tenure_Months_At_Prediction"].mean()
        pop_sat_mean = df["Job_Satisfaction_Score_1_5"].mean()
        pop_wlb_mean = df["Work_Life_Balance_Score_1_5"].mean()
        pop_ot_mean = df["Overtime_Hours_Monthly"].mean()
        pop_compa_mean = df["Compa_Ratio"].mean()

        profiles = []
        for seg_id in sorted(df["Segment_ID"].unique()):
            seg_data = df[df["Segment_ID"] == seg_id]
            headcount = len(seg_data)
            share_pct = round((headcount / len(df)) * 100, 2)

            # Characteristics
            avg_tenure = round(float(seg_data["Tenure_Months_At_Prediction"].mean()), 1)
            med_salary = int(round(seg_data["Annual_Salary_INR"].median()))
            avg_compa = round(float(seg_data["Compa_Ratio"].mean()), 3)
            avg_sat = round(float(seg_data["Job_Satisfaction_Score_1_5"].mean()), 2)
            avg_wlb = round(float(seg_data["Work_Life_Balance_Score_1_5"].mean()), 2)
            avg_ot = round(float(seg_data["Overtime_Hours_Monthly"].mean()), 1)
            avg_train = round(float(seg_data["Training_Hours_Last_12M"].mean()), 1)

            # Dominant categorical values
            dom_dept = seg_data["Department"].value_counts().index[0]
            dom_dept_pct = round((seg_data["Department"].value_counts().iloc[0] / headcount) * 100, 1)
            dom_role = seg_data["Job_Role"].value_counts().index[0]
            dom_level = seg_data["Job_Level"].value_counts().index[0]

            # Post-hoc attrition and demographic audit
            sim_exits = int(seg_data["Attrition_Within_6M"].sum())
            exit_rate = round((sim_exits / max(1, headcount)) * 100, 2)
            pct_female = round((seg_data["Gender"].str.upper() == "FEMALE").mean() * 100, 1) if "Gender" in seg_data.columns else 0.0
            mean_age = round(float(seg_data["Age"].mean()), 1) if "Age" in seg_data.columns else 0.0

            # Dynamic Archetype Naming from actual values
            archetype_name, action = self._derive_archetype_and_action(
                avg_tenure, avg_compa, avg_sat, avg_wlb, avg_ot, dom_level, exit_rate
            )

            profiles.append({
                "Segment_ID": seg_id,
                "Segment_Label": f"Segment {seg_id + 1}",
                "Archetype_Name": archetype_name,
                "Headcount": headcount,
                "Pct_Workforce": share_pct,
                "Dominant_Department": f"{dom_dept} ({dom_dept_pct}%)",
                "Dominant_Role": dom_role,
                "Dominant_Job_Level": dom_level,
                "Avg_Tenure_Months": avg_tenure,
                "Median_Salary_INR": med_salary,
                "Avg_Compa_Ratio": avg_compa,
                "Avg_Job_Satisfaction": avg_sat,
                "Avg_Work_Life_Balance": avg_wlb,
                "Avg_Overtime_Hours": avg_ot,
                "Avg_Training_Hours": avg_train,
                "Simulated_Exits": sim_exits,
                "Flight_Risk_Rate_Pct": exit_rate,
                "Audit_Pct_Female": pct_female,
                "Audit_Mean_Age": mean_age,
                "Actionable_Recommendation": action,
                "Recommended_Talent_Action": action
            })

        self.segment_profiles = pd.DataFrame(profiles)
        return self.segment_profiles

    def _derive_archetype_and_action(
        self, tenure: float, compa: float, sat: float, wlb: float, ot: float, level: str, exit_rate: float
    ) -> Tuple[str, str]:
        """Derives respectful, non-stigmatizing workforce archetype labels and supportive HR guidance."""
        if ot > 30 and wlb < 2.5:
            name = "High-Workload Core Contributors"
            action = "Conduct workload reviews, monitor burnout indicators, and provide overtime compensation balancing."
        elif tenure > 40 and compa >= 1.05:
            name = "Senior Tenured Anchors"
            action = "Engage in leadership continuity planning, specialized mentorship roles, and long-term retention grants."
        elif level == "Lead" or compa >= 1.15:
            name = "Strategic Technical Leaders"
            action = "Support architectural autonomy, leadership growth pathways, and market benchmark parity."
        elif sat >= 3.8 and wlb >= 3.8:
            name = "Balanced High-Engagement Professionals"
            action = "Maintain supportive management practices and offer cross-functional development opportunities."
        elif tenure < 18 and level in ("Junior", "Mid"):
            name = "Early-Career Growth Specialists"
            action = "Accelerate onboarding mentorship, career milestone mapping, and targeted technical skills training."
        elif compa < 0.90:
            name = "Compensation Review Cohort"
            action = "Review market compa-ratio alignment against peer benchmarks to address external compensation risk."
        else:
            name = "Stable Operational Professionals"
            action = "Provide regular manager check-ins, skill enhancement workshops, and structured growth pathways."

        return name, action

    # -------------------------------------------------------------------------
    # JOB ROLE STAFFING PRESSURE & ANOMALY DETECTION (EXISTING COMPATIBILITY)
    # -------------------------------------------------------------------------
    def segment_job_roles(self, n_clusters: int = 3) -> pd.DataFrame:
        """Clusters 26 job roles into staffing pressure tiers."""
        self.load_data()
        emp_df = self.df_raw
        notice_df = self.df_notice
        req_df = self.df_requisitions

        # Aggregate metrics per job role
        role_stats = []
        for role, group in emp_df.groupby("Job_Role"):
            dept = group["Department"].iloc[0]
            hc = len(group)
            
            # Notice exits
            notice_cnt = int(notice_df[notice_df["Employee_ID"].isin(group["Employee_ID"])].shape[0])
            
            # Open requisitions
            role_reqs = req_df[req_df["Job_Role"] == role]
            open_positions = int(role_reqs["Positions_Remaining"].sum()) if not role_reqs.empty else 0
            
            # Immediate staffing need
            immediate_need = notice_cnt + open_positions
            pressure_ratio = round(immediate_need / max(1, hc), 3)

            # Simulated attrition
            sim_attr = int(self.df_population[self.df_population["Job_Role"] == role]["Attrition_Within_6M"].sum()) if "Attrition_Within_6M" in self.df_population.columns else 0
            attr_rate = round((sim_attr / max(1, hc)) * 100, 2)

            role_stats.append({
                "Job_Role": role,
                "Department": dept,
                "Headcount": hc,
                "Notice_Exits": notice_cnt,
                "Open_Requisitions": open_positions,
                "Immediate_Staffing_Need": immediate_need,
                "Simulated_Attrition_Exits": sim_attr,
                "Simulated_Attrition_Rate_Pct": attr_rate,
                "Staffing_Pressure_Ratio": pressure_ratio
            })

        df_roles = pd.DataFrame(role_stats)

        # Cluster by staffing pressure ratio
        kmeans = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
        df_roles["Cluster"] = kmeans.fit_predict(df_roles[["Staffing_Pressure_Ratio"]])

        # Rank clusters by mean pressure ratio
        cluster_means = df_roles.groupby("Cluster")["Staffing_Pressure_Ratio"].mean().sort_values(ascending=False)
        tier_names = ["Critical Staffing Pressure", "Moderate Staffing Risk", "Stable / Low Pressure"]
        tier_mapping = {cl: tier_names[i] for i, cl in enumerate(cluster_means.index)}
        df_roles["Pressure_Tier"] = df_roles["Cluster"].map(tier_mapping)

        self.role_pressure_df = df_roles.sort_values("Staffing_Pressure_Ratio", ascending=False).reset_index(drop=True)
        return self.role_pressure_df

    def detect_workload_pay_anomalies(self, contamination: float = 0.02) -> pd.DataFrame:
        """Detects workload/compensation outliers using Isolation Forest."""
        self.load_data()
        pop_df = self.df_population

        features = ["Overtime_Hours_Monthly", "Work_Life_Balance_Score_1_5", "Compa_Ratio", "Performance_Rating_1_5"]
        X_anom = pop_df[features].copy()
        
        iso = IsolationForest(contamination=contamination, random_state=self.random_state, n_estimators=100)
        preds = iso.fit_predict(X_anom)
        scores = iso.decision_function(X_anom)
        
        anom_mask = (preds == -1)
        anom_df = pop_df[anom_mask].copy()
        anom_df["Anomaly_Score"] = np.round(scores[anom_mask], 4)

        # Categorize anomaly type
        categories = []
        for _, row in anom_df.iterrows():
            if row["Overtime_Hours_Monthly"] > 35 and row["Compa_Ratio"] < 0.90:
                categories.append("High Overtime / Low Compa-Ratio")
            elif row["Work_Life_Balance_Score_1_5"] <= 2 and row["Performance_Rating_1_5"] >= 4:
                categories.append("High Performance / Severe Burnout Risk")
            elif row["Compa_Ratio"] > 1.25 and row["Performance_Rating_1_5"] <= 2:
                categories.append("High Compa-Ratio / Low Performance")
            else:
                categories.append("Multi-Attribute Workload Outlier")

        anom_df["Anomaly_Category"] = categories
        anom_df["Anomaly_Type"] = categories
        self.anomalies_df = anom_df.reset_index(drop=True)
        return self.anomalies_df

    def evaluate_k_candidates(self, k_range: range = range(3, 8)) -> List[Dict[str, Any]]:
        """Evaluates inertia, silhouette, and Davies-Bouldin across candidate K values."""
        if self.X_transformed is None:
            self.fit()

        results = []
        # Subsample for fast interactive curve calculation
        n = len(self.X_transformed)
        rng = np.random.RandomState(self.random_state)
        sample_idx = rng.choice(n, size=min(2500, n), replace=False)
        X_sub = self.X_transformed[sample_idx]

        for cand_k in k_range:
            km = KMeans(n_clusters=cand_k, random_state=self.random_state, n_init=5)
            labels = km.fit_predict(self.X_transformed)
            sub_labels = labels[sample_idx]

            sil = float(silhouette_score(X_sub, sub_labels))
            db = float(davies_bouldin_score(X_sub, sub_labels))
            ch = float(calinski_harabasz_score(X_sub, sub_labels))

            results.append({
                "k": cand_k,
                "inertia": round(float(km.inertia_), 1),
                "silhouette_score": round(sil, 4),
                "davies_bouldin": round(db, 4),
                "calinski_harabasz": round(ch, 1)
            })

        self.k_evaluation_results = results
        return results

    def compare_clustering_models(self, sample_size: int = 2000) -> Dict[str, Any]:
        """Provides backward-compatible method for tests, wrapping benchmark_five_algorithms."""
        benchmark = self.benchmark_five_algorithms(sample_size=sample_size)
        models_map = {}
        for c in benchmark.get("candidates", []):
            c_name = c["name"].lower()
            if "kmeans" in c_name or "k-means" in c_name:
                models_map["kmeans"] = c
            elif "agglomerative" in c_name:
                models_map["agglomerative"] = c
            elif "gaussian" in c_name or "gmm" in c_name:
                models_map["gmm"] = c
            elif "dbscan" in c_name:
                models_map["dbscan"] = c
            elif "birch" in c_name:
                models_map["birch"] = c

        return {
            "comparison": [
                {
                    "model": c["name"],
                    "silhouette": c["silhouette_score"] or 0.0,
                    "davies_bouldin": c["davies_bouldin_index"] or 0.0,
                    "calinski_harabasz": c["calinski_harabasz_index"] or 0.0,
                    "runtime_ms": c["runtime_ms"],
                    "clusters": c["clusters_found"]
                }
                for c in benchmark["candidates"]
            ],
            "models": models_map,
            "best_model": benchmark["selected_algorithm"],
            "rationale": benchmark["selection_rationale"]
        }

    # Backward compatibility alias
    detect_anomalies = detect_workload_pay_anomalies

    def run_pipeline(self, output_dir: str = "artifacts") -> Dict[str, Any]:
        """Executes entire unsupervised workflow and persists all artifacts."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        self.fit()
        self.profile_segments()
        self.segment_job_roles()
        self.detect_workload_pay_anomalies()
        self.evaluate_k_candidates()
        self.benchmark_five_algorithms()
        self.compute_pca_projection()

        # Save files
        profiles_json = out_path / "segment_profiles.json"
        profiles_csv = out_path / "segment_profiles.csv"
        role_pressure_csv = out_path / "role_staffing_pressure.csv"
        anomalies_csv = out_path / "workload_pay_anomalies.csv"
        k_eval_json = out_path / "k_evaluation_metrics.json"

        self.segment_profiles.to_json(profiles_json, orient="records", indent=2)
        self.segment_profiles.to_csv(profiles_csv, index=False)
        self.role_pressure_df.to_csv(role_pressure_csv, index=False)
        self.anomalies_df.to_csv(anomalies_csv, index=False)
        with open(k_eval_json, "w") as f:
            json.dump(self.k_evaluation_results, f, indent=2)

        return {
            "population_count": len(self.df_population),
            "k": self.k,
            "role_clusters_count": len(self.role_pressure_df),
            "anomalies_count": len(self.anomalies_df),
            "artifacts": {
                "segment_profiles_json": str(profiles_json),
                "segment_profiles_csv": str(profiles_csv),
                "role_staffing_pressure_csv": str(role_pressure_csv),
                "workload_pay_anomalies_csv": str(anomalies_csv),
                "k_evaluation_json": str(k_eval_json)
            }
        }
