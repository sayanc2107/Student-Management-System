import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app.auth import get_password_hash
from app.config import settings

logger = logging.getLogger("student_management.seed")

async def seed_demo_data_if_empty(db):
    """Seed comprehensive realistic demo data if users collection is empty or only teacher exists"""
    user_count = await db.users.count_documents()
    if user_count > 1:
        logger.info("Database already seeded with demo data.")
        return

    logger.info("Initializing rich demo dataset for independent tuition management...")
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    in_three_days_str = (now + timedelta(days=3)).strftime("%Y-%m-%d")
    in_seven_days_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    # 1. Teacher Account
    teacher_pw = get_password_hash("Teacher@123")
    teacher_user = {
        "_id": ObjectId(),
        "name": settings.TEACHER_NAME,
        "email": "teacher@tuition.com",
        "username": "teacher",
        "passwordHash": teacher_pw,
        "role": "teacher",
        "studentId": None,
        "createdAt": now - timedelta(days=60),
        "updatedAt": now
    }
    # Also add the configured email as an alias or secondary teacher login
    if settings.TEACHER_EMAIL != "teacher@tuition.com":
        teacher_user_alt = {
            "_id": ObjectId(),
            "name": settings.TEACHER_NAME,
            "email": settings.TEACHER_EMAIL.lower(),
            "username": "sayan",
            "passwordHash": teacher_pw,
            "role": "teacher",
            "studentId": None,
            "createdAt": now - timedelta(days=60),
            "updatedAt": now
        }
        await db.users.insert_one(teacher_user_alt)

    await db.users.insert_one(teacher_user)

    # 2. Students & Linked User Accounts
    student_pw = get_password_hash("Student@123")

    demo_students = [
        {
            "name": "Aarav Mehta",
            "username": "aarav",
            "grade": "Class 10 - ICSE",
            "course": "Secondary Board Exam Mentorship",
            "subjects": ["Mathematics", "Physics", "Chemistry"],
            "email": "aarav.mehta@example.com",
            "mobile": "+91 98201 11223",
            "guardian": {
                "name": "Sanjay Mehta",
                "mobile": "+91 98201 99887",
                "email": "sanjay.mehta@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Excellent aptitude in algebra. Needs minor reinforcement in geometric theorems."
        },
        {
            "name": "Diya Sen",
            "username": "diya",
            "grade": "Grade 12 - CBSE",
            "course": "Senior Secondary Science Stream",
            "subjects": ["Mathematics", "Physics"],
            "email": "diya.sen@example.com",
            "mobile": "+91 98310 22334",
            "guardian": {
                "name": "Ananya Sen",
                "mobile": "+91 98310 88776",
                "email": "ananya.sen@example.com",
                "relationship": "Mother"
            },
            "enrollmentStatus": "active",
            "notes": "Consistently scores 90%+. Preparing for upcoming engineering entrance mocks."
        },
        {
            "name": "Rohan Verma",
            "username": "rohan",
            "grade": "Class 10 - CBSE",
            "course": "Secondary Board Intensive",
            "subjects": ["Mathematics"],
            "email": "rohan.verma@example.com",
            "mobile": "+91 98450 33445",
            "guardian": {
                "name": "Vikram Verma",
                "mobile": "+91 98450 77665",
                "email": "vikram.verma@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Benefiting greatly from step-by-step problem sessions. Attentive in class."
        },
        {
            "name": "Ananya Iyer",
            "username": "ananya",
            "grade": "Grade 12 - CBSE",
            "course": "Senior Secondary Science Stream",
            "subjects": ["Physics", "Chemistry", "Mathematics"],
            "email": "ananya.iyer@example.com",
            "mobile": "+91 98800 44556",
            "guardian": {
                "name": "Ramachandran Iyer",
                "mobile": "+91 98800 66554",
                "email": "ramachandran.iyer@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Very diligent homework submissions. Strong in conceptual physics derivations."
        },
        {
            "name": "Kabir Patel",
            "username": "kabir",
            "grade": "Grade 9 - State Board",
            "course": "Foundation Mathematics & Science",
            "subjects": ["Mathematics", "Science"],
            "email": "kabir.patel@example.com",
            "mobile": "+91 97240 55667",
            "guardian": {
                "name": "Meena Patel",
                "mobile": "+91 97240 44332",
                "email": "meena.patel@example.com",
                "relationship": "Mother"
            },
            "enrollmentStatus": "active",
            "notes": "Joined mid-term. Catching up quickly on quadratic equations."
        }
    ]

    student_id_map = {}
    for st in demo_students:
        s_oid = ObjectId()
        st["_id"] = s_oid
        st["createdAt"] = now - timedelta(days=45)
        st["updatedAt"] = now
        await db.students.insert_one(st)
        student_id_map[st["email"]] = str(s_oid)

        # Create user record for student sign-in
        user_doc = {
            "_id": ObjectId(),
            "name": st["name"],
            "email": st["email"],
            "username": st["username"],
            "passwordHash": student_pw,
            "role": "student",
            "studentId": str(s_oid),
            "createdAt": now - timedelta(days=45),
            "updatedAt": now
        }
        await db.users.insert_one(user_doc)

    aarav_id = student_id_map["aarav.mehta@example.com"]
    diya_id = student_id_map["diya.sen@example.com"]
    rohan_id = student_id_map["rohan.verma@example.com"]
    ananya_id = student_id_map["ananya.iyer@example.com"]
    kabir_id = student_id_map["kabir.patel@example.com"]

    all_student_ids = [aarav_id, diya_id, rohan_id, ananya_id, kabir_id]

    # 3. Classes
    past_class_id = str(ObjectId())
    classes_data = [
        {
            "_id": ObjectId(past_class_id),
            "title": "Thermodynamics & Heat Transfer Fundamentals",
            "subject": "Physics",
            "grade": "Grade 12 - CBSE",
            "date": yesterday_str,
            "startTime": "17:30",
            "endTime": "19:00",
            "mode": "Online",
            "meetingLink": "https://meet.google.com/abc-tuition-demo",
            "notes": "Covered Carnot engine cycles and entropy problems. Assigned problem set 3.",
            "assignedStudentIds": [diya_id, ananya_id],
            "status": "completed",
            "createdAt": now - timedelta(days=5),
            "updatedAt": now
        },
        {
            "_id": ObjectId(),
            "title": "Quadratic Equations Masterclass & Word Problems",
            "subject": "Mathematics",
            "grade": "Class 10 - ICSE / CBSE",
            "date": tomorrow_str,
            "startTime": "18:00",
            "endTime": "19:30",
            "mode": "Online",
            "meetingLink": "https://meet.google.com/xyz-math-live",
            "notes": "Please keep your formula notebooks and NCERT/Selina textbooks handy.",
            "assignedStudentIds": [aarav_id, rohan_id, kabir_id],
            "status": "scheduled",
            "createdAt": now - timedelta(days=2),
            "updatedAt": now
        },
        {
            "_id": ObjectId(),
            "title": "Ray Optics: Spherical Mirrors & Lens Maker Formula",
            "subject": "Physics",
            "grade": "Grade 12 - CBSE",
            "date": in_three_days_str,
            "startTime": "17:00",
            "endTime": "18:30",
            "mode": "Online",
            "meetingLink": "https://zoom.us/j/demo-tuition-session",
            "notes": "Sign conventions and sign diagram practice.",
            "assignedStudentIds": [diya_id, ananya_id],
            "status": "scheduled",
            "createdAt": now - timedelta(days=1),
            "updatedAt": now
        },
        {
            "_id": ObjectId(),
            "title": "Weekly Doubt Clearing & Problem Solving Clinic",
            "subject": "Mathematics",
            "grade": "All Batches",
            "date": in_seven_days_str,
            "startTime": "10:30",
            "endTime": "12:00",
            "mode": "Offline",
            "meetingLink": "",
            "notes": "Offline in-person classroom session at tuition center. Bring questions from past test papers.",
            "assignedStudentIds": all_student_ids,
            "status": "scheduled",
            "createdAt": now,
            "updatedAt": now
        }
    ]
    for c in classes_data:
        await db.classes.insert_one(c)

    # 4. Attendance Records for Past Class
    attendance_data = [
        {
            "_id": ObjectId(),
            "classId": past_class_id,
            "studentId": diya_id,
            "status": "present",
            "remarks": "Active participation in solving Carnot efficiency questions.",
            "recordedAt": now - timedelta(days=1),
            "updatedAt": now - timedelta(days=1)
        },
        {
            "_id": ObjectId(),
            "classId": past_class_id,
            "studentId": ananya_id,
            "status": "present",
            "remarks": "On time and completed whiteboard calculation.",
            "recordedAt": now - timedelta(days=1),
            "updatedAt": now - timedelta(days=1)
        }
    ]
    for a in attendance_data:
        await db.attendance.insert_one(a)

    # Class Feedback & Remarks for Past Class
    feedback_data = [
        {
            "_id": ObjectId(),
            "classId": past_class_id,
            "studentId": diya_id,
            "studentName": "Diya Sen",
            "authorId": diya_id,
            "authorName": "Diya Sen",
            "authorRole": "student",
            "feedback": "The explanation of Carnot cycle reversible stages was very clear. I will practice more numerical problems on entropy.",
            "sharedWithStudent": False,
            "createdAt": now - timedelta(days=1, hours=2),
            "updatedAt": now - timedelta(days=1, hours=2)
        },
        {
            "_id": ObjectId(),
            "classId": past_class_id,
            "studentId": diya_id,
            "studentName": "Diya Sen",
            "authorId": str(teacher_user["_id"]),
            "authorName": settings.TEACHER_NAME,
            "authorRole": "teacher",
            "feedback": "Great focus during thermodynamics problem solving today. Please memorize the temperature ratio formula.",
            "sharedWithStudent": True,
            "createdAt": now - timedelta(days=1, hours=1),
            "updatedAt": now - timedelta(days=1, hours=1)
        }
    ]
    for fb in feedback_data:
        await db.class_feedback.insert_one(fb)

    # 5. Homework Assignments
    hw1_id = str(ObjectId())
    hw2_id = str(ObjectId())
    hw3_id = str(ObjectId())

    homework_data = [
        {
            "_id": ObjectId(hw1_id),
            "title": "[DEMO] NCERT Exercise 4.3 - Quadratic Formulations",
            "subject": "Mathematics",
            "instructions": "Solve Questions 1 through 10 from Exercise 4.3. Show step-by-step discriminant calculations for each quadratic equation.",
            "assignedStudentIds": [aarav_id, rohan_id, kabir_id],
            "assignedDate": yesterday_str,
            "dueDate": in_three_days_str,  # Due soon
            "attachmentUrl": "https://example.com/demo-handout-quadratic.pdf",
            "attachmentName": "Quadratic_Equations_Handout.pdf",
            "totalMarks": 50,
            "createdAt": now - timedelta(days=2),
            "updatedAt": now
        },
        {
            "_id": ObjectId(hw2_id),
            "title": "[DEMO] Electromagnetic Induction Numerical Problem Set",
            "subject": "Physics",
            "instructions": "Complete the 5 numerical problems on Faraday's Law and Lenz's Law given on page 42 of the reference sheet.",
            "assignedStudentIds": [diya_id, ananya_id],
            "assignedDate": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
            "dueDate": yesterday_str,  # Overdue
            "attachmentUrl": "https://example.com/demo-emi-problems.pdf",
            "attachmentName": "EMI_Problems_Sheet.pdf",
            "totalMarks": 40,
            "createdAt": now - timedelta(days=5),
            "updatedAt": now
        },
        {
            "_id": ObjectId(hw3_id),
            "title": "[DEMO] Trigonometric Identities Practice Sheet",
            "subject": "Mathematics",
            "instructions": "Verify all 8 trigonometric proof identities using standard Pythagorean and quotient relations.",
            "assignedStudentIds": all_student_ids,
            "assignedDate": (now - timedelta(days=8)).strftime("%Y-%m-%d"),
            "dueDate": (now - timedelta(days=3)).strftime("%Y-%m-%d"),
            "attachmentUrl": "",
            "attachmentName": "",
            "totalMarks": 100,
            "createdAt": now - timedelta(days=8),
            "updatedAt": now
        }
    ]
    for hw in homework_data:
        await db.homework.insert_one(hw)

    # 6. Submissions
    submissions_data = [
        {
            "_id": ObjectId(),
            "homeworkId": hw1_id,
            "studentId": aarav_id,
            "submissionText": "Dear Teacher, I have solved all 10 questions. Here is my working for Q7 and Q8 where the roots involve radical expressions. Please check my discriminant steps.",
            "attachmentUrl": "https://example.com/demo-aarav-math-solutions.pdf",
            "attachmentName": "Aarav_Math_HW_Exercise_4.3.pdf",
            "submittedAt": now - timedelta(hours=3),
            "status": "submitted",  # Awaiting review
            "grade": None,
            "feedback": None,
            "updatedAt": now - timedelta(hours=3)
        },
        {
            "_id": ObjectId(),
            "homeworkId": hw2_id,
            "studentId": diya_id,
            "submissionText": "Uploaded numerical solutions for questions 1 to 5. Special attention given to magnetic flux direction in question 3.",
            "attachmentUrl": "https://example.com/demo-diya-physics-emi.pdf",
            "attachmentName": "Diya_Sen_EMI_Numericals.pdf",
            "submittedAt": now - timedelta(days=1, hours=4),
            "status": "reviewed",
            "grade": "38/40",
            "feedback": "Outstanding working Diya! Very clear circuit diagrams and correct Lenz's law polarities.",
            "reviewedAt": now - timedelta(hours=12),
            "reviewedBy": settings.TEACHER_NAME,
            "updatedAt": now - timedelta(hours=12)
        }
    ]
    for sub in submissions_data:
        await db.submissions.insert_one(sub)

    # 7. Exams with Google Form Links
    exams_data = [
        {
            "_id": ObjectId(),
            "title": "[DEMO] Mid-Term Mathematics Mock Examination 2026",
            "subject": "Mathematics",
            "grade": "Class 10 - ICSE / CBSE",
            "date": in_three_days_str,
            "startTime": "10:00",
            "endTime": "11:30",
            "durationMinutes": 90,
            "totalMarks": 80,
            "syllabus": "Real Numbers, Polynomials, Linear Equations in Two Variables, Quadratic Equations, and Arithmetic Progressions.",
            "formLink": "https://docs.google.com/forms/d/e/1FAIpQLSc-demo-exam-math/viewform",
            "createdAt": now - timedelta(days=3),
            "updatedAt": now
        },
        {
            "_id": ObjectId(),
            "title": "[DEMO] Unit Test: Ray Optics & Modern Physics",
            "subject": "Physics",
            "grade": "Grade 12 - CBSE",
            "date": in_seven_days_str,
            "startTime": "14:00",
            "endTime": "15:00",
            "durationMinutes": 60,
            "totalMarks": 50,
            "syllabus": "Reflection, Refraction at spherical surfaces, Dispersion, Photoelectric effect, and Bohr model of hydrogen atom.",
            "formLink": "https://docs.google.com/forms/d/e/1FAIpQLSc-demo-exam-physics/viewform",
            "createdAt": now - timedelta(days=2),
            "updatedAt": now
        }
    ]
    for ex in exams_data:
        await db.exams.insert_one(ex)

    # 8. Fees & Recorded Manual Payments
    fee_aarav_id = str(ObjectId())
    fee_diya_id = str(ObjectId())
    fee_rohan_id = str(ObjectId())
    fee_ananya_id = str(ObjectId())

    fees_data = [
        {
            "_id": ObjectId(fee_aarav_id),
            "studentId": aarav_id,
            "period": "November 2026 Tuition Fee",
            "amount": 3500.0,
            "dueDate": in_three_days_str,
            "description": "Monthly fee for 10th Grade ICSE Mathematics & Science (8 sessions)",
            "createdAt": now - timedelta(days=10),
            "updatedAt": now
        },
        {
            "_id": ObjectId(fee_diya_id),
            "studentId": diya_id,
            "period": "November 2026 Tuition Fee",
            "amount": 4000.0,
            "dueDate": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
            "description": "Monthly fee for 12th Grade CBSE Physics & Mathematics",
            "createdAt": now - timedelta(days=10),
            "updatedAt": now
        },
        {
            "_id": ObjectId(fee_rohan_id),
            "studentId": rohan_id,
            "period": "November 2026 Tuition Fee",
            "amount": 3000.0,
            "dueDate": tomorrow_str,
            "description": "Monthly fee for 10th Grade CBSE Mathematics",
            "createdAt": now - timedelta(days=12),
            "updatedAt": now
        },
        {
            "_id": ObjectId(fee_ananya_id),
            "studentId": ananya_id,
            "period": "October 2026 Tuition Fee",
            "amount": 4000.0,
            "dueDate": (now - timedelta(days=5)).strftime("%Y-%m-%d"),  # Overdue
            "description": "Monthly fee for 12th Grade Science Batch",
            "createdAt": now - timedelta(days=35),
            "updatedAt": now
        }
    ]
    for fee in fees_data:
        await db.fees.insert_one(fee)

    # Payments: (Only teacher recorded manual payments)
    payments_data = [
        # Diya paid in full via UPI (Teacher manually confirmed)
        {
            "_id": ObjectId(),
            "studentId": diya_id,
            "feeId": fee_diya_id,
            "amount": 4000.0,
            "paidAt": (now - timedelta(days=4)).strftime("%Y-%m-%d"),
            "method": "upi",
            "reference": "UPI/432190823411/AXIS",
            "note": "Paid via Google Pay to teacher UPI ID. Manually verified in Axis bank statement.",
            "isReversal": False,
            "createdBy": settings.TEACHER_NAME,
            "createdAt": now - timedelta(days=4)
        },
        # Rohan made a partial cash payment of 1,500 out of 3,000
        {
            "_id": ObjectId(),
            "studentId": rohan_id,
            "feeId": fee_rohan_id,
            "amount": 1500.0,
            "paidAt": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
            "method": "cash",
            "reference": "REC-NOV-042",
            "note": "Received ₹1,500 in cash during evening session. Remaining ₹1,500 balance due.",
            "isReversal": False,
            "createdBy": settings.TEACHER_NAME,
            "createdAt": now - timedelta(days=2)
        }
    ]
    for pay in payments_data:
        await db.payments.insert_one(pay)

    # 9. Tuition Profile in settings
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

    logger.info("Demo dataset successfully initialized with realistic teacher, students, classes, attendance, homework, exams, fees, and payments!")
