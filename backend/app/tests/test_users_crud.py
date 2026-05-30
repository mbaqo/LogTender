import uuid

import bcrypt
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app import crud
from app import schemas
from app.enums import UserRole
from app.tests.factories import make_student_create, make_user_create


def test_create_user_persists_and_hashes_secrets(db_session):
    user_in = make_user_create(email="user_test_1@example.com")

    user = crud.create_user(db_session, user=user_in)

    assert user.id is not None
    assert user.email == user_in.email
    assert bcrypt.checkpw(
        user_in.password.encode("utf-8"),
        user.hashed_password.encode("utf-8"),
    )
    assert bcrypt.checkpw(
        user_in.pin.encode("utf-8"),
        user.hashed_pin.encode("utf-8"),
    )
    assert user.hashed_password != user.hashed_pin


def test_create_user_generates_unique_public_ids(db_session):
    first_user = crud.create_user(
        db_session,
        user=make_user_create(email="first_public_id@example.com"),
    )
    second_user = crud.create_user(
        db_session,
        user=make_user_create(email="second_public_id@example.com"),
    )

    assert isinstance(first_user.public_id, uuid.UUID)
    assert isinstance(second_user.public_id, uuid.UUID)
    assert first_user.public_id != second_user.public_id


def test_create_user_normalizes_email(db_session):
    user_in = make_user_create(email="Mixed.Case@Example.COM")

    user = crud.create_user(db_session, user=user_in)

    assert user_in.email == "mixed.case@example.com"
    assert user.email == "mixed.case@example.com"


def test_verify_secret_accepts_matching_plain_secret():
    hashed = crud.hash_secret("testpassword")

    assert crud.verify_secret("testpassword", hashed) is True


def test_verify_secret_rejects_wrong_plain_secret():
    hashed = crud.hash_secret("testpassword")

    assert crud.verify_secret("wrongpassword", hashed) is False


def test_get_user_returns_user_by_internal_id(db_session):
    created_user = crud.create_user(
        db_session,
        user=make_user_create(email="get_by_id@example.com"),
    )

    user = crud.get_user(db_session, user_id=created_user.id)

    assert user == created_user


def test_get_user_by_public_id_returns_user(db_session):
    created_user = crud.create_user(
        db_session,
        user=make_user_create(email="get_by_public_id@example.com"),
    )

    user = crud.get_user_by_public_id(db_session, public_id=created_user.public_id)

    assert user == created_user


def test_get_user_by_email_returns_user(db_session):
    user_in = make_user_create(email="get_by_email@example.com")
    created_user = crud.create_user(db_session, user=user_in)

    user = crud.get_user_by_email(db_session, email=user_in.email)

    assert user == created_user


def test_get_user_by_email_normalizes_lookup_input(db_session):
    created_user = crud.create_user(
        db_session,
        user=make_user_create(email="lookup_normalized@example.com"),
    )

    user = crud.get_user_by_email(db_session, email="LOOKUP_NORMALIZED@EXAMPLE.COM")

    assert user == created_user


def test_get_user_by_email_finds_mixed_case_registration(db_session):
    crud.create_user(db_session, user=make_user_create(email="MixedCase@Ex.com"))

    user = crud.get_user_by_email(db_session, email="mixedcase@ex.com")

    assert user is not None


def test_list_users_returns_ordered_page(db_session):
    crud.create_user(
        db_session,
        user=make_user_create(
            email="z-last@example.com",
            first_name="Zoe",
            last_name="Zimmer",
        ),
    )
    first_user = crud.create_user(
        db_session,
        user=make_user_create(
            email="a-last@example.com",
            first_name="Ana",
            last_name="Adams",
        ),
    )

    users = crud.list_users(db_session, offset=0, limit=1)

    assert users == [first_user]


def test_update_user_profile_updates_only_provided_fields(db_session):
    user = crud.create_user(
        db_session,
        user=make_user_create(
            email="profile_update@example.com",
            first_name="Before",
            last_name="Person",
        ),
    )

    updated = crud.update_user_profile(
        db_session,
        user,
        schemas.UserUpdateProfile(
            first_name="After",
            role=UserRole.EMPLOYEE,
            facility_name="Updated Facility",
        ),
    )

    assert updated.first_name == "After"
    assert updated.last_name == "Person"
    assert updated.role == UserRole.EMPLOYEE
    assert updated.facility_name == "Updated Facility"


def test_update_user_email_normalizes_and_persists(db_session):
    user = crud.create_user(
        db_session,
        user=make_user_create(email="email_update@example.com"),
    )

    updated = crud.update_user_email(
        db_session,
        user,
        schemas.UserUpdateEmail(email="NEW.EMAIL@EXAMPLE.COM"),
    )

    assert updated.email == "new.email@example.com"
    assert crud.get_user_by_email(db_session, "new.email@example.com") == user


def test_update_user_password_rehashes_secret(db_session):
    user = crud.create_user(
        db_session,
        user=make_user_create(email="password_update@example.com"),
    )
    original_hash = user.hashed_password

    crud.update_user_password(
        db_session,
        user,
        schemas.UserUpdatePassword(password="newpassword"),
    )

    assert user.hashed_password != original_hash
    assert crud.verify_secret("newpassword", user.hashed_password) is True
    assert crud.verify_secret("testpassword", user.hashed_password) is False


def test_update_user_pin_rehashes_pin(db_session):
    user = crud.create_user(
        db_session,
        user=make_user_create(email="pin_update@example.com"),
    )
    original_hash = user.hashed_pin

    crud.update_user_pin(db_session, user, schemas.UserUpdatePin(pin="99999"))

    assert user.hashed_pin != original_hash
    assert crud.verify_secret("99999", user.hashed_pin) is True
    assert crud.verify_secret("12145", user.hashed_pin) is False


def test_delete_user_removes_user_without_related_rows(db_session):
    user = crud.create_user(
        db_session,
        user=make_user_create(email="delete_user@example.com"),
    )
    user_id = user.id

    crud.delete_user(db_session, user)

    assert crud.get_user(db_session, user_id=user_id) is None


def test_delete_user_rejects_retained_provider_records(db_session):
    user = crud.create_user(
        db_session,
        user=make_user_create(email="delete_user_with_student@example.com"),
    )
    crud.create_student(
        db_session,
        provider_id=user.id,
        student=make_student_create(),
    )

    with pytest.raises(ValueError, match="retained provider records"):
        crud.delete_user(db_session, user)


def test_get_user_returns_none_when_missing(db_session):
    assert crud.get_user(db_session, user_id=999999) is None


def test_get_user_by_public_id_returns_none_when_missing(db_session):
    assert crud.get_user_by_public_id(db_session, public_id=uuid.uuid4()) is None


def test_get_user_by_email_returns_none_when_missing(db_session):
    assert crud.get_user_by_email(db_session, email="missing@example.com") is None


def test_duplicate_email_raises_integrityerror_on_commit(db_session):
    crud.create_user(db_session, user=make_user_create(email="dupe@example.com"))
    db_session.commit()

    with pytest.raises(IntegrityError):
        crud.create_user(
            db_session,
            user=make_user_create(email="dupe@example.com", pin="99999"),
        )

    # Reset session state after expected DB error so teardown is clean.
    db_session.rollback()


def test_user_pin_letters_rejected():
    with pytest.raises(ValidationError):
        make_user_create(pin="abcde")


def test_user_pin_too_short_rejected():
    with pytest.raises(ValidationError):
        make_user_create(pin="1234")


def test_user_pin_too_long_rejected():
    with pytest.raises(ValidationError):
        make_user_create(pin="123456")


def test_user_password_too_short_rejected():
    with pytest.raises(ValidationError):
        make_user_create(password="short")


def test_user_invalid_email_rejected():
    with pytest.raises(ValidationError):
        make_user_create(email="not-an-email")
