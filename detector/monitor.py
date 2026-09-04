#!/usr/bin/env python3
"""Monitor de inferencia HTTP y alertas auditables de PT2."""

from __future__ import annotations

import argparse
import json
import os
import time

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np

from features import (
    FEATURE_COLUMNS,
    calculate_features,
    group_events,
    parse_event_line,
    read_events,
    window_start,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Lee ventanas HTTP, carga el modelo y registra alertas sin "
            "bloquear direcciones."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("/data/nginx/ia_access.jsonl"),
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("/models/detector.joblib"),
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=Path("/reports/detector/predictions.jsonl"),
    )
    parser.add_argument(
        "--alerts",
        type=Path,
        default=Path("/reports/alerts/alerts.jsonl"),
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Procesa un archivo terminado, quita bordes y sale.",
    )
    parser.add_argument(
        "--from-start",
        action="store_true",
        help="En vivo, comienza al principio en vez de esperar líneas nuevas.",
    )
    parser.add_argument(
        "--include-first-window",
        action="store_true",
        help="En vivo, no descarta la primera ventana potencialmente parcial.",
    )
    parser.add_argument("--grace-seconds", type=float, default=1.0)
    parser.add_argument("--poll-interval", type=float, default=0.2)
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Solo en replay: reemplaza los archivos de salida indicados.",
    )
    return parser.parse_args()


def load_bundle(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"No existe el modelo: {path}")

    # joblib utiliza serialización tipo pickle. Solo debe cargarse un artefacto
    # generado por este proyecto, nunca un modelo recibido de una fuente no
    # confiable.
    bundle = joblib.load(path)
    required = {
        "estimator",
        "threshold",
        "feature_columns",
        "window_seconds",
        "model_name",
    }
    missing = required - set(bundle)
    if missing:
        raise ValueError(
            "el artefacto no contiene: " + ", ".join(sorted(missing))
        )
    if tuple(bundle["feature_columns"]) != FEATURE_COLUMNS:
        raise ValueError(
            "las características del modelo no coinciden con features.py"
        )
    if int(bundle["window_seconds"]) <= 0:
        raise ValueError("window_seconds inválido en el modelo")
    return bundle


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def source_summary(events: list[dict]) -> dict:
    counts = Counter(
        str(event.get("remote_addr", "unknown")) for event in events
    )
    top_source, top_count = counts.most_common(1)[0]
    return {
        "observed_sources": len(counts),
        "top_remote_addr": top_source,
        "top_remote_addr_requests": top_count,
    }


def predict_window(
    bundle: dict,
    start: datetime,
    events: list[dict],
    predictions_path: Path,
    alerts_path: Path,
) -> dict:
    window_seconds = int(bundle["window_seconds"])
    features = calculate_features(
        start,
        events,
        window_seconds,
        "unlabeled",
    )
    matrix = np.asarray(
        [[features[column] for column in FEATURE_COLUMNS]],
        dtype=float,
    )

    estimator = bundle["estimator"]
    classes = list(estimator.classes_)
    attack_index = classes.index("attack")
    score = float(estimator.predict_proba(matrix)[0, attack_index])
    threshold = float(bundle["threshold"])
    prediction = "attack" if score >= threshold else "normal"
    action = "alert_only" if prediction == "attack" else "none"

    record = {
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "window_start": features["window_start"],
        "window_end": features["window_end"],
        "prediction": prediction,
        "attack_score": round(score, 9),
        "threshold": round(threshold, 9),
        "model_name": bundle["model_name"],
        "action": action,
        "features": {
            column: features[column] for column in FEATURE_COLUMNS
        },
        "source_summary": source_summary(events),
    }

    append_jsonl(predictions_path, record)
    if prediction == "attack":
        append_jsonl(alerts_path, record)

    print(json.dumps(record, ensure_ascii=False), flush=True)
    return record


def prepare_replay_outputs(arguments: argparse.Namespace) -> None:
    existing = [
        path
        for path in (arguments.predictions, arguments.alerts)
        if path.exists()
    ]
    if existing and not arguments.overwrite_output:
        raise ValueError(
            "ya existen salidas de replay; usa otras rutas o "
            "--overwrite-output: "
            + ", ".join(str(path) for path in existing)
        )
    if arguments.overwrite_output:
        for path in existing:
            path.unlink()


def run_replay(arguments: argparse.Namespace, bundle: dict) -> int:
    if not arguments.input.exists():
        raise ValueError(f"No existe el log: {arguments.input}")

    prepare_replay_outputs(arguments)
    events = read_events(arguments.input)
    windows = sorted(
        group_events(events, int(bundle["window_seconds"])).items()
    )
    if len(windows) < 3:
        raise ValueError(
            "se necesitan al menos tres ventanas para descartar bordes"
        )

    selected = windows[1:-1]
    attacks = 0
    for start, window_events in selected:
        record = predict_window(
            bundle,
            start,
            window_events,
            arguments.predictions,
            arguments.alerts,
        )
        attacks += record["prediction"] == "attack"

    print(
        f"Replay completado: ventanas={len(selected)}, "
        f"alertas_attack={attacks}"
    )
    return 0


def wait_for_log(path: Path, poll_interval: float) -> None:
    while not path.exists():
        print(f"Esperando el log: {path}", flush=True)
        time.sleep(poll_interval)


def run_follow(arguments: argparse.Namespace, bundle: dict) -> int:
    if arguments.poll_interval <= 0:
        raise ValueError("--poll-interval debe ser mayor que cero")
    if arguments.grace_seconds < 0:
        raise ValueError("--grace-seconds no puede ser negativo")

    wait_for_log(arguments.input, arguments.poll_interval)
    window_seconds = int(bundle["window_seconds"])
    current_start: datetime | None = None
    current_events: list[dict] = []
    first_completed = False
    invalid_lines = 0
    late_events = 0

    stream = arguments.input.open(encoding="utf-8")
    if not arguments.from_start:
        stream.seek(0, os.SEEK_END)

    print(
        f"Monitor activo: modelo={bundle['model_name']}, "
        f"ventana={window_seconds}s, umbral={bundle['threshold']:.6f}",
        flush=True,
    )

    def complete_window() -> None:
        nonlocal current_start, current_events, first_completed
        if current_start is None or not current_events:
            return

        should_process = arguments.include_first_window or first_completed
        if should_process:
            predict_window(
                bundle,
                current_start,
                current_events,
                arguments.predictions,
                arguments.alerts,
            )
        else:
            print(
                "Ventana inicial descartada por posible inicio parcial: "
                f"{current_start.isoformat()}",
                flush=True,
            )

        first_completed = True
        current_start = None
        current_events = []

    while True:
        line = stream.readline()

        if line:
            try:
                event = parse_event_line(line)
            except Exception as error:
                invalid_lines += 1
                print(
                    f"Línea inválida #{invalid_lines}: {error}",
                    flush=True,
                )
                continue

            event_start = window_start(event["_timestamp"], window_seconds)
            if current_start is None:
                current_start = event_start
                current_events = [event]
            elif event_start == current_start:
                current_events.append(event)
            elif event_start > current_start:
                complete_window()
                current_start = event_start
                current_events = [event]
            else:
                late_events += 1
                print(
                    f"Evento tardío ignorado #{late_events}: "
                    f"{event['_timestamp'].isoformat()}",
                    flush=True,
                )
            continue

        if current_start is not None:
            deadline = (
                current_start
                + timedelta(seconds=window_seconds)
                + timedelta(seconds=arguments.grace_seconds)
            )
            if datetime.now(timezone.utc) >= deadline:
                complete_window()

        try:
            current_position = stream.tell()
            current_stat = os.fstat(stream.fileno())
            path_stat = arguments.input.stat()
            if current_stat.st_ino != path_stat.st_ino:
                stream.close()
                stream = arguments.input.open(encoding="utf-8")
            elif path_stat.st_size < current_position:
                stream.seek(0)
        except FileNotFoundError:
            stream.close()
            wait_for_log(arguments.input, arguments.poll_interval)
            stream = arguments.input.open(encoding="utf-8")

        time.sleep(arguments.poll_interval)


def main() -> int:
    arguments = parse_arguments()
    bundle = load_bundle(arguments.model)
    if arguments.replay:
        return run_replay(arguments, bundle)
    return run_follow(arguments, bundle)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"Error: {error}") from error
