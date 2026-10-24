"""
Workforce Intelligence — Reference Script: segment_workforce.py
Executes the unsupervised workforce segmentation pipeline using src.segmentation.WorkforceSegmentation.
Saves all segment profiles, role staffing pressure tables, anomaly flags, and K-evaluation metrics to outputs/ and artifacts/.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from src.segmentation import WorkforceSegmentation


def main():
    parser = argparse.ArgumentParser(description="Workforce Segmentation Reference Runner")
    parser.add_argument(
        "--excel",
        type=str,
        default=None,
        help="Path to Excel dataset file (default: autodiscovered in data/)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Configurable number of workforce clusters (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Target output directory for artifacts (default: outputs)"
    )
    args = parser.parse_args()

    print(f"Starting workforce segmentation with K = {args.k}...")
    segmenter = WorkforceSegmentation(
        excel_path=args.excel,
        k=args.k,
        random_state=42
    )
    summary = segmenter.run_pipeline(output_dir=args.output_dir)

    print("\n=======================================================")
    print("   WORKFORCE SEGMENTATION COMPLETED SUCCESSFULLY")
    print("=======================================================")
    print(f"Total Eligible Employees Clustered: {summary['population_count']:,}")
    print(f"Number of Workforce Segments (K):   {summary['k']}")
    print(f"Job Roles Clustered by Pressure:    {summary['role_clusters_count']}")
    print(f"Identified Workload/Pay Anomalies:  {summary['anomalies_count']}")
    print("\nSaved Artifacts:")
    for key, path in summary["artifacts"].items():
        print(f"  - {key}: {path}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
