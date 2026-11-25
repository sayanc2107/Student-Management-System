from datetime import datetime, timezone
import re
from typing import Dict, Any, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher, get_password_hash
from app.models.schemas import StudentCreate, StudentUpdate, SetStudentPasswordRequest

router = APIRouter(prefix="/api/students", tags=["Students"])

@router.get("")
async def list_students(
    search: Optional[str] = None,
    grade: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """List students with search, grade filter, and status filter (Teacher only)"""
    db = get_database()
    query: Dict[str, Any] = {}

    if status_filter and status_filter != "all":
        query["enrollmentStatus"] = status_filter
    else:
        # Default don't show archived unless requested
        if status_filter != "all":
            query["enrollmentStatus"] = {"$ne": "archived"}

    if grade and grade != "all":
        query["grade"] = grade

    students = await db.students.find(query).sort("name", 1).to_list(500)

    # In-memory search filter for multi-field search
    if search:
        s_term = search.lower().strip()
        filtered = []
        for s in students:
            name_match = s_term in s.get("name", "").lower()
            username_match = s_term in s.get("username", "").lower()
            email_match = s_term in s.get("email", "").lower()
            mobile_match = s_term in s.get("mobile", "").lower()
            course_match = s_term in s.get("course", "").lower()
            if name_match or username_match or email_match or mobile_match or course_match:
                filtered.append(s)
        students = filtered

    # Transform ObjectId to str
    for s in students:
        s["id"] = str(s["_id"])

    return serialize_mongo(students)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher creates a student record and auto-provisions student login credentials"""
    db = get_database()
    now = datetime.now(timezone.utc)

    # Check if student with same email exists
    existing = await db.students.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email address already exists."
        )

    # Process and validate username
    raw_username = payload.username.strip().lower() if payload.username else None
    if raw_username:
        clean_username = re.sub(r'[^a-zA-Z0-9_.]', '', raw_username)
        if len(clean_username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters long and contain only letters, numbers, dots, or underscores."
            )
        # Check uniqueness in users and students
        existing_u = await db.users.find_one({"username": clean_username})
        if existing_u:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{clean_username}' is already in use. Please choose another username."
            )
        username = clean_username
    else:
        # Auto-generate a clean username from name or email prefix
        base_username = re.sub(r'[^a-zA-Z0-9_.]', '', payload.email.split('@')[0].lower())
        if len(base_username) < 3:
            base_username = re.sub(r'[^a-zA-Z0-9_.]', '', payload.name.lower())[:12] or "student"
        candidate = base_username
        counter = 1
        while await db.users.find_one({"username": candidate}):
            candidate = f"{base_username}{counter}"
            counter += 1
        username = candidate

    student_doc = {
        "name": payload.name.strip(),
        "username": username,
        "grade": payload.grade.strip(),
        "course": payload.course.strip() if payload.course else "General Tuition",
        "subjects": payload.subjects or [],
        "email": payload.email.lower().strip(),
        "mobile": payload.mobile.strip(),
        "guardian": payload.guardian.dict(),
        "enrollmentStatus": payload.enrollmentStatus,
        "notes": payload.notes or "",
        "createdAt": now,
        "updatedAt": now
    }

    insert_result = await db.students.insert_one(student_doc)
    student_id = insert_result.inserted_id

    # Create matching user account for student sign-in if not present
    existing_user = await db.users.find_one({"email": payload.email.lower()})
    if not existing_user:
        # Default student password is 'Student@123'
        user_doc = {
            "email": payload.email.lower().strip(),
            "username": username,
            "passwordHash": get_password_hash("Student@123"),
            "name": payload.name.strip(),
            "role": "student",
            "studentId": student_id,
            "createdAt": now,
            "updatedAt": now
        }
        await db.users.insert_one(user_doc)
    else:
        await db.users.update_one({"_id": existing_user["_id"]}, {"$set": {"username": username, "studentId": student_id}})

    student_doc["id"] = str(student_id)
    return serialize_mongo(student_doc)

@router.get("/{student_id}")
async def get_student(
    student_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get single student record.
    Security:
    - Teacher can view full record including parent/guardian details.
    - Student can view ONLY their own record, and parent/guardian contact details are redacted.
    """
    db = get_database()
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student ID format")

    oid = ObjectId(student_id)
    student = await db.students.find_one({"_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Access control
    if current_user.get("role") != "teacher":
        if str(current_user.get("studentId")) != student_id:
            raise HTTPException(status_code=403, detail="You do not have permission to view this profile.")
        # Requirement: "Keep parent contact details visible only to the teacher."
        if "guardian" in student:
            # Mask or remove parent phone/email for student view
            student["guardian"] = {
                "name": student["guardian"].get("name", "Guardian"),
                "relationship": student["guardian"].get("relationship", "Parent")
            }

    student["id"] = str(student["_id"])
    return serialize_mongo(student)

@router.put("/{student_id}")
async def update_student(
    student_id: str,
    payload: StudentUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher updates student record"""
    db = get_database()
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student ID")

    oid = ObjectId(student_id)
    student = await db.students.find_one({"_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_fields = {}
    if payload.name is not None:
        update_fields["name"] = payload.name.strip()
    if payload.username is not None:
        clean_uname = re.sub(r'[^a-zA-Z0-9_.]', '', payload.username.strip().lower())
        if len(clean_uname) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters long and contain only letters, numbers, dots, or underscores."
            )
        # Check uniqueness against other users
        existing_u = await db.users.find_one({"username": clean_uname, "studentId": {"$ne": str(oid)}})
        if existing_u:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{clean_uname}' is already in use by another user."
            )
        update_fields["username"] = clean_uname
        # Also sync username to linked user account
        await db.users.update_one(
            {"studentId": str(oid)},
            {"$set": {"username": clean_uname, "updatedAt": datetime.now(timezone.utc)}}
        )
    if payload.grade is not None:
        update_fields["grade"] = payload.grade.strip()
    if payload.course is not None:
        update_fields["course"] = payload.course.strip()
    if payload.subjects is not None:
        update_fields["subjects"] = payload.subjects
    if payload.email is not None:
        update_fields["email"] = payload.email.lower().strip()
    if payload.mobile is not None:
        update_fields["mobile"] = payload.mobile.strip()
    if payload.guardian is not None:
        update_fields["guardian"] = payload.guardian.dict()
    if payload.enrollmentStatus is not None:
        update_fields["enrollmentStatus"] = payload.enrollmentStatus
    if payload.notes is not None:
        update_fields["notes"] = payload.notes

    update_fields["updatedAt"] = datetime.now(timezone.utc)

    await db.students.update_one({"_id": oid}, {"$set": update_fields})
    updated = await db.students.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    return serialize_mongo(updated)

@router.post("/{student_id}/archive")
async def archive_student(
    student_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Archive a student record (preserves all history and payments)"""
    db = get_database()
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student ID")

    oid = ObjectId(student_id)
    await db.students.update_one(
        {"_id": oid},
        {"$set": {"enrollmentStatus": "archived", "updatedAt": datetime.now(timezone.utc)}}
    )
    return {"message": "Student archived successfully", "id": student_id}

@router.post("/{student_id}/restore")
async def restore_student(
    student_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Restore an archived student back to active"""
    db = get_database()
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student ID")

    oid = ObjectId(student_id)
    await db.students.update_one(
        {"_id": oid},
        {"$set": {"enrollmentStatus": "active", "updatedAt": datetime.now(timezone.utc)}}
    )
    return {"message": "Student restored successfully", "id": student_id}

@router.post("/{student_id}/set-password")
async def set_student_password(
    student_id: str,
    payload: SetStudentPasswordRequest,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher sets a student's password to a teacher-chosen password"""
    db = get_database()
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student ID")

    oid = ObjectId(student_id)
    student = await db.students.find_one({"_id": oid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if len(payload.newPassword) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    new_hash = get_password_hash(payload.newPassword)
    now = datetime.now(timezone.utc)

    # Update all matching user records by studentId or email
    query = {"$or": [{"studentId": str(oid)}, {"studentId": oid}, {"email": student.get("email", "").lower()}]}
    update_res = await db.users.update_many(
        query,
        {"$set": {"passwordHash": new_hash, "updatedAt": now}}
    )
    if update_res.matched_count == 0:
        # Create user account if didn't exist
        user_doc = {
            "email": student["email"].lower(),
            "username": student.get("username", student["email"].split("@")[0].lower()),
            "passwordHash": new_hash,
            "name": student["name"],
            "role": "student",
            "studentId": str(oid),
            "createdAt": now,
            "updatedAt": now
        }
        await db.users.insert_one(user_doc)

    return {"message": f"Password for student '{student['name']}' has been updated successfully."}
