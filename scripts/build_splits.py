#!/usr/bin/env python3
"""Construye train/validation/test por experimentos completos."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SPLIT_EXPERIMENTS = {
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
        description="Concatena CSV por ejecución sin mezclar ventanas al azar."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_experiment(path: Path, experiment: str) -> tuple[list[str], list[dict]]:
    expected_label = experiment.split("_", maxsplit=1)[0]

    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        header = list(reader.fieldnames or ())
        rows = list(reader)

    if not header or not rows:
        raise ValueError(f"{path}: CSV vacío o sin encabezado")
    if any(row.get("label") != expected_label for row in rows):
        raise ValueError(f"{path}: contiene etiquetas inesperadas")

    return header, rows


def main() -> int:
    arguments = parse_arguments()
    root = arguments.project_root.resolve()
    processed_dir = root / "datasets" / "processed"
    output_dir = root / "datasets" / "splits"
    manifest_path = output_dir / "manifest.json"

    input_paths = {
        experiment: processed_dir / f"{experiment}.csv"
        for experiments in SPLIT_EXPERIMENTS.values()
        for experiment in experiments
    }
    missing = [path for path in input_paths.values() if not path.exists()]
    if missing:
        print("No se pueden construir los splits. Faltan:")
        for path in missing:
            print(f"  - {path.relative_to(root)}")
        return 1

    outputs = [output_dir / f"{split}.csv" for split in SPLIT_EXPERIMENTS]
    outputs.append(manifest_path)
    existing = [path for path in outputs if path.exists()]
    if existing and not arguments.force:
        print("No se sobrescribirán splits existentes. Usa --force para regenerar:")
        for path in existing:
            print(f"  - {path.relative_to(root)}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_header: list[str] | None = None
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "separation_policy": "experimentos completos; sin división aleatoria",
        "splits": {},
        "inputs": {},
    }

    for split, experiments in SPLIT_EXPERIMENTS.items():
        combined: list[dict] = []

        for experiment in experiments:
            path = input_paths[experiment]
            header, rows = load_experiment(path, experiment)

            if canonical_header is None:
                canonical_header = header
            elif header != canonical_header:
                raise ValueError(f"{path}: encabezado distinto al resto")

            for row in rows:
                combined.append(
                    {
                        "experiment_id": experiment,
                        "split": split,
                        **row,
                    }
                )

            manifest["inputs"][experiment] = {
                "path": str(path.relative_to(root)),
                "sha256": sha256(path),
                "rows": len(rows),
                "label": experiment.split("_", maxsplit=1)[0],
            }

        fieldnames = ["experiment_id", "split", *(canonical_header or ())]
        output_path = output_dir / f"{split}.csv"
        temporary_path = output_path.with_suffix(".csv.tmp")
        with temporary_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined)
        temporary_path.replace(output_path)

        labels = Counter(row["label"] for row in combined)
        manifest["splits"][split] = {
            "path": str(output_path.relative_to(root)),
            "experiments": list(experiments),
            "rows": len(combined),
            "class_rows": dict(sorted(labels.items())),
            "sha256": sha256(output_path),
        }

        print(
            f"{split}: {len(combined)} ventanas "
            + ", ".join(f"{key}={value}" for key, value in sorted(labels.items()))
        )

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Manifiesto: {manifest_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
