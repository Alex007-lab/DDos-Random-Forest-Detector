# Protocolo de generación del dataset HTTP

## 1. Objetivo

Generar de forma controlada y reproducible tráfico HTTP normal y tráfico
de carga anómala contra Contramuseo.

Los registros producidos por Nginx se convertirán en ventanas numéricas
mediante el mismo extractor que posteriormente utilizará el monitor.

## 2. Alcance y autorización

Todas las pruebas se realizarán exclusivamente contra:

http://localhost:8080

La infraestructura pertenece al alumno y se ejecuta localmente mediante
Docker Compose.

No se ejecutarán pruebas contra sitios públicos, servicios de terceros
o direcciones sin autorización.

Los escenarios etiquetados como `attack` representan carga HTTP anómala
compatible con un ataque de laboratorio. No representan un DDoS
distribuido real, porque las peticiones provienen de una sola máquina.

## 3. Arquitectura utilizada

Cliente de carga
↓
localhost:8080
↓
Nginx
↓
Contramuseo o Flask
↓
ia_access.jsonl
↓
feature_extractor.py
↓
CSV con ventanas de 10 segundos

## 4. Fuente de datos

Los eventos se obtienen del archivo:

/var/log/nginx/ia_access.jsonl

Nginx guarda un objeto JSON por petición.

El detector accede al mismo archivo mediante el volumen Docker
`nginx-logs`, montado como solo lectura.

## 5. Herramienta de generación de tráfico

Se utilizará Locust como herramienta de pruebas de carga HTTP.

Locust permitirá controlar:

- Número de usuarios concurrentes.
- Velocidad de creación de usuarios.
- Duración del experimento.
- Tiempo de espera entre peticiones.
- Distribución de rutas solicitadas.

La versión utilizada se registrará junto con las evidencias.

## 6. Rutas de prueba

Los escenarios normales y anómalos utilizarán las mismas rutas para
evitar que el modelo aprenda únicamente que una ruta específica
representa un ataque.

Rutas iniciales:

- /
- /content/pulque.html
- /content/xochipilli.html
- /content/barbie.html
- /css/estilos.css
- /js/main.js
- /api/health
- /api/status

Los archivos MP3 no se incluirán en las pruebas de carga anómala para
evitar un consumo excesivo de almacenamiento, red y memoria.

## 7. Ventanas

Los registros se agruparán inicialmente en ventanas de 10 segundos.

Cada ventana generará una fila del dataset.

El tamaño será configurable mediante:

--window-seconds

Esto permitirá comparar posteriormente ventanas de 1, 5 o 10 segundos
sin implementar otro extractor.

## 8. Escenarios normales

El tráfico normal representará navegación moderada con pausas entre
peticiones.

| Experimento          | Usuarios |     Duración | Uso           |
| -------------------- | -------: | -----------: | ------------- |
| normal_train_01      |        2 | 120 segundos | Entrenamiento |
| normal_train_02      |        4 | 120 segundos | Entrenamiento |
| normal_train_03      |        6 | 120 segundos | Entrenamiento |
| normal_validation_01 |        5 | 120 segundos | Validación    |
| normal_test_01       |        7 | 120 segundos | Prueba final  |

Los usuarios tendrán pausas aleatorias para aproximarse al
comportamiento humano.

## 9. Escenarios de carga anómala

La carga anómala utilizará más usuarios y pausas muy pequeñas, pero
mantendrá las mismas rutas.

| Experimento          | Usuarios máximos iniciales |     Duración | Uso           |
| -------------------- | -------------------------: | -----------: | ------------- |
| attack_train_01      |                         20 | 120 segundos | Entrenamiento |
| attack_train_02      |                         30 | 120 segundos | Entrenamiento |
| attack_train_03      |                         40 | 120 segundos | Entrenamiento |
| attack_validation_01 |                         25 | 120 segundos | Validación    |
| attack_test_01       |                         35 | 120 segundos | Prueba final  |

Las cantidades podrán reducirse si el equipo muestra inestabilidad.
Cualquier cambio deberá registrarse en la bitácora.

Comandos reproducibles acordados:

```bash
./scripts/run_experiment.sh attack train 01 20 10 120s
./scripts/run_experiment.sh attack train 02 30 10 120s
./scripts/run_experiment.sh attack train 03 40 10 120s
./scripts/run_experiment.sh attack validation 01 25 10 120s
./scripts/run_experiment.sh attack test 01 35 10 120s
```

Se ejecutará un comando a la vez y se validará su evidencia antes de avanzar.

## 10. Medidas de seguridad

La carga aumentará progresivamente.

Una prueba se detendrá si ocurre alguna de estas condiciones:

- CPU cercana al 90 % de forma sostenida.
- Memoria superior al 85 %.
- Reinicio inesperado de un contenedor.
- Pérdida prolongada de respuesta.
- Temperatura anormal del equipo.
- Ejecución accidental contra una dirección distinta de localhost.

No se implementará bloqueo automático durante el segundo trimestre.

## 11. Aislamiento de experimentos

Cada ejecución tendrá su propio archivo JSONL.

Antes de limpiar el log activo, se copiará cualquier información
anterior que deba conservarse.

Los nombres seguirán este formato:

datasets/raw/normal_train_01.jsonl
datasets/raw/attack_train_01.jsonl
datasets/raw/normal_test_01.jsonl
datasets/raw/attack_test_01.jsonl

Los CSV procesados conservarán el mismo identificador:

datasets/processed/normal_train_01.csv
datasets/processed/attack_train_01.csv

No se etiquetará como normal o ataque un archivo que contenga
experimentos mezclados.

## 12. Etiquetado

La etiqueta se asignará por experimento:

- `normal`: experimento de navegación moderada.
- `attack`: experimento de carga anómala controlada.
- `unlabeled`: tráfico sin un origen experimental confirmado.

La etiqueta no será calculada a partir del código HTTP, tiempo de
respuesta o número de solicitudes.

## 13. Separación de datos

La separación se realizará por ejecuciones completas:

- Experimentos `train`: entrenamiento.
- Experimentos `validation`: ajuste de modelo y umbral.
- Experimentos `test`: evaluación final.

No se dividirán aleatoriamente ventanas de una misma ejecución entre
entrenamiento y prueba.

Esto evita que tráfico casi idéntico de una ejecución aparezca en ambos
conjuntos.

## 14. Evidencias conservadas

Por cada experimento se almacenará:

- Archivo JSONL original.
- CSV de características.
- Parámetros utilizados.
- Fecha y duración.
- Etiqueta.
- Reporte de Locust.
- Errores observados.
- Estado de los contenedores.
- Observación de CPU y memoria.

La auditoría se ejecutará con:

```bash
python3 scripts/validate_datasets.py \
  --json-output reports/data_validation.json
```

Nginx es la fuente de verdad del tráfico que alcanzó la aplicación. Los conteos
de Locust se conservan como evidencia complementaria y cualquier diferencia se
reporta sin modificar manualmente el RAW.

## 15. Limitaciones

- Las solicitudes se originan desde una sola computadora.
- Docker no conserva todavía la IP individual de clientes simulados.
- Los logs muestran únicamente tráfico que alcanza Nginx.
- No se observan directamente paquetes SYN, UDP o ICMP.
- El volumen de bytes depende de los recursos solicitados.
- Los resultados representan un entorno de laboratorio.
