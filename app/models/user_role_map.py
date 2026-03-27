from sqlalchemy import Column, Integer
from app.core.database import Base
from app.core.config import settings


class UserRoleMap(Base):
    __tablename__ = "user_role_map"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    map_id = Column(Integer, primary_key=True, index=True)

    role_id = Column(Integer, nullable=False)
    menu_id = Column(Integer, nullable=False)
