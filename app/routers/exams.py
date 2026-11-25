from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher
from app.models.schemas import ExamCreate, ExamUpdate

router = APIRouter(prefix="/api/exams", tags=["Exams & Tests"])

@router.get("")
async def list_exams(
    subject: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List exams.
    - Teacher: views all exams.
    - Student: views exams relevant to their subjects/grade.
    """
    db = get_database()
    query: Dict[str, Any] = {}
    if subject and subject != "all":
        query["subject"] = subject

    exams = await db.exams.find(query).sort("date", -1).to_list(100)
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    for e in exams:
        e["id"] = str(e["_id"])
        exam_date = str(e.get("date", ""))[:10]
        e["isUpcoming"] = exam_date >= today_str

    return serialize_mongo(exams)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher creates an exam record with optional Google Form link"""
    db = get_database()
    now = datetime.now(timezone.utc)

    exam_doc = {
        "title": payload.title.strip(),
        "subject": payload.subject.strip(),
        "grade": payload.grade.strip() if payload.grade else "",
        "date": payload.date,  # YYYY-MM-DD
        "startTime": payload.startTime.strip() if payload.startTime else "",
        "endTime": payload.endTime.strip() if payload.endTime else "",
        "durationMinutes": payload.durationMinutes or 60,
        "totalMarks": payload.totalMarks or 100,
        "syllabus": payload.syllabus.strip() if payload.syllabus else "",
        "formLink": payload.formLink.strip() if payload.formLink else "",
        "createdAt": now,
        "updatedAt": now
    }

    res = await db.exams.insert_one(exam_doc)
    exam_doc["id"] = str(res.inserted_id)
    return serialize_mongo(exam_doc)

@router.get("/{exam_id}")
async def get_exam(
    exam_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_database()
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    e = await db.exams.find_one({"_id": ObjectId(exam_id)})
    if not e:
        raise HTTPException(status_code=404, detail="Exam not found")

    e["id"] = str(e["_id"])
    return serialize_mongo(e)

@router.put("/{exam_id}")
async def update_exam(
    exam_id: str,
    payload: ExamUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    oid = ObjectId(exam_id)
    update_data = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    update_data["updatedAt"] = datetime.now(timezone.utc)

    await db.exams.update_one({"_id": oid}, {"$set": update_data})
    updated = await db.exams.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    return serialize_mongo(updated)

@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")

    oid = ObjectId(exam_id)
    await db.exams.delete_one({"_id": oid})
    return {"message": "Exam deleted successfully", "id": exam_id}
