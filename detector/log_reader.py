import json
from collections import Counter
from pathlib import Path


LOG_PATH = Path("/data/nginx/ia_access.jsonl")


def read_events(log_path):
    """Lee el archivo JSONL y devuelve una lista de eventos."""

    events = []

    with log_path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
                events.append(event)

            except json.JSONDecodeError as error:
                print(f"Línea {line_number} inválida: {error}")

    return events


def main():
    if not LOG_PATH.exists():
        raise SystemExit(f"No existe el archivo: {LOG_PATH}")

    events = read_events(LOG_PATH)

    if not events:
        raise SystemExit("El archivo existe, pero no contiene eventos.")

    statuses = Counter(event["status"] for event in events)
    methods = Counter(event["method"] for event in events)

    average_time = sum(
        float(event["request_time"]) for event in events
    ) / len(events)

    print(f"Eventos leídos: {len(events)}")

    print("\nMétodos HTTP:")
    for method, amount in sorted(methods.items()):
        print(f"  {method}: {amount}")

    print("\nEstados HTTP:")
    for status, amount in sorted(statuses.items()):
        print(f"  {status}: {amount}")

    print(f"\nTiempo promedio: {average_time:.6f} segundos")


if __name__ == "__main__":
    main()