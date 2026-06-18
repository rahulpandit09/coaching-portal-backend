from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin.notification import Notification
from app.schemas.admin.notification import NotificationCreate

router = APIRouter(prefix="/admin/notifications", tags=["Admin Notifications"])


# CREATE NOTIFICATION
@router.post("/")
def create_notification(data: NotificationCreate, db: Session = Depends(get_db)):

    notification = Notification(
        title=data.title,
        message=data.message,
        role=data.role,
        user_id=data.user_id,
        batch_id=data.batch_id,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return {"message": "Notification created successfully"}

@router.get("/student/{student_id}")
def get_student_notifications(student_id: int, db: Session = Depends(get_db)):
    
    notifications = db.query(Notification).filter(
        (Notification.role == "student") |
        (Notification.user_id == student_id)
    ).order_by(Notification.created_at.desc()).all()

    return notifications