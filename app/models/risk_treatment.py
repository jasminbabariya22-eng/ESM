from sqlalchemy import Column, Integer, String, Float, SmallInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.mst_status import Status
from app.models.user import User


class RiskTreatment(Base):
    __tablename__ = "risk_treatment"
    __table_args__ = {"schema": "ers"}

    risk_treatment_id = Column(Integer, primary_key=True, index=True)

    risk_description_id = Column(
        Integer,
        ForeignKey("ers.risk_description.risk_description_id"),
        nullable=False
    )

    risk_register_id = Column(
        Integer,
        ForeignKey("ers.risk_register.risk_register_id")
    )

    risk_id = Column(String(10))

    action_plan = Column(String(200), nullable=False)
    action_owner_id = Column(
        Integer,
        ForeignKey("ers.mst_users.id"),
        nullable=False
    )

    target_date = Column(DateTime)
    progress = Column(Float)
    action_status_id = Column(Integer, ForeignKey("ers.mst_status.id"))

    next_followup_date = Column(DateTime)

    created_on = Column(DateTime)
    created_by = Column(Integer, nullable=False)

    modified_on = Column(DateTime)
    modified_by = Column(Integer)

    is_deleted = Column(SmallInteger, default=0)

    # Relationships
    risk_description = relationship("RiskDescription", back_populates="treatments")
    risk_register = relationship("RiskRegister")


    # Action Owner
    action_owner = relationship(
        User,
        foreign_keys=[action_owner_id]
    )

    # Action Status
    action_status = relationship(
        Status,
        foreign_keys=[action_status_id]
    )


    @property
    def action_owner_name(self):
        return self.action_owner.user_name if self.action_owner else None


    @property
    def action_status_name(self):
        return self.action_status.status_name if self.action_status else None