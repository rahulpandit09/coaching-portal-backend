from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.crud.Batchs import batch_crud   # ✅ NEW
from app.models.Batchs.batch import Batch
from app.schemas.Batchs.batch import *

router = APIRouter(prefix="/admin/batches", tags=["Batches"])


# ─── Helper ─────────────────────────────
def generate_batch_id(db: Session) -> str:
    last = db.query(Batch).order_by(Batch.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    return f"BAT-{str(next_num).zfill(3)}"


def get_batch_or_404(batch_id: int, db: Session):
    batch = batch_crud.get_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


# ───────────────────────────────────────
# BATCH CRUD
# ───────────────────────────────────────

@router.get("/", response_model=List[BatchResponse])
def get_all_batches(
    search: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return batch_crud.get_all_batches(db, search, course, status)


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    return get_batch_or_404(batch_id, db)


@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(data: BatchCreate, db: Session = Depends(get_db)):
    batch_id = generate_batch_id(db)
    return batch_crud.create_batch(db, data, batch_id)


@router.put("/{batch_id}", response_model=BatchResponse)
def update_batch(batch_id: int, data: BatchUpdate, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)
    return batch_crud.update_batch(db, batch, data)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)
    batch_crud.delete_batch(db, batch)


# ───────────────────────────────────────
# STUDENTS
# ───────────────────────────────────────

@router.get("/{batch_id}/students", response_model=List[BatchStudentResponse])
def get_students(batch_id: int, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return batch_crud.get_students(db, batch_id)


@router.post("/{batch_id}/students", response_model=BatchStudentResponse)
def add_student(batch_id: int, data: BatchStudentAdd, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)

    if batch.students >= batch.max_students:
        raise HTTPException(status_code=400, detail="Batch is full")

    existing = batch_crud.get_enrollment(db, batch_id, data.student_id)
    if existing:
        raise HTTPException(status_code=400, detail="Student already enrolled")

    return batch_crud.add_student(db, batch, data)


@router.delete("/{batch_id}/students/{student_id}")
def remove_student(batch_id: int, student_id: int, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)

    enrollment = batch_crud.get_enrollment(db, batch_id, student_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not found")

    batch_crud.remove_student(db, batch, enrollment)


# ───────────────────────────────────────
# ATTENDANCE
# ───────────────────────────────────────

@router.get("/{batch_id}/attendance", response_model=List[AttendanceResponse])
def get_attendance(
    batch_id: int,
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    get_batch_or_404(batch_id, db)
    return batch_crud.get_attendance(db, batch_id, date)


@router.post("/{batch_id}/attendance", response_model=List[AttendanceResponse])
def mark_attendance(batch_id: int, data: AttendanceCreate, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return batch_crud.mark_attendance(db, batch_id, data)


# ───────────────────────────────────────
# TESTS
# ───────────────────────────────────────

@router.get("/{batch_id}/tests", response_model=List[TestResponse])
def get_tests(batch_id: int, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return batch_crud.get_tests(db, batch_id)


@router.post("/{batch_id}/tests", response_model=TestResponse)
def create_test(batch_id: int, data: TestCreate, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return batch_crud.create_test(db, batch_id, data)


@router.delete("/{batch_id}/tests/{test_id}")
def delete_test(batch_id: int, test_id: int, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)

    test = batch_crud.get_test(db, batch_id, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    batch_crud.delete_test(db, test)


# ───────────────────────────────────────
# RESULTS
# ───────────────────────────────────────

@router.get("/{batch_id}/tests/{test_id}/results", response_model=List[TestResultResponse])
def get_results(batch_id: int, test_id: int, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return batch_crud.get_results(db, test_id)


@router.post("/{batch_id}/tests/{test_id}/results", response_model=List[TestResultResponse])
def add_results(batch_id: int, test_id: int, results: List[TestResultAdd], db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return batch_crud.add_results(db, batch_id, test_id, results)