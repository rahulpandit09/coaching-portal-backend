from fastapi import Depends, HTTPException
from app.core.security import get_current_user

def admin_required(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

def teacher_required(user=Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher only")
    return user

def student_required(user=Depends(get_current_user)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student only")
    return user
