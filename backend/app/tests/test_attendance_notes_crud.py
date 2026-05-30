import datetime as dt
import uuid

import pytest

from app import crud, schemas
from app.tests.factories import (
    make_attendance_note_create,
    make_student_create,
    make_user_create,
)


def _create_provider_and_student(db_session):
    provider = crud.create_user(
        db_session,
        user=make_user_create(email="notes_provider@example.com"),
    )
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Notes"),
    )
    return provider, student


def test_create_attendance_note_for_provider_student(db_session):
    provider, student = _create_provider_and_student(db_session)

    note = crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=make_attendance_note_create(
            student_public_id=student.public_id,
            attendance_date=dt.date(2026, 5, 30),
            note="Guardian called ahead.",
        ),
    )

    assert note.provider_id == provider.id
    assert note.student_id == student.id
    assert note.attendance_date == dt.date(2026, 5, 30)
    assert note.note == "Guardian called ahead."
    assert crud.get_attendance_note(db_session, note.id) == note
    assert crud.get_attendance_note_by_public_id(db_session, note.public_id) == note


def test_create_attendance_note_rejects_other_provider_student(db_session):
    provider = crud.create_user(
        db_session,
        user=make_user_create(email="notes_scope_provider@example.com"),
    )
    other_provider = crud.create_user(
        db_session,
        user=make_user_create(email="notes_scope_other_provider@example.com"),
    )
    other_student = crud.create_student(
        db_session,
        provider_id=other_provider.id,
        student=make_student_create(first_name="Other"),
    )

    with pytest.raises(ValueError):
        crud.create_attendance_note(
            db_session,
            provider_id=provider.id,
            note=make_attendance_note_create(
                student_public_id=other_student.public_id,
                attendance_date=dt.date(2026, 5, 30),
            ),
        )


def test_create_attendance_note_rejects_second_note_for_student_day(db_session):
    provider, student = _create_provider_and_student(db_session)
    note_create = make_attendance_note_create(
        student_public_id=student.public_id,
        attendance_date=dt.date(2026, 5, 30),
    )
    crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=note_create,
    )

    with pytest.raises(ValueError, match="Attendance note already exists"):
        crud.create_attendance_note(
            db_session,
            provider_id=provider.id,
            note=note_create,
        )


def test_list_and_get_attendance_note_for_day(db_session):
    provider, student = _create_provider_and_student(db_session)
    other_student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Other"),
    )
    note = crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=make_attendance_note_create(
            student_public_id=student.public_id,
            attendance_date=dt.date(2026, 5, 30),
            note="Primary note",
        ),
    )
    crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=make_attendance_note_create(
            student_public_id=other_student.public_id,
            attendance_date=dt.date(2026, 5, 30),
            note="Other note",
        ),
    )

    notes_for_student = crud.list_attendance_notes_for_day(
        db_session,
        provider_id=provider.id,
        attendance_date=dt.date(2026, 5, 30),
        student_public_id=student.public_id,
    )

    assert notes_for_student == [note]
    assert (
        crud.get_attendance_note_for_day(
            db_session,
            provider_id=provider.id,
            student_public_id=student.public_id,
            attendance_date=dt.date(2026, 5, 30),
        )
        == note
    )


def test_update_attendance_note_allows_text_change_and_clear(db_session):
    provider, student = _create_provider_and_student(db_session)
    note = crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=make_attendance_note_create(
            student_public_id=student.public_id,
            attendance_date=dt.date(2026, 5, 30),
            note="Original note",
        ),
    )

    crud.update_attendance_note(
        db_session,
        note,
        schemas.AttendanceLogNoteUpdate(note="Updated note"),
    )
    assert note.note == "Updated note"

    crud.update_attendance_note(
        db_session,
        note,
        schemas.AttendanceLogNoteUpdate(note=None),
    )
    assert note.note is None


def test_delete_attendance_note_removes_record(db_session):
    provider, student = _create_provider_and_student(db_session)
    note = crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=make_attendance_note_create(
            student_public_id=student.public_id,
            attendance_date=dt.date(2026, 5, 30),
        ),
    )
    note_id = note.id

    crud.delete_attendance_note(db_session, note)

    assert crud.get_attendance_note(db_session, note_id) is None


def test_delete_student_rejects_retained_attendance_note(db_session):
    provider, student = _create_provider_and_student(db_session)
    crud.create_attendance_note(
        db_session,
        provider_id=provider.id,
        note=make_attendance_note_create(
            student_public_id=student.public_id,
            attendance_date=dt.date(2026, 5, 30),
        ),
    )

    with pytest.raises(ValueError, match="retained attendance records"):
        crud.delete_student(db_session, student)


def test_attendance_note_missing_lookups_return_none(db_session):
    assert crud.get_attendance_note(db_session, attendance_note_id=999999) is None
    assert crud.get_attendance_note_by_public_id(db_session, uuid.uuid4()) is None
