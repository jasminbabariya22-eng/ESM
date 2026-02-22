from sqlalchemy import Column, Integer, String, SmallInteger, TIMESTAMP
from sqlalchemy.orm import relationship
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
    dept_id = Column(Integer)
    role_id = Column(Integer)
    user_type_id = Column(Integer)
    is_deleted = Column(SmallInteger)
    created_on = Column(TIMESTAMP)