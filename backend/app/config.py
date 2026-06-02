import os
import secrets

# Directorio de datos (base de datos, clave secreta, resultados de escaneo)
BASE_DIR = os.path.expanduser("~/smart-home-vuln-manager/data")
os.makedirs(BASE_DIR, exist_ok=True)

# Clave secreta para firmar tokens JWT
SECRET_KEY_FILE = os.path.join(BASE_DIR, ".secret_key")

def _load_or_create_secret() -> str:
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "w") as f:
        f.write(key)
    os.chmod(SECRET_KEY_FILE, 0o600)
    return key

SECRET_KEY = _load_or_create_secret()

# JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Base de datos
DATABASE_URL = f"sqlite:///{BASE_DIR}/app.db"

# Escaneo continuo (minutos entre escaneos automáticos; 0 = desactivado)
DEFAULT_SCAN_INTERVAL_MINUTES = 60