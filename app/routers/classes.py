import calendar
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher
from app.models.schemas import ClassCreate, ClassUpdate, ClassFeedbackCreate

router = APIRouter(prefix="/api/classes", tags=["Classes & Schedule"])

@router.get("")
async def list_classes(
    month: Optional[int] = None,
    year: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    subject: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List classes.
    - Supports calendar month filtering with year & month (e.g. year=2026&month=11).
    - Teacher: see all classes.
    - Student: see classes assigned to them or where assignedStudentIds is empty.
    """
    db = get_database()
    query: Dict[str, Any] = {}

    if year and month:
        last_day = calendar.monthrange(year, month)[1]
        query["date"] = {
            "$gte": f"{year:04d}-{month:02d}-01",
            "$lte": f"{year:04d}-{month:02d}-{last_day:02d}"
        }
    elif start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}

    if subject and subject != "all":
        query["subject"] = subject

    # Role enforcement
    is_teacher = current_user.get("role") == "teacher"
    if not is_teacher:
        s_id = str(current_user.get("studentId", ""))
        query["$or"] = [
            {"assignedStudentIds": {"$size": 0}},
            {"assignedStudentIds": s_id}
        ]

    classes = await db.classes.find(query).sort([("date", 1), ("startTime", 1)]).to_list(500)
    
    # Pre-fetch students for teacher view so assigned student names are resolved
    students_map = {}
    if is_teacher:
        all_students = await db.students.find({}).to_list(1000)
        for s in all_students:
            students_map[str(s["_id"])] = {
                "id": str(s["_id"]),
                "name": s.get("name", "Student"),
                "username": s.get("username", ""),
                "grade": s.get("grade", "")
            }

    for c in classes:
        c["id"] = str(c["_id"])
        assigned_raw = [str(sid) for sid in c.get("assignedStudentIds", [])]
        c["assignedStudentIds"] = assigned_raw
        
        # Privacy preservation:
        # Teacher sees all assigned students.
        # Student sees ONLY their own name and own assignment.
        if is_teacher:
            c["assignedCount"] = len(assigned_raw)
            c["assignedStudents"] = [students_map[sid] for sid in assigned_raw if sid in students_map]
            c["assignedStudentNames"] = [s["name"] for s in c["assignedStudents"]]
        else:
            s_id = str(current_user.get("studentId", ""))
            student_name = current_user.get("name", "Student")
            c["assignedCount"] = 1
            c["assignedStudentIds"] = [s_id]
            c["assignedStudents"] = [{"id": s_id, "name": student_name, "username": current_user.get("username", ""), "grade": ""}]
            c["assignedStudentNames"] = [student_name]

        # Ensure mode exists
        if "mode" not in c or not c["mode"]:
            c["mode"] = "Online" if c.get("meetingLink") else "Offline"
        # Offline classes must not show a meeting link
        if c["mode"] == "Offline":
            c["meetingLink"] = ""

    return serialize_mongo(classes)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher creates a new scheduled class with mode: Online or Offline, and optional dedicated students"""
    db = get_database()
    now = datetime.now(timezone.utc)

    mode = "Offline" if payload.mode == "Offline" else "Online"
    # Online meeting links are optional and only generated/displayed for Online classes.
    # Offline classes must not require or show a meeting link.
    meeting_link = payload.meetingLink.strip() if (mode == "Online" and payload.meetingLink) else ""

    # Clean assigned student IDs
    clean_assigned_ids = [str(sid).strip() for sid in (payload.assignedStudentIds or []) if str(sid).strip()]

    class_doc = {
        "title": payload.title.strip(),
        "subject": payload.subject.strip(),
        "grade": payload.grade.strip() if payload.grade else "",
        "date": payload.date,  # YYYY-MM-DD
        "startTime": payload.startTime.strip(),
        "endTime": payload.endTime.strip(),
        "mode": mode,
        "meetingLink": meeting_link,
        "notes": payload.notes or "",
        "assignedStudentIds": clean_assigned_ids,
        "status": "scheduled",
        "createdAt": now,
        "updatedAt": now
    }

    res = await db.classes.insert_one(class_doc)
    class_doc["id"] = str(res.inserted_id)
    return serialize_mongo(class_doc)

@router.get("/{class_id}")
async def get_class(
    class_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_database()
    if not ObjectId.is_valid(class_id):
        raise HTTPException(status_code=400, detail="Invalid class ID")

    c = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Class not found")

    is_teacher = current_user.get("role") == "teacher"
    assigned_raw = [str(sid) for sid in c.get("assignedStudentIds", [])]

    # Role check
    if not is_teacher:
        s_id = str(current_user.get("studentId", ""))
        if assigned_raw and s_id not in assigned_raw:
            raise HTTPException(status_code=403, detail="You are not enrolled in this class.")

    c["id"] = str(c["_id"])
    if is_teacher:
        c["assignedStudentIds"] = assigned_raw
        c["assignedCount"] = len(assigned_raw)
        st_cursor = await db.students.find({"_id": {"$in": [ObjectId(sid) for sid in assigned_raw if ObjectId.is_valid(sid)]}}).to_list(100)
        c["assignedStudents"] = [{"id": str(s["_id"]), "name": s.get("name"), "username": s.get("username", ""), "grade": s.get("grade", "")} for s in st_cursor]
        c["assignedStudentNames"] = [s.get("name") for s in st_cursor]
    else:
        s_id = str(current_user.get("studentId", ""))
        student_name = current_user.get("name", "Student")
        c["assignedStudentIds"] = [s_id]
        c["assignedCount"] = 1
        c["assignedStudents"] = [{"id": s_id, "name": student_name}]
        c["assignedStudentNames"] = [student_name]

    if "mode" not in c or not c["mode"]:
        c["mode"] = "Online" if c.get("meetingLink") else "Offline"
    if c["mode"] == "Offline":
        c["meetingLink"] = ""

    return serialize_mongo(c)

@router.put("/{class_id}")
async def update_class(
    class_id: str,
    payload: ClassUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(class_id):
        raise HTTPException(status_code=400, detail="Invalid class ID")

    oid = ObjectId(class_id)
    existing = await db.classes.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Class not found")

    update_fields = {}
    for k, v in payload.dict(exclude_unset=True).items():
        if v is not None:
            update_fields[k] = v

    if "assignedStudentIds" in update_fields and update_fields["assignedStudentIds"] is not None:
        update_fields["assignedStudentIds"] = [str(sid).strip() for sid in update_fields["assignedStudentIds"] if str(sid).strip()]

    # Mode logic
    mode = update_fields.get("mode", existing.get("mode", "Online"))
    if mode == "Offline":
        update_fields["meetingLink"] = ""
    elif "meetingLink" in update_fields and update_fields["meetingLink"]:
        update_fields["meetingLink"] = update_fields["meetingLink"].strip()

    update_fields["updatedAt"] = datetime.now(timezone.utc)

    await db.classes.update_one({"_id": oid}, {"$set": update_fields})
    updated = await db.classes.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    if updated.get("mode") == "Offline":
        updated["meetingLink"] = ""
    return serialize_mongo(updated)

@router.delete("/{class_id}")
async def delete_class(
    class_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(class_id):
        raise HTTPException(status_code=400, detail="Invalid class ID")

    oid = ObjectId(class_id)
    await db.classes.delete_one({"_id": oid})
    # Also delete associated attendance and feedback records
    await db.attendance.delete_many({"classId": class_id})
    await db.class_feedback.delete_many({"classId": class_id})
    return {"message": "Class, attendance, and feedback records deleted successfully", "id": class_id}

# ==============================================================================
# CLASS FEEDBACK & REMARKS
# ==============================================================================

@router.get("/{class_id}/feedback")
async def get_class_feedback(
    class_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """View class feedback & remarks.
    - Teacher: can review all feedback for this class (teacher remarks & student feedback).
    - Student: can view only their own feedback and feedback shared with them by the teacher.
    """
    db = get_database()
    feedback_list = await db.class_feedback.find({"classId": class_id}).sort("createdAt", -1).to_list(200)

    is_teacher = current_user.get("role") == "teacher"
    my_student_id = str(current_user.get("studentId", ""))
    my_user_id = str(current_user["_id"])

    visible = []
    for item in feedback_list:
        item["id"] = str(item["_id"])
        if is_teacher:
            visible.append(item)
        else:
            if item.get("authorRole") == "teacher":
                # Only visible if teacher explicitly chose to share it with this student or generally
                if item.get("sharedWithStudent", False) and (not item.get("studentId") or str(item.get("studentId")) == my_student_id):
                    visible.append(item)
            else:
                # Student submitted feedback: only visible to the submitting student
                if str(item.get("authorId")) == my_user_id or (my_student_id and str(item.get("studentId")) == my_student_id):
                    visible.append(item)

    return serialize_mongo(visible)

@router.post("/{class_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_class_feedback(
    class_id: str,
    payload: ClassFeedbackCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Teacher or Student submits feedback/remarks after a class session"""
    db = get_database()
    now = datetime.now(timezone.utc)

    is_teacher = current_user.get("role") == "teacher"
    student_id = None
    student_name = ""

    if is_teacher:
        student_id = payload.studentId if payload.studentId else None
        if student_id and ObjectId.is_valid(student_id):
            st = await db.students.find_one({"_id": ObjectId(student_id)})
            student_name = st.get("name", "") if st else ""
        shared = payload.sharedWithStudent if payload.sharedWithStudent is not None else True
    else:
        student_id = str(current_user.get("studentId", ""))
        student_name = current_user.get("name", "Student")
        # Student feedback is private to teacher and this student by default
        shared = False

    feedback_doc = {
        "classId": class_id,
        "studentId": student_id,
        "studentName": student_name,
        "authorId": str(current_user["_id"]),
        "authorName": current_user.get("name", "User"),
        "authorRole": current_user.get("role", "student"),
        "feedback": payload.feedback.strip(),
        "sharedWithStudent": shared,
        "createdAt": now,
        "updatedAt": now
    }

    res = await db.class_feedback.insert_one(feedback_doc)
    feedback_doc["id"] = str(res.inserted_id)
    return serialize_mongo(feedback_doc)

@router.put("/feedback/{feedback_id}/share")
async def toggle_feedback_sharing(
    feedback_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher toggles whether a remark is shared with the student/class"""
    db = get_database()
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(status_code=400, detail="Invalid feedback ID")

    oid = ObjectId(feedback_id)
    item = await db.class_feedback.find_one({"_id": oid})
    if not item:
        raise HTTPException(status_code=404, detail="Feedback not found")

    new_state = not item.get("sharedWithStudent", False)
    await db.class_feedback.update_one(
        {"_id": oid},
        {"$set": {"sharedWithStudent": new_state, "updatedAt": datetime.now(timezone.utc)}}
    )

    return {"message": f"Feedback sharing updated to {new_state}", "sharedWithStudent": new_state}

@router.delete("/feedback/{feedback_id}")
async def delete_class_feedback(
    feedback_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a feedback entry (Teacher or author only)"""
    db = get_database()
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(status_code=400, detail="Invalid feedback ID")

    oid = ObjectId(feedback_id)
    item = await db.class_feedback.find_one({"_id": oid})
    if not item:
        raise HTTPException(status_code=404, detail="Feedback not found")

    is_teacher = current_user.get("role") == "teacher"
    is_author = str(item.get("authorId")) == str(current_user["_id"])

    if not is_teacher and not is_author:
        raise HTTPException(status_code=403, detail="Not authorized to delete this feedback.")

    await db.class_feedback.delete_one({"_id": oid})
    return {"message": "Feedback deleted successfully", "id": feedback_id}
