from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, SmallInteger
from app.core.database import Base
from app.core.config import settings

class WorkflowVisibility(Base):
    """
    SQLAlchemy model representing dynamic visibility access to risks/workflows.
    """
    __tablename__ = "workflow_visibility"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    role_id = Column(Integer, nullable=True)
    user_type_id = Column(Integer, nullable=True)
    visibility = Column(SmallInteger, default=1, nullable=False) # 1 = visible, 0 = hidden
    time = Column(DateTime, default=datetime.utcnow, nullable=False)
