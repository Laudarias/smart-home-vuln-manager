from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # necesario para SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Importar todos los modelos antes de crear las tablas."""
    from app.models.user import User           # noqa: F401
    from app.models.device import Device       # noqa: F401
    from app.models.scan import Scan           # noqa: F401
    from app.models.vulnerability import Vulnerability  # noqa: F401
    Base.metadata.create_all(bind=engine)