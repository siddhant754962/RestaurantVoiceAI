
import json
import urllib.request
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000/vapi/webhook"


def call_vapi_tool(tool_name, arguments=None):
    """Send a simulated Vapi tool call to FastAPI."""

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": f"test-{tool_name}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": arguments or {}
                    }
                }
            ]
        }
    }

    request = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_result(response):
    item = response["results"][0]

    if "error" in item:
        raise Exception(item["error"])

    return json.loads(item["result"])


# Use a date 14 days in the future.
reservation_date = (
    date.today() + timedelta(days=14)
).isoformat()

reservation_time = "19:00:00"

print("\nTEST 1: Get restaurant menu")

response = call_vapi_tool("get_menu")
result = extract_result(response)

assert result["success"] is True
assert len(result["menu"]) > 0

print("PASS: Menu returned successfully")
print(result["menu"])


print("\nTEST 2: Check table availability")

response = call_vapi_tool(
    "check_table_availability",
    {
        "reservation_date": reservation_date,
        "reservation_time": reservation_time
    }
)

result = extract_result(response)

assert result["success"] is True

print("Availability result:", result)


print("\nTEST 3: Create reservation")

response = call_vapi_tool(
    "book_table",
    {
        "customer_name": "Vapi Test Customer",
        "phone": "9876543210",
        "reservation_date": reservation_date,
        "reservation_time": reservation_time,
        "guests": 3,
        "special_requests": "Window seating if available"
    }
)

result = extract_result(response)

assert result["success"] is True, result

booking_id = result["booking_id"]

print("PASS: Reservation created")
print("Booking ID:", booking_id)
print("Reservation:", result)


print("\nTEST 4: Cancel reservation")

response = call_vapi_tool(
    "cancel_booking",
    {
        "booking_id": booking_id
    }
)

result = extract_result(response)

assert result["success"] is True

print("PASS: Reservation cancelled")
print(result)


print("\nTEST 5: Verify repeated cancellation is rejected")

response = call_vapi_tool(
    "cancel_booking",
    {
        "booking_id": booking_id
    }
)

result = extract_result(response)

assert result["success"] is False
assert result["message"] == "Booking is already cancelled."

print("PASS: Already-cancelled reservation rejected")


print("\n================================")
print("ALL VAPI TOOL TESTS PASSED")
print("================================")
