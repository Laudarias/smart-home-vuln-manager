"""
Conexión a la base de datos y configuración de SQLAlchemy.
Aquí se definen:
- la URL de la base de datos
- el motor de SQLAlchemy
- la sesión
- la clase base para los modelos
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

BASE_DIR = os.path.expanduser("~/proyecto/data")
os.makedirs(BASE_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{BASE_DIR}/app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()