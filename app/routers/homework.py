import os
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher
from app.models.schemas import HomeworkCreate, HomeworkUpdate, SubmissionCreate, SubmissionReview

router = APIRouter(prefix="/api/homework", tags=["Homework & Submissions"])

# File upload storage configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads", "submissions")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 25 MB file size limit (reasonable for code, pdf, powerpoint, zip, images, etc.)
MAX_FILE_SIZE = 25 * 1024 * 1024

@router.get("")
async def list_homework(
    subject: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List homework:
    - Teacher: sees all homework with submission stats.
    - Student: sees homework assigned to them with their individual submission status.
    """
    db = get_database()
    query: Dict[str, Any] = {}
    if subject and subject != "all":
        query["subject"] = subject

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    is_teacher = current_user.get("role") == "teacher"
    if not is_teacher:
        s_id = str(current_user.get("studentId", ""))
        query["$or"] = [
            {"assignedStudentIds": {"$size": 0}},
            {"assignedStudentIds": s_id}
        ]

    homework_list = await db.homework.find(query).sort("dueDate", -1).to_list(200)

    # For student, attach their submission and preserve privacy
    if not is_teacher:
        s_id = str(current_user.get("studentId", ""))
        student_name = current_user.get("name", "Student")
        my_subs = await db.submissions.find({"studentId": s_id}).to_list(200)
        sub_by_hw = {str(s["homeworkId"]): s for s in my_subs}

        for hw in homework_list:
            hw["id"] = str(hw["_id"])
            # Student can only see their own assignment details
            hw["assignedStudentIds"] = [s_id]
            hw["assignedStudents"] = [{"id": s_id, "name": student_name}]
            hw["assignedStudentNames"] = [student_name]
            hw["assignedCount"] = 1

            sub = sub_by_hw.get(hw["id"])
            due_str = str(hw.get("dueDate", ""))[:10]
            if sub:
                hw["submission"] = {
                    "id": str(sub["_id"]),
                    "status": sub.get("status"),
                    "studentName": student_name,
                    "submissionText": sub.get("submissionText"),
                    "attachmentUrl": sub.get("attachmentUrl"),
                    "attachmentName": sub.get("attachmentName"),
                    "submittedAt": sub.get("submittedAt"),
                    "grade": sub.get("grade"),
                    "feedback": sub.get("feedback")
                }
            else:
                hw["submission"] = None
                hw["status"] = "overdue" if due_str < today_str else "assigned"
    else:
        # Teacher: attach submission counters and assigned student details
        all_subs = await db.submissions.find({}).to_list(1000)
        subs_by_hw = {}
        for s in all_subs:
            subs_by_hw.setdefault(str(s["homeworkId"]), []).append(s)

        all_students = await db.students.find({}).to_list(1000)
        students_map = {
            str(st["_id"]): {
                "id": str(st["_id"]),
                "name": st.get("name", "Student"),
                "username": st.get("username", ""),
                "grade": st.get("grade", "")
            }
            for st in all_students
        }

        for hw in homework_list:
            hw["id"] = str(hw["_id"])
            assigned_raw = [str(sid) for sid in hw.get("assignedStudentIds", [])]
            hw["assignedStudentIds"] = assigned_raw
            hw["assignedCount"] = len(assigned_raw)
            hw["assignedStudents"] = [students_map[sid] for sid in assigned_raw if sid in students_map]
            hw["assignedStudentNames"] = [s["name"] for s in hw["assignedStudents"]]

            subs = subs_by_hw.get(hw["id"], [])
            hw["totalSubmissions"] = len(subs)
            hw["pendingReviews"] = sum(1 for s in subs if s.get("status") in ["submitted", "late"])
            hw["reviewedCount"] = sum(1 for s in subs if s.get("status") == "reviewed")

    return serialize_mongo(homework_list)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_homework(
    payload: HomeworkCreate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher creates new homework assignment with optional dedicated students"""
    db = get_database()
    now = datetime.now(timezone.utc)

    clean_assigned_ids = [str(sid).strip() for sid in (payload.assignedStudentIds or []) if str(sid).strip()]

    hw_doc = {
        "title": payload.title.strip(),
        "subject": payload.subject.strip(),
        "instructions": payload.instructions.strip(),
        "assignedStudentIds": clean_assigned_ids,
        "assignedDate": payload.assignedDate or now.strftime("%Y-%m-%d"),
        "dueDate": payload.dueDate,  # YYYY-MM-DD
        "attachmentUrl": payload.attachmentUrl or "",
        "attachmentName": payload.attachmentName or "",
        "totalMarks": payload.totalMarks or 100,
        "createdAt": now,
        "updatedAt": now
    }

    res = await db.homework.insert_one(hw_doc)
    hw_doc["id"] = str(res.inserted_id)
    return serialize_mongo(hw_doc)

@router.get("/{homework_id}")
async def get_homework(
    homework_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    db = get_database()
    if not ObjectId.is_valid(homework_id):
        raise HTTPException(status_code=400, detail="Invalid homework ID")

    hw = await db.homework.find_one({"_id": ObjectId(homework_id)})
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")

    is_teacher = current_user.get("role") == "teacher"
    assigned_raw = [str(sid) for sid in hw.get("assignedStudentIds", [])]

    if not is_teacher:
        s_id = str(current_user.get("studentId", ""))
        if assigned_raw and s_id not in assigned_raw:
            raise HTTPException(status_code=403, detail="You are not assigned to this homework.")

    hw["id"] = str(hw["_id"])

    # If student, attach their submission and preserve privacy
    if not is_teacher:
        s_id = str(current_user.get("studentId", ""))
        student_name = current_user.get("name", "Student")
        hw["assignedStudentIds"] = [s_id]
        hw["assignedStudents"] = [{"id": s_id, "name": student_name}]
        hw["assignedStudentNames"] = [student_name]
        hw["assignedCount"] = 1

        sub = await db.submissions.find_one({"homeworkId": homework_id, "studentId": s_id})
        if sub:
            sub["id"] = str(sub["_id"])
            sub["studentName"] = student_name
            hw["submission"] = sub
        else:
            hw["submission"] = None
    else:
        hw["assignedStudentIds"] = assigned_raw
        hw["assignedCount"] = len(assigned_raw)
        st_cursor = await db.students.find({"_id": {"$in": [ObjectId(sid) for sid in assigned_raw if ObjectId.is_valid(sid)]}}).to_list(100)
        hw["assignedStudents"] = [{"id": str(s["_id"]), "name": s.get("name"), "username": s.get("username", "")} for s in st_cursor]
        hw["assignedStudentNames"] = [s.get("name") for s in st_cursor]

    return serialize_mongo(hw)

@router.put("/{homework_id}")
async def update_homework(
    homework_id: str,
    payload: HomeworkUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(homework_id):
        raise HTTPException(status_code=400, detail="Invalid homework ID")

    oid = ObjectId(homework_id)
    update_data = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "assignedStudentIds" in update_data and update_data["assignedStudentIds"] is not None:
        update_data["assignedStudentIds"] = [str(sid).strip() for sid in update_data["assignedStudentIds"] if str(sid).strip()]
    update_data["updatedAt"] = datetime.now(timezone.utc)

    await db.homework.update_one({"_id": oid}, {"$set": update_data})
    updated = await db.homework.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    return serialize_mongo(updated)

@router.delete("/{homework_id}")
async def delete_homework(
    homework_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(homework_id):
        raise HTTPException(status_code=400, detail="Invalid homework ID")

    oid = ObjectId(homework_id)
    await db.homework.delete_one({"_id": oid})
    await db.submissions.delete_many({"homeworkId": homework_id})
    return {"message": "Homework and associated submissions deleted", "id": homework_id}

# ==============================================================================
# SUBMISSIONS & FILE UPLOADS
# ==============================================================================

@router.post("/upload")
async def upload_submission_file(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows uploading any file format (.c, .java, .pdf, .ppt, .pptx, etc.)
    with a 25 MB limit and secure storage.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read and validate file size
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb} MB. Selected file: {file_size / (1024*1024):.1f} MB."
        )

    # Secure filename creation: alphanumeric with original extension
    clean_original = re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(file.filename))
    unique_prefix = uuid.uuid4().hex[:12]
    safe_filename = f"{unique_prefix}_{clean_original}"
    dest_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(dest_path, "wb") as f:
        f.write(contents)

    size_formatted = f"{file_size / (1024 * 1024):.2f} MB" if file_size >= 1024 * 1024 else f"{file_size / 1024:.1f} KB"
    file_url = f"/static/uploads/submissions/{safe_filename}"

    return {
        "url": file_url,
        "fileUrl": file_url,
        "filename": file.filename,
        "fileName": file.filename,
        "fileSize": file_size,
        "sizeFormatted": size_formatted,
        "message": "File uploaded successfully"
    }

@router.post("/submit")
async def submit_homework(
    payload: SubmissionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Student submits text notes, a pasted link, or an uploaded file for homework"""
    db = get_database()
    s_id = current_user.get("studentId")
    if not s_id:
        raise HTTPException(status_code=403, detail="Student profile not linked to account.")

    s_id_str = str(s_id)
    hw = await db.homework.find_one({"_id": ObjectId(payload.homeworkId)})
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")

    # Verify at least some content is submitted
    text = (payload.submissionText or "").strip()
    url = (payload.attachmentUrl or "").strip()
    if not text and not url:
        raise HTTPException(status_code=400, detail="Please provide either solution notes, a link, or an uploaded file.")

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    due_str = str(hw.get("dueDate", ""))[:10]
    status_str = "late" if today_str > due_str else "submitted"

    sub_doc = {
        "homeworkId": payload.homeworkId,
        "studentId": s_id_str,
        "submissionText": text,
        "attachmentUrl": url,
        "attachmentName": payload.attachmentName or "",
        "submittedAt": now,
        "status": status_str,
        "grade": None,
        "feedback": None,
        "updatedAt": now
    }

    # Upsert submission: student can update until reviewed
    existing = await db.submissions.find_one({"homeworkId": payload.homeworkId, "studentId": s_id_str})
    if existing:
        await db.submissions.update_one(
            {"_id": existing["_id"]},
            {"$set": sub_doc}
        )
        sub_doc["id"] = str(existing["_id"])
    else:
        res = await db.submissions.insert_one(sub_doc)
        sub_doc["id"] = str(res.inserted_id)

    return serialize_mongo(sub_doc)

@router.get("/{homework_id}/submissions")
async def list_homework_submissions(
    homework_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher views all submissions for a homework assignment with status and timestamp"""
    db = get_database()
    subs = await db.submissions.find({"homeworkId": homework_id}).to_list(200)

    results = []
    for s in subs:
        s["id"] = str(s["_id"])
        # Fetch student details
        st = await db.students.find_one({"_id": ObjectId(s["studentId"])}) if ObjectId.is_valid(s["studentId"]) else None
        s["studentName"] = st.get("name", "Student") if st else "Student"
        s["studentUsername"] = st.get("username", "") if st else ""
        s["studentGrade"] = st.get("grade", "") if st else ""
        s["studentEmail"] = st.get("email", "") if st else ""
        results.append(s)

    return serialize_mongo(results)

@router.post("/submissions/{submission_id}/review")
async def review_submission(
    submission_id: str,
    payload: SubmissionReview,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher reviews a submission with marks/grade and feedback"""
    db = get_database()
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=400, detail="Invalid submission ID")

    oid = ObjectId(submission_id)
    sub = await db.submissions.find_one({"_id": oid})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    now = datetime.now(timezone.utc)
    await db.submissions.update_one(
        {"_id": oid},
        {
            "$set": {
                "grade": payload.grade.strip(),
                "feedback": payload.feedback.strip(),
                "status": "reviewed",
                "reviewedAt": now,
                "reviewedBy": current_user.get("name", "Teacher")
            }
        }
    )

    updated = await db.submissions.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    return serialize_mongo(updated)
