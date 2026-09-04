#!/usr/bin/env bash

set -euo pipefail


show_usage() {
    echo "Uso:"
    echo "  $0 <label> <split> <id> <usuarios> <spawn-rate> <duracion>"
    echo
    echo "Ejemplo:"
    echo "  $0 normal train 01 2 1 120s"
}


if [[ $# -ne 6 ]]; then
    show_usage
    exit 1
fi


LABEL="$1"
SPLIT="$2"
RUN_ID="$3"
USERS="$4"
SPAWN_RATE="$5"
DURATION="$6"


case "$LABEL" in
    normal)
        TRAFFIC_PROFILE="normal"
        ;;
    attack)
        TRAFFIC_PROFILE="anomalous"
        ;;
    *)
        echo "Error: label debe ser 'normal' o 'attack'."
        exit 1
        ;;
esac


case "$SPLIT" in
    train|validation|test)
        ;;
    *)
        echo "Error: split debe ser train, validation o test."
        exit 1
        ;;
esac


if [[ ! "$RUN_ID" =~ ^[0-9]{2}$ ]]; then
    echo "Error: el id debe tener dos dígitos, por ejemplo 01."
    exit 1
fi

if [[ ! "$USERS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: usuarios debe ser un entero mayor que cero."
    exit 1
fi

if [[ ! "$SPAWN_RATE" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: spawn-rate debe ser un entero mayor que cero."
    exit 1
fi

if [[ ! "$DURATION" =~ ^[1-9][0-9]*[sm]$ ]]; then
    echo "Error: duración debe tener formato 120s o 2m."
    exit 1
fi


SCRIPT_DIRECTORY="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

PROJECT_DIRECTORY="$(
    cd -- "$SCRIPT_DIRECTORY/.."
    pwd
)"

cd "$PROJECT_DIRECTORY"


EXPERIMENT="${LABEL}_${SPLIT}_${RUN_ID}"

RAW_OUTPUT="datasets/raw/${EXPERIMENT}.jsonl"
PROCESSED_OUTPUT="datasets/processed/${EXPERIMENT}.csv"
HTML_REPORT="reports/locust/${EXPERIMENT}.html"


mkdir -p datasets/raw/archive
mkdir -p datasets/processed
mkdir -p reports/locust


if [[ -e "$RAW_OUTPUT" ||
      -e "$PROCESSED_OUTPUT" ||
      -e "$HTML_REPORT" ]]; then
    echo "Error: ya existen resultados para ${EXPERIMENT}."
    echo "No se sobrescribirá evidencia existente."
    exit 1
fi


echo "Experimento: $EXPERIMENT"
echo "Perfil Locust: $TRAFFIC_PROFILE"
echo "Usuarios: $USERS"
echo "Spawn rate: $SPAWN_RATE"
echo "Duración: $DURATION"
echo


docker compose up -d nginx


ACTIVE_LINES="$(
    docker compose exec -T nginx \
        sh -c 'wc -l < /var/log/nginx/ia_access.jsonl'
)"


if (( ACTIVE_LINES > 0 )); then
    TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
    ARCHIVE_OUTPUT="datasets/raw/archive/pre_${EXPERIMENT}_${TIMESTAMP}.jsonl"

    echo "Archivando log activo en: $ARCHIVE_OUTPUT"

    docker compose cp \
        nginx:/var/log/nginx/ia_access.jsonl \
        "$ARCHIVE_OUTPUT"
fi


echo "Limpiando el log activo de Nginx."

docker compose exec -T nginx \
    sh -c ': > /var/log/nginx/ia_access.jsonl'


echo "Iniciando Locust."

docker compose run --rm \
    -e TRAFFIC_PROFILE="$TRAFFIC_PROFILE" \
    locust \
    -f /mnt/locust/locustfile.py \
    --headless \
    --host http://nginx \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --csv "/reports/${EXPERIMENT}" \
    --html "/reports/${EXPERIMENT}.html"


echo "Copiando el log generado."

docker compose cp \
    nginx:/var/log/nginx/ia_access.jsonl \
    "$RAW_OUTPUT"


echo "Extrayendo características."

docker compose run --rm detector \
    python feature_extractor.py \
    --input "/datasets/raw/${EXPERIMENT}.jsonl" \
    --output "/datasets/processed/${EXPERIMENT}.csv" \
    --label "$LABEL" \
    --window-seconds 10 \
    --drop-edge-windows


RAW_EVENTS="$(wc -l < "$RAW_OUTPUT")"
PROCESSED_LINES="$(wc -l < "$PROCESSED_OUTPUT")"
PROCESSED_WINDOWS=$((PROCESSED_LINES - 1))

INCLUDED_EVENTS="$(
    awk -F, '
        NR > 1 {
            total += $3
        }
        END {
            print total + 0
        }
    ' "$PROCESSED_OUTPUT"
)"

DISCARDED_EVENTS=$((RAW_EVENTS - INCLUDED_EVENTS))

echo "Limpiando el log activo ya respaldado."

docker compose exec -T nginx \
    sh -c ': > /var/log/nginx/ia_access.jsonl'
echo
echo "Experimento completado: $EXPERIMENT"
echo "Eventos capturados: $RAW_EVENTS"
echo "Eventos incluidos: $INCLUDED_EVENTS"
echo "Eventos descartados en bordes: $DISCARDED_EVENTS"
echo "Ventanas procesadas: $PROCESSED_WINDOWS"
echo "Log: $RAW_OUTPUT"
echo "Dataset: $PROCESSED_OUTPUT"
echo "Reporte: $HTML_REPORT"