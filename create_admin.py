from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.utils.hashing import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

existing_admin = db.query(User).filter(User.email == "admin@gmail.com").first()

if existing_admin:
    print("Admin already exists")
else:
    admin = User(
        full_name="Super Admin",
        email="admin@gmail.com",
        username="admin",
        password=hash_password("admin123"),
        role="admin"
    )

    db.add(admin)
    db.commit()
    print("Admin created successfully")

db.close()
