from sqlalchemy import Column, Integer, String, Float, SmallInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

from app.models.mst_status import Status


class RiskRegister(Base):
    __tablename__ = "risk_register"
    __table_args__ = {"schema": "ers"}

    risk_register_id = Column(Integer, primary_key=True)

    risk_id = Column(String(10), nullable=False)
    risk_name = Column(String(50), nullable=False)

    dept_id = Column(Integer, ForeignKey("ers.mst_department.id"), nullable=False)
    risk_owner_id = Column(Integer, ForeignKey("ers.mst_users.id"), nullable=False)

    financial_year = Column(String(10))
    risk_status = Column(Integer, ForeignKey("ers.mst_status.id"))
    risk_progress = Column(Float)

    risk_function_head_approval_status = Column(Integer, ForeignKey("ers.mst_status.id"))
    risk_function_head_approval_remark = Column(String(500))
    risk_function_head_approval_on = Column(DateTime)
    risk_function_head_approval_by = Column(Integer)

    risk_head_approval_status = Column(Integer, ForeignKey("ers.mst_status.id"))
    risk_head_approved_on = Column(DateTime)
    risk_head_approval_remark = Column(String(500))
    risk_head_approval_by = Column(Integer)

    created_by = Column(Integer, nullable=False, default=1)
    created_on = Column(DateTime)
    modified_by = Column(Integer)
    modified_on = Column(DateTime)

    is_active = Column(SmallInteger, default=0)
    is_deleted = Column(SmallInteger, default=0)

    # Relationships
    department = relationship("Department", backref="risks")
    risk_owner = relationship("User", foreign_keys=[risk_owner_id])
    status = relationship(
        "Status",
        foreign_keys=[risk_status]
    )
    
    function_head_status = relationship(
        "Status",
        foreign_keys=[risk_function_head_approval_status]
    )

    risk_head_status = relationship(
        "Status",
        foreign_keys=[risk_head_approval_status]
    )