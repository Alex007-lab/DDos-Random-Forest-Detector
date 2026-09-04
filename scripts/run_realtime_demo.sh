#!/usr/bin/env bash

set -euo pipefail


SCRIPT_DIRECTORY="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"
PROJECT_DIRECTORY="$(
    cd -- "$SCRIPT_DIRECTORY/.."
    pwd
)"

cd "$PROJECT_DIRECTORY"

if [[ ! -f models/detector.joblib ]]; then
    echo "Error: falta models/detector.joblib."
    echo "Ejecuta primero: ./scripts/run_pt2_pipeline.sh"
    exit 1
fi

RUN_TAG="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p reports/archive reports/demo reports/alerts reports/detector

docker compose --profile monitoring stop detector >/dev/null 2>&1 || true
docker compose up -d --build nginx

ACTIVE_LINES="$(
    docker compose exec -T nginx \
        sh -c 'wc -l < /var/log/nginx/ia_access.jsonl'
)"
if (( ACTIVE_LINES > 0 )); then
    docker compose cp \
        nginx:/var/log/nginx/ia_access.jsonl \
        "reports/archive/pre_demo_${RUN_TAG}.jsonl"
fi
docker compose exec -T nginx \
    sh -c ': > /var/log/nginx/ia_access.jsonl'

for output in \
    reports/detector/predictions.jsonl \
    reports/alerts/alerts.jsonl
do
    if [[ -s "$output" ]]; then
        base_name="$(basename "$output")"
        mv "$output" "reports/archive/${RUN_TAG}_${base_name}"
    fi
done

cleanup() {
    docker compose --profile monitoring stop detector >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose --profile monitoring up -d --build detector

echo "Fase normal: 2 usuarios durante 40 segundos."
docker compose run --rm \
    -e TRAFFIC_PROFILE=normal \
    locust \
    -f /mnt/locust/locustfile.py \
    --headless \
    --host http://nginx \
    --users 2 \
    --spawn-rate 1 \
    --run-time 40s \
    --csv "/reports/${RUN_TAG}_demo_normal" \
    --html "/reports/${RUN_TAG}_demo_normal.html"

sleep 12

echo "Fase anómala autorizada: 20 usuarios durante 40 segundos."
docker compose run --rm \
    -e TRAFFIC_PROFILE=anomalous \
    locust \
    -f /mnt/locust/locustfile.py \
    --headless \
    --host http://nginx \
    --users 20 \
    --spawn-rate 10 \
    --run-time 40s \
    --csv "/reports/${RUN_TAG}_demo_attack" \
    --html "/reports/${RUN_TAG}_demo_attack.html"

sleep 12

docker compose cp \
    nginx:/var/log/nginx/ia_access.jsonl \
    "reports/demo/${RUN_TAG}_traffic.jsonl"

cleanup
trap - EXIT

python3 - <<'PY'
from pathlib import Path
import json

predictions = Path("reports/detector/predictions.jsonl")
alerts = Path("reports/alerts/alerts.jsonl")

def read(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]

prediction_rows = read(predictions)
alert_rows = read(alerts)
normal = sum(row["prediction"] == "normal" for row in prediction_rows)
attack = sum(row["prediction"] == "attack" for row in prediction_rows)

print(f"Predicciones normales: {normal}")
print(f"Predicciones attack: {attack}")
print(f"Alertas registradas: {len(alert_rows)}")
if alert_rows:
    last = alert_rows[-1]
    print(
        "Última alerta: "
        f"score={last['attack_score']}, "
        f"RPS={last['features']['requests_per_second']}, "
        f"acción={last['action']}"
    )
PY

echo "Demostración terminada sin bloqueo automático."
echo "Predicciones: reports/detector/predictions.jsonl"
echo "Alertas: reports/alerts/alerts.jsonl"
echo "Tráfico RAW: reports/demo/${RUN_TAG}_traffic.jsonl"
