
from sqlalchemy import Column, Integer, String, Date, Time
from backend.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    reservation_date = Column(Date, nullable=False)
    reservation_time = Column(Time, nullable=False)
    guests = Column(Integer, nullable=False)
    status = Column(String(20), default="confirmed")
