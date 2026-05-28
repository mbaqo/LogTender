from app import schemas
from app.enums import UserRole


def make_user_create(**overrides: object) -> schemas.UserCreate:
    defaults = {
        "email": "user@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "profile_picture": None,
        "role": UserRole.PROVIDER,
        "facility_name": "Daycare LLC",
        "facility_address": None,
        "license_number": None,
        "password": "testpassword",
        "pin": "12145",
    }
    return schemas.UserCreate(**{**defaults, **overrides})
