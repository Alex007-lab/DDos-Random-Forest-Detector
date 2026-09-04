# Guía de cierre del segundo trimestre

## 1. Criterio de terminado

PT2 termina cuando puede demostrarse este recorrido completo:

```text
tráfico controlado
→ Nginx
→ JSONL RAW
→ características por ventanas
→ train / validation / test
→ baseline y modelo evaluado
→ tráfico nuevo
→ predicción
→ alerta auditable
```

No forman parte del cierre de PT2: bloqueo automático, firewall, dashboard,
Raspberry Pi y mitigación. Esos componentes corresponden a PT3.

## 2. Estado verificado antes de los experimentos finales

La auditoría de los archivos conservados encontró:

| Componente | Estado |
|---|---|
| Docker, Nginx, Flask y SQLite | Implementado |
| Captura JSONL y extractor | Implementado y reproducible |
| Experimentos normales | 5 de 5 |
| Experimentos de ataque | 1 de 5 |
| Ventanas normales verificadas | 54 |
| Ventanas attack verificadas | 11 |
| Splits finales | Código listo; espera cuatro experimentos |
| Baseline y modelo | Código listo; espera splits completos |
| Monitor y alertas | Implementado y probado con fixtures temporales |
| Bloqueo | No se implementa en PT2 |

Faltan estas ejecuciones reales:

```text
attack_train_02
attack_train_03
attack_validation_01
attack_test_01
```

No deben fabricarse, copiarse ni obtenerse dividiendo `attack_train_01`. Tienen
que ser ejecuciones independientes para mantener válida la evaluación.

## 3. Preparación segura

Desde la raíz del proyecto:

```bash
pwd
git status --short
docker --version
docker compose version
docker compose config --services
docker compose up -d --build nginx flask-api
docker compose ps
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

En otra terminal, observa recursos durante cada prueba:

```bash
docker stats contramuseo-nginx contramuseo-api
```

Detén la prueba con `Ctrl+C` si la CPU permanece cerca de 90 %, la memoria
supera 85 %, algún contenedor reinicia o el equipo se vuelve inestable. No
ejecutes los cuatro comandos al mismo tiempo.

## 4. Generar los cuatro experimentos faltantes

Ejecuta uno, valida su salida y solo entonces continúa con el siguiente.

### 4.1 Segundo entrenamiento de ataque

```bash
./scripts/run_experiment.sh attack train 02 30 10 120s
python3 scripts/validate_datasets.py --allow-incomplete
```

### 4.2 Tercer entrenamiento de ataque

```bash
./scripts/run_experiment.sh attack train 03 40 10 120s
python3 scripts/validate_datasets.py --allow-incomplete
```

### 4.3 Validación de ataque

```bash
./scripts/run_experiment.sh attack validation 01 25 10 120s
python3 scripts/validate_datasets.py --allow-incomplete
```

### 4.4 Test de ataque

```bash
./scripts/run_experiment.sh attack test 01 35 10 120s
python3 scripts/validate_datasets.py \
  --json-output reports/data_validation.json
```

La última validación debe mostrar:

```text
Estado: ok
```

Si un experimento se interrumpe, conserva los archivos parciales y registra el
motivo. No lo presentes como evidencia completa ni lo renombres como otra
ejecución.

## 5. Qué valida el auditor

`validate_datasets.py` comprueba por cada experimento:

- JSON válido y campos necesarios.
- Encabezado y etiqueta correctos.
- Ventanas de diez segundos.
- Valores finitos, no negativos y proporciones entre 0 y 1.
- Coherencia entre `request_count` y `requests_per_second`.
- Regeneración exacta del CSV desde el RAW con `features.py`.
- Reporte HTML y CSV de Locust.
- Conteos RAW, procesados, descartados y reportados por Locust.
- Hash SHA-256 de cada evidencia.
- Ausencia de RAW duplicados.

El RAW de Nginx es la fuente para entrenar. Locust es una medición secundaria
del generador. En `attack_train_01`, las 115 peticiones adicionales de Nginx:

- tienen el mismo `User-Agent` de Locust;
- son peticiones GET válidas;
- no son duplicados por conexión/número de petición;
- aparecen en el borde temporal de la ejecución de alta tasa.

La evidencia es compatible con una diferencia de instante de cierre entre el
reporte final de Locust y el log de Nginx. Es una inferencia, no una causa
demostrada; por eso el auditor conserva y reporta la diferencia en vez de
alterar los datos.

## 6. Construir splits, entrenar y evaluar

Cuando la auditoría esté en `ok`:

```bash
./scripts/run_pt2_pipeline.sh
```

El script ejecuta siete etapas:

1. Audita los diez experimentos.
2. Construye `train.csv`, `validation.csv` y `test.csv` por ejecuciones.
3. Construye la imagen reproducible del detector.
4. Compara regresión logística, árbol y Random Forest en validation.
5. Selecciona modelo y umbral sin consultar test.
6. Evalúa una vez en test y reproduce los RAW de test con el monitor.
7. Genera el reporte Markdown desde la evidencia real.

Resultados principales:

```text
datasets/splits/train.csv
datasets/splits/validation.csv
datasets/splits/test.csv
datasets/splits/manifest.json
models/detector.joblib
models/detector_metadata.json
reports/model/metrics.json
reports/model/confusion_matrix.csv
reports/model/test_predictions.csv
reports/model/feature_importance.csv
reports/alerts/attack_test_alerts.jsonl
reports/pt2_resultados.md
```

No uses `test.csv` para cambiar el modelo después de ver su resultado. Hacerlo
convertiría test en otro conjunto de validación e invalidaría la métrica final.

## 7. Cómo interpretar la evaluación

| Métrica | Pregunta que responde |
|---|---|
| Accuracy | ¿Qué proporción total clasificó correctamente? |
| Precision | De las alertas, ¿cuántas correspondían a attack? |
| Recall | De los ataques, ¿cuántos detectó? |
| F1 | ¿Qué equilibrio obtuvo entre precision y recall? |
| Falso positivo | ¿Cuántas ventanas normales alertó? |
| Falso negativo | ¿Cuántas ventanas attack dejó pasar? |

El baseline clasifica únicamente por `requests_per_second`. Si baseline y modelo
obtienen resultados perfectos, la conclusión correcta no es que el proyecto
resuelve cualquier DDoS: significa que los escenarios actuales están muy
separados por volumen. Esa observación debe presentarse como limitación y como
motivación para escenarios más variados en PT3.

## 8. Demostración en tiempo real

Después del pipeline:

```bash
./scripts/run_realtime_demo.sh
```

La demostración:

1. Archiva el log y las salidas activas anteriores.
2. Inicia Nginx y el monitor.
3. Genera 40 segundos de tráfico normal.
4. Genera 40 segundos de carga anómala local con 20 usuarios.
5. Conserva el RAW de la demostración.
6. Muestra cuántas ventanas fueron normales, attack y cuántas alertas hubo.

La acción registrada debe ser:

```json
"action": "alert_only"
```

Esto demuestra el alcance correcto: detectar y alertar sin bloquear.

## 9. Evidencia mínima para el asesor

```bash
docker compose ps
curl -s http://localhost:8080/api/health | python3 -m json.tool
python3 scripts/validate_datasets.py
python3 -m json.tool datasets/splits/manifest.json
python3 -m json.tool reports/model/metrics.json
column -s, -t < reports/model/confusion_matrix.csv
tail -n 1 reports/alerts/attack_test_alerts.jsonl | python3 -m json.tool
sed -n '1,240p' reports/pt2_resultados.md
```

## 10. Checklist final

- [ ] Los diez experimentos pasan el auditor.
- [ ] Los splits tienen ambas clases y experimentos independientes.
- [ ] Existe el hash de cada split y dataset de entrada.
- [ ] El baseline se ajustó con validation.
- [ ] El modelo se seleccionó con validation.
- [ ] Test se utilizó una sola vez después de la selección.
- [ ] La matriz de confusión y métricas están guardadas.
- [ ] El monitor procesa ventanas nuevas con las mismas características.
- [ ] El replay normal no genera alertas attack injustificadas.
- [ ] El replay y la demo attack generan alertas auditables.
- [ ] La acción sigue siendo `alert_only`.
- [ ] Las limitaciones están explicadas.
- [ ] Los resultados finales están incorporados a la documentación.
