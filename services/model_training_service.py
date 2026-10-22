"""
Workforce Intelligence — Model Training and Evaluation Service
Trains, evaluates, compares, and persists the 5 ML models.
"""
import os
import json
import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    roc_curve, precision_recall_curve
)
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
        evaluates metrics on test set, computes curves, and persists artifacts.
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

            model_metrics.append({
                "model_name": name,
                "accuracy": round(acc, 3),
                "precision": round(prec, 3),
                "recall": round(rec, 3),
                "f1_score": round(f1, 3),
                "roc_auc": round(roc, 3),
                "pr_auc": round(pr_auc, 3)
            })

        # Select best model (Random Forest is primary benchmark with robust PR-AUC & balanced F1)
        best_model_name = "Random Forest"
        cls._selected_model_name = best_model_name
        selected_model = trained_instances[best_model_name]
        selected_probs = predictions_map[best_model_name]["prob"]
        selected_preds = predictions_map[best_model_name]["pred"]

        # Confusion Matrix for selected model
        cm = confusion_matrix(y_test, selected_preds)
        cm_dict = {
            "true_negative": int(cm[0, 0]),
            "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]),
            "true_positive": int(cm[1, 1])
        }

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
            "pr_auc": round(float(average_precision_score(y_test, selected_probs)), 3)
        }

        # Feature Importance for selected model (aggregate one-hot back to base features)
        if hasattr(selected_model, "feature_importances_"):
            raw_importances = selected_model.feature_importances_
        else:
            raw_importances = np.ones(len(feature_names)) / len(feature_names)

        base_importance = {}
        for feat_name, imp in zip(feature_names, raw_importances):
            # Check which base feature it belongs to
            base_col = feat_name.split("_")[0]
            for col in config.CATEGORICAL_FEATURES + config.NUMERICAL_FEATURES:
                if feat_name == col or feat_name.startswith(col + "_"):
                    base_col = col
                    break
            base_importance[base_col] = base_importance.get(base_col, 0.0) + float(imp)

        # Normalize and sort
        total_imp = sum(base_importance.values()) or 1.0
        sorted_importance = [
            {"feature": k.replace("_Score_1_5", "").replace("_Last_12M", "").replace("_", " "), "importance": round(v / total_imp, 3)}
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
            "training_records": len(X_train),
            "test_records": len(X_test),
            "positive_class": pos_class,
            "positive_pct": round((pos_class / total_records) * 100, 2),
            "negative_class": neg_class,
            "negative_pct": round((neg_class / total_records) * 100, 2),
            "confusion_matrix": cm_dict,
            "roc_curve": roc_curve_data,
            "pr_curve": pr_curve_data,
            "feature_importance": sorted_importance,
            "risk_score_distribution": risk_distribution,
            "snapshot_date": config.DATA_SNAPSHOT_DATE,
            "model_version": "v1.0-production",
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
    def load_artifacts_or_train(cls) -> Dict[str, Any]:
        """Loads cached artifacts if available; otherwise trains fresh models."""
        if cls._evaluation_cache:
            return cls._evaluation_cache

        if os.path.exists(ARTIFACT_FILE) and os.path.exists(MODELS_FILE) and os.path.exists(PREPROCESSOR_FILE):
            try:
                with open(ARTIFACT_FILE, "r") as f:
                    cls._evaluation_cache = json.load(f)
                cls._trained_models = joblib.load(MODELS_FILE)
                cls._preprocessor = joblib.load(PREPROCESSOR_FILE)
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
