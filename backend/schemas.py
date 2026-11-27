
from pydantic import BaseModel, Field
from datetime import date, time


class BookingCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=20)
    reservation_date: date
    reservation_time: time
    guests: int = Field(ge=1, le=20)


class BookingResponse(BaseModel):
    id: int
    customer_name: str
    phone: str
    reservation_date: date
    reservation_time: time
    guests: int
    status: str

    class Config:
        from_attributes = True
