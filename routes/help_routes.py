"""
Workforce Intelligence — Documentation & Help Routes
Blueprint for glossary, data dictionary, and ethical AI guidelines.
"""
import json
import logging

from flask import Blueprint, render_template, jsonify
import config
from services.excel_service import ExcelService

logger = logging.getLogger(__name__)

help_bp = Blueprint("help", __name__)


@help_bp.route("/help")
def help_page():
    return render_template(
        "help.html",
        active_page="help",
        page_title="Documentation & Governance Guidelines",
        page_subtitle=(
            "Data dictionary, modeling methodology, algorithm catalog, "
            "and ethical AI safeguards"
        ),
        snapshot_date=config.DATA_SNAPSHOT_DATE
    )


@help_bp.route("/api/help/dictionary")
def get_data_dictionary():
    try:
        dd_df = ExcelService.get_sheet("Data_Dictionary")

        if dd_df is None:
            logger.error("ExcelService.get_sheet('Data_Dictionary') returned None")
            return jsonify({
                "success": False,
                "error": "The Data_Dictionary sheet could not be loaded."
            }), 500

        if not hasattr(dd_df, "to_json"):
            logger.error("Data_Dictionary is not a pandas DataFrame: %s", type(dd_df).__name__)
            return jsonify({
                "success": False,
                "error": "The Data_Dictionary source is not in the expected tabular format."
            }), 500

        # DataFrame.to_json converts NaN/NaT to JSON null and normalizes
        # pandas/numpy scalar values for a standards-compliant JSON response.
        records = json.loads(
            dd_df.to_json(
                orient="records",
                date_format="iso",
                date_unit="ms",
                force_ascii=False
            )
        )

        return jsonify({
            "success": True,
            "count": len(records),
            "dictionary": records
        })

    except Exception:
        logger.exception("Failed to load the data dictionary")
        return jsonify({
            "success": False,
            "error": "Unable to load the data dictionary. Check the application logs."
        }), 500
