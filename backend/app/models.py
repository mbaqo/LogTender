import uuid
import datetime
from typing import Optional

from sqlalchemy import String, Enum as SQLEnum, UUID, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .database import Base

from .enums import UserRole, Genders, Actions, EntryTypes, ResetVerificationMethods, ResetStatuses

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
    guardian_pin_resets: Mapped[list["GuardianPinReset"]] = relationship(
        back_populates="requested_by_user"
    )

class StudentGuardianLink(Base):
    __tablename__ = "student_guardian_links"

    student_id = mapped_column(ForeignKey("students.id"), primary_key=True)
    guardian_id = mapped_column(ForeignKey("guardians.id"), primary_key=True)
    relationship_to_student: Mapped[str] = mapped_column(String(50), nullable=False)

    student: Mapped["Student"] = relationship(back_populates="guardian_links")
    guardian: Mapped["Guardian"] = relationship(back_populates="student_links")


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

    date_of_birth: Mapped[datetime.date] = mapped_column()
    gender: Mapped[Genders] = mapped_column(SQLEnum(Genders), default = Genders.NA)

    medical_note: Mapped[Optional[str]] = mapped_column(String(350))
    state_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Provider Relationshp=ip
    provider: Mapped["User"] = relationship(back_populates="students")
    # guardian's relationship
    guardian_links: Mapped[list["StudentGuardianLink"]] = relationship( 
        back_populates="student",
        cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(back_populates="student")

class Guardian(Base):
    __tablename__ = "guardians"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255))

    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # PIN SET/RESET
    hashed_pin: Mapped[str] = mapped_column(String(255))
    pin_updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    failed_pin_attempts: Mapped[int] = mapped_column(default=0)
    pin_locked_until: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    requires_pin_reset: Mapped[bool] = mapped_column(default=False)
    last_pin_reset_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    pin_reset_requests: Mapped[list["GuardianPinReset"]] = relationship(
        back_populates="guardian",
        cascade="all, delete-orphan"
    )

    residential_address: Mapped[Optional[str]] = mapped_column(String(255))

    student_links: Mapped[list["StudentGuardianLink"]] = relationship(
        back_populates="guardian",
        cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(back_populates="guardian")

class GuardianPinReset(Base):
    __tablename__ = "guardian_pin_resets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    guardian_id: Mapped[int] = mapped_column(ForeignKey("guardians.id"), index=True)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    verification_method: Mapped[ResetVerificationMethods] = mapped_column(SQLEnum(ResetVerificationMethods), default=ResetVerificationMethods.SMS_OTP)
    status: Mapped[ResetStatuses] = mapped_column(SQLEnum(ResetStatuses), default=ResetStatuses.PENDING)

    reset_code_hash: Mapped[str] = mapped_column(String(255))
    verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    guardian: Mapped["Guardian"] = relationship(back_populates="pin_reset_requests")
    requested_by_user: Mapped["User"] = relationship(
        back_populates="guardian_pin_resets"
    )
    

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Multi-tenancy
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    
    # Which guardian performed the action (None if provider did it)
    guardian_id: Mapped[Optional[int]] = mapped_column(ForeignKey("guardians.id"), index=True)

    # 1. Audit Data
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    
    # event_time: The actual time of arrival/departure
    event_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    action: Mapped[Actions] = mapped_column(SQLEnum(Actions))
    entry_type: Mapped[EntryTypes] = mapped_column(SQLEnum(EntryTypes), default=EntryTypes.GUARDIAN)
    
    # Snapshot of the person's name for historical accuracy
    authorized_person_name: Mapped[str] = mapped_column(String(200))
    
    # 2. Compliance & Media
    # URL to the signature image stored in cloud storage
    guardian_signature_url: Mapped[Optional[str]] = mapped_column(String(512)) 
    note: Mapped[Optional[str]] = mapped_column(Text)

    # 3. The Audit Trail (Handling Edits)
    is_void: Mapped[bool] = mapped_column(default=False)\
    
    # Points to original log if this is a correction
    original_log_id: Mapped[Optional[int]] = mapped_column() 

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="attendance_logs")
    guardian: Mapped[Optional["Guardian"]] = relationship(back_populates="attendance_logs")