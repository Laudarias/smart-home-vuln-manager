from app.database import Base, engine
from app.models.user import User
from app.models.device import Device
from app.models.scan import Scan
from app.models.vulnerability import Vulnerability

def create_tables():
    Base.metadata.create_all(bind=engine)