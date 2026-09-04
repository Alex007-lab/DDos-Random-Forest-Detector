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

FORCE_ARGUMENTS=()
if [[ "${1:-}" == "--force" ]]; then
    FORCE_ARGUMENTS=(--force)
elif [[ $# -ne 0 ]]; then
    echo "Uso: $0 [--force]"
    exit 1
fi

echo "1/7 Validando evidencias de los diez experimentos."
python3 scripts/validate_datasets.py \
    --json-output reports/data_validation.json

echo "2/7 Construyendo splits por experimentos completos."
python3 scripts/build_splits.py "${FORCE_ARGUMENTS[@]}"

echo "3/7 Construyendo el entorno reproducible del detector."
docker compose build detector

echo "4/7 Entrenando, seleccionando y evaluando el modelo."
docker compose run --rm --no-deps detector \
    python train_model.py \
    --train /datasets/splits/train.csv \
    --validation /datasets/splits/validation.csv \
    --test /datasets/splits/test.csv \
    --model-output /models/detector.joblib \
    --metadata-output /models/detector_metadata.json \
    --metrics-output /reports/model/metrics.json \
    --confusion-output /reports/model/confusion_matrix.csv \
    --predictions-output /reports/model/test_predictions.csv \
    --importance-output /reports/model/feature_importance.csv \
    "${FORCE_ARGUMENTS[@]}"

echo "5/7 Reproduciendo el test normal con el monitor."
docker compose run --rm --no-deps detector \
    python monitor.py \
    --replay \
    --input /datasets/raw/normal_test_01.jsonl \
    --model /models/detector.joblib \
    --predictions /reports/detector/normal_test_predictions.jsonl \
    --alerts /reports/alerts/normal_test_alerts.jsonl \
    --overwrite-output

echo "6/7 Reproduciendo el test anómalo con el monitor."
docker compose run --rm --no-deps detector \
    python monitor.py \
    --replay \
    --input /datasets/raw/attack_test_01.jsonl \
    --model /models/detector.joblib \
    --predictions /reports/detector/attack_test_predictions.jsonl \
    --alerts /reports/alerts/attack_test_alerts.jsonl \
    --overwrite-output

echo "7/7 Generando el reporte de resultados desde la evidencia."
python3 scripts/generate_pt2_report.py

echo
echo "Pipeline PT2 completado."
echo "Modelo: models/detector.joblib"
echo "Métricas: reports/model/metrics.json"
echo "Matriz: reports/model/confusion_matrix.csv"
echo "Alertas replay: reports/alerts/attack_test_alerts.jsonl"
echo "Reporte final: reports/pt2_resultados.md"
