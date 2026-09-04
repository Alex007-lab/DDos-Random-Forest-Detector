"""Funciones compartidas para convertir eventos HTTP en características.

Este módulo es la única fuente de verdad para las variables utilizadas por:

* ``feature_extractor.py`` durante la preparación del dataset.
* ``monitor.py`` durante la inferencia y alerta.

Mantener ambos recorridos en el mismo módulo evita el *training-serving skew*:
entrenar con una fórmula y predecir en vivo con otra diferente.
"""

from __future__ import annotations

import json

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


FEATURE_COLUMNS = (
    "request_count",
    "requests_per_second",
    "error_4xx_ratio",
    "error_5xx_ratio",
    "bytes_total",
    "avg_request_length",
    "avg_request_time",
    "max_request_time",
    "unique_uris",
    "unique_connections",
)

DATASET_COLUMNS = (
    "window_start",
    "window_end",
    *FEATURE_COLUMNS,
    "label",
)

REQUIRED_EVENT_FIELDS = (
    "timestamp",
    "status",
    "bytes_sent",
    "request_length",
    "request_time",
    "uri",
    "connection",
)


def parse_event_line(line: str) -> dict:
    """Convierte y valida una línea JSONL de Nginx.

    La función valida tanto la presencia como la conversión de los campos que
    utiliza el extractor. Devuelve el evento con ``_timestamp`` en UTC.
    """

    event = json.loads(line)

    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
    if missing:
        raise ValueError(
            "faltan campos obligatorios: " + ", ".join(sorted(missing))
        )

    timestamp = datetime.fromisoformat(str(event["timestamp"]))
    if timestamp.tzinfo is None:
        raise ValueError("timestamp sin zona horaria")

    event["_timestamp"] = timestamp.astimezone(timezone.utc)

    # Validar aquí permite ignorar una línea defectuosa antes de llegar al
    # cálculo de toda una ventana.
    int(event["status"])
    int(event["bytes_sent"])
    int(event["request_length"])
    float(event["request_time"])
    str(event["uri"])
    str(event["connection"])

    return event


def read_events(input_path: Path) -> list[dict]:
    """Lee eventos válidos de un JSONL y reporta las líneas descartadas."""

    events: list[dict] = []

    with input_path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                events.append(parse_event_line(line))
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                print(f"Línea {line_number} ignorada: {error}")

    return events


def window_start(timestamp: datetime, window_seconds: int) -> datetime:
    """Redondea un timestamp al comienzo de su ventana UTC."""

    if window_seconds <= 0:
        raise ValueError("window_seconds debe ser mayor que cero")

    epoch_seconds = int(timestamp.timestamp())
    start_seconds = epoch_seconds - (epoch_seconds % window_seconds)

    return datetime.fromtimestamp(start_seconds, tz=timezone.utc)


def group_events(
    events: Iterable[dict],
    window_seconds: int,
) -> dict[datetime, list[dict]]:
    """Agrupa peticiones pertenecientes a la misma ventana."""

    windows: dict[datetime, list[dict]] = defaultdict(list)

    for event in events:
        start = window_start(event["_timestamp"], window_seconds)
        windows[start].append(event)

    return windows


def calculate_features(
    start: datetime,
    events: list[dict],
    window_seconds: int,
    label: str,
) -> dict:
    """Calcula las diez características numéricas de una ventana."""

    if not events:
        raise ValueError("no se pueden calcular características sin eventos")

    request_count = len(events)

    statuses = [int(event["status"]) for event in events]
    bytes_sent = [int(event["bytes_sent"]) for event in events]
    request_lengths = [int(event["request_length"]) for event in events]
    request_times = [float(event["request_time"]) for event in events]

    errors_4xx = sum(400 <= status < 500 for status in statuses)
    errors_5xx = sum(500 <= status < 600 for status in statuses)

    return {
        "window_start": start.isoformat(),
        "window_end": (
            start + timedelta(seconds=window_seconds)
        ).isoformat(),
        "request_count": request_count,
        "requests_per_second": round(
            request_count / window_seconds,
            6,
        ),
        "error_4xx_ratio": round(errors_4xx / request_count, 6),
        "error_5xx_ratio": round(errors_5xx / request_count, 6),
        "bytes_total": sum(bytes_sent),
        "avg_request_length": round(
            sum(request_lengths) / request_count,
            6,
        ),
        "avg_request_time": round(
            sum(request_times) / request_count,
            6,
        ),
        "max_request_time": max(request_times),
        "unique_uris": len({event["uri"] for event in events}),
        "unique_connections": len(
            {event["connection"] for event in events}
        ),
        "label": label,
    }
