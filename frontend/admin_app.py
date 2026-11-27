
import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ----------------

API_BASE_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

st.set_page_config(
    page_title="RestaurantVoiceAI Admin",
    page_icon="🍽️",
    layout="wide",
)

# ---------------- SESSION ----------------

if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = None

if "reservations" not in st.session_state:
    st.session_state.reservations = []

# ---------------- API HELPERS ----------------

def get_reservations(auth):
    response = requests.get(
        f"{API_BASE_URL}/admin/reservations",
        auth=auth,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def cancel_reservation(booking_id, auth):
    response = requests.delete(
        f"{API_BASE_URL}/admin/reservations/{booking_id}",
        auth=auth,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


# ---------------- LOGIN PAGE ----------------

st.title("🍽️ RestaurantVoiceAI")
st.caption("Restaurant Admin Dashboard")

if st.session_state.admin_auth is None:

    st.subheader("Admin Login")

    with st.form("admin_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_clicked = st.form_submit_button(
            "Login",
            use_container_width=True,
        )

    if login_clicked:
        if not username or not password:
            st.warning("Please enter username and password.")
        else:
            auth = (username, password)

            try:
                data = get_reservations(auth)
                st.session_state.admin_auth = auth
                st.session_state.reservations = data.get(
                    "reservations", []
                )
                st.success("Login successful!")
                st.rerun()

            except requests.exceptions.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 401:
                    st.error("Invalid username or password.")
                else:
                    st.error(f"Backend error: {exc}")

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to backend. "
                    "Please start your FastAPI server."
                )

            except requests.exceptions.RequestException as exc:
                st.error(f"Request failed: {exc}")

# ---------------- DASHBOARD ----------------

else:
    auth = st.session_state.admin_auth

    col1, col2 = st.columns([5, 1])

    with col1:
        st.subheader("Reservation Management")

    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.admin_auth = None
            st.session_state.reservations = []
            st.rerun()

    if st.button("🔄 Refresh Reservations"):
        try:
            data = get_reservations(auth)
            st.session_state.reservations = data.get(
                "reservations", []
            )
            st.success("Reservations refreshed.")
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not refresh reservations: {exc}")

    reservations = st.session_state.reservations

    total = len(reservations)
    confirmed = sum(
        1 for r in reservations if r.get("status") == "confirmed"
    )
    cancelled = sum(
        1 for r in reservations if r.get("status") == "cancelled"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Reservations", total)
    c2.metric("Confirmed", confirmed)
    c3.metric("Cancelled", cancelled)

    st.divider()

    st.subheader("All Reservations")

    if not reservations:
        st.info("No reservations found.")
    else:
        filter_status = st.selectbox(
            "Filter by status",
            ["All", "confirmed", "cancelled", "completed"],
        )

        filtered = reservations

        if filter_status != "All":
            filtered = [
                r for r in reservations
                if r.get("status") == filter_status
            ]

        for reservation in filtered:
            booking_id = reservation.get("booking_id")

            with st.container(border=True):
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.markdown(
                        f"**Booking #{booking_id} — "
                        f"{reservation.get('customer_name', 'N/A')}**"
                    )

                    st.write(
                        f"Phone: {reservation.get('phone', 'N/A')}"
                    )
                    st.write(
                        f"Date: {reservation.get('reservation_date', 'N/A')}"
                    )
                    st.write(
                        f"Time: {reservation.get('reservation_time', 'N/A')}"
                    )
                    st.write(
                        f"Guests: {reservation.get('guests', 'N/A')}"
                    )
                    st.write(
                        f"Table: {reservation.get('table_number', 'N/A')}"
                    )
                    st.write(
                        f"Duration: {reservation.get('duration_minutes', 'N/A')} minutes"
                    )
                    st.write(
                        f"Source: {reservation.get('source', 'N/A')}"
                    )
                    st.write(
                        f"Status: **{reservation.get('status', 'N/A').upper()}**"
                    )

                    if reservation.get("special_requests"):
                        st.write(
                            f"Special requests: "
                            f"{reservation['special_requests']}"
                        )

                with col2:
                    if reservation.get("status") == "confirmed":
                        if st.button(
                            "Cancel Booking",
                            key=f"cancel_{booking_id}",
                            type="secondary",
                        ):
                            try:
                                result = cancel_reservation(
                                    booking_id,
                                    auth,
                                )

                                if result.get("success"):
                                    st.success(
                                        f"Booking #{booking_id} cancelled."
                                    )
                                    data = get_reservations(auth)
                                    st.session_state.reservations = (
                                        data.get("reservations", [])
                                    )
                                    st.rerun()
                                else:
                                    st.error(
                                        result.get(
                                            "message",
                                            "Cancellation failed.",
                                        )
                                    )

                            except requests.exceptions.RequestException as exc:
                                st.error(
                                    f"Cancellation failed: {exc}"
                                )

    st.divider()
    st.caption("RestaurantVoiceAI | Admin Panel")
