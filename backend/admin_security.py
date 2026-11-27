
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

security = HTTPBasic()


def verify_admin(
    credentials: HTTPBasicCredentials = Depends(security),
):
    correct_username = os.getenv("ADMIN_USERNAME", "")
    correct_password = os.getenv("ADMIN_PASSWORD", "")

    if not correct_username or not correct_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials are not configured.",
        )

    username_ok = secrets.compare_digest(
        credentials.username,
        correct_username,
    )

    password_ok = secrets.compare_digest(
        credentials.password,
        correct_password,
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return {"username": credentials.username, "role": "admin"}
