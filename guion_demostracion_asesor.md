# Guion de demostración del Proyecto Terminal

## Contramuseo: captura de tráfico y preparación de datos para detección de anomalías

Este documento contiene los comandos necesarios para mostrar el estado real del proyecto al asesor. Está pensado para una demostración de aproximadamente **15 minutos**, seguida de una sección opcional de preguntas técnicas.

La demostración distingue claramente entre:

- Lo que ya está implementado: infraestructura, sitio, API, logs, pruebas de carga y extracción de características.
- Lo que está parcialmente terminado: dataset de tráfico anómalo.
- Lo que todavía falta: entrenamiento del modelo, detección en tiempo real, alertas y mitigación.

> **Regla de seguridad:** todos los comandos de carga deben ejecutarse únicamente contra el Nginx local del proyecto. Durante la presentación no es necesario repetir el experimento de alta intensidad; se mostrarán los reportes y datasets ya guardados.

---

# 1. Resumen que debes explicar antes de usar la terminal

Puedes comenzar con esta explicación:

> “Contramuseo es el servicio web que estamos observando. Las peticiones entran por Nginx, que entrega los archivos estáticos o reenvía las rutas `/api/` a Flask. Nginx registra cada petición en JSONL. Locust genera tráfico controlado y el extractor convierte esos registros en ventanas numéricas de diez segundos. Actualmente el proyecto llega hasta los datasets procesados; todavía falta entrenar el modelo y construir el monitor en tiempo real.”

El flujo actual es:

```text
Navegador o Locust
        ↓
      Nginx
       ├── Contramuseo: HTML, CSS, JS, imágenes y audio
       ├── Flask API: /api/health y /api/status
       └── ia_access.jsonl
                 ↓
        feature_extractor.py
                 ↓
          datasets/processed/*.csv
```

El flujo pendiente es:

```text
CSV de entrenamiento → modelo de IA → monitor en tiempo real → alerta → mitigación
```

---

## 2.4 Validar la configuración de Docker Compose

```bash
docker compose config --quiet
```

### Qué hace

Lee `docker-compose.yml`, sustituye las variables necesarias y comprueba la sintaxis.

### Salida esperada

No debe mostrar nada y debe regresar al prompt.

### Qué significa

La configuración es válida. La ausencia de salida significa éxito.

### Errores comunes

- `SECRET_KEY` no definida: falta `.env`.
- Error de YAML: indentación incorrecta en `docker-compose.yml`.

---

## 2.5 Mostrar qué servicios y perfiles existen sin revelar secretos

```bash
docker compose config --services
docker compose config --profiles
```

### Salida esperada

Los servicios deben incluir:

```text
nginx
detector
locust
flask-api
```

El perfil debe incluir:

```text
testing
```

### Qué significa

- `nginx`: entrada, archivos estáticos, proxy y logs.
- `flask-api`: backend y SQLite.
- `detector`: herramientas Python para leer y transformar logs.
- `locust`: generador de tráfico; solo se activa con el perfil de pruebas o mediante `docker compose run`.

---

## 2.6 Construir Flask antes de la presentación

```bash
docker compose build flask-api
```

### Qué hace

1. Lee `backend/Dockerfile`.
2. Usa la imagen base de Python 3.11.
3. Instala `backend/requirements.txt`.
4. Copia el código del backend.
5. Genera la imagen `proyecto-terminal-flask-api`.

### Salida esperada

Debe terminar sin errores e indicar que la imagen fue construida.

### Qué significa

El backend puede reproducirse a partir de los archivos del proyecto.

---

## 2.7 Iniciar los servicios

```bash
docker compose up -d
docker compose ps --all
```

### Qué hace

- `up -d` inicia los servicios en segundo plano.
- `ps --all` muestra contenedores activos y terminados.

### Salida esperada

Nginx y Flask deben aparecer como `Up`:

```text
contramuseo-api      Up      0.0.0.0:5000->5000/tcp
contramuseo-nginx    Up      0.0.0.0:8080->80/tcp
```

El detector puede aparecer como `Exited (0)`.

### Qué significa

Que el detector termine con código `0` no representa un fallo. Su comando actual, `log_reader.py`, lee el archivo, muestra un resumen y termina; todavía no es un monitor permanente.

---

# 3. Demostración en vivo ante el asesor

## Paso 1 — Mostrar la arquitectura (minutos 0–2)

Si copiaste la documentación generada dentro del proyecto:

```bash
xdg-open documentacion_tecnica/index.html
```

Para mostrar el SVG original:

```bash
xdg-open arquitectura-detallada-proyecto-terminal.svg
```

### Qué debes explicar

> “Docker ejecuta y conecta las herramientas. Nginx es la única entrada pública principal. Contramuseo es una carpeta montada en Nginx, Flask resuelve las rutas dinámicas, SQLite persiste datos y el volumen `nginx-logs` permite que Python lea los eventos.”

### Si `xdg-open` no funciona

Abre manualmente el archivo con el navegador o utiliza:

```bash
google-chrome documentacion_tecnica/index.html
```

---

## Paso 2 — Mostrar los contenedores (minutos 2–3)

```bash
docker compose ps --all
```

### Qué debes señalar

- El puerto `8080` de la computadora llega al puerto `80` de Nginx.
- El puerto `5000` permite depurar Flask directamente.
- En uso normal, las peticiones deben pasar por `8080` para que Nginx las registre.

### Explicación breve

> “Un servicio de Compose describe cómo debe ejecutarse una responsabilidad. Un contenedor es la instancia que Docker creó a partir de esa descripción.”

---

## Paso 3 — Comprobar la comunicación interna (minuto 3)

```bash
docker compose exec nginx getent hosts flask-api
```

### Salida esperada

Debe aparecer una dirección de la red Docker asociada a `flask-api`, normalmente:

```text
172.20.0.3    flask-api
```

### Qué significa

Docker proporciona DNS interno. Nginx no necesita conocer la dirección física del backend: puede comunicarse usando el nombre del servicio `flask-api`.

---

## Paso 4 — Validar Nginx (minuto 3–4)

```bash
docker compose exec nginx nginx -t
```

### Salida esperada

```text
syntax is ok
test is successful
```

### Qué significa

La sintaxis de `nginx/nginx.conf` es válida y Nginx puede cargarla.

### Qué debes decir

> “Nginx realiza tres trabajos: entrega Contramuseo, reenvía `/api/` a Flask y registra cada petición en JSONL.”

---

## Paso 5 — Abrir Contramuseo (minutos 4–5)

```bash
xdg-open http://localhost:8080/
```

También puedes comprobarlo desde la terminal:

```bash
curl -I http://localhost:8080/
```

### Salida esperada

```text
HTTP/1.1 200 OK
Server: nginx/1.25.5
Content-Type: text/html
```

### Qué significa

- `200 OK`: el recurso fue encontrado.
- `Server: nginx`: la respuesta pasó por Nginx.
- `Content-Type: text/html`: se devolvió una página HTML.

### Qué debes explicar

> “Nginx busca el archivo solicitado dentro de `contramuseo/`. El navegador después solicita CSS, JavaScript, imágenes, sidebar y otros recursos; cada solicitud produce un registro independiente.”

---

## Paso 6 — Comprobar la API Flask por medio de Nginx (minutos 5–6)

```bash
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

### Salida esperada

Debe contener información semejante a:

```json
{
  "db": "SQLite conectada",
  "servicio": "contramuseo-api",
  "status": "ok",
  "version": "0.1.0-semana8"
}
```

### Qué significa

1. `curl` envió la petición a Nginx en el puerto 8080.
2. Nginx reconoció `/api/`.
3. Nginx la reenvió a `flask-api:5000`.
4. Flask comprobó SQLite.
5. La respuesta regresó a través de Nginx.

Ahora consulta el estado:

```bash
curl -s http://localhost:8080/api/status | python3 -m json.tool
```

### Qué debes explicar

`/api/status` cuenta los registros de las tablas `users`, `podcasts` e `investigaciones`. La respuesta también enumera endpoints futuros, pero esos endpoints todavía no están implementados.

> **Importante:** si pruebas `localhost:5000` directamente, Flask puede responder, pero esa petición no pasará por Nginx y no aparecerá en el access log utilizado para los datasets.

---

## Paso 7 — Demostrar que una petición produce un evento (minutos 6–7)

Primero genera una petición reconocible:

```bash
curl -s -o /dev/null http://localhost:8080/api/health
```

Después muestra el último evento:

```bash
docker compose exec nginx tail -n 1 /var/log/nginx/ia_access.jsonl \
  | python3 -m json.tool
```

### Salida esperada

```json
{
  "timestamp": "2026-...",
  "remote_addr": "172.20.0.1",
  "method": "GET",
  "uri": "/api/health",
  "protocol": "HTTP/1.1",
  "status": 200,
  "bytes_sent": 95,
  "request_length": 88,
  "request_time": 0.001,
  "user_agent": "curl/...",
  "connection": 7,
  "connection_requests": 1
}
```

Los números exactos pueden cambiar.

### Significado de los campos

| Campo                 | Significado                                         |
| --------------------- | --------------------------------------------------- |
| `timestamp`           | Momento de la petición con zona horaria             |
| `remote_addr`         | Dirección observada por Nginx                       |
| `method`              | Método HTTP, por ejemplo `GET`                      |
| `uri`                 | Recurso solicitado                                  |
| `status`              | Código de respuesta                                 |
| `bytes_sent`          | Bytes enviados en el cuerpo de la respuesta         |
| `request_length`      | Tamaño de línea, cabeceras y cuerpo de la solicitud |
| `request_time`        | Tiempo total atendido por Nginx, en segundos        |
| `user_agent`          | Cliente declarado, por ejemplo curl o navegador     |
| `connection`          | Identificador interno de conexión Nginx             |
| `connection_requests` | Peticiones atendidas en esa conexión                |

### Qué debes decir

> “JSONL contiene un objeto JSON independiente por línea. Esta es la evidencia original que después se transforma en características.”

---

## Paso 8 — Ejecutar `log_reader.py` (minuto 7–8)

```bash
docker compose run --rm detector
```

### Salida esperada

```text
Eventos leídos: ...

Métodos HTTP:
  GET: ...

Estados HTTP:
  200: ...

Tiempo promedio: ... segundos
```

### Qué hace

- Abre `/data/nginx/ia_access.jsonl` dentro del contenedor.
- Cuenta métodos HTTP.
- Cuenta códigos de estado.
- Calcula el tiempo promedio.
- Imprime el resumen y termina.

### Qué significa

Comprueba que Python puede leer el volumen compartido y que las líneas tienen JSON válido.

### Qué no hace

No crea ventanas, no genera CSV, no entrena IA, no predice ataques y no funciona continuamente.

---

## Paso 9 — Mostrar los datasets RAW (minuto 8–9)

```bash
find datasets/raw -maxdepth 1 -type f -name '*.jsonl' -printf '%f\n' | sort
```

### Salida esperada

Debe incluir:

```text
attack_smoke.jsonl
attack_train_01.jsonl
normal_smoke.jsonl
normal_test_01.jsonl
normal_train_01.jsonl
normal_train_02.jsonl
normal_train_03.jsonl
normal_validation_01.jsonl
```

### Qué significa

Cada archivo representa un experimento separado. `raw` conserva una petición por línea y funciona como evidencia primaria.

Muestra cuántas peticiones tiene un experimento:

```bash
wc -l datasets/raw/normal_train_01.jsonl
wc -l datasets/raw/attack_train_01.jsonl
```

### Salida esperada

```text
122 datasets/raw/normal_train_01.jsonl
22878 datasets/raw/attack_train_01.jsonl
```

### Qué significa

El experimento anómalo generó muchas más peticiones durante una duración comparable.

Muestra una petición original:

```bash
head -n 1 datasets/raw/normal_train_01.jsonl | python3 -m json.tool
```

---

## Paso 10 — Mostrar `feature_extractor.py` sin modificar datasets oficiales (minutos 9–10)

```bash
docker compose run --rm detector sh -c '
python feature_extractor.py \
  --input /datasets/raw/normal_train_01.jsonl \
  --output /tmp/demo_asesor.csv \
  --label normal \
  --window-seconds 10 \
  --drop-edge-windows && \
sed -n "1,6p" /tmp/demo_asesor.csv
'
```

### Por qué se utiliza `/tmp`

El CSV de demostración se crea dentro de un contenedor temporal. Cuando el contenedor termina, desaparece. Los datasets oficiales permanecen intactos.

### Salida esperada

Primero debe mostrar:

```text
Eventos válidos leídos: 122
Eventos incluidos: 111
Eventos descartados: 11
Ventanas detectadas: 13
Ventanas descartadas: 2
Ventanas generadas: 11
Dataset creado: /tmp/demo_asesor.csv
```

Después mostrará el encabezado y las primeras filas del CSV.

### Qué significa

1. El extractor leyó 122 eventos originales.
2. Agrupó los eventos por ventanas de 10 segundos.
3. Eliminó la primera y última ventana porque estaban incompletas.
4. Conservó 111 eventos distribuidos en 11 ventanas completas.
5. Cada ventana se convirtió en una fila numérica.

### Qué debes decir

> “`feature_extractor.py` todavía no es la IA. Es el componente que traduce eventos HTTP a variables numéricas que un modelo podrá utilizar.”

---

## Paso 11 — Mostrar los datasets PROCESSED (minutos 10–11)

```bash
find datasets/processed -maxdepth 1 -type f -name '*.csv' -printf '%f\n' | sort
```

Muestra un CSV en forma de tabla:

```bash
column -s, -t < datasets/processed/normal_train_01.csv
```

### Qué representa cada fila

Una fila representa una ventana completa de 10 segundos.

### Columnas principales

| Columna               | Significado                            |
| --------------------- | -------------------------------------- |
| `window_start`        | Inicio de la ventana                   |
| `window_end`          | Fin de la ventana                      |
| `request_count`       | Peticiones incluidas                   |
| `requests_per_second` | Peticiones divididas entre 10 segundos |
| `error_4xx_ratio`     | Proporción de errores del cliente      |
| `error_5xx_ratio`     | Proporción de errores del servidor     |
| `bytes_total`         | Bytes enviados durante la ventana      |
| `avg_request_length`  | Tamaño promedio de solicitud           |
| `avg_request_time`    | Tiempo promedio en segundos            |
| `max_request_time`    | Tiempo máximo en segundos              |
| `unique_uris`         | Cantidad de rutas diferentes           |
| `unique_connections`  | Cantidad de conexiones distintas       |
| `label`               | `normal`, `attack` o `unlabeled`       |

### Diferencia RAW/PROCESSED

> “RAW permite auditar cada petición. PROCESSED resume el comportamiento por periodos y es la entrada futura para el modelo. Si modificamos las características, podemos regenerar PROCESSED usando RAW sin repetir el experimento.”

---

## Paso 12 — Comparar tráfico normal y anómalo (minutos 11–12)

```bash
for experiment in normal_train_01 attack_train_01; do
  awk -F, -v name="$experiment" '
    NR > 1 {
      windows++
      requests += $3
      rps += $4
    }
    END {
      printf "%s: ventanas=%d, peticiones_incluidas=%d, promedio_RPS=%.2f\n", \
             name, windows, requests, rps / windows
    }
  ' "datasets/processed/${experiment}.csv"
done
```

### Salida esperada

```text
normal_train_01: ventanas=11, peticiones_incluidas=111, promedio_RPS=1.01
attack_train_01: ventanas=11, peticiones_incluidas=21106, promedio_RPS=191.87
```

### Qué significa

- El escenario normal produjo aproximadamente una petición por segundo.
- El escenario anómalo produjo aproximadamente 192 peticiones por segundo.
- La diferencia principal del experimento actual es la intensidad.
- Esto demuestra que los datos separan claramente esos dos escenarios, pero todavía no representa una predicción de IA.

---

## Paso 13 — Mostrar los resultados de Locust (minutos 12–13)

Compara los resultados agregados:

```bash
for experiment in normal_train_01 attack_train_01; do
  awk -F, -v name="$experiment" '
    $2 == "Aggregated" {
      printf "%s: requests=%s, failures=%s, avg=%.3f ms, p95=%s ms, RPS=%.2f\n", \
             name, $3, $4, $6, $17, $10
    }
  ' "reports/locust/${experiment}_stats.csv"
done
```

### Salida esperada

```text
normal_train_01: requests=122, failures=0, avg=3.146 ms, p95=8 ms, RPS=1.03
attack_train_01: requests=22763, failures=0, avg=3.421 ms, p95=7 ms, RPS=191.02
```

### Significado de las métricas

| Métrica    | Significado                                     |
| ---------- | ----------------------------------------------- |
| `requests` | Peticiones completadas según Locust             |
| `failures` | Peticiones que Locust consideró fallidas        |
| `avg`      | Tiempo promedio de respuesta en milisegundos    |
| `p95`      | 95 % de las respuestas tardó ese tiempo o menos |
| `RPS`      | Peticiones completadas por segundo              |

### Conclusión correcta

> “La prueba anómala aumentó mucho el throughput, pero el servidor local siguió respondiendo y no produjo fallos. La anomalía aparece en el comportamiento antes de provocar indisponibilidad.”

Comprueba el archivo de fallos:

```bash
cat reports/locust/attack_train_01_failures.csv
```

### Salida esperada

Solo debe aparecer el encabezado:

```text
Method,Name,Error,Occurrences,First Seen,Last Seen
```

Esto significa que Locust no registró fallos.

Abre el reporte visual:

```bash
xdg-open reports/locust/attack_train_01.html
```

---

## Paso 14 — Mostrar consumo de recursos (minuto 13)

```bash
tail -n 15 reports/locust/attack_train_01_resources.log
```

### Qué muestra

- Porcentaje de CPU.
- Memoria utilizada.
- Entrada y salida de red.
- Número de procesos.

### Resultado observado

Durante las muestras finales del experimento:

- Nginx utilizó alrededor de 5–6 % de CPU y aproximadamente 15 MiB.
- Flask utilizó aproximadamente 4–8 % de CPU y alrededor de 104 MiB.
- No se observaron reinicios.

### Precaución

`NET I/O` es acumulativo desde que inició el contenedor; no representa el tráfico exclusivo de esa muestra.

---

## Paso 15 — Mostrar el estado académico real (minutos 13–14)

### Experimentos disponibles

```bash
printf 'RAW:\n'
find datasets/raw -maxdepth 1 -type f -name '*.jsonl' -printf '  %f\n' | sort

printf '\nPROCESSED:\n'
find datasets/processed -maxdepth 1 -type f -name '*.csv' -printf '  %f\n' | sort

printf '\nSPLITS:\n'
find datasets/splits -maxdepth 1 -type f -printf '  %f\n' | sort
```

### Qué debes explicar

- Normal tiene tres ejecuciones de entrenamiento, una de validación y una de prueba.
- Attack tiene un smoke test y `attack_train_01`.
- Todavía faltan `attack_train_02`, `attack_train_03`, `attack_validation_01` y `attack_test_01`.
- `datasets/splits/` está vacío porque aún no se han combinado los experimentos.

### Comprobar que todavía no existe un modelo

```bash
find detector backend scripts -type f \
  \( -name '*.joblib' -o -name '*.pkl' -o -name '*.pickle' -o -name '*.onnx' \) \
  -print
```

### Salida esperada

No debe aparecer ningún archivo.

### Qué significa

No existe todavía un modelo serializado.

También puedes comprobar que no hay entrenamiento o predicción:

```bash
rg -n 'fit\(|predict\(|IsolationForest|RandomForest|sklearn|joblib' \
  detector backend scripts \
  || echo 'No se encontró entrenamiento ni predicción implementados.'
```

### Qué debes decir

> “El estado actual termina en datasets procesados. No voy a presentar el extractor como si fuera la IA. Los siguientes entregables son completar attack, construir los splits, entrenar, evaluar y después crear el monitor con alertas.”

---

## Paso 16 — Cierre de la presentación (minuto 14–15)

Puedes cerrar con este resumen:

> “Ya existe una arquitectura reproducible con Docker, un punto de entrada con Nginx, una API Flask conectada a SQLite, captura estructurada de tráfico, pruebas controladas con Locust, evidencia RAW, reportes de rendimiento y extracción de diez características por ventana. El dataset normal está completo y el dataset attack está iniciado. Lo siguiente en el trimestre es completar esa clase, construir los splits, entrenar y evaluar un modelo y generar alertas auditables. La mitigación automática se realizará después de medir falsos positivos y será temporal y reversible.”

Estado resumido:

```text
[✓] Contramuseo
[✓] Docker Compose
[✓] Nginx y proxy hacia Flask
[✓] SQLite
[✓] Logs JSONL
[✓] Locust
[✓] Extractor de características
[✓] Dataset normal
[~] Dataset attack
[ ] Splits combinados
[ ] Modelo de IA
[ ] Detección en tiempo real
[ ] Alertas
[ ] Bloqueo temporal
```

---

# 4. Prueba en vivo opcional y segura de Locust

No es necesaria si el tiempo es limitado. Este smoke test usa un usuario normal durante 10 segundos, no guarda un dataset oficial y no ejecuta carga anómala.

```bash
docker compose run --rm \
  -e TRAFFIC_PROFILE=normal \
  locust \
  -f /mnt/locust/locustfile.py \
  --headless \
  --host http://nginx \
  --users 1 \
  --spawn-rate 1 \
  --run-time 10s
```

### Qué hace

1. Crea un contenedor temporal de Locust.
2. Usa el perfil normal.
3. Simula un usuario.
4. Genera como máximo un usuario por segundo.
5. Ejecuta el escenario durante 10 segundos.
6. Envía peticiones solo a `http://nginx` dentro de la red Docker.

### Salida esperada

Locust mostrará una tabla con:

- Número de peticiones.
- Número de fallos.
- Tiempos de respuesta.
- Peticiones por segundo.

### Después de la prueba

```bash
docker compose exec nginx tail -n 5 /var/log/nginx/ia_access.jsonl
```

Esto demuestra que las solicitudes de Locust también fueron observadas por Nginx.

> Este smoke test agrega líneas al log activo. No modifica los archivos históricos de `datasets/raw/` ni `datasets/processed/`.

---

# 5. Comandos opcionales para preguntas técnicas

## Mostrar la configuración de Nginx

```bash
sed -n '1,220p' nginx/nginx.conf
```

Puntos que debes señalar:

- `log_format ia_json`: define los campos JSON.
- `access_log`: escribe el JSONL.
- `try_files`: busca archivos estáticos y usa `index.html` como fallback.
- `location /api/`: reenvía a Flask.
- `proxy_pass http://flask-api:5000`: usa el DNS interno de Docker.

---

## Mostrar los endpoints Flask

```bash
docker compose run --rm --no-deps flask-api flask --app app routes
```

### Salida esperada

Debe incluir:

```text
health   GET   /api/health
status   GET   /api/status
static   GET   /static/<path:filename>
```

### Qué significa

Solo `health` y `status` son endpoints propios implementados actualmente. La ruta `static` es registrada automáticamente por Flask.

---

## Mostrar las tablas definidas en Flask

```bash
rg -n '^class (User|Podcast|Investigacion)' backend/app.py
```

### Qué significa

`app.py` define tres modelos SQLAlchemy. `db.create_all()` crea sus tablas si no existen.

---

## Mostrar el escenario Locust

```bash
sed -n '1,220p' loadtest/locustfile.py
```

Puntos que debes señalar:

- Perfil normal: espera entre 1 y 3 segundos.
- Perfil anómalo: espera entre 0.05 y 0.15 segundos.
- Ambos perfiles usan las mismas tareas.
- Los pesos `5`, `4`, `2` y `1` controlan la frecuencia relativa.
- Locust no ejecuta JavaScript como un navegador; envía las rutas definidas explícitamente.

---

## Mostrar la automatización de experimentos

```bash
sed -n '1,280p' scripts/run_experiment.sh
```

Puntos que debes señalar:

1. Valida seis parámetros.
2. Evita sobrescribir evidencia.
3. Archiva el log activo.
4. Ejecuta Locust.
5. Copia el JSONL a `datasets/raw/`.
6. Ejecuta el extractor.
7. Genera el CSV y reportes.
8. Informa capturados, incluidos y descartados.

---

## Mostrar los logs de servicios

```bash
docker compose logs --tail=30 nginx flask-api
```

### Qué significa

Permite diagnosticar errores de arranque, configuración, rutas, base de datos y comunicación.

---

## Mostrar los montajes y rutas desde el contenedor detector

```bash
docker compose run --rm --entrypoint sh detector -c '
printf "Código del detector:\n"
ls -la /app
printf "\nLog compartido:\n"
ls -lh /data/nginx/ia_access.jsonl
printf "\nDatasets montados:\n"
ls -la /datasets
'
```

### Qué significa

- `/app` contiene el código del detector montado como solo lectura.
- `/data/nginx` contiene el volumen de logs montado como solo lectura.
- `/datasets` permite leer RAW y escribir PROCESSED.

---

# 6. Comandos de diagnóstico rápido

## Si Nginx o Flask no aparecen como `Up`

```bash
docker compose ps --all
docker compose logs --tail=50 nginx flask-api
```

## Si el puerto 8080 está ocupado

```bash
sudo ss -ltnp 'sport = :8080'
```

## Si Flask no puede abrir SQLite

```bash
docker compose run --rm --no-deps --entrypoint env flask-api \
  | grep '^DATABASE_URL='
```

La salida correcta es:

```text
DATABASE_URL=sqlite:////app/database/contramuseo.db
```

## Si Nginx no puede localizar Flask

```bash
docker compose exec nginx getent hosts flask-api
docker compose exec nginx wget -qO- http://flask-api:5000/api/health
```

## Si el log parece vacío

```bash
curl -s -o /dev/null http://localhost:8080/api/health
docker compose exec nginx wc -l /var/log/nginx/ia_access.jsonl
docker compose exec nginx tail -n 1 /var/log/nginx/ia_access.jsonl
```

## Si el extractor falla

```bash
docker compose run --rm detector \
  python feature_extractor.py --help
```

Comprueba también:

```bash
ls -lh datasets/raw/normal_train_01.jsonl
head -n 1 datasets/raw/normal_train_01.jsonl | python3 -m json.tool
```

---

# 7. Detener el proyecto correctamente

Al terminar la demostración:

```bash
docker compose down
```

### Qué hace

- Detiene y elimina los contenedores de Compose.
- Elimina la red creada para el proyecto.
- Conserva los volúmenes y archivos del proyecto.

### Qué no debes usar

```bash
docker compose down -v
```

La opción `-v` elimina los volúmenes, incluido el volumen de logs. No la utilices mientras necesites conservar evidencia.

---

# 8. Checklist antes de presentar

```text
[ ] Estoy en ~/Documentos/proyecto-terminal
[ ] .env existe y está ignorado por Git
[ ] docker compose config --quiet termina correctamente
[ ] Flask ya fue construido
[ ] Nginx y Flask aparecen Up
[ ] http://localhost:8080 abre Contramuseo
[ ] /api/health responde 200
[ ] Puedo mostrar una línea JSONL válida
[ ] Puedo ejecutar log_reader.py
[ ] Existen los RAW y PROCESSED oficiales
[ ] Abre attack_train_01.html
[ ] Sé explicar 1.01 RPS frente a 191.87 RPS
[ ] Digo claramente que el modelo y las alertas todavía faltan
[ ] No muestro .env ni ejecuto docker compose config sin --quiet
[ ] No ejecuto carga anómala durante la presentación
```

## Mensaje final recomendado

> “La aportación actual es una tubería reproducible de observabilidad y generación de datos: desde una petición real hasta una fila de características trazable. La siguiente fase convierte esa tubería en un detector: completaré la clase attack, construiré los splits, entrenaré y evaluaré el modelo y después implementaré alertas en tiempo real. El bloqueo automático quedará condicionado a la medición de falsos positivos.”
