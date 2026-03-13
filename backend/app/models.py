import uuid
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, Enum as SQLEnum, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

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
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hash_password: Mapped[str] = mapped_column(String(255))
    hashed_pin: Mapped[str] = mapped_column(String(255))

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    # Picture url
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.PROVIDER)

    facility_name: Mapped[str] = mapped_column(String(200))
    facility_address: Mapped[Optional[str]] = mapped_column(String(255))
    license_number: Mapped[Optional[str]] = mapped_column(String(50), index=True)

    students: Mapped[list["Student"]] = relationship(back_populates="provider")

# Child:
# First Name
# Last Name
# picture
# Nickname (optional)
# Child ID (optional)
# Gender
# Date of Birth
# Medical Note
# Parents
# Attendance

class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID (as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # foreign key to link to user/provider
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[Optional[str]] = mapped_column(String(100))
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255))

    medical_note: Mapped[Optional[str]] = mapped_column(String(350))
    state_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Provider Relationshp=ip
    provider: Mapped["User"] = relationship(back_populates="students")



# Full Name (First Name, Last Name)
# Picture (Allows upload, defaults if not provided)
# Date of Birth (Format: 05/12/2023)
# Nickname/Preferred Name (Optional)
# State/Facility ID (Optional for legal/subsidy tracking)
# Gender (Selection: male, female, n/a)
# Allergy/Medical Note (Free-text field)