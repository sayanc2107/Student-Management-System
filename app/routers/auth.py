from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from bson import ObjectId
from app.database import get_database
from app.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.models.schemas import UserLogin, Token, UserResponse, ChangePasswordRequest

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    db = get_database()
    identifier = (credentials.username or credentials.email).lower().strip()
    user = await db.users.find_one({
        "$or": [
            {"email": identifier},
            {"username": identifier}
        ]
    })

    if not user or not verify_password(credentials.password, user.get("passwordHash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT Token
    token_data = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "username": user.get("username"),
        "role": user.get("role", "student"),
        "name": user.get("name", ""),
        "studentId": str(user.get("studentId")) if user.get("studentId") else None
    }
    access_token = create_access_token(token_data)

    user_resp = UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user.get("username"),
        name=user.get("name", "User"),
        role=user.get("role", "student"),
        studentId=str(user.get("studentId")) if user.get("studentId") else None,
        createdAt=user.get("createdAt")
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_resp
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["_id"]),
        email=current_user["email"],
        username=current_user.get("username"),
        name=current_user.get("name", "User"),
        role=current_user.get("role", "student"),
        studentId=str(current_user.get("studentId")) if current_user.get("studentId") else None,
        createdAt=current_user.get("createdAt")
    )

@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows teachers and students to change their own password while signed in"""
    db = get_database()

    # Verify current password
    if not verify_password(payload.currentPassword, current_user.get("passwordHash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect. Please verify and try again."
        )

    if len(payload.newPassword) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    new_hash = get_password_hash(payload.newPassword)
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"passwordHash": new_hash, "updatedAt": datetime.now(timezone.utc)}}
    )

    return {"message": "Your password has been changed successfully."}
