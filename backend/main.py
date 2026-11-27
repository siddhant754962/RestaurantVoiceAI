
import json
from datetime import date, time
from typing import Any

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import (
    Base,
    engine,
    get_db,
    SessionLocal,
)

from backend.models import Booking
from backend.schemas import BookingCreate, BookingResponse
from backend import models, restaurant_models

from backend.services.reservation_service import (
    initialize_restaurant,
    check_reservation_availability,
    create_reservation,
    cancel_reservation,
)
from backend.admin_security import verify_admin

# ---------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    initialize_restaurant(db)


# ---------------------------------------
# FASTAPI APP
# ---------------------------------------

app = FastAPI(
    title="RestaurantVoiceAI API",
    description="Restaurant reservation and voice agent backend",
    version="2.0.0"
)


# ---------------------------------------
# RESTAURANT CONFIGURATION
# ---------------------------------------

MENU = [
    {"name": "Paneer Butter Masala", "price": 220},
    {"name": "Veg Biryani", "price": 180},
    {"name": "Dal Makhani", "price": 190},
    {"name": "Butter Naan", "price": 40},
    {"name": "Masala Dosa", "price": 120},
    {"name": "Cold Coffee", "price": 90}
]

MAX_TABLES = 10


# ---------------------------------------
# BASIC ROUTES
# ---------------------------------------

@app.get("/")
def home():
    return {
        "message": "RestaurantVoiceAI backend is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/menu")
def get_menu():
    return {"menu": MENU}


# ---------------------------------------
# LEGACY BOOKING AVAILABILITY
# Existing REST endpoints are preserved.
# Vapi uses the new reservation service.
# ---------------------------------------

def check_availability(
    db: Session,
    reservation_date: date,
    reservation_time: time
):
    booked = db.query(func.count(Booking.id)).filter(
        Booking.reservation_date == reservation_date,
        Booking.reservation_time == reservation_time,
        Booking.status == "confirmed"
    ).scalar()

    available = MAX_TABLES - booked

    return {
        "available": available > 0,
        "available_tables": available,
        "date": str(reservation_date),
        "time": str(reservation_time)
    }


@app.get("/availability")
def availability(
    reservation_date: date,
    reservation_time: time,
    db: Session = Depends(get_db)
):
    return check_availability(
        db,
        reservation_date,
        reservation_time
    )


# ---------------------------------------
# LEGACY REST BOOKING ENDPOINTS
# Preserved for backward compatibility.
# ---------------------------------------

@app.post("/bookings", response_model=BookingResponse)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db)
):
    if booking.reservation_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Reservation date cannot be in the past"
        )

    availability_result = check_availability(
        db,
        booking.reservation_date,
        booking.reservation_time
    )

    if not availability_result["available"]:
        raise HTTPException(
            status_code=409,
            detail="No tables available at this time"
        )

    new_booking = Booking(**booking.model_dump())

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking


@app.get("/bookings")
def list_bookings(db: Session = Depends(get_db)):
    bookings = db.query(Booking).order_by(
        Booking.id.desc()
    ).all()

    return {
        "bookings": [
            BookingResponse.model_validate(b).model_dump(mode="json")
            for b in bookings
        ]
    }


@app.delete("/bookings/{booking_id}")
def cancel_legacy_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    booking.status = "cancelled"
    db.commit()

    return {
        "success": True,
        "message": f"Booking {booking_id} cancelled"
    }




@app.get("/admin/reservations")
def admin_list_reservations(
    db: Session = Depends(get_db),
    admin: dict = Depends(verify_admin),
):
    reservations = (
        db.query(restaurant_models.RestaurantReservation)
        .order_by(restaurant_models.RestaurantReservation.id.desc())
        .all()
    )

    return {
        "total": len(reservations),
        "reservations": [
            {
                "booking_id": r.id,
                "customer_name": r.customer_name,
                "phone": r.phone,
                "reservation_date": r.starts_at.date().isoformat(),
                "reservation_time": r.starts_at.time().isoformat(),
                "guests": r.guests,
                "table_number": r.restaurant_table.table_number,
                "duration_minutes": r.duration_minutes,
                "status": r.status,
                "source": r.source,
                "special_requests": r.special_requests,
            }
            for r in reservations
        ],
    }


@app.delete("/admin/reservations/{booking_id}")
def admin_cancel_reservation(
    booking_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(verify_admin),
):
    result = cancel_reservation(db=db, booking_id=booking_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if result.get("message") == "Booking not found."
            else 400,
            detail=result.get("message"),
        )

    return result

# ---------------------------------------
# VAPI FUNCTION TOOL EXECUTION
# Connected to NEW reservation service.
# ---------------------------------------

def execute_tool(
    name: str,
    args: dict,
    db: Session
) -> Any:

    if name == "get_menu":
        return {
            "success": True,
            "menu": MENU
        }

    elif name == "check_table_availability":

        result = check_reservation_availability(
            db=db,
            reservation_date=args["reservation_date"],
            reservation_time=args["reservation_time"]
        )

        return result

    elif name == "book_table":

        result = create_reservation(
            db=db,
            customer_name=args["customer_name"],
            phone=args["phone"],
            reservation_date=args["reservation_date"],
            reservation_time=args["reservation_time"],
            guests=int(args["guests"]),
            source="vapi",
            special_requests=args.get("special_requests")
        )

        return result

    elif name == "cancel_booking":

        booking_id = int(args["booking_id"])

        result = cancel_reservation(
            db=db,
            booking_id=booking_id
        )

        return result

    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------
# VAPI WEBHOOK
# Existing webhook contract preserved.
# ---------------------------------------

@app.post("/vapi/webhook")
async def vapi_webhook(
    payload: dict,
    db: Session = Depends(get_db)
):

    message = payload.get("message", {})

    if message.get("type") != "tool-calls":
        return {"received": True}

    results = []

    for tool_call in message.get("toolCallList", []):

        tool_id = tool_call.get("id")

        try:
            function = tool_call.get("function", {})

            name = function.get("name")
            args = function.get("arguments", {})

            if isinstance(args, str):
                args = json.loads(args)

            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")

            output = execute_tool(
                name=name,
                args=args,
                db=db
            )

            results.append({
                "toolCallId": tool_id,
                "result": json.dumps(output)
            })

        except Exception as exc:

            results.append({
                "toolCallId": tool_id,
                "error": str(exc)
            })

    return {
        "results": results
    }
