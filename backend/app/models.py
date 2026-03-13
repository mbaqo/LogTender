import uuid
from datetime import date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, String, Enum as SQLEnum, UUID, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class UserRole(str, PyEnum):
    ADMIN = "admin"
    PROVIDER = "provider"
    EMPLOYEE = "employee"

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

guardian_student_association = Table(
    "guardian_student_association",
    Base.metadata,
    Column("student_id", ForeignKey("students.id"), primary_key=True),
    Column("guardian_id", ForeignKey("guardians.id"), primary_key=True),
)

class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # foreign key to link to user/provider
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[Optional[str]] = mapped_column(String(100))
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255))

    date_of_birth: Mapped[date] = mapped_column()
    gender: Mapped[str] = mapped_column(String(20))

    medical_note: Mapped[Optional[str]] = mapped_column(String(350))
    state_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Provider Relationshp=ip
    provider: Mapped["User"] = relationship(back_populates="students")
    # parents relationship
    guardians: Mapped[list["Guardian"]] = relationship(
        secondary=guardian_student_association, 
        back_populates="students"
    )

class Guardian(Base):
    __tablename__ = "guardians"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))

    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    hashed_pin: Mapped[str] = mapped_column(String(255))

    residential_address: Mapped[Optional[str]] = mapped_column(String(255))

    students: Mapped[list["Student"]] = relationship(
        secondary=guardian_student_association, 
        back_populates="guardians"
    )