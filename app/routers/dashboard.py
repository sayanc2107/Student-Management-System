from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from bson import ObjectId
from fastapi import APIRouter, Depends
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher
from app.config import settings

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

def parse_date(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)

@router.get("/teacher")
async def get_teacher_dashboard(current_user: Dict[str, Any] = Depends(require_teacher)):
    """Teacher dashboard metrics:
    - Upcoming classes
    - Homework due soon & overdue
    - Recent submissions awaiting review
    - Students with unpaid or partly paid fees
    - Summary counts
    """
    db = get_database()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # 1. Upcoming classes (next 7 days)
    seven_days_later = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    classes_cursor = db.classes.find({
        "date": {"$gte": today_str, "$lte": seven_days_later},
        "status": {"$ne": "cancelled"}
    }).sort([("date", 1), ("startTime", 1)])
    upcoming_classes = await classes_cursor.to_list(15)
    for c in upcoming_classes:
        c["id"] = str(c["_id"])
        c["assignedStudentCount"] = len(c.get("assignedStudentIds", []))

    # 2. Homework Due Soon (next 3 days) and Overdue
    three_days_later = (now + timedelta(days=3)).strftime("%Y-%m-%d")
    all_hw = await db.homework.find({}).sort("dueDate", 1).to_list(100)
    homework_due_soon = []
    homework_overdue = []

    # Get submissions to check review status
    all_subs = await db.submissions.find({}).to_list(1000)
    subs_by_hw = {}
    for s in all_subs:
        hw_id = str(s.get("homeworkId"))
        subs_by_hw.setdefault(hw_id, []).append(s)

    for hw in all_hw:
        hw["id"] = str(hw["_id"])
        due_str = str(hw.get("dueDate", ""))[:10]
        hw_subs = subs_by_hw.get(hw["id"], [])
        hw["submissionCount"] = len(hw_subs)
        hw["pendingReviewCount"] = sum(1 for s in hw_subs if s.get("status") == "submitted")

        if due_str < today_str:
            homework_overdue.append(hw)
        elif today_str <= due_str <= three_days_later:
            homework_due_soon.append(hw)

    # 3. Recent submissions awaiting review
    pending_submissions = []
    for s in all_subs:
        if s.get("status") == "submitted":
            s["id"] = str(s["_id"])
            # attach student and homework info
            st = await db.students.find_one({"_id": ObjectId(s["studentId"])}) if ObjectId.is_valid(str(s.get("studentId"))) else None
            hw = await db.homework.find_one({"_id": ObjectId(s["homeworkId"])}) if ObjectId.is_valid(str(s.get("homeworkId"))) else None
            s["studentName"] = st.get("name", "Student") if st else "Student"
            s["homeworkTitle"] = hw.get("title", "Homework") if hw else "Homework"
            s["subject"] = hw.get("subject", "") if hw else ""
            pending_submissions.append(s)
    pending_submissions.sort(key=lambda x: str(x.get("submittedAt", "")), reverse=True)

    # 4. Students with unpaid or partly paid fees
    all_students = await db.students.find({"enrollmentStatus": {"$ne": "archived"}}).to_list(200)
    all_fees = await db.fees.find({}).to_list(1000)
    all_payments = await db.payments.find({}).to_list(2000)

    # Calculate student balance
    student_balances = {}
    for st in all_students:
        s_id = str(st["_id"])
        student_balances[s_id] = {
            "studentId": s_id,
            "studentName": st.get("name"),
            "grade": st.get("grade"),
            "totalFees": 0.0,
            "totalPaid": 0.0,
            "balance": 0.0,
            "unpaidFeeCount": 0,
            "overdueFeeCount": 0
        }

    for f in all_fees:
        s_id = str(f.get("studentId"))
        if s_id in student_balances:
            amt = float(f.get("amount", 0))
            student_balances[s_id]["totalFees"] += amt
            due_str = str(f.get("dueDate", ""))[:10]
            if due_str < today_str:
                student_balances[s_id]["overdueFeeCount"] += 1

    for p in all_payments:
        s_id = str(p.get("studentId"))
        if s_id in student_balances:
            amt = float(p.get("amount", 0))
            if p.get("isReversal"):
                student_balances[s_id]["totalPaid"] -= amt
            else:
                student_balances[s_id]["totalPaid"] += amt

    unpaid_students = []
    total_pending_fee_amount = 0.0
    for s_id, data in student_balances.items():
        bal = data["totalFees"] - data["totalPaid"]
        data["balance"] = max(0.0, bal)
        if bal > 0:
            total_pending_fee_amount += bal
            unpaid_students.append(data)

    unpaid_students.sort(key=lambda x: x["balance"], reverse=True)

    # Total active students count
    active_students_count = sum(1 for s in all_students if s.get("enrollmentStatus") == "active")

    return serialize_mongo({
        "stats": {
            "activeStudents": active_students_count,
            "upcomingClasses": len(upcoming_classes),
            "pendingReviews": len(pending_submissions),
            "totalPendingFees": round(total_pending_fee_amount, 2),
            "currency": settings.CURRENCY_SYMBOL
        },
        "upcomingClasses": upcoming_classes[:5],
        "homeworkDueSoon": homework_due_soon[:5],
        "homeworkOverdue": homework_overdue[:5],
        "pendingSubmissions": pending_submissions[:5],
        "unpaidStudents": unpaid_students[:5]
    })

@router.get("/student")
async def get_student_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Student dashboard summary - view only their own records"""
    db = get_database()
    student_id = current_user.get("studentId")
    if not student_id and current_user.get("role") != "teacher":
        return {"error": "Student profile not linked to user account"}

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    s_id_str = str(student_id)
    student_name = current_user.get("name", "Student")

    # Upcoming classes for this student (dedicated or general)
    classes_cursor = db.classes.find({
        "date": {"$gte": today_str},
        "status": {"$ne": "cancelled"},
        "$or": [
            {"assignedStudentIds": {"$size": 0}},
            {"assignedStudentIds": s_id_str}
        ]
    }).sort([("date", 1), ("startTime", 1)])
    my_classes = await classes_cursor.to_list(5)
    for c in my_classes:
        c["id"] = str(c["_id"])
        c["assignedStudentCount"] = 1
        c["assignedStudentNames"] = [student_name]

    # Homework assigned to this student (dedicated or general)
    all_hw = await db.homework.find({
        "$or": [
            {"assignedStudentIds": {"$size": 0}},
            {"assignedStudentIds": s_id_str}
        ]
    }).sort("dueDate", 1).to_list(50)

    # My submissions
    my_subs = await db.submissions.find({"studentId": student_id}).to_list(100)
    subs_map = {str(s["homeworkId"]): s for s in my_subs}

    my_homework = []
    for hw in all_hw:
        hw_id = str(hw["_id"])
        sub = subs_map.get(hw_id)
        due_str = str(hw.get("dueDate", ""))[:10]
        status = "submitted" if sub else ("overdue" if due_str < today_str else "assigned")
        if sub and sub.get("status") == "reviewed":
            status = "reviewed"

        my_homework.append({
            "id": hw_id,
            "title": hw.get("title"),
            "subject": hw.get("subject"),
            "dueDate": hw.get("dueDate"),
            "status": status,
            "grade": sub.get("grade") if sub else None,
            "feedback": sub.get("feedback") if sub else None,
            "submissionId": str(sub["_id"]) if sub else None
        })

    # My fees & balance
    fees = await db.fees.find({"studentId": student_id}).to_list(100)
    payments = await db.payments.find({"studentId": student_id}).to_list(100)

    total_fees = sum(float(f.get("amount", 0)) for f in fees)
    total_paid = sum(
        -float(p.get("amount", 0)) if p.get("isReversal") else float(p.get("amount", 0))
        for p in payments
    )
    balance = max(0.0, total_fees - total_paid)

    # Next exams
    upcoming_exams = await db.exams.find({"date": {"$gte": today_str}}).sort("date", 1).to_list(5)
    for e in upcoming_exams:
        e["id"] = str(e["_id"])

    return serialize_mongo({
        "stats": {
            "upcomingClasses": len(my_classes),
            "pendingHomework": sum(1 for h in my_homework if h["status"] in ["assigned", "overdue"]),
            "balanceDue": round(balance, 2),
            "currency": settings.CURRENCY_SYMBOL
        },
        "upcomingClasses": my_classes,
        "homework": my_homework[:6],
        "upcomingExams": upcoming_exams,
        "teacherContact": {
            "name": settings.TEACHER_NAME,
            "email": settings.TEACHER_EMAIL,
            "phone": settings.TEACHER_PHONE,
            "whatsapp": settings.TEACHER_WHATSAPP,
            "tuitionName": settings.TUITION_NAME,
            "upiId": settings.TEACHER_UPI_ID,
            "upiName": settings.TEACHER_UPI_NAME
        }
    })
