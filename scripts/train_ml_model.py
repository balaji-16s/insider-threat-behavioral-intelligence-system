#!/usr/bin/env python3
"""
Train and persist the ML anomaly detection model (Isolation Forest).

Trains the model ONCE on the ingested dataset (feature vectors are built
from the database exactly the way the runtime pipeline builds them) and
saves it to ``data/models/isolation_forest.joblib`` plus a metadata JSON.
The app then loads this persisted model for scoring, so "Run ML Detection"
performs inference instead of re-fitting the model on every call — which
keeps whole-org scoring fast on the large CERT dataset (1,000 employees /
4.37M events).

Usage:
    python scripts/train_ml_model.py
    python scripts/train_ml_model.py --days 30 --contamination 0.05
    python scripts/train_ml_model.py --max-users 200
    python scripts/train_ml_model.py --retrain   # (training always overwrites)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SessionLocal  # noqa: E402
from app.services.ml_anomaly_detection import (  # noqa: E402
    MODEL_META_PATH,
    MODEL_PATH,
    train_and_save_model,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the Isolation Forest anomaly model from the database and save it."
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Lookback window (days) used for feature extraction (default: 30)",
    )
    parser.add_argument(
        "--contamination", type=float, default=0.05,
        help="Expected proportion of outliers (default: 0.05)",
    )
    parser.add_argument(
        "--max-users", type=int, default=None,
        help="Limit the number of employees used for training (default: all)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = train_and_save_model(
            db,
            days=args.days,
            contamination=args.contamination,
            max_users=args.max_users,
        )
    finally:
        db.close()

    if not result["trained"]:
        print(f"✗ Training failed: {result['reason']}")
        sys.exit(1)

    print("=" * 60)
    print("  ✅ ML MODEL TRAINED & PERSISTED")
    print("=" * 60)
    print(f"  Model:            {result['model']} {result['version']}")
    print(f"  Contamination:    {result['contamination']}")
    print(f"  Lookback (days):  {result['lookback_days']}")
    print(f"  Training samples: {result['samples']:,} employees")
    if result["no_activity"]:
        print(f"  No activity:      {result['no_activity']} (excluded)")
    print(f"  Trained at:       {result['trained_at']}")
    print(f"  Model file:       {result['model_path']}")
    print()
    print("  The app now scores with this trained model. Run it again with")
    print("  different --days/--contamination to retrain.")


if __name__ == "__main__":
    main()
