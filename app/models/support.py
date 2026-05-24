from sqlalchemy import Column, Integer, String
from app.database.connection import Base

class SupportAccess(Base):
    __tablename__ = "support_access"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
