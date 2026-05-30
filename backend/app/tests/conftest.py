import os
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.pool import StaticPool


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

# Keep tests importable even when a developer has not created a local .env yet.
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "logtender_test")
os.environ.setdefault("BCRYPT_ROUNDS", "4")


_DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST")
if not _DATABASE_URL_TEST:
    raise RuntimeError(
        "DATABASE_URL_TEST is required for backend tests. "
        "Point it at a dedicated PostgreSQL test database."
    )

# Make the application import the same test database URL the test suite uses.
os.environ["DATABASE_URL"] = _DATABASE_URL_TEST


def _get_test_database_url() -> str:
    """
    Require a dedicated PostgreSQL test database.

    The test suite must not silently fall back to SQLite because that can hide
    Postgres-specific behavior and make the suite look green against the wrong
    storage engine.
    """
    return _DATABASE_URL_TEST


@pytest.fixture(scope="session")
def engine():
    """
    Session-scoped Engine for the dedicated test database.

    NullPool avoids cross-test connection reuse issues when using nested tx.
    """
    database_url = _get_test_database_url()

    # Ensure app config loads with a database URL even when .env is absent.
    os.environ["DATABASE_URL"] = database_url

    if database_url.startswith("sqlite"):
        eng = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
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

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        pytest.skip(f"Test database is not reachable: {exc}")
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
