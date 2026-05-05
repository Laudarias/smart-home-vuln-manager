import os
import secrets
from pathlib import Path

# Directorio de datos (base de datos, clave secreta, resultados de escaneo)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Clave secreta para firmar tokens JWT
_SECRET_KEY_FILE = DATA_DIR / ".secret_key"

def _get_or_create_secret_key() -> str:
    if _SECRET_KEY_FILE.exists():
        return _SECRET_KEY_FILE.read_text().strip()
    key = secrets.token_hex(32)
    _SECRET_KEY_FILE.write_text(key)
    _SECRET_KEY_FILE.chmod(0o600)   # sólo el propietario puede leer
    return key

SECRET_KEY: str = _get_or_create_secret_key()

# JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 días; el usuario no tiene que iniciar sesión tan seguido

# Base de datos
DATABASE_URL = f"sqlite:///{DATA_DIR}/app.db"

# Escaneo continuo (minutos entre escaneos automáticos; 0 = desactivado)
SCAN_INTERVAL_MINUTES: int = int(os.environ.get("SCAN_INTERVAL_MINUTES", "60"))

# Directorio temporal para resultados de escaneo
SCAN_TMP_DIR = DATA_DIR / "scan_tmp"
SCAN_TMP_DIR.mkdir(exist_ok=True)