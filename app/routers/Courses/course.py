from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.Courses.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseStatusUpdate,
)
from app.crud.Courses import course as crud


router = APIRouter(
    prefix="/api/courses",
    tags=["Teacher Courses Assign"],
)


# ─── GET all courses ──────────────────────────────────────────────────────────
# GET /api/courses
# GET /api/courses?search=rahul&subject=Physics&batch=Batch+A&status=Active

@router.get("", response_model=List[CourseResponse])
def list_courses(
    search:  Optional[str] = Query(default="", description="Search by name, ID or teacher"),
    subject: Optional[str] = Query(default="", description="Filter by subject"),
    batch:   Optional[str] = Query(default="", description="Filter by batch"),
    status:  Optional[str] = Query(default="", description="Filter by status: Active or Inactive"),
    db: Session = Depends(get_db),
):
    return crud.get_all_courses(db, search, subject, batch, status)


# ─── GET single course ────────────────────────────────────────────────────────
# GET /api/courses/1

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
):
    course = crud.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ─── CREATE course ────────────────────────────────────────────────────────────
# POST /api/courses

@router.post("", response_model=CourseResponse, status_code=201)
def create_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
):
    return crud.create_course(db, data)


# ─── UPDATE course (full update) ──────────────────────────────────────────────
# PATCH /api/courses/1

@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    data: CourseUpdate,
    db: Session = Depends(get_db),
):
    course = crud.update_course(db, course_id, data)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ─── UPDATE status only (toggle) ─────────────────────────────────────────────
# PATCH /api/courses/1/status
# Body: { "status": "Active" } or { "status": "Inactive" }

@router.patch("/{course_id}/status", response_model=CourseResponse)
def update_course_status(
    course_id: int,
    data: CourseStatusUpdate,
    db: Session = Depends(get_db),
):
    course = crud.update_course_status(db, course_id, data)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ─── DELETE course ─────────────────────────
# DELETE /api/courses/1

@router.delete("/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
):
    success = crud.delete_course(db, course_id)
    if not success:
        raise HTTPException(status_code=404, detail="Course not found")
