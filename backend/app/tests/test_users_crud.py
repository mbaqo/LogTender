import uuid
import pytest

from sqlalchemy.exc import IntegrityError

from app import crud, schemas
from app.enums import UserRole



def test_create_user_persists_and_hashes_secrets(db_session):
    user_in = schemas.UserCreate(
        email="user_test_1@example.com",
        first_name="John",
        last_name="Smith",
        profile_picture=None,
        role=UserRole.PROVIDER,
        facility_name="Daycare LLC",
        facility_address="123 Test St",
        license_number=None,
        password="testpassword",
        pin="12145",
    )

    user = crud.create_user(db_session, user=user_in)

    assert user.id is not None
    assert isinstance(user.public_id, uuid.UUID)
    assert user.email == user_in.email

    assert user.hashed_password != user_in.password
    assert user.hashed_pin != user_in.pin


def test_duplicate_email_raises_integrityerror_on_commit(db_session):
    user_in_1 = schemas.UserCreate(
        email="dupe@example.com",
        first_name="A",
        last_name="B",
        profile_picture=None,
        role=UserRole.PROVIDER,
        facility_name="X",
        facility_address=None,
        license_number=None,
        password="testpassword",
        pin="12145",
    )
    crud.create_user(db_session, user=user_in_1)
    db_session.commit()

    user_in_2 = schemas.UserCreate(
        email="dupe@example.com",
        first_name="C",
        last_name="D",
        profile_picture=None,
        role=UserRole.PROVIDER,
        facility_name="Y",
        facility_address=None,
        license_number=None,
        password="testpassword",
        pin="99999",
    )
    # create_user() flushes, so the constraint violation is raised on flush,
    # not necessarily on commit.
    with pytest.raises(IntegrityError):
        crud.create_user(db_session, user=user_in_2)

    # Reset session state after expected DB error so teardown is clean.
    db_session.rollback()
