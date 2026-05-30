import datetime as dt
import uuid

import pytest

from app import crud
from app.enums import Actions, AttendanceStatus, EntryTypes
from app.tests.factories import (
    make_check_in_create,
    make_check_out_create,
    make_guardian_create,
    make_manual_attendance_create,
    make_mark_absent_create,
    make_attendance_correction,
    make_student_create,
    make_student_link_create,
    make_user_create,
)


def _attendance_setup(db_session, *, provider_email: str = "attendance_provider@example.com"):
    provider = crud.create_user(db_session, user=make_user_create(email=provider_email))
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Attendance"),
    )
    guardian = crud.create_guardian(
        db_session,
        provider_id=provider.id,
        guardian=make_guardian_create(
            email=f"guardian_{provider.id}@example.com",
            student_links=[
                make_student_link_create(
                    student_public_id=student.public_id,
                    relationship_to_student="guardian",
                )
            ],
        ),
    )
    return provider, student, guardian


def _at(hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime(2026, 5, 30, hour, minute, tzinfo=dt.UTC)


def test_attendance_status_defaults_to_can_check_in(db_session):
    provider, student, _guardian = _attendance_setup(
        db_session, provider_email="status_default_provider@example.com"
    )

    status = crud.get_attendance_day_status(
        db_session,
        provider_id=provider.id,
        student_public_id=student.public_id,
        attendance_date=dt.date(2026, 5, 30),
    )

    assert status.current_status == AttendanceStatus.CAN_CHECK_IN
    assert status.event_time is None


def test_guardian_check_in_records_auditable_log_and_updates_status(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="check_in_provider@example.com"
    )

    log = crud.create_attendance_check_in(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_in_create(student_public_id=student.public_id),
        event_time=_at(8, 15),
    )
    status = crud.get_attendance_day_status(
        db_session,
        provider_id=provider.id,
        student_public_id=student.public_id,
        attendance_date=dt.date(2026, 5, 30),
    )

    assert log.action == Actions.CHECK_IN
    assert log.entry_type == EntryTypes.GUARDIAN
    assert log.guardian_id == guardian.id
    assert log.authorized_person_name == "Gary Guardian"
    assert log.guardian_signature_url == "https://example.com/signature-in.png"
    assert status.current_status == AttendanceStatus.CAN_CHECK_OUT
    assert status.authorized_person_name == "Gary Guardian"


def test_check_out_after_check_in_returns_day_to_can_check_in(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="check_out_provider@example.com"
    )
    crud.create_attendance_check_in(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_in_create(student_public_id=student.public_id),
        event_time=_at(8),
    )

    log = crud.create_attendance_check_out(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_out_create(student_public_id=student.public_id),
        event_time=_at(16, 30),
    )
    status = crud.get_attendance_day_status(
        db_session,
        provider_id=provider.id,
        student_public_id=student.public_id,
        attendance_date=dt.date(2026, 5, 30),
    )

    assert log.action == Actions.CHECK_OUT
    assert status.current_status == AttendanceStatus.CAN_CHECK_IN


def test_local_evening_attendance_stays_on_local_day(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="local_evening_provider@example.com"
    )
    local_evening_in_utc = dt.datetime(2026, 5, 31, 2, 0, tzinfo=dt.UTC)

    log = crud.create_attendance_check_in(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_in_create(student_public_id=student.public_id),
        event_time=local_evening_in_utc,
    )

    assert crud.list_attendance_logs_for_day(
        db_session,
        provider_id=provider.id,
        attendance_date=dt.date(2026, 5, 30),
    ) == [log]
    assert crud.list_attendance_logs_for_day(
        db_session,
        provider_id=provider.id,
        attendance_date=dt.date(2026, 5, 31),
    ) == []


def test_check_out_before_check_in_is_rejected(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="checkout_before_checkin_provider@example.com"
    )

    with pytest.raises(ValueError):
        crud.create_attendance_check_out(
            db_session,
            provider_id=provider.id,
            guardian_id=guardian.id,
            attendance=make_check_out_create(student_public_id=student.public_id),
            event_time=_at(10),
        )


def test_duplicate_check_in_is_rejected(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="duplicate_checkin_provider@example.com"
    )
    crud.create_attendance_check_in(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_in_create(student_public_id=student.public_id),
        event_time=_at(8),
    )

    with pytest.raises(ValueError):
        crud.create_attendance_check_in(
            db_session,
            provider_id=provider.id,
            guardian_id=guardian.id,
            attendance=make_check_in_create(student_public_id=student.public_id),
            event_time=_at(9),
        )


def test_unlinked_guardian_cannot_record_attendance(db_session):
    provider, student, _guardian = _attendance_setup(
        db_session, provider_email="unlinked_guardian_provider@example.com"
    )
    unlinked_guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(
            email="unlinked_guardian@example.com",
            phone_number="+14155552678",
        ),
    )

    with pytest.raises(ValueError):
        crud.create_attendance_check_in(
            db_session,
            provider_id=provider.id,
            guardian_id=unlinked_guardian.id,
            attendance=make_check_in_create(student_public_id=student.public_id),
            event_time=_at(8),
        )


def test_provider_scope_blocks_other_provider_student_attendance(db_session):
    provider, _student, guardian = _attendance_setup(
        db_session, provider_email="scope_provider@example.com"
    )
    other_provider, other_student, _other_guardian = _attendance_setup(
        db_session, provider_email="scope_other_provider@example.com"
    )

    with pytest.raises(ValueError):
        crud.create_attendance_check_in(
            db_session,
            provider_id=provider.id,
            guardian_id=guardian.id,
            attendance=make_check_in_create(student_public_id=other_student.public_id),
            event_time=_at(8),
        )

    assert (
        crud.get_attendance_day_status(
            db_session,
            provider_id=other_provider.id,
            student_public_id=other_student.public_id,
            attendance_date=dt.date(2026, 5, 30),
        ).current_status
        == AttendanceStatus.CAN_CHECK_IN
    )


def test_mark_absent_sets_absent_status_and_blocks_attendance(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="absent_provider@example.com"
    )

    absent_log = crud.mark_student_absent(
        db_session,
        provider_id=provider.id,
        attendance=make_mark_absent_create(student_public_id=student.public_id),
        event_time=_at(7),
    )
    status = crud.get_attendance_day_status(
        db_session,
        provider_id=provider.id,
        student_public_id=student.public_id,
        attendance_date=dt.date(2026, 5, 30),
    )

    assert absent_log.action == Actions.ABSENT
    assert status.current_status == AttendanceStatus.IS_ABSENT
    with pytest.raises(ValueError):
        crud.create_attendance_check_in(
            db_session,
            provider_id=provider.id,
            guardian_id=guardian.id,
            attendance=make_check_in_create(student_public_id=student.public_id),
            event_time=_at(8),
        )


def test_absent_after_existing_attendance_is_rejected(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="absent_after_attendance_provider@example.com"
    )
    crud.create_attendance_check_in(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_in_create(student_public_id=student.public_id),
        event_time=_at(8),
    )

    with pytest.raises(ValueError):
        crud.mark_student_absent(
            db_session,
            provider_id=provider.id,
            attendance=make_mark_absent_create(student_public_id=student.public_id),
            event_time=_at(9),
        )


def test_manual_entries_accept_valid_chronological_sequence(db_session):
    provider, student, _guardian = _attendance_setup(
        db_session, provider_email="manual_sequence_provider@example.com"
    )

    check_in = crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=student.public_id,
            event_time=_at(8),
            action=Actions.CHECK_IN,
        ),
    )
    check_out = crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=student.public_id,
            event_time=_at(12),
            action=Actions.CHECK_OUT,
        ),
    )

    assert check_in.entry_type == EntryTypes.PROVIDER
    assert check_out.entry_type == EntryTypes.PROVIDER
    assert [
        log.action
        for log in crud.list_attendance_logs_for_day(
            db_session,
            provider_id=provider.id,
            attendance_date=dt.date(2026, 5, 30),
            student_public_id=student.public_id,
        )
    ] == [Actions.CHECK_IN, Actions.CHECK_OUT]


def test_manual_entry_rejects_sequence_that_would_be_invalid_when_sorted(db_session):
    provider, student, _guardian = _attendance_setup(
        db_session, provider_email="manual_invalid_provider@example.com"
    )
    crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=student.public_id,
            event_time=_at(9),
            action=Actions.CHECK_IN,
        ),
    )

    with pytest.raises(ValueError):
        crud.create_manual_attendance_entry(
            db_session,
            provider_id=provider.id,
            attendance=make_manual_attendance_create(
                student_public_id=student.public_id,
                event_time=_at(8),
                action=Actions.CHECK_OUT,
            ),
        )


def test_correction_voids_original_log_and_adds_replacement(db_session):
    provider, student, _guardian = _attendance_setup(
        db_session, provider_email="correction_provider@example.com"
    )
    original_log = crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=student.public_id,
            event_time=_at(8),
            action=Actions.CHECK_IN,
        ),
    )

    corrected_log = crud.correct_attendance_log(
        db_session,
        provider_id=provider.id,
        correction=make_attendance_correction(
            student_public_id=student.public_id,
            original_log_public_id=original_log.public_id,
            event_time=_at(8, 30),
            action=Actions.CHECK_IN,
        ),
    )
    active_logs = crud.list_attendance_logs_for_day(
        db_session,
        provider_id=provider.id,
        attendance_date=dt.date(2026, 5, 30),
        student_public_id=student.public_id,
    )
    all_logs = crud.list_attendance_logs_for_day(
        db_session,
        provider_id=provider.id,
        attendance_date=dt.date(2026, 5, 30),
        student_public_id=student.public_id,
        include_void=True,
    )

    assert original_log.is_void is True
    assert corrected_log.original_log_id == original_log.id
    assert active_logs == [corrected_log]
    assert all_logs == [original_log, corrected_log]


def test_correction_rejects_invalid_replacement_sequence(db_session):
    provider, student, _guardian = _attendance_setup(
        db_session, provider_email="bad_correction_provider@example.com"
    )
    check_in = crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=student.public_id,
            event_time=_at(8),
            action=Actions.CHECK_IN,
        ),
    )
    crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=student.public_id,
            event_time=_at(12),
            action=Actions.CHECK_OUT,
        ),
    )

    with pytest.raises(ValueError):
        crud.correct_attendance_log(
            db_session,
            provider_id=provider.id,
            correction=make_attendance_correction(
                student_public_id=student.public_id,
                original_log_public_id=check_in.public_id,
                event_time=_at(13),
                action=Actions.CHECK_IN,
            ),
        )

    assert check_in.is_void is False


def test_correction_rejects_move_that_breaks_original_student_sequence(db_session):
    provider, original_student, _guardian = _attendance_setup(
        db_session, provider_email="move_correction_provider@example.com"
    )
    corrected_student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Corrected"),
    )
    check_in = crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=original_student.public_id,
            event_time=_at(8),
            action=Actions.CHECK_IN,
        ),
    )
    crud.create_manual_attendance_entry(
        db_session,
        provider_id=provider.id,
        attendance=make_manual_attendance_create(
            student_public_id=original_student.public_id,
            event_time=_at(12),
            action=Actions.CHECK_OUT,
        ),
    )

    with pytest.raises(ValueError):
        crud.correct_attendance_log(
            db_session,
            provider_id=provider.id,
            correction=make_attendance_correction(
                student_public_id=corrected_student.public_id,
                original_log_public_id=check_in.public_id,
                event_time=_at(8),
                action=Actions.CHECK_IN,
            ),
        )

    assert check_in.is_void is False


def test_void_attendance_log_excludes_log_from_status(db_session):
    provider, student, guardian = _attendance_setup(
        db_session, provider_email="void_provider@example.com"
    )
    log = crud.create_attendance_check_in(
        db_session,
        provider_id=provider.id,
        guardian_id=guardian.id,
        attendance=make_check_in_create(student_public_id=student.public_id),
        event_time=_at(8),
    )

    crud.void_attendance_log(
        db_session,
        provider_id=provider.id,
        attendance_log_public_id=log.public_id,
    )
    status = crud.get_attendance_day_status(
        db_session,
        provider_id=provider.id,
        student_public_id=student.public_id,
        attendance_date=dt.date(2026, 5, 30),
    )

    assert log.is_void is True
    assert status.current_status == AttendanceStatus.CAN_CHECK_IN


def test_attendance_missing_lookups_return_none(db_session):
    assert crud.get_attendance_log(db_session, attendance_log_id=999999) is None
    assert crud.get_attendance_log_by_public_id(db_session, uuid.uuid4()) is None
