import argparse
import csv
import json

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Convierte logs JSONL de Nginx en ventanas numéricas."
    )

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    parser.add_argument(
        "--label",
        choices=["normal", "attack", "unlabeled"],
        default="unlabeled",
    )

    parser.add_argument(
        "--window-seconds",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--drop-edge-windows",
        action="store_true",
        help=(
            "Descarta la primera y la última ventana para evitar "
            "periodos parciales de inicio y finalización."
        ),
    )

    return parser.parse_args()


def window_start(timestamp, window_seconds):
    """Redondea un timestamp al comienzo de su ventana."""

    epoch_seconds = int(timestamp.timestamp())
    start_seconds = epoch_seconds - (epoch_seconds % window_seconds)

    return datetime.fromtimestamp(
        start_seconds,
        tz=timezone.utc,
    )


def read_events(input_path):
    """Lee y valida los eventos del archivo JSONL."""

    events = []

    with input_path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)

                timestamp = datetime.fromisoformat(
                    event["timestamp"]
                ).astimezone(timezone.utc)

                event["_timestamp"] = timestamp
                events.append(event)

            except (json.JSONDecodeError, KeyError, ValueError) as error:
                print(f"Línea {line_number} ignorada: {error}")

    return events


def group_events(events, window_seconds):
    """Agrupa peticiones pertenecientes a la misma ventana."""

    windows = defaultdict(list)

    for event in events:
        start = window_start(
            event["_timestamp"],
            window_seconds,
        )

        windows[start].append(event)

    return windows


def calculate_features(start, events, window_seconds, label):
    """Calcula las características numéricas de una ventana."""

    request_count = len(events)

    statuses = [int(event["status"]) for event in events]
    bytes_sent = [int(event["bytes_sent"]) for event in events]
    request_lengths = [
        int(event["request_length"]) for event in events
    ]
    request_times = [
        float(event["request_time"]) for event in events
    ]

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
        "unique_uris": len({
            event["uri"] for event in events
        }),
        "unique_connections": len({
            event["connection"] for event in events
        }),
        "label": label,
    }


def write_csv(rows, output_path):
    """Escribe las ventanas en formato CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    arguments = parse_arguments()

    if arguments.window_seconds <= 0:
        raise SystemExit("--window-seconds debe ser mayor que cero.")

    input_path = Path(arguments.input)
    output_path = Path(arguments.output)

    if not input_path.exists():
        raise SystemExit(f"No existe el archivo: {input_path}")

    events = read_events(input_path)

    if not events:
        raise SystemExit("No se encontraron eventos válidos.")

    windows = group_events(
        events,
        arguments.window_seconds,
    )

    all_windows = sorted(windows.items())
    selected_windows = all_windows
    discarded_window_count = 0

    if arguments.drop_edge_windows:
        if len(all_windows) < 3:
            raise SystemExit(
                "Se necesitan al menos 3 ventanas para descartar los bordes."
            )

        selected_windows = all_windows[1:-1]
        discarded_window_count = 2

    rows = [
        calculate_features(
            start,
            window_events,
            arguments.window_seconds,
            arguments.label,
        )
        for start, window_events in selected_windows
    ]

    included_event_count = sum(
        len(window_events)
        for _, window_events in selected_windows
    )

    discarded_event_count = len(events) - included_event_count

    write_csv(rows, output_path)

    print(f"Eventos válidos leídos: {len(events)}")
    print(f"Eventos incluidos: {included_event_count}")
    print(f"Eventos descartados: {discarded_event_count}")
    print(f"Ventanas detectadas: {len(all_windows)}")
    print(f"Ventanas descartadas: {discarded_window_count}")
    print(f"Ventanas generadas: {len(rows)}")
    print(f"Dataset creado: {output_path}")


if __name__ == "__main__":
    main()