# ── Etapa base ──────────────────────────────────────────────────────────────
# python:3.11-slim es ~150 MB vs ~900 MB de la imagen completa.
# "slim" tiene lo mínimo para correr Python; sin compiladores ni docs.
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# ── Dependencias del sistema (mínimas) ───────────────────────────────────────
# Necesitamos gcc solo para compilar algunas dependencias de Python.
# Lo instalamos, compilamos, y lo eliminamos en el mismo RUN para no
# engordar la imagen final.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencias Python ───────────────────────────────────────────────────────
# Copiamos requirements.txt ANTES que el código.
# Docker cachea esta capa: si el código cambia pero requirements.txt no,
# no reinstala los paquetes → builds mucho más rápidos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Código de la aplicación ────────────────────────────────────────────────
COPY . .

# ── Crear carpeta de base de datos si no existe ───────────────────────────
RUN mkdir -p /app/database

# ── Puerto que expone el contenedor ───────────────────────────────────────
EXPOSE 5000

# ── Comando de arranque ────────────────────────────────────────────────────
# En desarrollo usamos flask run con --reload para recarga automática.
# En producción (T3) cambiaremos a: gunicorn -w 4 -b 0.0.0.0:5000 app:app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]
