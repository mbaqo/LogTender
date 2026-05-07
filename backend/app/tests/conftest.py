import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool


def _get_test_database_url() -> str:
    """
    Prefer DATABASE_URL_TEST for isolation.

    Safety: we refuse to run against DATABASE_URL unless you explicitly opt in
    by setting ALLOW_TESTS_ON_DATABASE_URL=1.
    """
    url_test = os.getenv("DATABASE_URL_TEST")
    if url_test:
        return url_test

    url_default = os.getenv("DATABASE_URL")
    if not url_default:
        pytest.skip(
            "No DATABASE_URL_TEST or DATABASE_URL set. "
            "Set DATABASE_URL_TEST to an empty Postgres test database."
        )

    if os.getenv("ALLOW_TESTS_ON_DATABASE_URL") != "1":
        pytest.skip(
            "Refusing to run tests against DATABASE_URL. "
            "Set DATABASE_URL_TEST to a dedicated test database, or set "
            "ALLOW_TESTS_ON_DATABASE_URL=1 if you understand the risk."
        )

    return url_default


@pytest.fixture(scope="session")
def engine():
    """
    Session-scoped Engine for the dedicated test database.

    NullPool avoids cross-test connection reuse issues when using nested tx.
    """
    database_url = _get_test_database_url()

    # Ensure app config loads with a database URL even when .env is absent.
    os.environ.setdefault("DATABASE_URL", database_url)

    eng = create_engine(database_url, poolclass=NullPool)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def create_test_schema(engine):
    """
    Create/drop tables once per test session.

    If you prefer per-test schema isolation later, move create/drop into the
    db_session fixture.
    """
    from app.database import Base  # imported after env is set
    from app import models  # noqa: F401  (register models with Base)

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(engine):
    """
    Function-scoped SQLAlchemy Session wrapped in a transaction.

    Pattern:
    - Begin an outer transaction on a dedicated connection
    - Open a SAVEPOINT via begin_nested()
    - Roll back outer transaction at end of test for isolation
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(bind=connection, class_=Session, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    # Enable code-under-test to call session.commit() without breaking isolation.
    nested = session.begin_nested()

    from sqlalchemy import event

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = sess.begin_nested()

    try:
        yield session
    finally:
        # If a test hit an IntegrityError (or similar), the Session is left in a
        # failed transaction state until rollback() is called. Ensure we reset
        # it before closing, otherwise teardown can emit warnings/errors.
        try:
            session.rollback()
        except Exception:
            # Best-effort cleanup; outer transaction rollback below will still
            # ensure DB isolation.
            pass
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
