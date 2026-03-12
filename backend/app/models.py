from enum import Enum as PyEnum
from typing import Optional

from .database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Enum as SQLEnum

class UserRole(str, PyEnum):
    ADMIN = "admin"
    PROVIDER = "provider"
    EMPLOYEE = "employee"

## User
# email
# password
# pin
# facility name
# facility address
# provider id
# First name
# Last name
# Role

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hash_password: Mapped[str] = mapped_column(String(255))
    hashed_pin: Mapped[str] = mapped_column(String(255))

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.PROVIDER)
    # status = mapped_column(Enum(Status, name="status_enum"))

    facility_name: Mapped[str] = mapped_column(String(200))
    facility_address: Mapped[Optional[str]] = mapped_column(String(255))
    license_number: Mapped[Optional[str]] = mapped_column(String(50), index=True)



# Full Name (First Name, Last Name)
# Picture (Allows upload, defaults if not provided)
# Date of Birth (Format: 05/12/2023)
# Nickname/Preferred Name (Optional)
# State/Facility ID (Optional for legal/subsidy tracking)
# Gender (Selection: male, female, n/a)
# Allergy/Medical Note (Free-text field)