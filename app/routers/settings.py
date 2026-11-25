from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_database
from app.auth import get_current_user, require_teacher
from app.config import settings
from app.models.schemas import SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["Settings & Profile"])

@router.get("/contact")
async def get_teacher_contact():
    """Public / Student endpoint:
    Displays teacher's configured contact details and direct UPI information.
    Provides email with 'mailto:' link.
    """
    db = get_database()
    custom = await db.settings.find_one({"type": "tuition_profile"})
    if custom:
        return {
            "teacherName": custom.get("teacherName", settings.TEACHER_NAME),
            "teacherEmail": custom.get("teacherEmail", settings.TEACHER_EMAIL),
            "teacherPhone": custom.get("teacherPhone", settings.TEACHER_PHONE),
            "teacherWhatsapp": custom.get("teacherWhatsapp", settings.TEACHER_WHATSAPP),
            "tuitionName": custom.get("tuitionName", settings.TUITION_NAME),
            "tuitionAddress": custom.get("tuitionAddress", settings.TUITION_ADDRESS),
            "teacherUpiId": custom.get("teacherUpiId", settings.TEACHER_UPI_ID),
            "teacherUpiName": custom.get("teacherUpiName", settings.TEACHER_UPI_NAME),
            "teacherUpiQrUrl": custom.get("teacherUpiQrUrl", settings.TEACHER_UPI_QR_URL),
            "currencySymbol": settings.CURRENCY_SYMBOL,
            "timezone": settings.TIMEZONE,
            "mailtoLink": f"mailto:{custom.get('teacherEmail', settings.TEACHER_EMAIL)}?subject=Inquiry%20regarding%20Tuition"
        }

    return {
        "teacherName": settings.TEACHER_NAME,
        "teacherEmail": settings.TEACHER_EMAIL,
        "teacherPhone": settings.TEACHER_PHONE,
        "teacherWhatsapp": settings.TEACHER_WHATSAPP,
        "tuitionName": settings.TUITION_NAME,
        "tuitionAddress": settings.TUITION_ADDRESS,
        "teacherUpiId": settings.TEACHER_UPI_ID,
        "teacherUpiName": settings.TEACHER_UPI_NAME,
        "teacherUpiQrUrl": settings.TEACHER_UPI_QR_URL,
        "currencySymbol": settings.CURRENCY_SYMBOL,
        "timezone": settings.TIMEZONE,
        "mailtoLink": f"mailto:{settings.TEACHER_EMAIL}?subject=Inquiry%20regarding%20Tuition"
    }

@router.get("/full")
async def get_full_settings(current_user: Dict[str, Any] = Depends(require_teacher)):
    """Teacher-only endpoint to view all system configuration and database status"""
    db = get_database()
    custom = await db.settings.find_one({"type": "tuition_profile"})

    from app.database import db_manager
    status_info = {
        "databaseEngine": "MongoDB Atlas" if db_manager.is_atlas else "Offline / Local Engine",
        "connectionStatus": db_manager.connection_status,
        "atlasConfigured": bool(settings.MONGODB_URI and ("mongodb://" in settings.MONGODB_URI or "mongodb+srv://" in settings.MONGODB_URI)),
        "databaseName": settings.DATABASE_NAME,
        "timezone": settings.TIMEZONE,
        "currency": settings.CURRENCY_SYMBOL
    }

    profile = custom if custom else {
        "teacherName": settings.TEACHER_NAME,
        "teacherEmail": settings.TEACHER_EMAIL,
        "teacherPhone": settings.TEACHER_PHONE,
        "teacherWhatsapp": settings.TEACHER_WHATSAPP,
        "tuitionName": settings.TUITION_NAME,
        "tuitionAddress": settings.TUITION_ADDRESS,
        "teacherUpiId": settings.TEACHER_UPI_ID,
        "teacherUpiName": settings.TEACHER_UPI_NAME,
        "teacherUpiQrUrl": settings.TEACHER_UPI_QR_URL,
    }

    return {
        "profile": profile,
        "system": status_info
    }

@router.put("/profile")
async def update_settings(
    payload: SettingsUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher updates profile, contact details, and UPI information"""
    db = get_database()
    now = datetime.now(timezone.utc)

    update_fields = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    update_fields["type"] = "tuition_profile"
    update_fields["updatedAt"] = now

    await db.settings.update_one(
        {"type": "tuition_profile"},
        {"$set": update_fields},
        upsert=True
    )

    return {"message": "Settings updated successfully", "updated": update_fields}
