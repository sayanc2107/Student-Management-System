import logging
import asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app.auth import get_password_hash
from app.config import settings

logger = logging.getLogger("student_management.seed")

async def seed_demo_data(db):
    """
    Idempotent, safe demo-data seed command.
    Inserts or updates a small set of clearly labeled, fictional demo records.
    Running this operation multiple times will NOT create duplicate demo records.
    """
    logger.info("Starting idempotent seed of fictional demo data...")
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    in_three_days_str = (now + timedelta(days=3)).strftime("%Y-%m-%d")
    in_seven_days_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    # 1. Demo Teacher Accounts (fictional credentials, bcrypt hashed)
    teacher_pw = get_password_hash("Teacher@123")
    demo_teacher = {
        "name": settings.TEACHER_NAME,
        "email": "teacher@example.com",
        "username": "teacher",
        "passwordHash": teacher_pw,
        "role": "teacher",
        "studentId": None,
        "isDemo": True,
        "updatedAt": now
    }

    # Upsert primary demo teacher
    existing_t = await db.users.find_one({"$or": [{"username": "teacher"}, {"email": "teacher@example.com"}]})
    if existing_t:
        await db.users.update_one({"_id": existing_t["_id"]}, {"$set": demo_teacher})
        teacher_user_id = str(existing_t["_id"])
    else:
        demo_teacher["_id"] = ObjectId()
        demo_teacher["createdAt"] = now - timedelta(days=60)
        res = await db.users.insert_one(demo_teacher)
        teacher_user_id = str(res.inserted_id)

    # Legacy alias teacher@tuition.com for backward compatibility
    existing_alias = await db.users.find_one({"email": "teacher@tuition.com"})
    if not existing_alias:
        await db.users.insert_one({
            "_id": ObjectId(),
            "name": settings.TEACHER_NAME,
            "email": "teacher@tuition.com",
            "username": "teacher_alias",
            "passwordHash": teacher_pw,
            "role": "teacher",
            "studentId": None,
            "isDemo": True,
            "createdAt": now - timedelta(days=60),
            "updatedAt": now
        })

    # 2. Fictional Demo Students & User Accounts
    student_pw = get_password_hash("Student@123")
    demo_students = [
        {
            "name": "Aarav Mehta",
            "username": "aarav",
            "grade": "Class 10 - ICSE",
            "course": "Secondary Board Exam Mentorship",
            "subjects": ["Mathematics", "Physics", "Chemistry"],
            "email": "student1@example.com",
            "legacyEmail": "aarav.mehta@example.com",
            "mobile": "+91 98000 00001",
            "guardian": {
                "name": "Sanjay Mehta",
                "mobile": "+91 98000 00002",
                "email": "parent1@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Fictional demo student record. Strong in algebra.",
            "isDemo": True
        },
        {
            "name": "Diya Sen",
            "username": "diya",
            "grade": "Grade 12 - CBSE",
            "course": "Senior Secondary Science Stream",
            "subjects": ["Mathematics", "Physics"],
            "email": "student2@example.com",
            "legacyEmail": "diya.sen@example.com",
            "mobile": "+91 98000 00003",
            "guardian": {
                "name": "Sourav Sen",
                "mobile": "+91 98000 00004",
                "email": "parent2@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Fictional demo student record. Physics enthusiast.",
            "isDemo": True
        },
        {
            "name": "Rohan Verma",
            "username": "rohan",
            "grade": "Class 10 - CBSE",
            "course": "Secondary Board Intensive",
            "subjects": ["Mathematics"],
            "email": "student3@example.com",
            "legacyEmail": "rohan.verma@example.com",
            "mobile": "+91 98000 00005",
            "guardian": {
                "name": "Vikram Verma",
                "mobile": "+91 98000 00006",
                "email": "parent3@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Fictional demo student record. Diligent problem solver.",
            "isDemo": True
        },
        {
            "name": "Ananya Iyer",
            "username": "ananya",
            "grade": "Grade 12 - CBSE",
            "course": "Senior Secondary Science Stream",
            "subjects": ["Physics", "Chemistry", "Mathematics"],
            "email": "student4@example.com",
            "legacyEmail": "ananya.iyer@example.com",
            "mobile": "+91 98000 00007",
            "guardian": {
                "name": "R. Iyer",
                "mobile": "+91 98000 00008",
                "email": "parent4@example.com",
                "relationship": "Mother"
            },
            "enrollmentStatus": "active",
            "notes": "Fictional demo student record. Strong derivation skills.",
            "isDemo": True
        },
        {
            "name": "Kabir Patel",
            "username": "kabir",
            "grade": "Grade 9 - State Board",
            "course": "Foundation Mathematics & Science",
            "subjects": ["Mathematics", "Science"],
            "email": "student5@example.com",
            "legacyEmail": "kabir.patel@example.com",
            "mobile": "+91 98000 00009",
            "guardian": {
                "name": "Nilesh Patel",
                "mobile": "+91 98000 00010",
                "email": "parent5@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Fictional demo student record. Foundation course learner.",
            "isDemo": True
        }
    ]

    student_id_map = {}
    for st_data in demo_students:
        legacy_email = st_data.pop("legacyEmail", None)
        uname = st_data["username"]
        email = st_data["email"]

        existing_st = await db.students.find_one({
            "$or": [{"username": uname}, {"email": email}, {"email": legacy_email}]
        })
        if existing_st:
            st_id = str(existing_st["_id"])
            await db.students.update_one({"_id": existing_st["_id"]}, {"$set": st_data})
        else:
            new_oid = ObjectId()
            st_id = str(new_oid)
            st_data["_id"] = new_oid
            st_data["createdAt"] = now - timedelta(days=45)
            st_data["updatedAt"] = now
            await db.students.insert_one(st_data)

        student_id_map[uname] = st_id
        student_id_map[email] = st_id
        if legacy_email:
            student_id_map[legacy_email] = st_id

        # Upsert student user authentication account
        user_doc = {
            "name": st_data["name"],
            "email": email,
            "username": uname,
            "passwordHash": student_pw,
            "role": "student",
            "studentId": st_id,
            "isDemo": True,
            "updatedAt": now
        }
        existing_u = await db.users.find_one({"$or": [{"username": uname}, {"email": email}, {"email": legacy_email}]})
        if existing_u:
            await db.users.update_one({"_id": existing_u["_id"]}, {"$set": user_doc})
        else:
            user_doc["_id"] = ObjectId()
            user_doc["createdAt"] = now - timedelta(days=45)
            await db.users.insert_one(user_doc)

        # Also support legacy email login in development/testing
        if legacy_email:
            legacy_u = await db.users.find_one({"email": legacy_email})
            if not legacy_u:
                await db.users.insert_one({
                    "_id": ObjectId(),
                    "name": st_data["name"],
                    "email": legacy_email,
                    "username": f"{uname}_legacy",
                    "passwordHash": student_pw,
                    "role": "student",
                    "studentId": st_id,
                    "isDemo": True,
                    "createdAt": now - timedelta(days=45),
                    "updatedAt": now
                })

    aarav_id = student_id_map["aarav"]
    diya_id = student_id_map["diya"]
    rohan_id = student_id_map["rohan"]
    ananya_id = student_id_map["ananya"]
    kabir_id = student_id_map["kabir"]
    all_student_ids = [aarav_id, diya_id, rohan_id, ananya_id, kabir_id]

    # 3. Fictional Classes (Online & Offline)
    classes_data = [
        {
            "title": "[Demo] Thermodynamics & Heat Transfer Fundamentals",
            "subject": "Physics",
            "grade": "Grade 12 - CBSE",
            "date": yesterday_str,
            "startTime": "17:30",
            "endTime": "19:00",
            "mode": "Online",
            "meetingLink": "https://meet.google.com/abc-tuition-demo",
            "notes": "Covered Carnot engine cycles and entropy problems.",
            "assignedStudentIds": [diya_id, ananya_id],
            "status": "completed",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "title": "[Demo] Quadratic Equations Masterclass & Word Problems",
            "subject": "Mathematics",
            "grade": "Class 10 - ICSE / CBSE",
            "date": tomorrow_str,
            "startTime": "18:00",
            "endTime": "19:30",
            "mode": "Online",
            "meetingLink": "https://meet.google.com/xyz-math-live",
            "notes": "Keep formula notebooks and NCERT textbooks handy.",
            "assignedStudentIds": [aarav_id, rohan_id, kabir_id],
            "status": "scheduled",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "title": "[Demo] Ray Optics: Spherical Mirrors & Lens Maker Formula",
            "subject": "Physics",
            "grade": "Grade 12 - CBSE",
            "date": in_three_days_str,
            "startTime": "17:00",
            "endTime": "18:30",
            "mode": "Online",
            "meetingLink": "https://zoom.us/j/demo-tuition-session",
            "notes": "Sign conventions and ray diagram practice.",
            "assignedStudentIds": [diya_id, ananya_id],
            "status": "scheduled",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "title": "[Demo] Weekly Doubt Clearing & Problem Solving Clinic",
            "subject": "Mathematics",
            "grade": "All Batches",
            "date": in_seven_days_str,
            "startTime": "10:30",
            "endTime": "12:00",
            "mode": "Offline",
            "meetingLink": "",
            "notes": "Offline in-person classroom session at tuition center.",
            "assignedStudentIds": all_student_ids,
            "status": "scheduled",
            "isDemo": True,
            "updatedAt": now
        }
    ]

    class_id_map = {}
    for c in classes_data:
        title = c["title"]
        existing_c = await db.classes.find_one({"title": title, "isDemo": True})
        if existing_c:
            class_id_map[title] = str(existing_c["_id"])
            await db.classes.update_one({"_id": existing_c["_id"]}, {"$set": c})
        else:
            new_c_id = ObjectId()
            c["_id"] = new_c_id
            c["createdAt"] = now - timedelta(days=5)
            await db.classes.insert_one(c)
            class_id_map[title] = str(new_c_id)

    thermo_class_id = class_id_map["[Demo] Thermodynamics & Heat Transfer Fundamentals"]

    # 4. Attendance Records
    attendance_data = [
        {"classId": thermo_class_id, "studentId": diya_id, "status": "present", "remarks": "Active participation.", "isDemo": True},
        {"classId": thermo_class_id, "studentId": ananya_id, "status": "late", "remarks": "Joined 10 mins late due to school lab.", "isDemo": True}
    ]
    for att in attendance_data:
        existing_att = await db.attendance.find_one({"classId": att["classId"], "studentId": att["studentId"]})
        if existing_att:
            await db.attendance.update_one({"_id": existing_att["_id"]}, {"$set": att})
        else:
            att["_id"] = ObjectId()
            att["recordedAt"] = now - timedelta(days=1)
            await db.attendance.insert_one(att)

    # 5. Homework Assignments
    homework_data = [
        {
            "title": "[Demo] NCERT Chapter 4: Quadratic Formula & Discriminant Analysis",
            "subject": "Mathematics",
            "instructions": "Solve Questions 1 through 15 from Exercise 4.3. Show discriminant analysis.",
            "assignedStudentIds": [aarav_id, rohan_id, kabir_id],
            "assignedDate": (now - timedelta(days=3)).strftime("%Y-%m-%d"),
            "dueDate": yesterday_str,
            "attachmentUrl": "/static/uploads/submissions/sample_assignment.pdf",
            "attachmentName": "quadratic_equations_worksheet.pdf",
            "totalMarks": 50,
            "isDemo": True,
            "updatedAt": now
        },
        {
            "title": "[Demo] Numerical Problems on Lens Maker's Formula & Combinations",
            "subject": "Physics",
            "instructions": "Calculate focal lengths of thin lenses in contact. Solve problems 5 to 12.",
            "assignedStudentIds": [diya_id, ananya_id],
            "assignedDate": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
            "dueDate": tomorrow_str,
            "attachmentUrl": "",
            "attachmentName": "",
            "totalMarks": 40,
            "isDemo": True,
            "updatedAt": now
        },
        {
            "title": "[Demo] Trigonometric Identities & Heights & Distances",
            "subject": "Mathematics",
            "instructions": "Complete Board past-year questions from 2020-2024.",
            "assignedStudentIds": all_student_ids,
            "assignedDate": today_str,
            "dueDate": in_three_days_str,
            "attachmentUrl": "",
            "attachmentName": "",
            "totalMarks": 30,
            "isDemo": True,
            "updatedAt": now
        }
    ]

    hw_id_map = {}
    for h in homework_data:
        title = h["title"]
        existing_h = await db.homework.find_one({"title": title, "isDemo": True})
        if existing_h:
            hw_id_map[title] = str(existing_h["_id"])
            await db.homework.update_one({"_id": existing_h["_id"]}, {"$set": h})
        else:
            new_h_id = ObjectId()
            h["_id"] = new_h_id
            h["createdAt"] = now - timedelta(days=3)
            await db.homework.insert_one(h)
            hw_id_map[title] = str(new_h_id)

    math_hw_id = hw_id_map["[Demo] NCERT Chapter 4: Quadratic Formula & Discriminant Analysis"]
    phys_hw_id = hw_id_map["[Demo] Numerical Problems on Lens Maker's Formula & Combinations"]

    # 6. Submissions
    submissions_data = [
        {
            "homeworkId": math_hw_id,
            "studentId": aarav_id,
            "submissionText": "Completed all 15 problems. Derivation steps shown in attached code solution.",
            "attachmentUrl": "/static/uploads/submissions/aarav_quadratic.c",
            "attachmentName": "quadratic_solver.c",
            "status": "reviewed",
            "grade": "48/50 (A+)",
            "feedback": "Outstanding work! Very clean calculations.",
            "submittedAt": now - timedelta(days=1),
            "reviewedAt": now - timedelta(hours=12),
            "isDemo": True
        },
        {
            "homeworkId": math_hw_id,
            "studentId": rohan_id,
            "submissionText": "Solved questions 1-12. Need assistance on question 13.",
            "attachmentUrl": "",
            "attachmentName": "",
            "status": "submitted",
            "grade": None,
            "feedback": None,
            "submittedAt": now - timedelta(hours=8),
            "isDemo": True
        },
        {
            "homeworkId": phys_hw_id,
            "studentId": diya_id,
            "submissionText": "All numerical problems completed with sign diagrams.",
            "attachmentUrl": "/static/uploads/submissions/diya_optics.pdf",
            "attachmentName": "lens_maker_problems.pdf",
            "status": "submitted",
            "grade": None,
            "feedback": None,
            "submittedAt": now - timedelta(hours=4),
            "isDemo": True
        }
    ]
    for sub in submissions_data:
        existing_sub = await db.submissions.find_one({
            "homeworkId": sub["homeworkId"],
            "studentId": sub["studentId"]
        })
        if existing_sub:
            await db.submissions.update_one({"_id": existing_sub["_id"]}, {"$set": sub})
        else:
            sub["_id"] = ObjectId()
            await db.submissions.insert_one(sub)

    # 7. Exams
    exams_data = [
        {
            "title": "[Demo] Term 2 Mid-Review: Quadratic Equations & AP",
            "subject": "Mathematics",
            "grade": "Class 10",
            "date": in_seven_days_str,
            "startTime": "10:00",
            "durationMinutes": 60,
            "totalMarks": 50,
            "syllabus": "Quadratic Equations, Nature of Roots, Arithmetic Progressions",
            "formLink": "https://forms.gle/demo-quadratics-exam",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "title": "[Demo] Senior Physics Unit Test: Optics & Thermodynamics",
            "subject": "Physics",
            "grade": "Grade 12",
            "date": (now + timedelta(days=10)).strftime("%Y-%m-%d"),
            "startTime": "11:00",
            "durationMinutes": 90,
            "totalMarks": 70,
            "syllabus": "Wave Optics, Ray Optics, Heat Transfer, Carnot Cycles",
            "formLink": "https://forms.gle/demo-physics-test",
            "isDemo": True,
            "updatedAt": now
        }
    ]
    for ex in exams_data:
        existing_ex = await db.exams.find_one({"title": ex["title"], "isDemo": True})
        if existing_ex:
            await db.exams.update_one({"_id": existing_ex["_id"]}, {"$set": ex})
        else:
            ex["_id"] = ObjectId()
            ex["createdAt"] = now - timedelta(days=2)
            await db.exams.insert_one(ex)

    # 8. Fees & Manual Payments
    fees_data = [
        {
            "studentId": aarav_id,
            "period": "November 2026 Tuition",
            "amount": 3500.0,
            "dueDate": yesterday_str,
            "description": "8 sessions - Mathematics & Physics",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "studentId": diya_id,
            "period": "November 2026 Tuition",
            "amount": 4000.0,
            "dueDate": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
            "description": "Senior Physics & Mathematics Mentorship",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "studentId": rohan_id,
            "period": "November 2026 Tuition",
            "amount": 3000.0,
            "dueDate": tomorrow_str,
            "description": "Mathematics Secondary Batch",
            "isDemo": True,
            "updatedAt": now
        },
        {
            "studentId": ananya_id,
            "period": "November 2026 Tuition",
            "amount": 4000.0,
            "dueDate": in_three_days_str,
            "description": "Senior Science Full Stream",
            "isDemo": True,
            "updatedAt": now
        }
    ]

    fee_id_map = {}
    for fee in fees_data:
        key = f"{fee['studentId']}_{fee['period']}"
        existing_f = await db.fees.find_one({"studentId": fee["studentId"], "period": fee["period"], "isDemo": True})
        if existing_f:
            fee_id_map[key] = str(existing_f["_id"])
            await db.fees.update_one({"_id": existing_f["_id"]}, {"$set": fee})
        else:
            new_f_id = ObjectId()
            fee["_id"] = new_f_id
            fee["createdAt"] = now - timedelta(days=10)
            await db.fees.insert_one(fee)
            fee_id_map[key] = str(new_f_id)

    # Manual Payments
    diya_fee_id = fee_id_map.get(f"{diya_id}_November 2026 Tuition")
    rohan_fee_id = fee_id_map.get(f"{rohan_id}_November 2026 Tuition")

    payments_data = [
        {
            "studentId": diya_id,
            "feeId": diya_fee_id,
            "amount": 4000.0,
            "paidAt": (now - timedelta(days=4)).strftime("%Y-%m-%d"),
            "method": "upi",
            "reference": "UPI/DEMO/432190823411",
            "note": "Paid via Google Pay to teacher UPI ID sayan2008c@pthdfc. Confirmed manually.",
            "isReversal": False,
            "createdBy": settings.TEACHER_NAME,
            "isDemo": True
        },
        {
            "studentId": rohan_id,
            "feeId": rohan_fee_id,
            "amount": 1500.0,
            "paidAt": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
            "method": "cash",
            "reference": "REC-DEMO-042",
            "note": "Received ₹1,500 in cash. Remaining ₹1,500 balance due.",
            "isReversal": False,
            "createdBy": settings.TEACHER_NAME,
            "isDemo": True
        }
    ]

    for pay in payments_data:
        existing_p = await db.payments.find_one({"reference": pay["reference"], "isDemo": True})
        if existing_p:
            await db.payments.update_one({"_id": existing_p["_id"]}, {"$set": pay})
        else:
            pay["_id"] = ObjectId()
            pay["createdAt"] = now - timedelta(days=2)
            await db.payments.insert_one(pay)

    # 9. Tuition Profile Settings
    settings_doc = {
        "type": "tuition_profile",
        "teacherName": settings.TEACHER_NAME,
        "teacherEmail": settings.TEACHER_EMAIL,
        "teacherPhone": settings.TEACHER_PHONE,
        "teacherWhatsapp": settings.TEACHER_WHATSAPP,
        "tuitionName": settings.TUITION_NAME,
        "tuitionAddress": settings.TUITION_ADDRESS,
        "teacherUpiId": settings.TEACHER_UPI_ID,
        "teacherUpiName": settings.TEACHER_UPI_NAME,
        "teacherUpiQrUrl": settings.TEACHER_UPI_QR_URL,
        "currency": settings.CURRENCY_SYMBOL,
        "timezone": settings.TIMEZONE,
        "updatedAt": now
    }
    await db.settings.update_one(
        {"type": "tuition_profile"},
        {"$set": settings_doc},
        upsert=True
    )

    logger.info("Fictional demo dataset seeded successfully (idempotent, no duplicates created).")

async def remove_demo_data(db):
    """
    Safely removes all fictional demo records created with isDemo: True.
    Does NOT touch real production data, real users, or custom student profiles.
    """
    logger.info("Removing fictional demo records...")
    demo_filter = {"isDemo": True}

    # In MemoryDatabase or Motor
    col_names = ["attendance", "submissions", "homework", "classes", "exams", "payments", "fees", "students", "users"]
    results = {}
    for c_name in col_names:
        col = getattr(db, c_name)
        if hasattr(col, "delete_many"):
            res = await col.delete_many(demo_filter)
            results[c_name] = getattr(res, "deleted_count", 0)
        else:
            # Fallback for mock collection without delete_many
            to_delete = [doc["_id"] for doc in col.docs.values() if doc.get("isDemo") is True]
            for doc_id in to_delete:
                del col.docs[str(doc_id)]
            results[c_name] = len(to_delete)

    logger.info(f"Demo data cleanup completed: {results}")
    return results

async def get_demo_status(db):
    """Reports total and demo record counts across collections"""
    stats = {}
    collections = ["users", "students", "classes", "homework", "fees", "payments"]
    for col_name in collections:
        col = getattr(db, col_name)
        total = await col.count_documents()
        demo = await col.count_documents({"isDemo": True})
        stats[col_name] = {"total": total, "demo": demo, "production": total - demo}
    return stats

# Backward compatibility alias
seed_demo_data_if_empty = seed_demo_data
