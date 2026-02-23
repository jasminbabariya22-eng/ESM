from sqlalchemy import Column, Integer, String, SmallInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "mst_users"
    __table_args__ = {"schema": "ers"}

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String, nullable=False)
    password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    contact_no = Column(String)
    country = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, nullable=False)

    dept_id = Column(Integer, ForeignKey("ers.mst_department.id"))
    role_id = Column(Integer, ForeignKey("ers.mst_user_role.id"))
    user_type_id = Column(Integer, ForeignKey("ers.mst_user_type.id"))

    is_deleted = Column(SmallInteger, default=0)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    department = relationship("Department", backref="users")
    role = relationship("UserRole", backref="users")
    user_type = relationship("UserType", backref="users")