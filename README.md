# Contramuseo - detector HTTP de PT2

Prototipo académico que protege el sitio Contramuseo en un laboratorio local.
Nginx registra el tráfico HTTP, un extractor lo convierte en ventanas numéricas
y un modelo clasifica cada ventana como `normal` o `attack`. En el segundo
trimestre la respuesta es una alerta auditable; no se bloquean direcciones.

## Flujo implementado

```text
Navegador o Locust
        ↓
      Nginx ──→ Contramuseo / API Flask / SQLite
        ↓
 ia_access.jsonl
        ↓
 feature_extractor.py
        ↓
 CSV por ventanas de 10 segundos
        ↓
 train_model.py ──→ modelo + métricas + matriz de confusión
        ↓
 monitor.py ──→ predicciones + alertas
```

## Componentes principales

- `docker-compose.yml`: infraestructura reproducible.
- `nginx/nginx.conf`: sitio, proxy y JSONL.
- `loadtest/locustfile.py`: tráfico normal y anómalo autorizado.
- `scripts/run_experiment.sh`: captura una ejecución sin sobrescribir evidencia.
- `detector/features.py`: fórmula única de las diez características.
- `detector/feature_extractor.py`: RAW JSONL a CSV.
- `scripts/validate_datasets.py`: auditoría y regeneración de CSV desde RAW.
- `scripts/build_splits.py`: separación por experimentos completos.
- `detector/train_model.py`: baseline, selección, evaluación y artefacto.
- `detector/monitor.py`: inferencia por ventanas y alertas `alert_only`.
- `scripts/run_pt2_pipeline.sh`: cierre reproducible del entrenamiento.
- `scripts/run_realtime_demo.sh`: demostración local normal/ataque.

## Inicio rápido

Trabaja siempre desde la raíz del proyecto. Debe existir un `.env` privado con
una `SECRET_KEY` aleatoria; `.env.example` explica cómo generarla.

```bash
docker compose up -d --build nginx flask-api
curl -s http://localhost:8080/api/health | python3 -m json.tool
python3 scripts/validate_datasets.py --allow-incomplete
```

Cuando existan los diez experimentos requeridos:

```bash
./scripts/run_pt2_pipeline.sh
./scripts/run_realtime_demo.sh
```

La guía completa está en `docs/guia_cierre_pt2.md`.

## Límites del alcance

- Solo se prueba infraestructura propia en `localhost` o la red de Docker.
- `attack` significa carga HTTP anómala controlada, no un DDoS real.
- El modelo observa ventanas agregadas, no paquetes de red.
- El bloqueo, dashboard y despliegue en Raspberry Pi pertenecen a PT3.
