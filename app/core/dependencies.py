from fastapi import Depends, HTTPException
from app.core.security import get_current_user

def admin_required(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can access this")
    return user

def teacher_required(user=Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only Teacher can access this")
    return user

def student_required(user=Depends(get_current_user)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only Student can access this")
    return user
