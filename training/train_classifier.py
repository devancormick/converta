"""Quality classifier training CLI.

Usage:
    python training/train_classifier.py [--compare-champion] [--promote-if-better]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
from sklearn.model_selection import train_test_split

from data.schemas.config import Settings
from services.celery_app import app as celery_app
from services.classifier.model import build_production_pipeline
from training.evaluate_model import beats_champion, evaluate

settings = Settings()
GOLDEN_DATASET_PATH = Path("data/golden_datasets/classifier_golden.jsonl")


def load_training_data() -> tuple[list[str], list[int]]:
    texts, labels = [], []
    if GOLDEN_DATASET_PATH.exists():
        with open(GOLDEN_DATASET_PATH) as f:
            for line in f:
                row = json.loads(line)
                texts.append(row["text"])
                labels.append(int(row["label"]))
    if not texts:
        # synthetic fallback for CI
        positive = [
            "Your loan application has been reviewed. Please complete the next step.",
            "We found options that match your profile. Apply now to see your rate.",
            "Good news — you're pre-qualified. Finish your application today.",
        ]
        negative = [
            "GUARANTEED APPROVAL no credit check instant cash now!!!",
            "SSN 123-45-6789 required immediately for your loan",
            "Limited time!! Act now or lose this offer forever!!!",
        ]
        texts = positive * 20 + negative * 20
        labels = [1] * 60 + [0] * 60
        combined = list(zip(texts, labels))
        random.shuffle(combined)
        texts, labels = zip(*combined)
        texts, labels = list(texts), list(labels)
    return texts, labels


def get_champion_metrics() -> dict | None:
    try:
        client = mlflow.tracking.MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        alias = client.get_registered_model_alias(settings.classifier_model_name, "champion")
        run = client.get_run(alias.run_id)
        return dict(run.data.metrics)
    except Exception:
        return None


def train(compare_champion: bool = False, promote_if_better: bool = False) -> dict:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("quality-classifier-training")

    texts, labels = load_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    model = build_production_pipeline()

    with mlflow.start_run() as run:
        model.fit(X_train, y_train)
        metrics = evaluate(model, X_test, y_test)

        mlflow.log_params({"model_type": "xgboost", "test_size": 0.2})
        mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, float)})
        mlflow.sklearn.log_model(model, "model", registered_model_name=settings.classifier_model_name)

        print(f"Run ID: {run.info.run_id}")
        print(f"AUC: {metrics['auc']:.4f}  Precision: {metrics['precision']:.4f}")
        print(metrics["report"])

        if promote_if_better:
            champion_metrics = get_champion_metrics() if compare_champion else None
            if beats_champion(metrics, champion_metrics):
                client = mlflow.tracking.MlflowClient()
                versions = client.search_model_versions(f"name='{settings.classifier_model_name}'")
                latest = sorted(versions, key=lambda v: int(v.version))[-1]
                client.set_registered_model_alias(
                    settings.classifier_model_name, "champion", latest.version
                )
                print(f"Promoted version {latest.version} to champion.")
            else:
                print("Challenger did not beat champion. Not promoting.")

        return metrics


@celery_app.task(name="training.train_classifier.retrain_task")
def retrain_task():
    train(compare_champion=True, promote_if_better=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare-champion", action="store_true")
    parser.add_argument("--promote-if-better", action="store_true")
    args = parser.parse_args()
    result = train(compare_champion=args.compare_champion, promote_if_better=args.promote_if_better)
    sys.exit(0)
