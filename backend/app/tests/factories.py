import datetime as dt
import uuid

from app import schemas
from app.enums import Actions, Genders, ResetVerificationMethods, UserRole


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


def make_student_create(**overrides: object) -> schemas.StudentCreate:
    defaults = {
        "first_name": "Sam",
        "last_name": "Student",
        "nickname": "Sammy",
        "profile_picture": None,
        "date_of_birth": dt.date(2021, 5, 17),
        "gender": Genders.NA,
        "medical_note": None,
        "state_id": None,
        "guardian_links": [],
    }
    return schemas.StudentCreate(**{**defaults, **overrides})


def make_guardian_create(**overrides: object) -> schemas.GuardianCreate:
    defaults = {
        "first_name": "Gary",
        "last_name": "Guardian",
        "profile_picture": None,
        "phone_number": "+14155552671",
        "email": "guardian@example.com",
        "residential_address": None,
        "pin": "54321",
        "student_links": [],
    }
    return schemas.GuardianCreate(**{**defaults, **overrides})


def make_guardian_link_create(
    *, guardian_public_id: uuid.UUID, relationship_to_student: str = "guardian"
) -> schemas.GuardianLinkCreate:
    return schemas.GuardianLinkCreate(
        guardian_public_id=guardian_public_id,
        relationship_to_student=relationship_to_student,
    )


def make_student_link_create(
    *, student_public_id: uuid.UUID, relationship_to_student: str = "guardian"
) -> schemas.StudentLinkCreate:
    return schemas.StudentLinkCreate(
        student_public_id=student_public_id,
        relationship_to_student=relationship_to_student,
    )


def make_check_in_create(
    *, student_public_id: uuid.UUID, **overrides: object
) -> schemas.AttendanceCheckInCreate:
    defaults = {
        "student_public_id": student_public_id,
        "guardian_signature_url": "https://example.com/signature-in.png",
        "authorized_person_name": "Gary Guardian",
    }
    return schemas.AttendanceCheckInCreate(**{**defaults, **overrides})


def make_check_out_create(
    *, student_public_id: uuid.UUID, **overrides: object
) -> schemas.AttendanceCheckOutCreate:
    defaults = {
        "student_public_id": student_public_id,
        "guardian_signature_url": "https://example.com/signature-out.png",
        "authorized_person_name": "Gary Guardian",
    }
    return schemas.AttendanceCheckOutCreate(**{**defaults, **overrides})


def make_mark_absent_create(
    *, student_public_id: uuid.UUID,
) -> schemas.AttendanceMarkAbsentCreate:
    return schemas.AttendanceMarkAbsentCreate(student_public_id=student_public_id)


def make_manual_attendance_create(
    *,
    student_public_id: uuid.UUID,
    event_time: dt.datetime,
    action: Actions,
) -> schemas.AttendanceManualEntryCreate:
    return schemas.AttendanceManualEntryCreate(
        student_public_id=student_public_id,
        event_time=event_time,
        action=action,
    )


def make_attendance_correction(
    *,
    student_public_id: uuid.UUID,
    original_log_public_id: uuid.UUID,
    event_time: dt.datetime,
    action: Actions,
) -> schemas.AttendanceCorrection:
    return schemas.AttendanceCorrection(
        student_public_id=student_public_id,
        original_log_public_id=original_log_public_id,
        event_time=event_time,
        action=action,
    )


def make_attendance_note_create(
    *, student_public_id: uuid.UUID, attendance_date: dt.date, note: str = "Sick day"
) -> schemas.AttendanceLogNoteCreate:
    return schemas.AttendanceLogNoteCreate(
        student_public_id=student_public_id,
        attendance_date=attendance_date,
        note=note,
    )


def make_guardian_pin_reset_request(
    *,
    guardian_public_id: uuid.UUID,
    verification_method: ResetVerificationMethods = ResetVerificationMethods.SMS_OTP,
) -> schemas.GuardianPinResetRequest:
    return schemas.GuardianPinResetRequest(
        guardian_public_id=guardian_public_id,
        verification_method=verification_method,
    )
