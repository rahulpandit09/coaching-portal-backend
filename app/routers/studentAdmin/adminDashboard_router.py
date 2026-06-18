from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
from app.database import SessionLocal
from app.models.admin.adminDashboard_model import adminDashboardStudent
from app.core.security import get_current_user
from sqlalchemy import text
from app.models.user import User
from app.database import get_db

router = APIRouter(
    prefix="/admin/adminDashboard_student",
    tags=["adminDashboard_student"]
)

@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):

    total_students = db.query(adminDashboardStudent).count()
    paid_students = db.query(adminDashboardStudent).filter(adminDashboardStudent.status == "paid").count()
    pending_students = db.query(adminDashboardStudent).filter(adminDashboardStudent.status == "pending").count()
    unpaid_students = db.query(adminDashboardStudent).filter(adminDashboardStudent.status == "unpaid").count()

    total_revenue = db.query(func.sum(adminDashboardStudent.fees)).scalar() or 0

    pending_amount = db.query(func.sum(adminDashboardStudent.fees))\
        .filter(adminDashboardStudent.status == "pending")\
        .scalar() or 0

    #  NEW: Month Revenue
    current_month = datetime.now().month
    month_revenue = db.query(func.sum(adminDashboardStudent.fees))\
        .filter(
            adminDashboardStudent.status == "paid",
            extract("month", adminDashboardStudent.created_at) == current_month
        ).scalar() or 0

    #  NEW: Today Revenue
    today = datetime.now().date()
    today_revenue = db.query(func.sum(adminDashboardStudent.fees))\
        .filter(
            adminDashboardStudent.status == "paid",
            func.date(adminDashboardStudent.created_at) == today
        ).scalar() or 0

    return {
        "totalStudents": total_students,
        "paidStudents": paid_students,
        "pendingStudents": pending_students,
        "unpaidStudents": unpaid_students,
        "totalRevenue": float(total_revenue),
        "pendingAmount": float(pending_amount),
        "monthRevenue": float(month_revenue),
        "todayRevenue": float(today_revenue)
    }


@router.get("/dashboard/course-distribution")
def course_distribution(db: Session = Depends(get_db)):

    result = (
        db.query(
            adminDashboardStudent.course,
            func.count(adminDashboardStudent.id).label("total")
        )
        .group_by(adminDashboardStudent.course)
        .all()
    )

    return [
        {"name": row.course, "value": row.total}
        for row in result
    ]


@router.get("/dashboard/student-growth")
def student_growth(db: Session = Depends(get_db)):

    result = (
        db.query(
            extract("month", adminDashboardStudent.created_at).label("month"),
            func.count(adminDashboardStudent.id).label("students")
        )
        .group_by(extract("month", adminDashboardStudent.created_at))
        .order_by(extract("month", adminDashboardStudent.created_at))
        .all()
    )

    return [
        {"month": f"Month {int(row.month)}", "students": row.students}
        for row in result
    ]


@router.get("/dashboard/revenue")
def monthly_revenue(db: Session = Depends(get_db)):

    result = (
        db.query(
            extract("month", adminDashboardStudent.created_at).label("month"),
            func.sum(adminDashboardStudent.fees).label("revenue")
        )
        .filter(adminDashboardStudent.status == "paid")
        .group_by(extract("month", adminDashboardStudent.created_at))
        .order_by(extract("month", adminDashboardStudent.created_at))
        .all()
    )

    return [
        {"month": f"Month {int(row.month)}", "revenue": float(row.revenue)}
        for row in result
    ]

@router.get("/dashboard/header")
def get_header_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Professional Header API
    Returns:
    - Logged in username
    - Role
    - Last login
    - System status
    - Pending notifications
    - Today's date
    """

    # 🔹 Format Last Login
    last_login = (
        current_user.last_login.strftime("%I:%M %p")
        if current_user.last_login
        else "First Login"
    )

    # 🔹 System Health Check
    try:
        db.execute(text("SELECT 1"))
        system_status = "Active"
    except Exception:
        system_status = "Down"

    # 🔹 Pending Students = Notifications
    notifications = (
        db.query(adminDashboardStudent)
        .filter(adminDashboardStudent.status == "pending")
        .count()
    )

    return {
        "username": current_user.username,
        "role": current_user.role,
        "lastLogin": last_login,
        "systemStatus": system_status,
        "notifications": notifications,
        "todayDate": datetime.now().strftime("%d %B %Y")
    }