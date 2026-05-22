from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_default_password = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())