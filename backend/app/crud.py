from __future__ import annotations

import datetime as dt
import os
import uuid
from zoneinfo import ZoneInfo

import bcrypt
from pydantic import TypeAdapter, ValidationError
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas
from .enums import Actions, AttendanceStatus, EntryTypes, ResetStatuses


DEFAULT_PIN_RESET_EXPIRATION_MINUTES = 15
DEFAULT_PIN_RESET_MAX_FAILED_ATTEMPTS = 5
DEFAULT_GUARDIAN_LOCK_MINUTES = 15
DEFAULT_GUARDIAN_MAX_FAILED_PIN_ATTEMPTS = 5
DEFAULT_ATTENDANCE_TIMEZONE = "America/Los_Angeles"
PHONE_NUMBER_ADAPTER = TypeAdapter(PhoneNumber)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _as_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)


def _bcrypt_rounds() -> int:
    return int(os.getenv("BCRYPT_ROUNDS", "12"))


def _normalize_email(email: str) -> str:
    return email.lower()


def _normalize_optional_email(email: str | None) -> str | None:
    return email.lower() if email else None


def _serialize_phone(phone_number: object | None) -> str | None:
    if phone_number is None:
        return None
    try:
        return str(PHONE_NUMBER_ADAPTER.validate_python(phone_number))
    except ValidationError:
        return str(phone_number)


def _attendance_timestamp():
    return func.coalesce(models.AttendanceLog.event_time, models.AttendanceLog.created_at)


def _attendance_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("ATTENDANCE_TIMEZONE", DEFAULT_ATTENDANCE_TIMEZONE))


def _attendance_date(value: dt.datetime) -> dt.date:
    return _as_utc(value).astimezone(_attendance_timezone()).date()


def _day_bounds(attendance_date: dt.date) -> tuple[dt.datetime, dt.datetime]:
    timezone = _attendance_timezone()
    start = dt.datetime.combine(attendance_date, dt.time.min, tzinfo=timezone)
    end = dt.datetime.combine(
        attendance_date + dt.timedelta(days=1),
        dt.time.min,
        tzinfo=timezone,
    )
    return start.astimezone(dt.UTC), end.astimezone(dt.UTC)


def hash_secret(secret: str) -> str:
    """Hash a password or PIN using bcrypt."""
    hashed = bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt(rounds=_bcrypt_rounds()))
    return hashed.decode("utf-8")


def verify_secret(plain: str, hashed: str) -> bool:
    """Verify a plain password or PIN against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# Users
def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email=_normalize_email(user.email),
        first_name=user.first_name,
        last_name=user.last_name,
        profile_picture=user.profile_picture,
        role=user.role,
        facility_name=user.facility_name,
        facility_address=user.facility_address,
        license_number=user.license_number,
        hashed_password=hash_secret(user.password),
        hashed_pin=hash_secret(user.pin),
    )
    db.add(db_user)
    db.flush()
    return db_user


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def get_user_by_public_id(db: Session, public_id: uuid.UUID) -> models.User | None:
    statement = select(models.User).where(models.User.public_id == public_id)
    return db.scalars(statement).one_or_none()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    statement = select(models.User).where(models.User.email == _normalize_email(email))
    return db.scalars(statement).one_or_none()


def list_users(db: Session, *, offset: int = 0, limit: int = 100) -> list[models.User]:
    statement = (
        select(models.User)
        .order_by(models.User.last_name, models.User.first_name, models.User.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def update_user_profile(
    db: Session, db_user: models.User, user_update: schemas.UserUpdateProfile
) -> models.User:
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(db_user, field, value)
    db.flush()
    return db_user


def update_user_email(
    db: Session, db_user: models.User, email_update: schemas.UserUpdateEmail
) -> models.User:
    db_user.email = _normalize_email(email_update.email)
    db.flush()
    return db_user


def update_user_password(
    db: Session, db_user: models.User, password_update: schemas.UserUpdatePassword
) -> models.User:
    db_user.hashed_password = hash_secret(password_update.password)
    db.flush()
    return db_user


def update_user_pin(
    db: Session, db_user: models.User, pin_update: schemas.UserUpdatePin
) -> models.User:
    db_user.hashed_pin = hash_secret(pin_update.pin)
    db.flush()
    return db_user


def delete_user(db: Session, db_user: models.User) -> None:
    has_students = db.scalar(
        select(models.Student.id).where(models.Student.provider_id == db_user.id).limit(1)
    )
    has_attendance_logs = db.scalar(
        select(models.AttendanceLog.id)
        .where(models.AttendanceLog.provider_id == db_user.id)
        .limit(1)
    )
    has_attendance_notes = db.scalar(
        select(models.AttendanceLogNote.id)
        .where(models.AttendanceLogNote.provider_id == db_user.id)
        .limit(1)
    )
    has_pin_resets = db.scalar(
        select(models.GuardianPinReset.id)
        .where(models.GuardianPinReset.requested_by_user_id == db_user.id)
        .limit(1)
    )
    if any(
        (
            has_students,
            has_attendance_logs,
            has_attendance_notes,
            has_pin_resets,
        )
    ):
        raise ValueError("Cannot delete a user with retained provider records.")

    db.delete(db_user)
    db.flush()


# Students and guardians
def create_student(
    db: Session, *, provider_id: int, student: schemas.StudentCreate
) -> models.Student:
    guardian_links: list[tuple[models.Guardian, str]] = []
    for link in student.guardian_links:
        guardian = get_guardian_by_public_id(db, link.guardian_public_id)
        if guardian is None:
            raise ValueError("Guardian not found.")
        guardian_links.append((guardian, link.relationship_to_student))

    db_student = models.Student(
        provider_id=provider_id,
        first_name=student.first_name,
        last_name=student.last_name,
        nickname=student.nickname,
        profile_picture=student.profile_picture,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        medical_note=student.medical_note,
        state_id=student.state_id,
    )
    db.add(db_student)
    db.flush()

    for guardian, relationship_to_student in guardian_links:
        link_student_guardian(
            db,
            student=db_student,
            guardian=guardian,
            relationship_to_student=relationship_to_student,
        )

    db.flush()
    return db_student


def get_student(db: Session, student_id: int) -> models.Student | None:
    return db.get(models.Student, student_id)


def get_student_by_public_id(db: Session, public_id: uuid.UUID) -> models.Student | None:
    statement = select(models.Student).where(models.Student.public_id == public_id)
    return db.scalars(statement).one_or_none()


def get_student_for_provider(
    db: Session, *, provider_id: int, student_public_id: uuid.UUID
) -> models.Student | None:
    statement = select(models.Student).where(
        models.Student.provider_id == provider_id,
        models.Student.public_id == student_public_id,
    )
    return db.scalars(statement).one_or_none()


def list_students_for_provider(
    db: Session, *, provider_id: int, offset: int = 0, limit: int = 100
) -> list[models.Student]:
    statement = (
        select(models.Student)
        .where(models.Student.provider_id == provider_id)
        .options(
            selectinload(models.Student.guardian_links).selectinload(
                models.StudentGuardianLink.guardian
            )
        )
        .order_by(models.Student.last_name, models.Student.first_name, models.Student.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def update_student(
    db: Session, db_student: models.Student, student_update: schemas.StudentUpdate
) -> models.Student:
    for field, value in student_update.model_dump(exclude_unset=True).items():
        setattr(db_student, field, value)
    db.flush()
    return db_student


def update_student_medical_note(
    db: Session,
    db_student: models.Student,
    note_update: schemas.StudentUpdateMedicalNote,
) -> models.Student:
    db_student.medical_note = note_update.medical_note
    db.flush()
    return db_student


def delete_student(db: Session, db_student: models.Student) -> None:
    has_attendance_logs = db.scalar(
        select(models.AttendanceLog.id)
        .where(models.AttendanceLog.student_id == db_student.id)
        .limit(1)
    )
    has_attendance_notes = db.scalar(
        select(models.AttendanceLogNote.id)
        .where(models.AttendanceLogNote.student_id == db_student.id)
        .limit(1)
    )
    if has_attendance_logs or has_attendance_notes:
        raise ValueError("Cannot delete a student with retained attendance records.")

    db.delete(db_student)
    db.flush()


def create_guardian(
    db: Session,
    *,
    guardian: schemas.GuardianCreate,
    provider_id: int | None = None,
) -> models.Guardian:
    student_links: list[tuple[models.Student, str]] = []
    for link in guardian.student_links:
        student = get_student_by_public_id(db, link.student_public_id)
        if student is None:
            raise ValueError("Student not found.")
        if provider_id is not None and student.provider_id != provider_id:
            raise ValueError("Student does not belong to this provider.")
        student_links.append((student, link.relationship_to_student))

    db_guardian = models.Guardian(
        first_name=guardian.first_name,
        last_name=guardian.last_name,
        profile_picture=guardian.profile_picture,
        phone_number=_serialize_phone(guardian.phone_number),
        email=_normalize_optional_email(guardian.email),
        hashed_pin=hash_secret(guardian.pin),
        residential_address=guardian.residential_address,
    )
    db.add(db_guardian)
    db.flush()

    for student, relationship_to_student in student_links:
        link_student_guardian(
            db,
            student=student,
            guardian=db_guardian,
            relationship_to_student=relationship_to_student,
        )

    db.flush()
    return db_guardian


def get_guardian(db: Session, guardian_id: int) -> models.Guardian | None:
    return db.get(models.Guardian, guardian_id)


def get_guardian_by_public_id(db: Session, public_id: uuid.UUID) -> models.Guardian | None:
    statement = select(models.Guardian).where(models.Guardian.public_id == public_id)
    return db.scalars(statement).one_or_none()


def get_guardian_by_email(db: Session, email: str) -> models.Guardian | None:
    statement = select(models.Guardian).where(
        models.Guardian.email == _normalize_email(email)
    )
    return db.scalars(statement).one_or_none()


def list_guardians_by_phone_number(
    db: Session, phone_number: object
) -> list[models.Guardian]:
    statement = (
        select(models.Guardian)
        .where(models.Guardian.phone_number == _serialize_phone(phone_number))
        .order_by(models.Guardian.id)
    )
    return list(db.scalars(statement))


def get_guardian_by_phone_number(
    db: Session, phone_number: object
) -> models.Guardian | None:
    guardians = list_guardians_by_phone_number(db, phone_number)
    if len(guardians) > 1:
        raise ValueError("Multiple guardians share this phone number.")
    return guardians[0] if guardians else None


def list_guardians_for_provider(
    db: Session, *, provider_id: int, offset: int = 0, limit: int = 100
) -> list[models.Guardian]:
    statement = (
        select(models.Guardian)
        .join(
            models.StudentGuardianLink,
            models.StudentGuardianLink.guardian_id == models.Guardian.id,
        )
        .join(
            models.Student,
            models.Student.id == models.StudentGuardianLink.student_id,
        )
        .where(models.Student.provider_id == provider_id)
        .options(
            selectinload(models.Guardian.student_links).selectinload(
                models.StudentGuardianLink.student
            )
        )
        .distinct()
        .order_by(models.Guardian.last_name, models.Guardian.first_name, models.Guardian.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def update_guardian(
    db: Session, db_guardian: models.Guardian, guardian_update: schemas.GuardianUpdate
) -> models.Guardian:
    for field, value in guardian_update.model_dump(exclude_unset=True).items():
        if field == "phone_number":
            value = _serialize_phone(value)
        elif field == "email":
            value = _normalize_optional_email(value)
        setattr(db_guardian, field, value)
    db.flush()
    return db_guardian


def delete_guardian(db: Session, db_guardian: models.Guardian) -> None:
    has_attendance_logs = db.scalar(
        select(models.AttendanceLog.id)
        .where(models.AttendanceLog.guardian_id == db_guardian.id)
        .limit(1)
    )
    if has_attendance_logs:
        raise ValueError("Cannot delete a guardian with retained attendance records.")

    db.delete(db_guardian)
    db.flush()


def get_student_guardian_link(
    db: Session, *, student_id: int, guardian_id: int
) -> models.StudentGuardianLink | None:
    statement = select(models.StudentGuardianLink).where(
        models.StudentGuardianLink.student_id == student_id,
        models.StudentGuardianLink.guardian_id == guardian_id,
    )
    return db.scalars(statement).one_or_none()


def link_student_guardian(
    db: Session,
    *,
    student: models.Student,
    guardian: models.Guardian,
    relationship_to_student: str,
) -> models.StudentGuardianLink:
    existing_link = get_student_guardian_link(
        db, student_id=student.id, guardian_id=guardian.id
    )
    if existing_link is not None:
        existing_link.relationship_to_student = relationship_to_student
        db.flush()
        return existing_link

    db_link = models.StudentGuardianLink(
        student_id=student.id,
        guardian_id=guardian.id,
        relationship_to_student=relationship_to_student,
    )
    db.add(db_link)
    db.flush()
    return db_link


def unlink_student_guardian(
    db: Session, *, student: models.Student, guardian: models.Guardian
) -> bool:
    link = get_student_guardian_link(db, student_id=student.id, guardian_id=guardian.id)
    if link is None:
        return False

    db.delete(link)
    db.flush()
    return True


def update_guardian_student_links(
    db: Session,
    *,
    guardian: models.Guardian,
    links_update: schemas.GuardianStudentLinksUpdate,
    relationship_to_student: str = "guardian",
    provider_id: int | None = None,
) -> models.Guardian:
    for student_public_id in links_update.remove_student_public_ids:
        student = get_student_by_public_id(db, student_public_id)
        if student is not None and (
            provider_id is None or student.provider_id == provider_id
        ):
            unlink_student_guardian(db, student=student, guardian=guardian)

    for student_public_id in links_update.add_student_public_ids:
        student = get_student_by_public_id(db, student_public_id)
        if student is None:
            raise ValueError("Student not found.")
        if provider_id is not None and student.provider_id != provider_id:
            raise ValueError("Student does not belong to this provider.")
        link_student_guardian(
            db,
            student=student,
            guardian=guardian,
            relationship_to_student=relationship_to_student,
        )

    db.flush()
    return guardian


def guardian_belongs_to_provider(
    db: Session, *, guardian_id: int, provider_id: int
) -> bool:
    statement = (
        select(models.Guardian.id)
        .join(
            models.StudentGuardianLink,
            models.StudentGuardianLink.guardian_id == models.Guardian.id,
        )
        .join(
            models.Student,
            models.Student.id == models.StudentGuardianLink.student_id,
        )
        .where(
            models.Guardian.id == guardian_id,
            models.Student.provider_id == provider_id,
        )
        .limit(1)
    )
    return db.scalars(statement).first() is not None


# Attendance logs and status
def get_attendance_log(db: Session, attendance_log_id: int) -> models.AttendanceLog | None:
    return db.get(models.AttendanceLog, attendance_log_id)


def get_attendance_log_by_public_id(
    db: Session, public_id: uuid.UUID
) -> models.AttendanceLog | None:
    statement = select(models.AttendanceLog).where(
        models.AttendanceLog.public_id == public_id
    )
    return db.scalars(statement).one_or_none()


def list_attendance_logs_for_day(
    db: Session,
    *,
    provider_id: int,
    attendance_date: dt.date,
    student_public_id: uuid.UUID | None = None,
    include_void: bool = False,
) -> list[models.AttendanceLog]:
    start, end = _day_bounds(attendance_date)
    statement = (
        select(models.AttendanceLog)
        .join(models.Student)
        .where(
            models.AttendanceLog.provider_id == provider_id,
            _attendance_timestamp() >= start,
            _attendance_timestamp() < end,
        )
        .options(selectinload(models.AttendanceLog.student))
        .order_by(_attendance_timestamp(), models.AttendanceLog.id)
    )
    if student_public_id is not None:
        statement = statement.where(models.Student.public_id == student_public_id)
    if not include_void:
        statement = statement.where(models.AttendanceLog.is_void.is_(False))
    return list(db.scalars(statement))


def _active_logs_for_student_day(
    db: Session,
    *,
    provider_id: int,
    student_id: int,
    attendance_date: dt.date,
) -> list[models.AttendanceLog]:
    start, end = _day_bounds(attendance_date)
    statement = (
        select(models.AttendanceLog)
        .where(
            models.AttendanceLog.provider_id == provider_id,
            models.AttendanceLog.student_id == student_id,
            models.AttendanceLog.is_void.is_(False),
            _attendance_timestamp() >= start,
            _attendance_timestamp() < end,
        )
        .order_by(_attendance_timestamp(), models.AttendanceLog.id)
    )
    return list(db.scalars(statement))


def _validate_attendance_sequence(
    entries: list[tuple[dt.datetime, int, Actions]]
) -> bool:
    if not entries:
        return True

    ordered_entries = sorted(entries, key=lambda entry: (entry[0], entry[1]))
    state = AttendanceStatus.CAN_CHECK_IN

    for index, (_, _, action) in enumerate(ordered_entries):
        if action == Actions.ABSENT:
            return len(ordered_entries) == 1 and index == 0
        if action == Actions.CHECK_IN:
            if state != AttendanceStatus.CAN_CHECK_IN:
                return False
            state = AttendanceStatus.CAN_CHECK_OUT
            continue
        if action == Actions.CHECK_OUT:
            if state != AttendanceStatus.CAN_CHECK_OUT:
                return False
            state = AttendanceStatus.CAN_CHECK_IN
            continue
        return False

    return True


def _ensure_attendance_sequence_accepts(
    existing_logs: list[models.AttendanceLog],
    *,
    candidate_event_time: dt.datetime,
    candidate_action: Actions,
) -> None:
    entries: list[tuple[dt.datetime, int, Actions]] = []
    for log in existing_logs:
        event_time = log.event_time or log.created_at
        if event_time is None:
            continue
        entries.append((_as_utc(event_time), log.id or 0, log.action))

    entries.append((_as_utc(candidate_event_time), 10**12, candidate_action))

    if not _validate_attendance_sequence(entries):
        raise ValueError("Invalid attendance sequence for the day.")


def _ensure_attendance_logs_are_sequence_valid(
    logs: list[models.AttendanceLog],
) -> None:
    entries = [
        (_as_utc(log.event_time or log.created_at), log.id or 0, log.action)
        for log in logs
        if log.event_time is not None or log.created_at is not None
    ]
    if not _validate_attendance_sequence(entries):
        raise ValueError("Correction would leave invalid attendance sequence.")


def _ensure_guardian_can_act_for_student(
    db: Session, *, guardian_id: int, student_id: int
) -> models.Guardian:
    guardian = get_guardian(db, guardian_id)
    if guardian is None:
        raise ValueError("Guardian not found.")

    link = get_student_guardian_link(
        db, student_id=student_id, guardian_id=guardian_id
    )
    if link is None:
        raise ValueError("Guardian is not linked to this student.")
    return guardian


def _create_attendance_log(
    db: Session,
    *,
    provider_id: int,
    student_id: int,
    action: Actions,
    entry_type: EntryTypes,
    event_time: dt.datetime,
    guardian_id: int | None = None,
    authorized_person_name: str | None = None,
    guardian_signature_url: str | None = None,
    original_log_id: int | None = None,
) -> models.AttendanceLog:
    db_log = models.AttendanceLog(
        provider_id=provider_id,
        student_id=student_id,
        guardian_id=guardian_id,
        event_time=_as_utc(event_time),
        action=action,
        entry_type=entry_type,
        authorized_person_name=authorized_person_name,
        guardian_signature_url=guardian_signature_url,
        original_log_id=original_log_id,
    )
    db.add(db_log)
    db.flush()
    return db_log


def create_attendance_check_in(
    db: Session,
    *,
    provider_id: int,
    guardian_id: int,
    attendance: schemas.AttendanceCheckInCreate,
    event_time: dt.datetime | None = None,
) -> models.AttendanceLog:
    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=attendance.student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    _ensure_guardian_can_act_for_student(db, guardian_id=guardian_id, student_id=student.id)
    timestamp = event_time or _utc_now()
    existing_logs = _active_logs_for_student_day(
        db,
        provider_id=provider_id,
        student_id=student.id,
        attendance_date=_attendance_date(timestamp),
    )
    _ensure_attendance_sequence_accepts(
        existing_logs,
        candidate_event_time=timestamp,
        candidate_action=Actions.CHECK_IN,
    )

    return _create_attendance_log(
        db,
        provider_id=provider_id,
        student_id=student.id,
        guardian_id=guardian_id,
        action=attendance.action,
        entry_type=attendance.entry_type,
        event_time=timestamp,
        authorized_person_name=attendance.authorized_person_name,
        guardian_signature_url=attendance.guardian_signature_url,
    )


def create_attendance_check_out(
    db: Session,
    *,
    provider_id: int,
    guardian_id: int,
    attendance: schemas.AttendanceCheckOutCreate,
    event_time: dt.datetime | None = None,
) -> models.AttendanceLog:
    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=attendance.student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    _ensure_guardian_can_act_for_student(db, guardian_id=guardian_id, student_id=student.id)
    timestamp = event_time or _utc_now()
    existing_logs = _active_logs_for_student_day(
        db,
        provider_id=provider_id,
        student_id=student.id,
        attendance_date=_attendance_date(timestamp),
    )
    _ensure_attendance_sequence_accepts(
        existing_logs,
        candidate_event_time=timestamp,
        candidate_action=Actions.CHECK_OUT,
    )

    return _create_attendance_log(
        db,
        provider_id=provider_id,
        student_id=student.id,
        guardian_id=guardian_id,
        action=attendance.action,
        entry_type=attendance.entry_type,
        event_time=timestamp,
        authorized_person_name=attendance.authorized_person_name,
        guardian_signature_url=attendance.guardian_signature_url,
    )


def mark_student_absent(
    db: Session,
    *,
    provider_id: int,
    attendance: schemas.AttendanceMarkAbsentCreate,
    event_time: dt.datetime | None = None,
) -> models.AttendanceLog:
    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=attendance.student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    timestamp = event_time or _utc_now()
    existing_logs = _active_logs_for_student_day(
        db,
        provider_id=provider_id,
        student_id=student.id,
        attendance_date=_attendance_date(timestamp),
    )
    _ensure_attendance_sequence_accepts(
        existing_logs,
        candidate_event_time=timestamp,
        candidate_action=Actions.ABSENT,
    )

    return _create_attendance_log(
        db,
        provider_id=provider_id,
        student_id=student.id,
        action=attendance.action,
        entry_type=attendance.entry_type,
        event_time=timestamp,
    )


def create_manual_attendance_entry(
    db: Session,
    *,
    provider_id: int,
    attendance: schemas.AttendanceManualEntryCreate,
) -> models.AttendanceLog:
    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=attendance.student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    timestamp = _as_utc(attendance.event_time)
    existing_logs = _active_logs_for_student_day(
        db,
        provider_id=provider_id,
        student_id=student.id,
        attendance_date=_attendance_date(timestamp),
    )
    _ensure_attendance_sequence_accepts(
        existing_logs,
        candidate_event_time=timestamp,
        candidate_action=attendance.action,
    )

    return _create_attendance_log(
        db,
        provider_id=provider_id,
        student_id=student.id,
        action=attendance.action,
        entry_type=attendance.entry_type,
        event_time=timestamp,
    )


def correct_attendance_log(
    db: Session,
    *,
    provider_id: int,
    correction: schemas.AttendanceCorrection,
) -> models.AttendanceLog:
    original_log = get_attendance_log_by_public_id(db, correction.original_log_public_id)
    if (
        original_log is None
        or original_log.provider_id != provider_id
        or original_log.is_void
    ):
        raise ValueError("Original attendance log not found for this provider.")

    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=correction.student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    correction_time = _as_utc(correction.event_time)
    original_time = _as_utc(original_log.event_time or original_log.created_at)
    original_remaining_logs = [
        log
        for log in _active_logs_for_student_day(
            db,
            provider_id=provider_id,
            student_id=original_log.student_id,
            attendance_date=_attendance_date(original_time),
        )
        if log.id != original_log.id
    ]
    _ensure_attendance_logs_are_sequence_valid(original_remaining_logs)

    corrected_existing_logs = [
        log
        for log in _active_logs_for_student_day(
            db,
            provider_id=provider_id,
            student_id=student.id,
            attendance_date=_attendance_date(correction_time),
        )
        if log.id != original_log.id
    ]
    _ensure_attendance_sequence_accepts(
        corrected_existing_logs,
        candidate_event_time=correction_time,
        candidate_action=correction.action,
    )

    original_log.is_void = True
    corrected_log = _create_attendance_log(
        db,
        provider_id=provider_id,
        student_id=student.id,
        action=correction.action,
        entry_type=correction.entry_type,
        event_time=correction_time,
        original_log_id=original_log.id,
    )
    db.flush()
    return corrected_log


def void_attendance_log(
    db: Session, *, provider_id: int, attendance_log_public_id: uuid.UUID
) -> models.AttendanceLog:
    attendance_log = get_attendance_log_by_public_id(db, attendance_log_public_id)
    if attendance_log is None or attendance_log.provider_id != provider_id:
        raise ValueError("Attendance log not found for this provider.")
    attendance_log.is_void = True
    db.flush()
    return attendance_log


def get_attendance_day_status(
    db: Session,
    *,
    provider_id: int,
    student_public_id: uuid.UUID,
    attendance_date: dt.date,
) -> schemas.AttendanceDayStatusResponse:
    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    logs = _active_logs_for_student_day(
        db,
        provider_id=provider_id,
        student_id=student.id,
        attendance_date=attendance_date,
    )
    if not logs:
        return schemas.AttendanceDayStatusResponse(
            event_time=None,
            authorized_person_name=None,
            current_status=AttendanceStatus.CAN_CHECK_IN,
        )

    last_log = logs[-1]
    if last_log.action == Actions.CHECK_IN:
        current_status = AttendanceStatus.CAN_CHECK_OUT
    elif last_log.action == Actions.CHECK_OUT:
        current_status = AttendanceStatus.CAN_CHECK_IN
    else:
        current_status = AttendanceStatus.IS_ABSENT

    return schemas.AttendanceDayStatusResponse(
        event_time=last_log.event_time or last_log.created_at,
        authorized_person_name=last_log.authorized_person_name,
        current_status=current_status,
    )


# Attendance notes
def create_attendance_note(
    db: Session,
    *,
    provider_id: int,
    note: schemas.AttendanceLogNoteCreate,
) -> models.AttendanceLogNote:
    student = get_student_for_provider(
        db, provider_id=provider_id, student_public_id=note.student_public_id
    )
    if student is None:
        raise ValueError("Student not found for this provider.")

    existing_note = db.scalar(
        select(models.AttendanceLogNote.id).where(
            models.AttendanceLogNote.student_id == student.id,
            models.AttendanceLogNote.attendance_date == note.attendance_date,
        )
    )
    if existing_note is not None:
        raise ValueError("Attendance note already exists for this student and date.")

    db_note = models.AttendanceLogNote(
        provider_id=provider_id,
        student_id=student.id,
        attendance_date=note.attendance_date,
        note=note.note,
    )
    db.add(db_note)
    db.flush()
    return db_note


def get_attendance_note(
    db: Session, attendance_note_id: int
) -> models.AttendanceLogNote | None:
    return db.get(models.AttendanceLogNote, attendance_note_id)


def get_attendance_note_by_public_id(
    db: Session, public_id: uuid.UUID
) -> models.AttendanceLogNote | None:
    statement = select(models.AttendanceLogNote).where(
        models.AttendanceLogNote.public_id == public_id
    )
    return db.scalars(statement).one_or_none()


def list_attendance_notes_for_day(
    db: Session,
    *,
    provider_id: int,
    attendance_date: dt.date,
    student_public_id: uuid.UUID | None = None,
) -> list[models.AttendanceLogNote]:
    statement = (
        select(models.AttendanceLogNote)
        .join(models.Student)
        .where(
            models.AttendanceLogNote.provider_id == provider_id,
            models.AttendanceLogNote.attendance_date == attendance_date,
        )
        .order_by(models.Student.last_name, models.Student.first_name)
    )
    if student_public_id is not None:
        statement = statement.where(models.Student.public_id == student_public_id)
    return list(db.scalars(statement))


def get_attendance_note_for_day(
    db: Session,
    *,
    provider_id: int,
    student_public_id: uuid.UUID,
    attendance_date: dt.date,
) -> models.AttendanceLogNote | None:
    notes = list_attendance_notes_for_day(
        db,
        provider_id=provider_id,
        attendance_date=attendance_date,
        student_public_id=student_public_id,
    )
    return notes[0] if notes else None


def update_attendance_note(
    db: Session,
    db_note: models.AttendanceLogNote,
    note_update: schemas.AttendanceLogNoteUpdate,
) -> models.AttendanceLogNote:
    for field, value in note_update.model_dump(exclude_unset=True).items():
        setattr(db_note, field, value)
    db.flush()
    return db_note


def delete_attendance_note(db: Session, db_note: models.AttendanceLogNote) -> None:
    db.delete(db_note)
    db.flush()


# Guardian PIN reset and PIN verification
def create_guardian_pin_reset(
    db: Session,
    *,
    provider_id: int,
    reset_request: schemas.GuardianPinResetRequest,
    reset_code: str,
    expires_at: dt.datetime | None = None,
    now: dt.datetime | None = None,
) -> models.GuardianPinReset:
    provider = get_user(db, provider_id)
    if provider is None:
        raise ValueError("Provider not found.")

    guardian = get_guardian_by_public_id(db, reset_request.guardian_public_id)
    if guardian is None or not guardian_belongs_to_provider(
        db, guardian_id=guardian.id, provider_id=provider_id
    ):
        raise ValueError("Guardian not found for this provider.")

    timestamp = now or _utc_now()
    expiration = expires_at or (
        timestamp + dt.timedelta(minutes=DEFAULT_PIN_RESET_EXPIRATION_MINUTES)
    )
    guardian.requires_pin_reset = True

    db_reset = models.GuardianPinReset(
        guardian_id=guardian.id,
        requested_by_user_id=provider.id,
        verification_method=reset_request.verification_method,
        status=ResetStatuses.PENDING,
        reset_code_hash=hash_secret(reset_code),
        expires_at=_as_utc(expiration),
    )
    db.add(db_reset)
    db.flush()
    return db_reset


def get_guardian_pin_reset(
    db: Session, reset_id: int
) -> models.GuardianPinReset | None:
    return db.get(models.GuardianPinReset, reset_id)


def get_guardian_pin_reset_by_public_id(
    db: Session, public_id: uuid.UUID
) -> models.GuardianPinReset | None:
    statement = select(models.GuardianPinReset).where(
        models.GuardianPinReset.public_id == public_id
    )
    return db.scalars(statement).one_or_none()


def list_guardian_pin_resets_for_guardian(
    db: Session, *, guardian_id: int
) -> list[models.GuardianPinReset]:
    statement = (
        select(models.GuardianPinReset)
        .where(models.GuardianPinReset.guardian_id == guardian_id)
        .order_by(models.GuardianPinReset.created_at.desc(), models.GuardianPinReset.id.desc())
    )
    return list(db.scalars(statement))


def verify_guardian_pin_reset(
    db: Session,
    *,
    reset_public_id: uuid.UUID,
    code: str,
    now: dt.datetime | None = None,
    max_failed_attempts: int = DEFAULT_PIN_RESET_MAX_FAILED_ATTEMPTS,
) -> models.GuardianPinReset | None:
    reset = get_guardian_pin_reset_by_public_id(db, reset_public_id)
    timestamp = now or _utc_now()
    if (
        reset is None
        or reset.status != ResetStatuses.PENDING
        or _as_utc(reset.expires_at) <= _as_utc(timestamp)
    ):
        return None

    if not verify_secret(code, reset.reset_code_hash):
        reset.failed_verification_attempts += 1
        if reset.failed_verification_attempts >= max_failed_attempts:
            reset.status = ResetStatuses.LOCKED
            reset.locked_at = _as_utc(timestamp)
        db.flush()
        return None

    reset.status = ResetStatuses.VERIFIED
    reset.verified_at = _as_utc(timestamp)
    db.flush()
    return reset


def complete_guardian_pin_reset(
    db: Session,
    *,
    reset_public_id: uuid.UUID,
    new_pin: str,
    now: dt.datetime | None = None,
) -> models.Guardian | None:
    reset = get_guardian_pin_reset_by_public_id(db, reset_public_id)
    timestamp = now or _utc_now()
    if (
        reset is None
        or reset.status != ResetStatuses.VERIFIED
        or _as_utc(reset.expires_at) <= _as_utc(timestamp)
    ):
        return None

    guardian = reset.guardian
    guardian.hashed_pin = hash_secret(new_pin)
    guardian.pin_updated_at = _as_utc(timestamp)
    guardian.last_pin_reset_at = _as_utc(timestamp)
    guardian.requires_pin_reset = False
    guardian.failed_pin_attempts = 0
    guardian.pin_locked_until = None
    # Consume the reset so the verified window cannot be replayed.
    reset.status = ResetStatuses.COMPLETED
    db.flush()
    return guardian


def verify_guardian_pin(
    db: Session,
    *,
    guardian: models.Guardian,
    pin: str,
    now: dt.datetime | None = None,
    max_failed_attempts: int = DEFAULT_GUARDIAN_MAX_FAILED_PIN_ATTEMPTS,
    lock_minutes: int = DEFAULT_GUARDIAN_LOCK_MINUTES,
) -> bool:
    timestamp = now or _utc_now()
    if guardian.pin_locked_until is not None and _as_utc(
        guardian.pin_locked_until
    ) > _as_utc(timestamp):
        return False

    if guardian.pin_locked_until is not None:
        guardian.failed_pin_attempts = 0
        guardian.pin_locked_until = None

    if verify_secret(pin, guardian.hashed_pin):
        guardian.failed_pin_attempts = 0
        guardian.pin_locked_until = None
        db.flush()
        return True

    guardian.failed_pin_attempts += 1
    if guardian.failed_pin_attempts >= max_failed_attempts:
        guardian.pin_locked_until = _as_utc(timestamp) + dt.timedelta(
            minutes=lock_minutes
        )
    db.flush()
    return False
