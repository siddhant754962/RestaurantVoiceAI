
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class RestaurantSettings(Base):
    __tablename__ = "restaurant_settings"

    id = Column(Integer, primary_key=True, default=1)
    restaurant_type = Column(String(50), nullable=False, default="multi")
    default_reservation_duration = Column(
        Integer, nullable=False, default=90
    )
    total_tables = Column(Integer, nullable=False, default=10)
    restaurant_name = Column(
        String(150), nullable=False, default="RestaurantVoiceAI"
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(Integer, unique=True, nullable=False)
    capacity = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    reservations = relationship(
        "RestaurantReservation",
        back_populates="restaurant_table"
    )


class RestaurantReservation(Base):
    __tablename__ = "restaurant_reservations"

    id = Column(Integer, primary_key=True, index=True)

    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)

    guests = Column(Integer, nullable=False)

    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)

    duration_minutes = Column(Integer, nullable=False, default=90)

    table_id = Column(
        Integer,
        ForeignKey("restaurant_tables.id"),
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False,
        default="confirmed"
    )

    source = Column(String(30), nullable=False, default="vapi")

    special_requests = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    restaurant_table = relationship(
        "RestaurantTable",
        back_populates="reservations"
    )

    events = relationship(
        "BookingEvent",
        back_populates="reservation",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("guests >= 1", name="valid_guest_count"),
        CheckConstraint(
            "duration_minutes > 0",
            name="valid_reservation_duration"
        ),
        CheckConstraint(
            "status IN ('confirmed', 'cancelled', 'completed')",
            name="valid_reservation_status"
        ),
        Index(
            "idx_reservation_time_status",
            "starts_at",
            "ends_at",
            "status"
        ),
    )


class BookingEvent(Base):
    __tablename__ = "booking_events"

    id = Column(Integer, primary_key=True, index=True)

    reservation_id = Column(
        Integer,
        ForeignKey("restaurant_reservations.id"),
        nullable=False
    )

    event_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    reservation = relationship(
        "RestaurantReservation",
        back_populates="events"
    )
