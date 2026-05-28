import uuid

import bcrypt
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app import crud
from app.tests.factories import make_user_create


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
