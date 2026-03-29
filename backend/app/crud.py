# Implement core CRUD for User, Student, Guardian, and link-table operations.
#   2. Add attendance CRUD/service functions next.
#      Include check-in, check-out, mark absent, manual entry, correction, and day-status queries.
#   3. Add guardian PIN reset CRUD flows.
#      Request reset, verify code, complete reset with new PIN.
#   4. Once CRUD is stable, initialize Alembic and create the first migration.
#   5. Then add Pytest with DB/session fixtures and smoke tests for the core CRUD paths.

# def create_user(db: Session, user: UserCreate):
#     """Creates a new user record in the database."""
#     fake_hashed_password = user.password + "notreallyhashed"
#     db_user = User(email=user.email, hashed_password=fake_hashed_password)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user

import bcrypt
from sqlalchemy.orm import Session

from . import models, schemas

def hash_pwd(password: str) -> str:
    pwd = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
    return pwd.decode("utf-8")

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email = user.email,
        first_name = user.first_name,
        last_name = user.last_name,
        profile_picture = user.profile_picture,
        role = user.role,
        facility_name = user.facility_name,
        facility_address = user.facility_address,
        license_number = user.license_number,
        hashed_password = hash_pwd(user.password),
        hashed_pin = hash_pwd(user.pin)
    )
    db.add(db_user)
    db.refresh(db_user)
    return db_user
