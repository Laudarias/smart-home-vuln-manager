from sqlalchemy import Column, Integer, String, Boolean
from app.models import Base


class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, index=True)
    hashed_password     = Column(String, nullable=False)
    is_default_password = Column(Boolean, default=True)