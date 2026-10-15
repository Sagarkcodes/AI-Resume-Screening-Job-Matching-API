from sqlalchemy import text

from app.db.session import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user, version()")
        )

        database, user, version = result.fetchone()

    assert database == "resume_matcher"
    assert user is not None
    assert "PostgreSQL" in version