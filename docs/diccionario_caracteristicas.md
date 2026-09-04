# Diccionario de características del detector HTTP

## Propósito

Este documento describe las variables generadas a partir de los registros
HTTP de Nginx. Los eventos individuales se agrupan en ventanas temporales
configurables. Para los primeros experimentos se utilizarán ventanas de
10 segundos.

El mismo extractor deberá utilizarse para preparar el conjunto de
entrenamiento y para procesar tráfico nuevo durante la inferencia.

## Metadatos de la ventana

| Campo        | Tipo           | Descripción                                                  |
| ------------ | -------------- | ------------------------------------------------------------ |
| window_start | Fecha ISO 8601 | Inicio de la ventana en UTC                                  |
| window_end   | Fecha ISO 8601 | Final de la ventana en UTC                                   |
| label        | Categórica     | Etiqueta asignada al experimento: normal, attack o unlabeled |

Los metadatos identifican la ventana, pero `window_start` y `window_end`
no se utilizarán inicialmente como entradas del modelo.

## Características numéricas

| Característica      | Tipo    | Cálculo                                | Interpretación                      |
| ------------------- | ------- | -------------------------------------- | ----------------------------------- |
| request_count       | Entero  | Número de eventos en la ventana        | Cantidad total de peticiones        |
| requests_per_second | Decimal | request_count / duración de la ventana | Intensidad promedio del tráfico     |
| error_4xx_ratio     | Decimal | respuestas 4xx / request_count         | Proporción de errores del cliente   |
| error_5xx_ratio     | Decimal | respuestas 5xx / request_count         | Proporción de errores del servidor  |
| bytes_total         | Entero  | Suma de bytes_sent                     | Volumen total de respuesta          |
| avg_request_length  | Decimal | Promedio de request_length             | Tamaño promedio de las solicitudes  |
| avg_request_time    | Decimal | Promedio de request_time               | Duración promedio de las peticiones |
| max_request_time    | Decimal | Máximo request_time                    | Petición más lenta de la ventana    |
| unique_uris         | Entero  | Cantidad de valores uri distintos      | Diversidad de recursos solicitados  |
| unique_connections  | Entero  | Cantidad de conexiones distintas       | Conexiones observadas en la ventana |

## Origen de los datos

| Campo JSONL         | Variable de Nginx    |
| ------------------- | -------------------- |
| timestamp           | $time_iso8601        |
| remote_addr         | $remote_addr         |
| method              | $request_method      |
| uri                 | $uri                 |
| protocol            | $server_protocol     |
| status              | $status              |
| bytes_sent          | $body_bytes_sent     |
| request_length      | $request_length      |
| request_time        | $request_time        |
| user_agent          | $http_user_agent     |
| connection          | $connection          |
| connection_requests | $connection_requests |

## Etiquetas

### normal

Ventanas obtenidas durante experimentos de navegación legítima y carga
moderada dentro del laboratorio.

### attack

Ventanas obtenidas durante experimentos de carga HTTP anómala,
ejecutados únicamente contra infraestructura propia y autorizada.

### unlabeled

Ventanas cuyo origen experimental no ha sido verificado. No deben
utilizarse directamente para entrenar o evaluar el modelo.

## Limitaciones actuales

- Docker presenta actualmente `172.20.0.1` como dirección de origen.
- No se utilizará `remote_addr` como característica hasta conservar
  correctamente la IP original.
- `user_agent` puede ser falsificado y no se utilizará inicialmente.
- Las ventanas sin peticiones no aparecen en el dataset.
- Los logs HTTP no representan ataques que no alcanzan la capa HTTP.
- Un gran volumen de bytes puede corresponder a imágenes o audios legítimos.
- Los identificadores de conexión pueden reiniciarse cuando Nginx se reinicia.
