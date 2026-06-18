from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.admin.student import Student
from app.models.admin.payment import Payment
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


# SUMMARY API (FULL VERSION)


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):

    total_students = db.query(func.count(Student.id)).scalar() or 0

    paid_students = db.query(func.count(Student.id))\
        .filter(Student.pending_amount == 0).scalar() or 0

    pending_students = db.query(func.count(Student.id))\
        .filter(Student.pending_amount > 0).scalar() or 0

    total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0

    # This Month Revenue
    first_day_of_month = datetime.utcnow().replace(day=1)
    month_revenue = db.query(func.sum(Payment.amount))\
        .filter(Payment.payment_date >= first_day_of_month)\
        .scalar() or 0

    # Today Revenue
    today = datetime.utcnow().date()
    today_revenue = db.query(func.sum(Payment.amount))\
        .filter(func.date(Payment.payment_date) == today)\
        .scalar() or 0

    pending_amount = db.query(func.sum(Student.pending_amount)).scalar() or 0

    return {
        "total_students": total_students,
        "paid_students": paid_students,
        "pending_students": pending_students,
        "total_revenue": total_revenue,
        "month_revenue": month_revenue,
        "today_revenue": today_revenue,
        "pending_amount": pending_amount,
    }


# ===========================
# MONTHLY REVENUE
# ===========================

@router.get("/monthly-revenue")
def get_monthly_revenue(db: Session = Depends(get_db)):

    result = db.query(
        func.to_char(Payment.payment_date, 'Mon').label("month"),
        func.extract('month', Payment.payment_date).label("month_number"),
        func.sum(Payment.amount).label("revenue")
    ).group_by("month", "month_number")\
     .order_by("month_number")\
     .all()

    return [
        {"month": r.month, "revenue": float(r.revenue)}
        for r in result
    ]


# ===========================
# STUDENT GROWTH
# ===========================

@router.get("/student-growth")
def get_student_growth(db: Session = Depends(get_db)):

    result = db.query(
        func.to_char(Student.created_at, 'Mon').label("month"),
        func.extract('month', Student.created_at).label("month_number"),
        func.count(Student.id).label("students")
    ).group_by("month", "month_number")\
     .order_by("month_number")\
     .all()

    return [
        {"month": r.month, "students": r.students}
        for r in result
    ]


# ===========================
# RECENT STUDENTS
# ===========================

@router.get("/recent-students")
def get_recent_students(db: Session = Depends(get_db)):

    students = db.query(Student)\
        .order_by(Student.created_at.desc())\
        .limit(5)\
        .all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "course_id": s.course_id,
            "pending_amount": s.pending_amount,
            "created_at": s.created_at,
            "status": "Paid" if s.pending_amount == 0 else "Pending"
        }
        for s in students
    ]


# ===========================
# TEST DATA
# ===========================

@router.post("/test-data")
def insert_test_data(db: Session = Depends(get_db)):

    s1 = Student(name="Rahul", course_id=1, pending_amount=2000)
    s2 = Student(name="Aman", course_id=2, pending_amount=0)

    db.add_all([s1, s2])
    db.commit()

    db.refresh(s1)
    db.refresh(s2)

    p1 = Payment(student_id=s1.id, amount=5000)
    p2 = Payment(student_id=s2.id, amount=7000)

    db.add_all([p1, p2])
    db.commit()

    return {"message": "Test data inserted successfully"}