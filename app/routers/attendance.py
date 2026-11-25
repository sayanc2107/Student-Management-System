from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher
from app.models.schemas import AttendanceBulkUpdate

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

@router.get("/class/{class_id}")
async def get_class_attendance(
    class_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher views attendance roster for a class"""
    db = get_database()
    if not ObjectId.is_valid(class_id):
        raise HTTPException(status_code=400, detail="Invalid class ID")

    c = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Class not found")

    # Get students assigned or all active students if unassigned
    assigned_ids = c.get("assignedStudentIds", [])
    if assigned_ids:
        query_ids = [ObjectId(sid) for sid in assigned_ids if ObjectId.is_valid(sid)]
        students = await db.students.find({"_id": {"$in": query_ids}}).to_list(100)
    else:
        students = await db.students.find({"enrollmentStatus": "active"}).to_list(100)

    # Get existing attendance records for this class
    records = await db.attendance.find({"classId": class_id}).to_list(200)
    att_map = {str(r.get("studentId")): r for r in records}

    roster = []
    for s in students:
        s_id = str(s["_id"])
        att = att_map.get(s_id)
        roster.append({
            "studentId": s_id,
            "studentName": s.get("name"),
            "grade": s.get("grade"),
            "status": att.get("status") if att else "present",
            "remarks": att.get("remarks") if att else "",
            "recordedAt": att.get("recordedAt") if att else None
        })

    return serialize_mongo({
        "classId": class_id,
        "classTitle": c.get("title"),
        "classDate": c.get("date"),
        "subject": c.get("subject"),
        "roster": roster
    })

@router.post("/bulk")
async def save_class_attendance(
    payload: AttendanceBulkUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher marks/updates attendance in bulk for a class"""
    db = get_database()
    now = datetime.now(timezone.utc)

    for rec in payload.records:
        await db.attendance.update_one(
            {"classId": payload.classId, "studentId": rec.studentId},
            {
                "$set": {
                    "classId": payload.classId,
                    "studentId": rec.studentId,
                    "status": rec.status,
                    "remarks": rec.remarks or "",
                    "recordedAt": now,
                    "updatedAt": now
                }
            },
            upsert=True
        )

    return {"message": "Attendance saved successfully", "count": len(payload.records)}

@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """View attendance history for a student.
    - Teacher can view any student.
    - Student can view ONLY their own attendance.
    """
    db = get_database()
    if current_user.get("role") != "teacher":
        if str(current_user.get("studentId", "")) != student_id:
            raise HTTPException(status_code=403, detail="Access denied. You can only view your own attendance.")

    records = await db.attendance.find({"studentId": student_id}).to_list(500)
    # Join class details
    results = []
    for r in records:
        c_id = r.get("classId")
        c = await db.classes.find_one({"_id": ObjectId(c_id)}) if ObjectId.is_valid(c_id) else None
        results.append({
            "id": str(r["_id"]),
            "classId": c_id,
            "classTitle": c.get("title") if c else "Class",
            "subject": c.get("subject") if c else "",
            "date": c.get("date") if c else "",
            "time": f"{c.get('startTime', '')} - {c.get('endTime', '')}" if c else "",
            "status": r.get("status"),
            "remarks": r.get("remarks")
        })

    results.sort(key=lambda x: str(x.get("date", "")), reverse=True)

    # Calculate statistics
    total = len(results)
    present = sum(1 for x in results if x["status"] == "present")
    absent = sum(1 for x in results if x["status"] == "absent")
    late = sum(1 for x in results if x["status"] == "late")
    percentage = round((present / total * 100), 1) if total > 0 else 100.0

    return serialize_mongo({
        "studentId": student_id,
        "totalClasses": total,
        "present": present,
        "absent": absent,
        "late": late,
        "attendancePercentage": percentage,
        "records": results
    })
