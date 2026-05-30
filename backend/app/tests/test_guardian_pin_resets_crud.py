import datetime as dt
import uuid

import pytest

from app import crud
from app.enums import ResetStatuses
from app.tests.factories import (
    make_guardian_create,
    make_guardian_pin_reset_request,
    make_student_create,
    make_student_link_create,
    make_user_create,
)


def _pin_reset_setup(db_session, *, provider_email: str = "reset_provider@example.com"):
    provider = crud.create_user(db_session, user=make_user_create(email=provider_email))
    student = crud.create_student(
        db_session,
        provider_id=provider.id,
        student=make_student_create(first_name="Reset"),
    )
    guardian = crud.create_guardian(
        db_session,
        provider_id=provider.id,
        guardian=make_guardian_create(
            email=f"reset_guardian_{provider.id}@example.com",
            student_links=[
                make_student_link_create(student_public_id=student.public_id)
            ],
        ),
    )
    return provider, student, guardian


def _now() -> dt.datetime:
    return dt.datetime(2026, 5, 30, 12, 0, tzinfo=dt.UTC)


def test_create_guardian_pin_reset_hashes_code_and_sets_pending(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="create_reset_provider@example.com"
    )

    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )

    assert reset.status == ResetStatuses.PENDING
    assert reset.requested_by_user_id == provider.id
    assert reset.guardian_id == guardian.id
    assert reset.reset_code_hash != "12345"
    assert crud.verify_secret("12345", reset.reset_code_hash) is True
    assert guardian.requires_pin_reset is True
    assert crud.get_guardian_pin_reset(db_session, reset.id) == reset
    assert crud.get_guardian_pin_reset_by_public_id(db_session, reset.public_id) == reset


def test_create_guardian_pin_reset_rejects_unlinked_guardian(db_session):
    provider, _student, _guardian = _pin_reset_setup(
        db_session, provider_email="unlinked_reset_provider@example.com"
    )
    unlinked_guardian = crud.create_guardian(
        db_session,
        guardian=make_guardian_create(
            email="unlinked_reset_guardian@example.com",
            phone_number="+14155552679",
        ),
    )

    with pytest.raises(ValueError):
        crud.create_guardian_pin_reset(
            db_session,
            provider_id=provider.id,
            reset_request=make_guardian_pin_reset_request(
                guardian_public_id=unlinked_guardian.public_id
            ),
            reset_code="12345",
            now=_now(),
        )


def test_verify_guardian_pin_reset_rejects_wrong_code(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="wrong_code_reset_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )

    result = crud.verify_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        code="99999",
        now=_now(),
    )

    assert result is None
    assert reset.status == ResetStatuses.PENDING
    assert reset.failed_verification_attempts == 1
    assert reset.verified_at is None


def test_verify_guardian_pin_reset_rejects_expired_code(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="expired_reset_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        expires_at=_now() + dt.timedelta(minutes=1),
        now=_now(),
    )

    result = crud.verify_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        code="12345",
        now=_now() + dt.timedelta(minutes=2),
    )

    assert result is None
    assert reset.status == ResetStatuses.PENDING


def test_verify_guardian_pin_reset_sets_verified_status(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="verify_reset_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )

    verified_reset = crud.verify_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        code="12345",
        now=_now() + dt.timedelta(minutes=2),
    )

    assert verified_reset == reset
    assert reset.status == ResetStatuses.VERIFIED
    assert reset.verified_at == _now() + dt.timedelta(minutes=2)


def test_verify_guardian_pin_reset_locks_after_attempt_limit(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="locked_reset_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )

    for attempt in range(2):
        assert (
            crud.verify_guardian_pin_reset(
                db_session,
                reset_public_id=reset.public_id,
                code="99999",
                now=_now() + dt.timedelta(minutes=attempt),
                max_failed_attempts=2,
            )
            is None
        )

    assert reset.failed_verification_attempts == 2
    assert reset.status == ResetStatuses.LOCKED
    assert reset.locked_at == _now() + dt.timedelta(minutes=1)
    assert (
        crud.verify_guardian_pin_reset(
            db_session,
            reset_public_id=reset.public_id,
            code="12345",
            now=_now() + dt.timedelta(minutes=2),
            max_failed_attempts=2,
        )
        is None
    )


def test_complete_guardian_pin_reset_requires_verified_reset(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="complete_requires_verified_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )

    result = crud.complete_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        new_pin="77777",
        now=_now() + dt.timedelta(minutes=3),
    )

    assert result is None
    assert crud.verify_secret("77777", guardian.hashed_pin) is False


def test_complete_guardian_pin_reset_updates_pin_and_audit_fields(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="complete_reset_provider@example.com"
    )
    guardian.failed_pin_attempts = 4
    guardian.pin_locked_until = _now() + dt.timedelta(minutes=5)
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )
    crud.verify_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        code="12345",
        now=_now() + dt.timedelta(minutes=1),
    )

    updated_guardian = crud.complete_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        new_pin="77777",
        now=_now() + dt.timedelta(minutes=2),
    )

    assert updated_guardian == guardian
    assert crud.verify_secret("77777", guardian.hashed_pin) is True
    assert guardian.requires_pin_reset is False
    assert guardian.failed_pin_attempts == 0
    assert guardian.pin_locked_until is None
    assert guardian.last_pin_reset_at == _now() + dt.timedelta(minutes=2)


def test_complete_guardian_pin_reset_is_single_use(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="single_use_reset_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        now=_now(),
    )
    crud.verify_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        code="12345",
        now=_now() + dt.timedelta(minutes=1),
    )

    first_completion = crud.complete_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        new_pin="77777",
        now=_now() + dt.timedelta(minutes=2),
    )
    second_completion = crud.complete_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        new_pin="88888",
        now=_now() + dt.timedelta(minutes=3),
    )

    assert first_completion == guardian
    assert reset.status == ResetStatuses.COMPLETED
    assert second_completion is None
    assert crud.verify_secret("77777", guardian.hashed_pin) is True
    assert crud.verify_secret("88888", guardian.hashed_pin) is False


def test_complete_guardian_pin_reset_rejects_expired_verified_reset(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="expired_complete_reset_provider@example.com"
    )
    reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="12345",
        expires_at=_now() + dt.timedelta(minutes=2),
        now=_now(),
    )
    crud.verify_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        code="12345",
        now=_now() + dt.timedelta(minutes=1),
    )

    result = crud.complete_guardian_pin_reset(
        db_session,
        reset_public_id=reset.public_id,
        new_pin="77777",
        now=_now() + dt.timedelta(minutes=3),
    )

    assert result is None
    assert crud.verify_secret("77777", guardian.hashed_pin) is False


def test_list_guardian_pin_resets_for_guardian(db_session):
    provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="list_resets_provider@example.com"
    )
    first_reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="11111",
        now=_now(),
    )
    second_reset = crud.create_guardian_pin_reset(
        db_session,
        provider_id=provider.id,
        reset_request=make_guardian_pin_reset_request(
            guardian_public_id=guardian.public_id
        ),
        reset_code="22222",
        now=_now() + dt.timedelta(minutes=1),
    )

    resets = crud.list_guardian_pin_resets_for_guardian(
        db_session, guardian_id=guardian.id
    )

    assert resets == [second_reset, first_reset]


def test_verify_guardian_pin_resets_failures_and_locks(db_session):
    _provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="pin_attempts_provider@example.com"
    )

    assert (
        crud.verify_guardian_pin(
            db_session,
            guardian=guardian,
            pin="00000",
            now=_now(),
            max_failed_attempts=2,
            lock_minutes=10,
        )
        is False
    )
    assert guardian.failed_pin_attempts == 1
    assert guardian.pin_locked_until is None

    assert (
        crud.verify_guardian_pin(
            db_session,
            guardian=guardian,
            pin="00000",
            now=_now(),
            max_failed_attempts=2,
            lock_minutes=10,
        )
        is False
    )
    assert guardian.failed_pin_attempts == 2
    assert guardian.pin_locked_until == _now() + dt.timedelta(minutes=10)

    assert (
        crud.verify_guardian_pin(
            db_session,
            guardian=guardian,
            pin="54321",
            now=_now() + dt.timedelta(minutes=1),
            max_failed_attempts=2,
            lock_minutes=10,
        )
        is False
    )


def test_verify_guardian_pin_success_clears_previous_failures(db_session):
    _provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="pin_success_provider@example.com"
    )
    guardian.failed_pin_attempts = 1
    guardian.pin_locked_until = _now() - dt.timedelta(minutes=1)

    assert (
        crud.verify_guardian_pin(
            db_session,
            guardian=guardian,
            pin="54321",
            now=_now(),
            max_failed_attempts=2,
            lock_minutes=10,
        )
        is True
    )
    assert guardian.failed_pin_attempts == 0
    assert guardian.pin_locked_until is None


def test_expired_guardian_pin_lock_starts_a_fresh_attempt_window(db_session):
    _provider, _student, guardian = _pin_reset_setup(
        db_session, provider_email="pin_expired_lock_provider@example.com"
    )
    guardian.failed_pin_attempts = 2
    guardian.pin_locked_until = _now() - dt.timedelta(minutes=1)

    assert (
        crud.verify_guardian_pin(
            db_session,
            guardian=guardian,
            pin="00000",
            now=_now(),
            max_failed_attempts=2,
            lock_minutes=10,
        )
        is False
    )
    assert guardian.failed_pin_attempts == 1
    assert guardian.pin_locked_until is None


def test_guardian_pin_reset_missing_lookup_returns_none(db_session):
    assert crud.get_guardian_pin_reset(db_session, reset_id=999999) is None
    assert crud.get_guardian_pin_reset_by_public_id(db_session, uuid.uuid4()) is None
