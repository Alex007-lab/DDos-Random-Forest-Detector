#!/usr/bin/env python3
"""Genera el reporte Markdown de resultados a partir de evidencia real."""

from __future__ import annotations

import argparse
import json

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/pt2_resultados.md"),
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"No existe la evidencia: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def percentage(value: float) -> str:
    return f"{value * 100:.2f} %"


def main() -> int:
    arguments = parse_arguments()
    root = arguments.project_root.resolve()
    output = arguments.output
    if not output.is_absolute():
        output = root / output

    validation = read_json(root / "reports/data_validation.json")
    metrics = read_json(root / "reports/model/metrics.json")
    metadata = read_json(root / "models/detector_metadata.json")
    alerts = read_jsonl(root / "reports/alerts/attack_test_alerts.jsonl")

    if validation.get("status") != "ok":
        raise ValueError(
            "data_validation.json no está en estado ok; no se emitirá un "
            "reporte final"
        )

    model_test = metrics["model_test"]
    baseline_test = metrics["baseline"]["test"]
    class_windows = validation["class_windows"]

    experiment_lines = []
    for item in validation["experiments"]:
        experiment_lines.append(
            "| {experiment} | {split} | {label} | {raw_events} | "
            "{processed_windows} | {included_events} | {locust_requests} | "
            "{nginx_minus_locust} |".format(
                nginx_minus_locust=item.get("nginx_minus_locust", 0),
                **item,
            )
        )

    warning_lines = validation.get("warnings") or ["Ninguna."]
    alert_example = alerts[-1] if alerts else None
    if alert_example:
        alert_text = (
            f"- Ventana: `{alert_example['window_start']}` a "
            f"`{alert_example['window_end']}`\n"
            f"- Predicción: `{alert_example['prediction']}`\n"
            f"- Score: `{alert_example['attack_score']}`\n"
            f"- Umbral: `{alert_example['threshold']}`\n"
            f"- RPS: `{alert_example['features']['requests_per_second']}`\n"
            f"- Acción: `{alert_example['action']}`"
        )
    else:
        alert_text = (
            "No se encontró una alerta en el replay de `attack_test_01`. "
            "Este resultado debe investigarse antes de presentar."
        )

    content = f"""# Resultados finales del segundo trimestre

Generado automáticamente el {datetime.now(timezone.utc).isoformat()} a partir
de los datasets, métricas y alertas conservados por el proyecto.

## Resultado ejecutivo

- Estado de la auditoría de datos: `{validation['status']}`.
- Ventanas normales: {class_windows.get('normal', 0)}.
- Ventanas de ataque: {class_windows.get('attack', 0)}.
- Modelo seleccionado: `{metrics['selected_model']}`.
- Umbral del modelo: `{metrics['selected_threshold']:.9f}`.
- F1 final en test: {percentage(model_test['f1'])}.
- Alertas en el replay de ataque: {len(alerts)}.
- Acción implementada en PT2: `alert_only`; no existe bloqueo automático.

## Evidencia por experimento

| Experimento | Split | Clase | RAW | Ventanas | Eventos incluidos | Locust | Nginx - Locust |
|---|---|---|---:|---:|---:|---:|---:|
{chr(10).join(experiment_lines)}

Los RAW de Nginx son la fuente de verdad para las características. Las
diferencias con el resumen final de Locust se conservan como observaciones de
instrumentación y no se corrigen manualmente.

## Selección y evaluación del modelo

El modelo y su umbral se eligieron únicamente con `validation.csv`. Después se
consultó `test.csv` una vez para la evaluación final.

| Método | Accuracy | Precision | Recall | F1 | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| {metrics['selected_model']} | {percentage(model_test['accuracy'])} | {percentage(model_test['precision'])} | {percentage(model_test['recall'])} | {percentage(model_test['f1'])} | {model_test['false_positive']} | {model_test['false_negative']} |
| Baseline RPS | {percentage(baseline_test['accuracy'])} | {percentage(baseline_test['precision'])} | {percentage(baseline_test['recall'])} | {percentage(baseline_test['f1'])} | {baseline_test['false_positive']} | {baseline_test['false_negative']} |

Regla base: clasificar como ataque cuando `requests_per_second` sea mayor o
igual a `{metrics['baseline']['validation']['threshold']:.6f}`. La comparación
permite comprobar si el modelo aporta algo frente a una regla de volumen.

## Ejemplo de alerta auditable

{alert_text}

## Reproducibilidad

- Versión del artefacto: `{metadata['artifact_version']}`.
- Python: `{metadata['python_version']}`.
- scikit-learn: `{metadata['sklearn_version']}`.
- Ventana: `{metadata['window_seconds']}` segundos.
- Características: {', '.join(f'`{name}`' for name in metadata['feature_columns'])}.
- Hash train: `{metadata['dataset_sha256']['train']}`.
- Hash validation: `{metadata['dataset_sha256']['validation']}`.
- Hash test: `{metadata['dataset_sha256']['test']}`.

## Advertencias de la auditoría

{chr(10).join(f'- {warning}' for warning in warning_lines)}

## Limitaciones

- Los experimentos representan carga HTTP anómala local, no un DDoS distribuido real.
- El origen observado es el contenedor de Locust; aún no identifica clientes públicos individuales.
- El dataset es pequeño y las clases pueden estar separadas principalmente por intensidad.
- Métricas altas en este laboratorio no demuestran generalización a tráfico de producción.
- Las ventanas vacías no aparecen en el dataset.
- PT2 alerta, pero no bloquea ni desconecta al origen. Esa mitigación corresponde a PT3.
"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Reporte creado: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(f"Error: {error}") from error
