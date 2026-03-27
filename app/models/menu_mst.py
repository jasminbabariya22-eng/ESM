from sqlalchemy import Column, Integer, String, SmallInteger
from app.core.database import Base
from app.core.config import settings


class Menu(Base):
    __tablename__ = "menu_mst"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    menu_id = Column(Integer, primary_key=True, index=True)
    
    menu_name = Column(String(200), nullable=False)
    is_deleted = Column(SmallInteger, default=0)