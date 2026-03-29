from backend.app.database import SessionLocal, engine
from backend.app import crud, schemas, models
from backend.app.enums import UserRole


def main() -> None:
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user_in = schemas.UserCreate(
            email="usertest3@gmail.com",
            first_name="Johnnolicense",
            last_name="Smith",
            profile_picture="https://attendance-app-storage.s3.amazonaws.com/users/johndoe-avatar.jpg",
            role=UserRole.PROVIDER,
            facility_name="Daycare LLC.",
            facility_address="87899 76th Ave W",
            password="testpassword",
            pin="12145",
        )

        user = crud.create_user(db, user=user_in)
        db.commit()
        print("Created user:", user.id, user.email, user.public_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
