from app.database import SessionLocal, Base, engine

# IMPORTANT: import ALL models so SQLAlchemy registers them
from app.models import user, course as course_model, lecture, enrollment, test, result
from app.models.Student.RegistrationForm import RegistrationStudent

from app.models.user import User
from app.utils.hashing import hash_password

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
