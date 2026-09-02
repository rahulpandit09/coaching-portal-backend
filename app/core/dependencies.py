from fastapi import status, Depends, HTTPException
from app.database import get_db
from app.core.security import get_current_user

def tutor_required(user=Depends(get_current_user)):
    role_name = user.role.name if user.role else None
    if role_name not in ["Tutor", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Tutor or Admin can access this")
    return user

def teacher_required(user=Depends(get_current_user)):
    role_name = user.role.name if user.role else None
    if role_name not in ["Teacher", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Teacher or Admin can access this")
    return user

def student_required(user=Depends(get_current_user)):
    role_name = user.role.name if user.role else None
    if role_name not in ["Student", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Student or Admin can access this")
    return user

def parent_required(user=Depends(get_current_user)):
    role_name = user.role.name if user.role else None
    if role_name not in ["Parent", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Parent or Admin can access this")
    return user

def admin_required(user=Depends(get_current_user)):
    role_name = user.role.name if user.role else None
    if role_name != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin can access this")
    return user

