#!/usr/bin/env python3
"""Entrena, selecciona y evalúa el detector HTTP de PT2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from features import FEATURE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABELS = ("normal", "attack")
POSITIVE_LABEL = "attack"
RANDOM_STATE = 42


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compara modelos con validation, evalúa una vez con test y "
            "guarda un artefacto reproducible."
        )
    )
    parser.add_argument(
        "--train",
        type=Path,
        default=PROJECT_ROOT / "datasets/splits/train.csv",
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=PROJECT_ROOT / "datasets/splits/validation.csv",
    )
    parser.add_argument(
        "--test",
        type=Path,
        default=PROJECT_ROOT / "datasets/splits/test.csv",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=PROJECT_ROOT / "models/detector.joblib",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=PROJECT_ROOT / "models/detector_metadata.json",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=PROJECT_ROOT / "reports/model/metrics.json",
    )
    parser.add_argument(
        "--confusion-output",
        type=Path,
        default=PROJECT_ROOT / "reports/model/confusion_matrix.csv",
    )
    parser.add_argument(
        "--predictions-output",
        type=Path,
        default=PROJECT_ROOT / "reports/model/test_predictions.csv",
    )
    parser.add_argument(
        "--importance-output",
        type=Path,
        default=PROJECT_ROOT / "reports/model/feature_importance.csv",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_dataset(path: Path) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    if not path.exists():
        raise ValueError(f"No existe el split: {path}")

    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    if not rows:
        raise ValueError(f"El split está vacío: {path}")

    matrix: list[list[float]] = []
    labels: list[str] = []

    for number, row in enumerate(rows, start=2):
        try:
            values = [float(row[column]) for column in FEATURE_COLUMNS]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{path}, fila {number}: {error}") from error

        if not np.isfinite(values).all():
            raise ValueError(f"{path}, fila {number}: NaN o infinito")

        label = row.get("label", "")
        if label not in LABELS:
            raise ValueError(
                f"{path}, fila {number}: etiqueta no válida {label!r}"
            )

        matrix.append(values)
        labels.append(label)

    present = set(labels)
    if present != set(LABELS):
        raise ValueError(
            f"{path}: debe contener ambas clases; contiene {sorted(present)}"
        )

    return np.asarray(matrix, dtype=float), np.asarray(labels), rows


def positive_scores(estimator, matrix: np.ndarray) -> np.ndarray:
    if not hasattr(estimator, "predict_proba"):
        raise ValueError("el estimador no produce probabilidades")

    classes = list(estimator.classes_)
    if POSITIVE_LABEL not in classes:
        raise ValueError("el estimador no contiene la clase attack")

    return estimator.predict_proba(matrix)[:, classes.index(POSITIVE_LABEL)]


def metrics_for(
    actual: np.ndarray,
    scores: np.ndarray,
    threshold: float,
) -> dict:
    predicted = np.where(scores >= threshold, POSITIVE_LABEL, "normal")
    matrix = confusion_matrix(actual, predicted, labels=list(LABELS))
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision": float(
            precision_score(
                actual,
                predicted,
                pos_label=POSITIVE_LABEL,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                actual,
                predicted,
                pos_label=POSITIVE_LABEL,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                actual,
                predicted,
                pos_label=POSITIVE_LABEL,
                zero_division=0,
            )
        ),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
    }


def threshold_candidates(scores: np.ndarray) -> list[float]:
    unique = sorted(float(value) for value in np.unique(scores))
    if not unique:
        return [0.5]

    spread = max(abs(unique[0]), abs(unique[-1]), 1.0)
    epsilon = spread * 1e-9
    candidates = {
        unique[0] - epsilon,
        unique[-1] + epsilon,
        *unique,
    }
    candidates.update(
        (left + right) / 2
        for left, right in zip(unique, unique[1:])
    )
    if 0 <= unique[0] and unique[-1] <= 1:
        candidates.update({0.0, 0.5, 1.0})
    return sorted(candidates)


def select_threshold(actual: np.ndarray, scores: np.ndarray) -> dict:
    evaluated = [
        metrics_for(actual, scores, threshold)
        for threshold in threshold_candidates(scores)
    ]

    # Primero F1 y recall; en empate se prefiere un umbral cercano a 0.5.
    return max(
        evaluated,
        key=lambda item: (
            item["f1"],
            item["recall"],
            item["precision"],
            item["accuracy"],
            -abs(item["threshold"] - 0.5),
        ),
    )


def build_candidates() -> dict:
    return {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=2000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "decision_tree": DecisionTreeClassifier(
            class_weight="balanced",
            max_depth=3,
            min_samples_leaf=2,
            random_state=RANDOM_STATE,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            max_depth=5,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
    }


def feature_importance(estimator, model_name: str) -> list[tuple[str, float]]:
    if model_name == "logistic_regression":
        values = np.abs(
            estimator.named_steps["classifier"].coef_[0]
        )
    else:
        values = estimator.feature_importances_

    return sorted(
        zip(FEATURE_COLUMNS, (float(value) for value in values)),
        key=lambda item: item[1],
        reverse=True,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    arguments = parse_arguments()
    output_paths = (
        arguments.model_output,
        arguments.metadata_output,
        arguments.metrics_output,
        arguments.confusion_output,
        arguments.predictions_output,
        arguments.importance_output,
    )
    existing = [path for path in output_paths if path.exists()]
    if existing and not arguments.force:
        print("No se sobrescribirán resultados existentes. Usa --force:")
        for path in existing:
            print(f"  - {path}")
        return 1

    train_x, train_y, train_rows = load_dataset(arguments.train)
    validation_x, validation_y, validation_rows = load_dataset(
        arguments.validation
    )
    test_x, test_y, test_rows = load_dataset(arguments.test)

    validation_results: dict[str, dict] = {}
    fitted_models: dict[str, object] = {}

    for name, estimator in build_candidates().items():
        estimator.fit(train_x, train_y)
        scores = positive_scores(estimator, validation_x)
        validation_results[name] = select_threshold(validation_y, scores)
        fitted_models[name] = estimator

    simplicity = {
        "logistic_regression": 3,
        "decision_tree": 2,
        "random_forest": 1,
    }
    selected_name = max(
        validation_results,
        key=lambda name: (
            validation_results[name]["f1"],
            validation_results[name]["recall"],
            validation_results[name]["precision"],
            validation_results[name]["accuracy"],
            simplicity[name],
        ),
    )
    selected_model = fitted_models[selected_name]
    threshold = validation_results[selected_name]["threshold"]

    # El conjunto test se consulta únicamente después de seleccionar modelo y
    # umbral con validation.
    test_scores = positive_scores(selected_model, test_x)
    test_metrics = metrics_for(test_y, test_scores, threshold)
    test_predicted = np.where(
        test_scores >= threshold,
        POSITIVE_LABEL,
        "normal",
    )

    baseline_validation = select_threshold(
        validation_y,
        validation_x[:, FEATURE_COLUMNS.index("requests_per_second")],
    )
    baseline_test = metrics_for(
        test_y,
        test_x[:, FEATURE_COLUMNS.index("requests_per_second")],
        baseline_validation["threshold"],
    )

    created_at = datetime.now(timezone.utc).isoformat()
    dataset_hashes = {
        "train": sha256(arguments.train),
        "validation": sha256(arguments.validation),
        "test": sha256(arguments.test),
    }
    row_counts = {
        "train": len(train_rows),
        "validation": len(validation_rows),
        "test": len(test_rows),
    }

    bundle = {
        "artifact_version": 1,
        "created_at": created_at,
        "model_name": selected_name,
        "estimator": selected_model,
        "threshold": threshold,
        "positive_label": POSITIVE_LABEL,
        "feature_columns": list(FEATURE_COLUMNS),
        "window_seconds": 10,
        "dataset_sha256": dataset_hashes,
        "sklearn_version": sklearn.__version__,
    }

    metadata = {
        key: value
        for key, value in bundle.items()
        if key != "estimator"
    }
    metadata.update(
        {
            "python_version": platform.python_version(),
            "labels": list(LABELS),
            "selection_rule": (
                "máximo F1, recall, precision y accuracy en validation; "
                "en empate se prefiere el modelo más interpretable"
            ),
            "test_usage": (
                "evaluado después de fijar modelo y umbral; no usar para ajuste"
            ),
        }
    )

    metrics = {
        "created_at": created_at,
        "row_counts": row_counts,
        "validation_candidates": validation_results,
        "selected_model": selected_name,
        "selected_threshold": threshold,
        "model_test": test_metrics,
        "baseline": {
            "rule": "attack si requests_per_second >= threshold",
            "validation": baseline_validation,
            "test": baseline_test,
        },
    }

    arguments.model_output.parent.mkdir(parents=True, exist_ok=True)
    temporary_model = arguments.model_output.with_suffix(
        arguments.model_output.suffix + ".tmp"
    )
    joblib.dump(bundle, temporary_model)
    temporary_model.replace(arguments.model_output)
    write_json(arguments.metadata_output, metadata)
    write_json(arguments.metrics_output, metrics)

    arguments.confusion_output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.confusion_output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["actual\\predicted", "normal", "attack"])
        matrix = confusion_matrix(test_y, test_predicted, labels=list(LABELS))
        writer.writerow(["normal", int(matrix[0, 0]), int(matrix[0, 1])])
        writer.writerow(["attack", int(matrix[1, 0]), int(matrix[1, 1])])

    arguments.predictions_output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.predictions_output.open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        fieldnames = [
            "experiment_id",
            "window_start",
            "window_end",
            "actual_label",
            "predicted_label",
            "attack_score",
            "threshold",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for source, actual, predicted, score in zip(
            test_rows,
            test_y,
            test_predicted,
            test_scores,
        ):
            writer.writerow(
                {
                    "experiment_id": source.get("experiment_id", ""),
                    "window_start": source.get("window_start", ""),
                    "window_end": source.get("window_end", ""),
                    "actual_label": actual,
                    "predicted_label": predicted,
                    "attack_score": f"{float(score):.9f}",
                    "threshold": f"{float(threshold):.9f}",
                }
            )

    arguments.importance_output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.importance_output.open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["feature", "importance_absolute"])
        for feature, importance in feature_importance(
            selected_model,
            selected_name,
        ):
            writer.writerow([feature, f"{importance:.9f}"])

    print(f"Modelo seleccionado: {selected_name}")
    print(f"Umbral: {threshold:.6f}")
    print(
        "Test modelo: "
        f"accuracy={test_metrics['accuracy']:.4f}, "
        f"precision={test_metrics['precision']:.4f}, "
        f"recall={test_metrics['recall']:.4f}, "
        f"F1={test_metrics['f1']:.4f}"
    )
    print(
        "Test baseline: "
        f"accuracy={baseline_test['accuracy']:.4f}, "
        f"precision={baseline_test['precision']:.4f}, "
        f"recall={baseline_test['recall']:.4f}, "
        f"F1={baseline_test['f1']:.4f}"
    )
    print(f"Artefacto: {arguments.model_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
