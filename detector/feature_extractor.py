import argparse
import csv

from pathlib import Path

from features import calculate_features, group_events, read_events


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
