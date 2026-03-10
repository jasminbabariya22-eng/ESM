from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class RiskActionFollowup(Base):

    __tablename__ = "risk_action_followup"
    __table_args__ = {"schema": "ers"}

    followup_id = Column(Integer, primary_key=True, index=True)

    reference_id = Column(Integer, nullable=False)

    module_name = Column(String(50))

    remark = Column(String(500), nullable=False)

    progress = Column(Integer)

    status = Column(Integer)

    next_followup_date = Column(DateTime)

    created_on = Column(DateTime, server_default=func.now())

    created_by = Column(Integer, nullable=False, default=1)