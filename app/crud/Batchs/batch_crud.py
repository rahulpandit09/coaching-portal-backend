from sqlalchemy.orm import Session
from app.models.Batchs.batch import (
    Batch, BatchStudent, BatchAttendance,
    BatchTest, BatchTestResult
)


# BATCH CRUD
def get_all_batches(db: Session, search=None, course=None, status=None):
    query = db.query(Batch)

    if search:
        q = f"%{search.lower()}%"
        query = query.filter(
            Batch.name.ilike(q) |
            Batch.batch_id.ilike(q) |
            Batch.teacher.ilike(q) |
            Batch.course.ilike(q)
        )

    if course:
        query = query.filter(Batch.course == course)

    if status:
        query = query.filter(Batch.status == status)

    return query.order_by(Batch.id.asc()).all()


def get_batch_by_id(db: Session, batch_id: int):
    return db.query(Batch).filter(Batch.id == batch_id).first()


def create_batch(db: Session, data, batch_id: str):
    batch = Batch(
        **data.model_dump(),
        batch_id=batch_id,
        students=0
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def update_batch(db: Session, batch: Batch, data):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(batch, field, value)

    db.commit()
    db.refresh(batch)
    return batch


def delete_batch(db: Session, batch: Batch):
    db.delete(batch)
    db.commit()

# STUDENTS
def get_students(db: Session, batch_id: int):
    return db.query(BatchStudent).filter(
        BatchStudent.batch_id == batch_id
    ).all()


def get_enrollment(db: Session, batch_id: int, student_id: int):
    return db.query(BatchStudent).filter(
        BatchStudent.batch_id == batch_id,
        BatchStudent.student_id == student_id
    ).first()


def add_student(db: Session, batch: Batch, data):
    enrollment = BatchStudent(
        batch_id=batch.id,
        student_id=data.student_id,
        student_name=data.student_name,
        phone=data.phone,
        attendance=0,
        fee_status="Pending",
    )
    db.add(enrollment)

    batch.students += 1
    db.commit()
    db.refresh(enrollment)
    return enrollment


def remove_student(db: Session, batch: Batch, enrollment: BatchStudent):
    db.delete(enrollment)

    if batch.students > 0:
        batch.students -= 1

    db.commit()



# ATTENDANCE
def get_attendance(db: Session, batch_id: int, date=None):
    query = db.query(BatchAttendance).filter(
        BatchAttendance.batch_id == batch_id
    )

    if date:
        query = query.filter(BatchAttendance.date == date)

    return query.order_by(BatchAttendance.date.desc()).all()


def mark_attendance(db: Session, batch_id: int, data):
    db.query(BatchAttendance).filter(
        BatchAttendance.batch_id == batch_id,
        BatchAttendance.date == data.date,
    ).delete()

    records = []
    for r in data.records:
        record = BatchAttendance(
            batch_id=batch_id,
            student_id=r.student_id,
            student_name=r.student_name,
            date=data.date,
            present=r.present,
        )
        db.add(record)
        records.append(record)

    db.commit()

    for rec in records:
        db.refresh(rec)

    return records



# TESTS
def get_tests(db: Session, batch_id: int):
    return db.query(BatchTest).filter(
        BatchTest.batch_id == batch_id
    ).all()


def create_test(db: Session, batch_id: int, data):
    test = BatchTest(batch_id=batch_id, **data.model_dump())
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


def get_test(db: Session, batch_id: int, test_id: int):
    return db.query(BatchTest).filter(
        BatchTest.id == test_id,
        BatchTest.batch_id == batch_id
    ).first()


def delete_test(db: Session, test):
    db.delete(test)
    db.commit()



# RESULTS
def get_results(db: Session, test_id: int):
    return db.query(BatchTestResult).filter(
        BatchTestResult.test_id == test_id
    ).all()


def add_results(db: Session, batch_id: int, test_id: int, results):
    saved = []

    for r in results:
        existing = db.query(BatchTestResult).filter(
            BatchTestResult.test_id == test_id,
            BatchTestResult.student_id == r.student_id,
        ).first()

        if existing:
            existing.marks = r.marks
            existing.remarks = r.remarks
            saved.append(existing)
        else:
            result = BatchTestResult(
                test_id=test_id,
                batch_id=batch_id,
                student_id=r.student_id,
                student_name=r.student_name,
                marks=r.marks,
                remarks=r.remarks,
            )
            db.add(result)
            saved.append(result)

    db.commit()

    for s in saved:
        db.refresh(s)

    return saved