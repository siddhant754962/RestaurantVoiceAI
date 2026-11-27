
from datetime import date, timedelta

from backend.database import SessionLocal
from backend.restaurant_models import (
    RestaurantSettings,
    RestaurantTable,
    RestaurantReservation,
    BookingEvent,
)
from backend.services.reservation_service import (
    initialize_restaurant,
    check_reservation_availability,
    create_reservation,
    cancel_reservation,
)


db = SessionLocal()
created_ids = []

try:
    print("\nTEST 1: Initialize restaurant")
    settings = initialize_restaurant(db)

    assert settings.restaurant_type == "multi"
    assert settings.default_reservation_duration == 90
    assert settings.total_tables == 10

    print("PASS: Multi-cuisine, 90 minutes, 10 tables")

    print("\nTEST 2: Verify table count")
    table_count = db.query(RestaurantTable).count()

    assert table_count == 10
    print(f"PASS: {table_count} tables created")

    print("\nTEST 3: Check future availability")
    booking_date = (date.today() + timedelta(days=3)).isoformat()
    booking_time = "19:00:00"

    availability = check_reservation_availability(
        db,
        booking_date,
        booking_time
    )

    assert availability["success"] is True
    assert availability["available"] is True
    assert availability["duration_minutes"] == 90

    print("PASS: Future reservation slot is available")

    print("\nTEST 4: Book all 10 tables at the same time")

    for number in range(10):
        result = create_reservation(
            db=db,
            customer_name=f"Test Customer {number + 1}",
            phone=f"90000000{number:02d}",
            reservation_date=booking_date,
            reservation_time=booking_time,
            guests=2,
            source="phase4_test",
        )

        assert result["success"] is True, result
        created_ids.append(result["booking_id"])

    print("PASS: All 10 tables allocated")

    print("\nTEST 5: Eleventh booking must be rejected")

    result = create_reservation(
        db=db,
        customer_name="Eleventh Customer",
        phone="9999999999",
        reservation_date=booking_date,
        reservation_time=booking_time,
        guests=2,
        source="phase4_test",
    )

    assert result["success"] is False
    print("PASS: No table available for the eleventh booking")

    print("\nTEST 6: Cancel one booking")

    cancellation = cancel_reservation(db, created_ids[0])

    assert cancellation["success"] is True
    print("PASS: Reservation cancelled")

    print("\nTEST 7: Cancelled table becomes available")

    result = create_reservation(
        db=db,
        customer_name="Replacement Customer",
        phone="9888888888",
        reservation_date=booking_date,
        reservation_time=booking_time,
        guests=2,
        source="phase4_test",
    )

    assert result["success"] is True
    created_ids.append(result["booking_id"])

    print("PASS: Cancelled table can be booked again")

    print("\nTEST 8: Booking history is retained")

    event_count = db.query(BookingEvent).filter(
        BookingEvent.reservation_id == created_ids[0]
    ).count()

    assert event_count >= 2
    print("PASS: Creation and cancellation events retained")

    print("\nALL PHASE 4.1 TESTS PASSED")

finally:
    # Cancel test reservations to leave the test slots free.
    for booking_id in created_ids:
        cancel_reservation(db, booking_id)

    db.close()
