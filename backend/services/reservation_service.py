
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.restaurant_models import (
    RestaurantSettings,
    RestaurantTable,
    RestaurantReservation,
    BookingEvent,
)


def initialize_restaurant(db: Session):
    """Create default settings and ten tables if they don't exist."""

    settings = db.query(RestaurantSettings).filter(
        RestaurantSettings.id == 1
    ).first()

    if not settings:
        settings = RestaurantSettings(
            id=1,
            restaurant_type="multi",
            default_reservation_duration=90,
            total_tables=10,
            restaurant_name="RestaurantVoiceAI",
        )
        db.add(settings)

    existing_tables = db.query(RestaurantTable).count()

    if existing_tables < 10:
        existing_numbers = {
            row.table_number
            for row in db.query(RestaurantTable.table_number).all()
        }

        for number in range(1, 11):
            if number not in existing_numbers:
                db.add(
                    RestaurantTable(
                        table_number=number,
                        capacity=None,
                        is_active=True,
                    )
                )

    db.commit()
    return settings


def get_restaurant_settings(db: Session):
    settings = db.query(RestaurantSettings).filter(
        RestaurantSettings.id == 1
    ).first()

    if not settings:
        settings = initialize_restaurant(db)

    return settings


def find_available_table(
    db: Session,
    starts_at: datetime,
    duration_minutes: int,
):
    """Find a table without an overlapping active reservation."""

    ends_at = starts_at + timedelta(minutes=duration_minutes)

    tables = (
        db.query(RestaurantTable)
        .filter(RestaurantTable.is_active.is_(True))
        .order_by(RestaurantTable.table_number.asc())
        .all()
    )

    for table in tables:
        conflict = (
            db.query(RestaurantReservation)
            .filter(
                RestaurantReservation.table_id == table.id,
                RestaurantReservation.status == "confirmed",
                RestaurantReservation.starts_at < ends_at,
                RestaurantReservation.ends_at > starts_at,
            )
            .first()
        )

        if not conflict:
            return table

    return None


def check_reservation_availability(
    db: Session,
    reservation_date: str,
    reservation_time: str,
):
    try:
        starts_at = datetime.fromisoformat(
            f"{reservation_date}T{reservation_time}"
        )
    except ValueError:
        return {
            "success": False,
            "available": False,
            "message": "Invalid reservation date or time."
        }

    if starts_at <= datetime.now():
        return {
            "success": True,
            "available": False,
            "message": "Reservation must be in the future."
        }

    settings = get_restaurant_settings(db)
    duration = settings.default_reservation_duration

    table = find_available_table(db, starts_at, duration)

    if not table:
        return {
            "success": True,
            "available": False,
            "message": "No table is available for this time.",
            "duration_minutes": duration,
        }

    return {
        "success": True,
        "available": True,
        "table_number": table.table_number,
        "duration_minutes": duration,
        "starts_at": starts_at.isoformat(),
        "ends_at": (
            starts_at + timedelta(minutes=duration)
        ).isoformat(),
    }


def create_reservation(
    db: Session,
    customer_name: str,
    phone: str,
    reservation_date: str,
    reservation_time: str,
    guests: int,
    source: str = "vapi",
    special_requests: str = None,
):
    if guests < 1:
        return {
            "success": False,
            "message": "Guest count must be at least one."
        }

    try:
        starts_at = datetime.fromisoformat(
            f"{reservation_date}T{reservation_time}"
        )
    except ValueError:
        return {
            "success": False,
            "message": "Invalid reservation date or time."
        }

    if starts_at <= datetime.now():
        return {
            "success": False,
            "message": "Reservation must be in the future."
        }

    settings = get_restaurant_settings(db)
    duration = settings.default_reservation_duration

    try:
        # Begin a transaction before checking and inserting.
        table = find_available_table(db, starts_at, duration)

        if not table:
            return {
                "success": False,
                "message": "No table is available for this time."
            }

        ends_at = starts_at + timedelta(minutes=duration)

        reservation = RestaurantReservation(
            customer_name=customer_name.strip(),
            phone=phone.strip(),
            guests=guests,
            starts_at=starts_at,
            ends_at=ends_at,
            duration_minutes=duration,
            table_id=table.id,
            status="confirmed",
            source=source,
            special_requests=special_requests,
        )

        db.add(reservation)
        db.flush()

        db.add(
            BookingEvent(
                reservation_id=reservation.id,
                event_type="created",
                description="Reservation created successfully.",
            )
        )

        db.commit()
        db.refresh(reservation)

        return {
            "success": True,
            "booking_id": reservation.id,
            "customer_name": reservation.customer_name,
            "phone": reservation.phone,
            "reservation_date": reservation.starts_at.date().isoformat(),
            "reservation_time": reservation.starts_at.time().isoformat(),
            "duration_minutes": reservation.duration_minutes,
            "guests": reservation.guests,
            "table_number": table.table_number,
            "status": reservation.status,
        }

    except IntegrityError:
        db.rollback()
        return {
            "success": False,
            "message": "Reservation conflict. Please check availability again."
        }

    except Exception:
        db.rollback()
        raise


def cancel_reservation(db: Session, booking_id: int):
    reservation = db.query(RestaurantReservation).filter(
        RestaurantReservation.id == booking_id
    ).first()

    if not reservation:
        return {
            "success": False,
            "message": "Booking not found."
        }

    if reservation.status == "cancelled":
        return {
            "success": False,
            "message": "Booking is already cancelled."
        }

    reservation.status = "cancelled"

    db.add(
        BookingEvent(
            reservation_id=reservation.id,
            event_type="cancelled",
            description="Reservation cancelled.",
        )
    )

    db.commit()

    return {
        "success": True,
        "booking_id": reservation.id,
        "status": "cancelled",
        "message": "Reservation cancelled successfully."
    }
