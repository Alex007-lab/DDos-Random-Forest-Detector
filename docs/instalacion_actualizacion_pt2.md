# Instalación de la actualización PT2

El ZIP contiene rutas relativas a la raíz de `proyecto-terminal`. No incluye ni
elimina audios, imágenes, la base de datos, `.env` o datasets existentes.

## 1. Respaldar el estado actual

Si el proyecto ya está en Git, crea un commit antes de aplicar la actualización:

```bash
cd ~/Documentos/proyecto-terminal
git status --short
git add .
git commit -m "Respaldo antes del cierre de PT2"
```

Si todavía no deseas crear el commit, conserva al menos la salida de
`git status --short` y no descartes cambios propios.

## 2. Extraer el paquete

Suponiendo que el ZIP está en Descargas:

```bash
cd ~/Documentos/proyecto-terminal
unzip -o ~/Descargas/pt2_codigo_actualizado.zip -d .
chmod +x scripts/*.sh scripts/*.py detector/*.py
```

La extracción reemplaza únicamente los archivos técnicos incluidos en el ZIP.
El `.env` privado no está incluido; solo se actualiza `.env.example` con un
placeholder seguro.

## 3. Verificar la actualización

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/run_experiment.sh \
  scripts/run_pt2_pipeline.sh \
  scripts/run_realtime_demo.sh
docker compose config --services
python3 scripts/validate_datasets.py --allow-incomplete
```

Antes de generar experimentos, revisa `docs/guia_cierre_pt2.md`.
