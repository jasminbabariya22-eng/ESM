from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base

class UserType(Base):
    __tablename__ = "mst_user_type"
    __table_args__ = {"schema": "ers"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(100))
    created_by = Column(Integer, default=1)
    created_on = Column(DateTime)
    modified_by = Column(Integer)
    modified_on = Column(DateTime)
    is_deleted = Column(Integer)