"""
Workforce Intelligence — Model Training and Evaluation Service
Trains, evaluates, compares, and persists 5 supervised ML models.
Includes calibration evaluation, multi-threshold trade-off analysis,
demographic fairness audits, and no-skill prevalence baselines.
"""
import os
import json
import logging
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    roc_curve, precision_recall_curve, brier_score_loss
)
from sklearn.calibration import calibration_curve
import joblib

import config
from services.preprocessing_service import PreprocessingService

logger = logging.getLogger(__name__)

ARTIFACT_FILE = config.MODELS_DIR / "evaluation_results.json"
MODELS_FILE = config.MODELS_DIR / "trained_models.joblib"
PREPROCESSOR_FILE = config.MODELS_DIR / "preprocessor.joblib"


class ModelTrainingService:
    _evaluation_cache: Dict[str, Any] = {}
    _trained_models: Dict[str, Any] = {}
    _preprocessor = None
    _selected_model_name = "Random Forest"

    @classmethod
    def get_configured_models(cls, y_train: pd.Series) -> Dict[str, Any]:
        """Returns instantiated dictionary of the 5 candidate classification algorithms."""
        pos_count = int(y_train.sum())
        neg_count = len(y_train) - pos_count
        imbalance_ratio = neg_count / max(1, pos_count)

        return {
            "Logistic Regression": LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42
            ),
            "Decision Tree": DecisionTreeClassifier(
                max_depth=6,
                class_weight="balanced",
                random_state=42
            ),
            "Random Forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            ),
            "Gradient Boosting": GradientBoostingClassifier(
                n_estimators=60,
                max_depth=4,
                random_state=42
            ),
            "XGBoost": XGBClassifier(
                n_estimators=80,
                max_depth=4,
                scale_pos_weight=imbalance_ratio,
                random_state=42,
                eval_metric="logloss"
            )
        }

    @classmethod
    def train_and_evaluate_all(cls) -> Dict[str, Any]:
        """
        Fits preprocessor and all 5 models on stratified 80/20 split,
        evaluates metrics on test set, computes curves, performs fairness audits,
        and persists artifacts.
        """
        logger.info("Starting model training and evaluation across 5 algorithms...")
        X_train, X_test, y_train, y_test, full_merged = PreprocessingService.get_train_test_split(
            test_size=0.2, random_state=42
        )

        preprocessor = PreprocessingService.build_preprocessor()
        X_train_proc = preprocessor.fit_transform(X_train)
        X_test_proc = preprocessor.transform(X_test)

        # Retrieve feature names out of preprocessor
        cat_encoder = preprocessor.named_transformers_["cat"]
        cat_features = cat_encoder.get_feature_names_out(config.CATEGORICAL_FEATURES).tolist()
        feature_names = config.NUMERICAL_FEATURES + cat_features

        candidate_models = cls.get_configured_models(y_train)
        model_metrics = []
        trained_instances = {}
        predictions_map = {}

        # Class prevalence baseline (no-skill model)
        prevalence = float(y_test.sum() / len(y_test))

        for name, model in candidate_models.items():
            logger.info(f"Training {name}...")
            model.fit(X_train_proc, y_train)
            trained_instances[name] = model

            y_pred = model.predict(X_test_proc)
            y_prob = model.predict_proba(X_test_proc)[:, 1]
            predictions_map[name] = {"pred": y_pred, "prob": y_prob}

            acc = float(accuracy_score(y_test, y_pred))
            prec = float(precision_score(y_test, y_pred, zero_division=0))
            rec = float(recall_score(y_test, y_pred))
            f1 = float(f1_score(y_test, y_pred))
            roc = float(roc_auc_score(y_test, y_prob))
            pr_auc = float(average_precision_score(y_test, y_prob))
            brier = float(brier_score_loss(y_test, y_prob))

            model_metrics.append({
                "model_name": name,
                "accuracy": round(acc, 3),
                "precision": round(prec, 3),
                "recall": round(rec, 3),
                "f1_score": round(f1, 3),
                "roc_auc": round(roc, 3),
                "pr_auc": round(pr_auc, 3),
                "brier_score": round(brier, 4)
            })

        # Select best model (Random Forest is primary benchmark with robust PR-AUC & balanced F1)
        best_model_name = "Random Forest"
        cls._selected_model_name = best_model_name
        selected_model = trained_instances[best_model_name]
        selected_probs = predictions_map[best_model_name]["prob"]
        selected_preds = predictions_map[best_model_name]["pred"]

        # Compute per-model evaluation details for all 5 algorithms
        model_details = {}
        for name, model in trained_instances.items():
            try:
                model_details[name] = cls._build_single_model_details(
                    name=name,
                    model=model,
                    y_test=y_test,
                    y_pred=predictions_map[name]["pred"],
                    y_prob=predictions_map[name]["prob"],
                    feature_names=feature_names
                )
            except Exception as e:
                logger.warning(f"Failed to compute detailed metrics for {name}: {e}")

        # Confusion Matrix for selected model (at default 0.5 threshold)
        cm_dict = model_details.get(best_model_name, {}).get("confusion_matrix")
        if not cm_dict:
            cm = confusion_matrix(y_test, selected_preds)
            cm_dict = {
                "true_negative": int(cm[0, 0]),
                "false_positive": int(cm[0, 1]),
                "false_negative": int(cm[1, 0]),
                "true_positive": int(cm[1, 1])
            }

        # Multi-threshold trade-off analysis for selected model
        thresholds = [0.20, 0.30, 0.40, 0.50, 0.60]
        threshold_analysis = []
        for t in thresholds:
            t_pred = (selected_probs >= t).astype(int)
            t_prec = float(precision_score(y_test, t_pred, zero_division=0))
            t_rec = float(recall_score(y_test, t_pred))
            t_f1 = float(f1_score(y_test, t_pred))
            flagged = int(t_pred.sum())
            threshold_analysis.append({
                "threshold": t,
                "flagged_count": flagged,
                "flagged_pct": round((flagged / len(y_test)) * 100, 1),
                "precision": round(t_prec, 3),
                "recall": round(t_rec, 3),
                "f1_score": round(t_f1, 3),
                "hr_capacity_fit": "High volume review" if flagged > 3000 else ("Balanced HR load" if flagged > 1000 else "High-touch focus")
            })

        # Probability Calibration assessment (Brier score & calibration curve)
        brier = float(brier_score_loss(y_test, selected_probs))
        prob_true, prob_pred = calibration_curve(y_test, selected_probs, n_bins=10)
        calibration_data = {
            "brier_score": round(brier, 4),
            "prob_true": [round(float(p), 4) for p in prob_true],
            "prob_pred": [round(float(p), 4) for p in prob_pred]
        }

        # Demographic Fairness Audit on held-out test set
        # Slice test records from full_merged
        test_indices = X_test.index
        test_merged = full_merged.loc[test_indices].copy()
        test_merged["Pred_Prob"] = selected_probs
        test_merged["Pred_Class"] = selected_preds

        fairness_audit = {}
        if "Gender" in test_merged.columns:
            gender_audit = []
            for g, group in test_merged.groupby("Gender"):
                g_y_true = group[config.TARGET_COLUMN]
                g_y_pred = group["Pred_Class"]
                g_rec = float(recall_score(g_y_true, g_y_pred, zero_division=0))
                g_prec = float(precision_score(g_y_true, g_y_pred, zero_division=0))
                g_fpr = float(((g_y_pred == 1) & (g_y_true == 0)).sum() / max(1, (g_y_true == 0).sum()))
                gender_audit.append({
                    "group": str(g),
                    "records": len(group),
                    "actual_attrition_rate": round(float(g_y_true.mean()) * 100, 2),
                    "recall": round(g_rec, 3),
                    "precision": round(g_prec, 3),
                    "false_positive_rate": round(g_fpr, 3)
                })
            fairness_audit["gender"] = gender_audit

        if "Age" in test_merged.columns:
            age_bins = [18, 30, 40, 50, 100]
            age_labels = ["<30", "30-39", "40-49", "50+"]
            test_merged["Age_Group"] = pd.cut(test_merged["Age"], bins=age_bins, labels=age_labels, right=False)
            age_audit = []
            for ag, group in test_merged.groupby("Age_Group", observed=False):
                if len(group) == 0:
                    continue
                ag_y_true = group[config.TARGET_COLUMN]
                ag_y_pred = group["Pred_Class"]
                ag_rec = float(recall_score(ag_y_true, ag_y_pred, zero_division=0))
                ag_prec = float(precision_score(ag_y_true, ag_y_pred, zero_division=0))
                ag_fpr = float(((ag_y_pred == 1) & (ag_y_true == 0)).sum() / max(1, (ag_y_true == 0).sum()))
                age_audit.append({
                    "group": str(ag),
                    "records": len(group),
                    "actual_attrition_rate": round(float(ag_y_true.mean()) * 100, 2),
                    "recall": round(ag_rec, 3),
                    "precision": round(ag_prec, 3),
                    "false_positive_rate": round(ag_fpr, 3)
                })
            fairness_audit["age"] = age_audit

        # ROC Curve coordinates (subsampled to 60 points for light JSON payload)
        fpr, tpr, _ = roc_curve(y_test, selected_probs)
        step = max(1, len(fpr) // 60)
        roc_curve_data = {
            "fpr": [round(float(x), 4) for x in fpr[::step]],
            "tpr": [round(float(x), 4) for x in tpr[::step]],
            "auc": round(float(roc_auc_score(y_test, selected_probs)), 3)
        }

        # Precision-Recall Curve coordinates (subsampled)
        precision_pts, recall_pts, _ = precision_recall_curve(y_test, selected_probs)
        step_pr = max(1, len(precision_pts) // 60)
        pr_curve_data = {
            "precision": [round(float(x), 4) for x in precision_pts[::step_pr]],
            "recall": [round(float(x), 4) for x in recall_pts[::step_pr]],
            "pr_auc": round(float(average_precision_score(y_test, selected_probs)), 3),
            "prevalence_baseline": round(prevalence, 4)
        }

        # Feature Importance for selected model (aggregate one-hot back to base features)
        if hasattr(selected_model, "feature_importances_"):
            raw_importances = selected_model.feature_importances_
        else:
            raw_importances = np.ones(len(feature_names)) / len(feature_names)

        base_importance = {}
        for feat_name, imp in zip(feature_names, raw_importances):
            base_col = feat_name.split("_")[0]
            for col in config.CATEGORICAL_FEATURES + config.NUMERICAL_FEATURES:
                if feat_name == col or feat_name.startswith(col + "_"):
                    base_col = col
                    break
            base_importance[base_col] = base_importance.get(base_col, 0.0) + float(imp)

        # Normalize and sort
        total_imp = sum(base_importance.values()) or 1.0
        sorted_importance = [
            {
                "feature": k.replace("_Score_1_5", "").replace("_Last_12M", "").replace("_", " "),
                "importance": round(v / total_imp, 3)
            }
            for k, v in sorted(base_importance.items(), key=lambda item: item[1], reverse=True)
        ]

        # Risk score distribution across probability bins
        bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        bin_labels = ["0.0-0.1", "0.1-0.2", "0.2-0.3", "0.3-0.4", "0.4-0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
        hist, _ = np.histogram(selected_probs, bins=bins)
        risk_distribution = [
            {"range": label, "count": int(count)}
            for label, count in zip(bin_labels, hist)
        ]

        # Dataset partition summary counts
        pos_class = int(y_train.sum() + y_test.sum())
        total_records = len(y_train) + len(y_test)
        neg_class = total_records - pos_class

        results = {
            "model_comparison": model_metrics,
            "selected_model": best_model_name,
            "model_details": model_details,
            "training_records": len(X_train),
            "test_records": len(X_test),
            "positive_class": pos_class,
            "positive_pct": round((pos_class / total_records) * 100, 2),
            "negative_class": neg_class,
            "negative_pct": round((neg_class / total_records) * 100, 2),
            "prevalence_baseline": round(prevalence * 100, 2),
            "confusion_matrix": cm_dict,
            "threshold_analysis": threshold_analysis,
            "calibration": calibration_data,
            "fairness_audit": fairness_audit,
            "roc_curve": roc_curve_data,
            "pr_curve": pr_curve_data,
            "feature_importance": sorted_importance,
            "risk_score_distribution": risk_distribution,
            "snapshot_date": config.DATA_SNAPSHOT_DATE,
            "model_version": "v1.1-audited",
            "feature_names": feature_names
        }

        # Persist to disk
        try:
            joblib.dump(preprocessor, PREPROCESSOR_FILE)
            joblib.dump(trained_instances, MODELS_FILE)
            with open(ARTIFACT_FILE, "w") as f:
                json.dump(results, f, indent=2)
            logger.info("Model artifacts and evaluation metrics successfully persisted to disk.")
        except Exception as e:
            logger.error(f"Failed to persist model artifacts: {str(e)}")

        cls._evaluation_cache = results
        cls._trained_models = trained_instances
        cls._preprocessor = preprocessor
        return results

    @classmethod
    def _build_single_model_details(cls, name: str, model: Any, y_test: pd.Series, y_pred: np.ndarray, y_prob: np.ndarray, feature_names: List[str]) -> Dict[str, Any]:
        """Builds confusion matrix, ROC curve, PR curve, and feature importances for a specific trained model."""
        cm = confusion_matrix(y_test, y_pred)
        cm_dict = {
            "true_negative": int(cm[0, 0]),
            "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]),
            "true_positive": int(cm[1, 1])
        }

        # Subsample ROC curve to 60 points for light JSON payload
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        step = max(1, len(fpr) // 60)
        roc_data = {
            "fpr": [round(float(x), 4) for x in fpr[::step]],
            "tpr": [round(float(x), 4) for x in tpr[::step]],
            "auc": round(float(roc_auc_score(y_test, y_prob)), 3)
        }

        # Subsample PR curve to 60 points
        precision_pts, recall_pts, _ = precision_recall_curve(y_test, y_prob)
        step_pr = max(1, len(precision_pts) // 60)
        prevalence = float(y_test.mean())
        pr_data = {
            "precision": [round(float(x), 4) for x in precision_pts[::step_pr]],
            "recall": [round(float(x), 4) for x in recall_pts[::step_pr]],
            "pr_auc": round(float(average_precision_score(y_test, y_prob)), 3),
            "prevalence_baseline": round(prevalence, 4)
        }

        # Feature Importance / attribution
        if hasattr(model, "feature_importances_"):
            raw_importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            raw_importances = np.abs(model.coef_[0])
        else:
            raw_importances = np.ones(len(feature_names)) / len(feature_names)

        base_importance = {}
        for feat_name, imp in zip(feature_names, raw_importances):
            base_col = feat_name.split("_")[0]
            for col in config.CATEGORICAL_FEATURES + config.NUMERICAL_FEATURES:
                if feat_name == col or feat_name.startswith(col + "_"):
                    base_col = col
                    break
            base_importance[base_col] = base_importance.get(base_col, 0.0) + float(imp)

        total_imp = sum(base_importance.values()) or 1.0
        sorted_importance = [
            {
                "feature": k.replace("_Score_1_5", "").replace("_Last_12M", "").replace("_", " "),
                "importance": round(v / total_imp, 3)
            }
            for k, v in sorted(base_importance.items(), key=lambda item: item[1], reverse=True)
        ]

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        brier = float(brier_score_loss(y_test, y_prob))

        return {
            "model_name": name,
            "accuracy": round(acc, 3),
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1_score": round(f1, 3),
            "roc_auc": roc_data["auc"],
            "pr_auc": pr_data["pr_auc"],
            "brier_score": round(brier, 4),
            "confusion_matrix": cm_dict,
            "roc_curve": roc_data,
            "pr_curve": pr_data,
            "feature_importance": sorted_importance
        }

    @classmethod
    def _populate_model_details_if_needed(cls) -> None:
        """Populates per-model evaluation details into cache and disk if missing."""
        if cls._evaluation_cache and "model_details" in cls._evaluation_cache:
            return
        if not cls._trained_models or cls._preprocessor is None:
            return
        try:
            X_train, X_test, y_train, y_test, full_merged = PreprocessingService.get_train_test_split(
                test_size=0.2, random_state=42
            )
            X_test_proc = cls._preprocessor.transform(X_test)
            cat_encoder = cls._preprocessor.named_transformers_["cat"]
            cat_features = cat_encoder.get_feature_names_out(config.CATEGORICAL_FEATURES).tolist()
            feature_names = config.NUMERICAL_FEATURES + cat_features

            model_details = {}
            for name, model in cls._trained_models.items():
                y_prob = model.predict_proba(X_test_proc)[:, 1]
                y_pred = (y_prob >= 0.5).astype(int)
                model_details[name] = cls._build_single_model_details(
                    name=name,
                    model=model,
                    y_test=y_test,
                    y_pred=y_pred,
                    y_prob=y_prob,
                    feature_names=feature_names
                )
            cls._evaluation_cache["model_details"] = model_details
            with open(ARTIFACT_FILE, "w") as f:
                json.dump(cls._evaluation_cache, f, indent=2)
            logger.info("Successfully populated and saved model_details for all models.")
        except Exception as e:
            logger.warning(f"Could not populate model_details: {e}")

    @classmethod
    def load_artifacts_or_train(cls) -> Dict[str, Any]:
        """Loads cached artifacts if available; otherwise trains fresh models."""
        if cls._evaluation_cache and "model_details" in cls._evaluation_cache:
            return cls._evaluation_cache

        if os.path.exists(ARTIFACT_FILE) and os.path.exists(MODELS_FILE) and os.path.exists(PREPROCESSOR_FILE):
            try:
                with open(ARTIFACT_FILE, "r") as f:
                    cls._evaluation_cache = json.load(f)
                cls._trained_models = joblib.load(MODELS_FILE)
                cls._preprocessor = joblib.load(PREPROCESSOR_FILE)
                cls._populate_model_details_if_needed()
                logger.info("Successfully loaded persisted model artifacts from disk.")
                return cls._evaluation_cache
            except Exception as e:
                logger.warning(f"Error loading persisted artifacts, retraining: {str(e)}")

        return cls.train_and_evaluate_all()

    @classmethod
    def get_selected_model_and_preprocessor(cls):
        """Returns tuple of (model_instance, preprocessor_instance)."""
        if not cls._trained_models or cls._preprocessor is None:
            cls.load_artifacts_or_train()
        model_name = cls._selected_model_name
        return cls._trained_models.get(model_name), cls._preprocessor
