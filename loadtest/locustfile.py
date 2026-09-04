import os
import random

from locust import HttpUser, between, task


# Permite elegir el tipo de tráfico desde Docker.
TRAFFIC_PROFILE = os.getenv("TRAFFIC_PROFILE", "normal").strip().lower()

PROFILES = {
    # Visitante normal: espera entre 1 y 3 segundos.
    "normal": (1.0, 3.0),

    # Tráfico anómalo de laboratorio: espera muy poco.
    "anomalous": (0.05, 0.15),
}

if TRAFFIC_PROFILE not in PROFILES:
    raise ValueError(
        "TRAFFIC_PROFILE debe ser 'normal' o 'anomalous'"
    )

WAIT_MIN, WAIT_MAX = PROFILES[TRAFFIC_PROFILE]


EXHIBIT_PAGES = [
    "/content/barbie.html",
    "/content/cabina_telefonica.html",
    "/content/codice_nunaha.html",
    "/content/cuauhtemoc.html",
    "/content/teporingo.html",
    "/content/xochipilli.html",
]

STATIC_RESOURCES = [
    "/sidebar.html",
    "/css/estilos.css",
    "/js/main.js",
    "/js/mosaic.js",
]

API_ENDPOINTS = [
    "/api/health",
    "/api/status",
]


class ContramuseoUser(HttpUser):
    """
    Representa a un visitante virtual de Contramuseo.
    """

    wait_time = between(WAIT_MIN, WAIT_MAX)

    @task(5)
    def visit_home(self):
        self.client.get("/", name="/")

    @task(4)
    def visit_exhibit(self):
        path = random.choice(EXHIBIT_PAGES)
        self.client.get(path, name="/content/[exhibit]")

    @task(2)
    def request_static_resource(self):
        path = random.choice(STATIC_RESOURCES)
        self.client.get(path, name="/static/[resource]")

    @task(1)
    def request_api(self):
        path = random.choice(API_ENDPOINTS)
        self.client.get(path, name="/api/[endpoint]")