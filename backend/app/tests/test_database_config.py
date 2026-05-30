import os

from sqlalchemy import text
from sqlalchemy.engine import make_url


def test_db_session_uses_database_url_test(db_session):
    expected = make_url(os.environ["DATABASE_URL_TEST"])

    current_database, current_user = db_session.execute(
        text("select current_database(), current_user")
    ).one()

    assert current_database == expected.database
    assert current_user == expected.username
