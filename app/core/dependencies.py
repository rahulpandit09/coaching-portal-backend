from fastapi import status
from fastapi import Depends, HTTPException
from app.core.security import get_current_user

def tutor_required(user=Depends(get_current_user)):
    if user.role != "Tutor":
        raise HTTPException(status_code=403, detail="Only Tutor can access this")
    return user

def teacher_required(user=Depends(get_current_user)):
    if user.role != "Teacher":
        raise HTTPException(status_code=403, detail="Only Teacher can access this")
    return user

def student_required(user=Depends(get_current_user)):
    if user.role != "Student":
        raise HTTPException(status_code=403, detail="Only Student can access this")
    return user

def parent_required(user=Depends(get_current_user)):
    if user.role != "Parent":
        raise HTTPException(status_code=403, detail="only Parent can access this")
    return user
