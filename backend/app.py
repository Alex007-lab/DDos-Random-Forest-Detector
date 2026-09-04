"""
Contramuseo — Flask API
Semana 8: versión mínima con health check y estructura base.
Las rutas de autenticación y subida de podcasts se añaden en Semana 10.
"""

import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

# ─────────────────────────────────────────────────────────────────────────────
#  Inicialización de la app y extensiones
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# Configuración desde variables de entorno (definidas en docker-compose.yml)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///database/contramuseo.db'   # fallback para correr sin Docker
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # silencia una advertencia

db = SQLAlchemy(app)

# ─────────────────────────────────────────────────────────────────────────────
#  Modelos (tablas de la base de datos)
#  Semana 8: definimos la estructura; la llenamos en Semana 9-10.
# ─────────────────────────────────────────────────────────────────────────────

class User(db.Model):
    """Usuarios del sistema: administradores y creadores de contenido."""
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(20), default='creator')  # 'admin' | 'creator'
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relación: un usuario puede tener muchos podcasts
    podcasts   = db.relationship('Podcast', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Podcast(db.Model):
    """Podcasts subidos por los creadores de contenido."""
    __tablename__ = 'podcasts'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    audio_path  = db.Column(db.String(500), nullable=False)  # ruta al .mp3
    objeto_id   = db.Column(db.String(100))  # ej: 'pulque', 'xochipilli'
    author_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at  = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Podcast {self.title}>'


class Investigacion(db.Model):
    """Investigaciones (textos) subidas por los creadores."""
    __tablename__ = 'investigaciones'

    id         = db.Column(db.Integer, primary_key=True)
    titulo     = db.Column(db.String(200), nullable=False)
    contenido  = db.Column(db.Text)
    objeto_id  = db.Column(db.String(100))
    author_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# ─────────────────────────────────────────────────────────────────────────────
#  Crear tablas al arrancar (solo si no existen)
# ─────────────────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    print("[DB] Tablas verificadas / creadas correctamente.")

# ─────────────────────────────────────────────────────────────────────────────
#  Rutas — Semana 8: solo endpoints de verificación
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/health')
def health():
    """
    Endpoint de salud. Permite verificar que el contenedor está vivo.
    Llámalo con: curl http://localhost:5000/api/health
    Nginx lo llama en: http://localhost/api/health
    """
    return jsonify({
        'status': 'ok',
        'servicio': 'contramuseo-api',
        'version': '0.1.0-semana8',
        'db': 'SQLite conectada'
    }), 200


@app.route('/api/status')
def status():
    """
    Información del estado actual de la API y tablas de la BD.
    Útil para verificar que los modelos se crearon correctamente.
    """
    try:
        user_count    = User.query.count()
        podcast_count = Podcast.query.count()
        inv_count     = Investigacion.query.count()
        db_ok = True
    except Exception as e:
        user_count = podcast_count = inv_count = 0
        db_ok = False
        print(f"[ERROR] BD: {e}")

    return jsonify({
        'api': 'contramuseo-flask-api',
        'db_conectada': db_ok,
        'tablas': {
            'users':          user_count,
            'podcasts':       podcast_count,
            'investigaciones': inv_count
        },
        'proximos_endpoints': [
            'POST /api/auth/login       (Semana 10)',
            'POST /api/auth/logout      (Semana 10)',
            'GET  /api/podcasts         (Semana 10)',
            'POST /api/podcasts/upload  (Semana 10)',
            'GET  /api/admin/users      (Semana 10)',
        ]
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
#  Punto de entrada (solo cuando corres: python app.py)
#  Con Docker usamos: flask run (definido en el CMD del Dockerfile)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
