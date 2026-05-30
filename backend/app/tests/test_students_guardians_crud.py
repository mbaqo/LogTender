import uuid

import pytest
from pydantic_extra_types.phone_numbers import PhoneNumber

from app import crud, schemas
from app.tests.factories import (
    make_guardian_create,
    make_guardian_link_create,
    make_student_create,
    make_student_link_create,
    make_user_create,
)


def _create_provider(db_session, *, email: str = "provider@example.com"):
    return crud.create_user(db_session, user=make_user_create(email=email))


def test_create_student_links_existing_guardian(db_session):
    provider = _create_provider(db_session, email="student_links_provider@example.com")
    guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="student_link_guardian@example.com"),
    )

    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(
            guardian_links=[
                make_guardian_link_create(
                    guardian_public_id=guardian.public_id,
                    relationship_to_student="mother",
                )
            ]
        ),
    )

    link = crud.get_student_guardian_link(
        db_session, student_id=student.id, guardian_id=guardian.id
    )
    assert student.provider_id == provider.id
    assert link is not None
    assert link.relationship_to_student == "mother"


def test_create_student_rejects_missing_guardian_before_insert(db_session):
    provider = _create_provider(db_session, email="missing_guardian_provider@example.com")

    with pytest.raises(ValueError):
        crud.create_student(
            db_session,
            provider_id=provider.id,
            student=make_student_create(
                first_name="ShouldNotPersist",
                guardian_links=[
                    make_guardian_link_create(guardian_public_id=uuid.uuid4())
                ],
            ),
        )

    assert crud.list_students_for_provider(db_session, provider_id=provider.id) == []


def test_create_guardian_links_existing_student(db_session):
    provider = _create_provider(db_session, email="guardian_links_provider@example.com")
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Linked"),
    )

    guardian = crud.create_guardian(
        db_session,
        provider_id=provider.id,
        guardian=make_guardian_create(
            email="guardian_linked@example.com",
            student_links=[
                make_student_link_create(
                    student_public_id=student.public_id,
                    relationship_to_student="father",
                )
            ],
        ),
    )

    link = crud.get_student_guardian_link(
        db_session, student_id=student.id, guardian_id=guardian.id
    )
    assert link is not None
    assert link.relationship_to_student == "father"


def test_create_guardian_rejects_other_provider_student(db_session):
    provider = _create_provider(db_session, email="owner_provider@example.com")
    other_provider = _create_provider(db_session, email="other_provider@example.com")
    other_student = crud.create_student(
        db_session,
        provider_id=other_provider.id,
        student=make_student_create(first_name="Other"),
    )

    with pytest.raises(ValueError):
        crud.create_guardian(
            db_session,
            provider_id=provider.id,
            guardian=make_guardian_create(
                email="bad_cross_provider_guardian@example.com",
                student_links=[
                    make_student_link_create(student_public_id=other_student.public_id)
                ],
            ),
        )

    assert (
        crud.get_guardian_by_email(db_session, "bad_cross_provider_guardian@example.com")
        is None
    )


def test_list_students_for_provider_scopes_results(db_session):
    provider = _create_provider(db_session, email="list_students_provider@example.com")
    other_provider = _create_provider(
        db_session, email="list_students_other_provider@example.com"
    )
    provider_student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(last_name="Alpha"),
    )
    crud.create_student(
        db_session,
        provider_id=other_provider.id,
        student=make_student_create(last_name="Beta"),
    )

    students = crud.list_students_for_provider(db_session, provider_id=provider.id)

    assert students == [provider_student]


def test_list_guardians_for_provider_scopes_through_student_links(db_session):
    provider = _create_provider(db_session, email="list_guardians_provider@example.com")
    other_provider = _create_provider(
        db_session, email="list_guardians_other_provider@example.com"
    )
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Scoped"),
    )
    other_student = crud.create_student(
        db_session,
        provider_id=other_provider.id,
        student=make_student_create(first_name="Other"),
    )
    guardian = crud.create_guardian(
        db_session,
        provider_id=provider.id,
        guardian=make_guardian_create(
            email="scoped_guardian@example.com",
            student_links=[
                make_student_link_create(student_public_id=student.public_id)
            ],
        ),
    )
    crud.create_guardian(
        db_session,
        provider_id=other_provider.id,
        guardian=make_guardian_create(
            email="other_scoped_guardian@example.com",
            phone_number="+14155552672",
            student_links=[
                make_student_link_create(student_public_id=other_student.public_id)
            ],
        ),
    )

    guardians = crud.list_guardians_for_provider(db_session, provider_id=provider.id)

    assert guardians == [guardian]


def test_update_student_and_medical_note(db_session):
    provider = _create_provider(db_session, email="update_student_provider@example.com")
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Before", medical_note="Old note"),
    )

    crud.update_student(
        db_session,
        student,
        schemas.StudentUpdate(first_name="After", nickname="Updated Nickname"),
    )
    crud.update_student_medical_note(
        db_session,
        student,
        schemas.StudentUpdateMedicalNote(medical_note="Updated medical note"),
    )

    assert student.first_name == "After"
    assert student.nickname == "Updated Nickname"
    assert student.medical_note == "Updated medical note"


def test_update_guardian_normalizes_email_and_phone(db_session):
    guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="before_guardian@example.com"),
    )

    crud.update_guardian(
        db_session,
        guardian,
        schemas.GuardianUpdate(
            email="AFTER_GUARDIAN@EXAMPLE.COM",
            phone_number=PhoneNumber("+14155552673"),
            first_name="Updated",
        ),
    )

    assert guardian.email == "after_guardian@example.com"
    assert guardian.phone_number == "tel:+1-415-555-2673"
    assert guardian.first_name == "Updated"
    assert crud.get_guardian_by_email(db_session, "after_guardian@example.com") == guardian
    assert crud.get_guardian_by_phone_number(db_session, "+14155552673") == guardian


def test_phone_lookup_returns_all_guardians_when_household_number_is_shared(db_session):
    first_guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="shared_phone_one@example.com"),
    )
    second_guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="shared_phone_two@example.com"),
    )

    guardians = crud.list_guardians_by_phone_number(db_session, "+14155552671")

    assert guardians == [first_guardian, second_guardian]
    with pytest.raises(ValueError, match="Multiple guardians"):
        crud.get_guardian_by_phone_number(db_session, "+14155552671")


def test_link_student_guardian_updates_existing_relationship(db_session):
    provider = _create_provider(db_session, email="link_update_provider@example.com")
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(),
    )
    guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="link_update_guardian@example.com"),
    )

    first_link = crud.link_student_guardian(
        db_session,
        student=student,
        guardian=guardian,
        relationship_to_student="aunt",
    )
    second_link = crud.link_student_guardian(
        db_session,
        student=student,
        guardian=guardian,
        relationship_to_student="guardian",
    )

    assert second_link == first_link
    assert second_link.relationship_to_student == "guardian"


def test_unlink_student_guardian_returns_status(db_session):
    provider = _create_provider(db_session, email="unlink_provider@example.com")
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(),
    )
    guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="unlink_guardian@example.com"),
    )
    crud.link_student_guardian(
        db_session,
        student=student,
        guardian=guardian,
        relationship_to_student="guardian",
    )

    assert crud.unlink_student_guardian(
        db_session, student=student, guardian=guardian
    ) is True
    assert crud.unlink_student_guardian(
        db_session, student=student, guardian=guardian
    ) is False


def test_delete_student_removes_guardian_links_without_attendance_history(db_session):
    provider = _create_provider(db_session, email="delete_linked_student_provider@example.com")
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(),
    )
    guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(email="delete_linked_student_guardian@example.com"),
    )
    crud.link_student_guardian(
        db_session,
        student=student,
        guardian=guardian,
        relationship_to_student="guardian",
    )
    student_id = student.id

    crud.delete_student(db_session, student)

    assert crud.get_student(db_session, student_id) is None
    assert (
        crud.get_student_guardian_link(
            db_session,
            student_id=student_id,
            guardian_id=guardian.id,
        )
        is None
    )


def test_update_guardian_student_links_adds_and_removes(db_session):
    provider = _create_provider(db_session, email="links_update_provider@example.com")
    first_student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="First"),
    )
    second_student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Second"),
    )
    guardian = crud.create_guardian(
        db_session,
        provider_id=provider.id,
        guardian=make_guardian_create(
            email="links_update_guardian@example.com",
            student_links=[
                make_student_link_create(student_public_id=first_student.public_id)
            ],
        ),
    )

    crud.update_guardian_student_links(
        db_session,
        guardian=guardian,
        provider_id=provider.id,
        relationship_to_student="emergency contact",
        links_update=schemas.GuardianStudentLinksUpdate(
            add_student_public_ids=[second_student.public_id],
            remove_student_public_ids=[first_student.public_id],
        ),
    )

    assert (
        crud.get_student_guardian_link(
            db_session, student_id=first_student.id, guardian_id=guardian.id
        )
        is None
    )
    second_link = crud.get_student_guardian_link(
        db_session, student_id=second_student.id, guardian_id=guardian.id
    )
    assert second_link is not None
    assert second_link.relationship_to_student == "emergency contact"


def test_student_and_guardian_missing_lookups_return_none(db_session):
    assert crud.get_student(db_session, student_id=999999) is None
    assert crud.get_student_by_public_id(db_session, uuid.uuid4()) is None
    assert crud.get_guardian(db_session, guardian_id=999999) is None
    assert crud.get_guardian_by_public_id(db_session, uuid.uuid4()) is None
