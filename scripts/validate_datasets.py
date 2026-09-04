#!/usr/bin/env python3
"""Audita la integridad y trazabilidad de los datasets de PT2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys

from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "detector"))

from features import (  # noqa: E402
    DATASET_COLUMNS,
    FEATURE_COLUMNS,
    calculate_features,
    group_events,
    parse_event_line,
)


EXPECTED_EXPERIMENTS = {
    "train": (
        "normal_train_01",
        "normal_train_02",
        "normal_train_03",
        "attack_train_01",
        "attack_train_02",
        "attack_train_03",
    ),
    "validation": (
        "normal_validation_01",
        "attack_validation_01",
    ),
    "test": (
        "normal_test_01",
        "attack_test_01",
    ),
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida JSONL, CSV procesados y reportes de Locust sin "
            "modificar la evidencia."
        )
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Reporta experimentos faltantes como advertencias.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Guarda un reporte estructurado opcional.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_raw(path: Path) -> tuple[list[dict], list[str]]:
    events: list[dict] = []
    errors: list[str] = []

    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                events.append(parse_event_line(line))
            except Exception as error:  # Se conserva la línea exacta en RAW.
                errors.append(f"línea {line_number}: {error}")

    return events, errors


def read_processed(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def rows_match(expected: dict, actual: dict) -> bool:
    for column in DATASET_COLUMNS:
        if column in {"window_start", "window_end", "label"}:
            if str(expected[column]) != str(actual[column]):
                return False
            continue

        try:
            if not math.isclose(
                float(expected[column]),
                float(actual[column]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return False
        except (KeyError, TypeError, ValueError):
            return False

    return True


def locust_aggregate(path: Path) -> dict | None:
    if not path.exists():
        return None

    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("Name") == "Aggregated":
                return row
    return None


def validate_numeric_rows(
    experiment: str,
    rows: list[dict],
    label: str,
    window_seconds: int,
) -> list[str]:
    errors: list[str] = []
    seen_windows: set[str] = set()

    for number, row in enumerate(rows, start=2):
        prefix = f"{experiment} fila {number}"

        if row.get("label") != label:
            errors.append(
                f"{prefix}: etiqueta {row.get('label')!r}; se esperaba {label!r}"
            )

        try:
            start = datetime.fromisoformat(row["window_start"])
            end = datetime.fromisoformat(row["window_end"])
            if (end - start).total_seconds() != window_seconds:
                errors.append(f"{prefix}: duración de ventana incorrecta")
            if row["window_start"] in seen_windows:
                errors.append(f"{prefix}: ventana duplicada")
            seen_windows.add(row["window_start"])

            values = {name: float(row[name]) for name in FEATURE_COLUMNS}
            if not all(math.isfinite(value) for value in values.values()):
                errors.append(f"{prefix}: contiene NaN o infinito")
            if any(value < 0 for value in values.values()):
                errors.append(f"{prefix}: contiene una característica negativa")
            if not 0 <= values["error_4xx_ratio"] <= 1:
                errors.append(f"{prefix}: error_4xx_ratio fuera de [0, 1]")
            if not 0 <= values["error_5xx_ratio"] <= 1:
                errors.append(f"{prefix}: error_5xx_ratio fuera de [0, 1]")
            expected_rps = values["request_count"] / window_seconds
            if not math.isclose(
                values["requests_per_second"],
                expected_rps,
                abs_tol=1e-6,
            ):
                errors.append(f"{prefix}: requests_per_second inconsistente")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{prefix}: valor inválido ({error})")

    return errors


def validate_experiment(
    root: Path,
    split: str,
    experiment: str,
    window_seconds: int,
) -> tuple[dict, list[str], list[str]]:
    label = experiment.split("_", maxsplit=1)[0]
    raw_path = root / "datasets" / "raw" / f"{experiment}.jsonl"
    processed_path = root / "datasets" / "processed" / f"{experiment}.csv"
    stats_path = root / "reports" / "locust" / f"{experiment}_stats.csv"
    html_path = root / "reports" / "locust" / f"{experiment}.html"

    errors: list[str] = []
    warnings: list[str] = []
    result = {
        "experiment": experiment,
        "split": split,
        "label": label,
        "raw_events": 0,
        "processed_windows": 0,
        "included_events": 0,
        "locust_requests": None,
    }

    missing = [
        str(path.relative_to(root))
        for path in (raw_path, processed_path, stats_path, html_path)
        if not path.exists()
    ]
    if missing:
        errors.append("faltan evidencias: " + ", ".join(missing))
        return result, errors, warnings

    events, raw_errors = read_raw(raw_path)
    if raw_errors:
        errors.append(
            f"{len(raw_errors)} líneas RAW inválidas; primera: {raw_errors[0]}"
        )
    if not events:
        errors.append("el RAW no contiene eventos válidos")
        return result, errors, warnings

    header, rows = read_processed(processed_path)
    if tuple(header) != DATASET_COLUMNS:
        errors.append(
            "encabezado CSV distinto al contrato: " + ",".join(header)
        )
    if not rows:
        errors.append("el CSV procesado no contiene ventanas")
        return result, errors, warnings

    errors.extend(
        validate_numeric_rows(experiment, rows, label, window_seconds)
    )

    all_windows = sorted(group_events(events, window_seconds).items())
    if len(all_windows) < 3:
        errors.append("se necesitan al menos tres ventanas para quitar bordes")
        expected_rows: list[dict] = []
    else:
        expected_rows = [
            calculate_features(start, window_events, window_seconds, label)
            for start, window_events in all_windows[1:-1]
        ]

    if len(expected_rows) != len(rows):
        errors.append(
            f"el CSV tiene {len(rows)} ventanas; al regenerar se obtienen "
            f"{len(expected_rows)}"
        )
    else:
        mismatches = sum(
            not rows_match(expected, actual)
            for expected, actual in zip(expected_rows, rows)
        )
        if mismatches:
            errors.append(
                f"{mismatches} ventanas no coinciden con el RAW regenerado"
            )

    aggregate = locust_aggregate(stats_path)
    if aggregate is None:
        errors.append("el reporte de Locust no contiene la fila Aggregated")
        locust_requests = None
    else:
        try:
            locust_requests = int(aggregate["Request Count"])
            failures = int(aggregate["Failure Count"])
            if failures:
                warnings.append(f"Locust reportó {failures} fallos")
        except (KeyError, TypeError, ValueError):
            locust_requests = None
            errors.append("conteos inválidos en el reporte de Locust")

    included_events = sum(int(row["request_count"]) for row in rows)
    result.update(
        {
            "raw_events": len(events),
            "processed_windows": len(rows),
            "included_events": included_events,
            "discarded_edge_events": len(events) - included_events,
            "locust_requests": locust_requests,
            "raw_sha256": sha256(raw_path),
            "processed_sha256": sha256(processed_path),
        }
    )

    if locust_requests is not None:
        difference = len(events) - locust_requests
        result["nginx_minus_locust"] = difference
        if difference:
            warnings.append(
                "Nginx y Locust difieren en "
                f"{difference:+d} peticiones; Nginx se conserva como fuente RAW"
            )

    return result, errors, warnings


def main() -> int:
    arguments = parse_arguments()
    root = arguments.project_root.resolve()

    if arguments.window_seconds <= 0:
        raise SystemExit("--window-seconds debe ser mayor que cero")

    report = {
        "status": "ok",
        "project_root": str(root),
        "window_seconds": arguments.window_seconds,
        "experiments": [],
        "errors": [],
        "warnings": [],
        "class_windows": {},
    }
    raw_hashes: dict[str, str] = {}

    for split, experiments in EXPECTED_EXPERIMENTS.items():
        for experiment in experiments:
            result, errors, warnings = validate_experiment(
                root,
                split,
                experiment,
                arguments.window_seconds,
            )

            missing_only = errors and all(
                error.startswith("faltan evidencias:") for error in errors
            )
            if arguments.allow_incomplete and missing_only:
                report["warnings"].extend(
                    f"{experiment}: {error}" for error in errors
                )
            else:
                report["errors"].extend(
                    f"{experiment}: {error}" for error in errors
                )

            report["warnings"].extend(
                f"{experiment}: {warning}" for warning in warnings
            )
            report["experiments"].append(result)

            digest = result.get("raw_sha256")
            if digest:
                if digest in raw_hashes:
                    report["errors"].append(
                        f"RAW duplicado: {experiment} y {raw_hashes[digest]}"
                    )
                raw_hashes[digest] = experiment

    class_windows = Counter()
    for experiment in report["experiments"]:
        class_windows[experiment["label"]] += experiment["processed_windows"]
    report["class_windows"] = dict(sorted(class_windows.items()))

    if report["errors"]:
        report["status"] = "error"
    elif any("faltan evidencias" in item for item in report["warnings"]):
        report["status"] = "incomplete"

    if arguments.json_output:
        output_path = arguments.json_output
        if not output_path.is_absolute():
            output_path = root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"Estado: {report['status']}")
    print(
        "Ventanas por clase: "
        + ", ".join(
            f"{label}={amount}"
            for label, amount in report["class_windows"].items()
        )
    )
    for warning in report["warnings"]:
        print(f"ADVERTENCIA: {warning}")
    for error in report["errors"]:
        print(f"ERROR: {error}")

    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
