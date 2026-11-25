from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.database import get_database, serialize_mongo
from app.auth import get_current_user, require_teacher
from app.config import settings
from app.models.schemas import FeeCreate, FeeUpdate, PaymentCreate, PaymentReversal

router = APIRouter(prefix="/api/fees", tags=["Fees & Payments"])

def compute_fee_status(fee: Dict[str, Any], paid_amount: float, today_str: str) -> str:
    amount = float(fee.get("amount", 0))
    if paid_amount >= amount:
        return "paid"
    elif paid_amount > 0:
        return "partly_paid"
    else:
        due_str = str(fee.get("dueDate", ""))[:10]
        if due_str < today_str:
            return "overdue"
        return "unpaid"

@router.get("")
async def list_fees(
    student_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List fee charges and computed payment status.
    - Teacher: views all or filter by student.
    - Student: strictly views only their own fee charges.
    """
    db = get_database()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Access control
    if current_user.get("role") != "teacher":
        s_id = str(current_user.get("studentId", ""))
        student_id = s_id

    query: Dict[str, Any] = {}
    if student_id:
        query["studentId"] = student_id

    fees = await db.fees.find(query).sort("dueDate", -1).to_list(500)

    # Fetch all payments for these fees / students
    payments_query: Dict[str, Any] = {}
    if student_id:
        payments_query["studentId"] = student_id
    payments = await db.payments.find(payments_query).to_list(2000)

    # Compute paid amount per fee
    paid_by_fee = {}
    for p in payments:
        fid = str(p.get("feeId", ""))
        if fid:
            amt = float(p.get("amount", 0))
            if p.get("isReversal"):
                paid_by_fee[fid] = paid_by_fee.get(fid, 0.0) - amt
            else:
                paid_by_fee[fid] = paid_by_fee.get(fid, 0.0) + amt

    # Cache students for names
    student_cache = {}

    results = []
    for f in fees:
        f_id = str(f["_id"])
        s_id = str(f.get("studentId"))
        f["id"] = f_id
        paid_amt = max(0.0, paid_by_fee.get(f_id, 0.0))
        computed_status = compute_fee_status(f, paid_amt, today_str)

        if status_filter and status_filter != "all" and computed_status != status_filter:
            continue

        if s_id not in student_cache:
            st = await db.students.find_one({"_id": ObjectId(s_id)}) if ObjectId.is_valid(s_id) else None
            student_cache[s_id] = st.get("name", "Student") if st else "Student"

        f["studentName"] = student_cache[s_id]
        f["paidAmount"] = round(paid_amt, 2)
        f["dueAmount"] = round(max(0.0, float(f.get("amount", 0)) - paid_amt), 2)
        f["status"] = computed_status
        results.append(f)

    return serialize_mongo(results)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_fee(
    payload: FeeCreate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher creates a fee charge for a student"""
    db = get_database()
    now = datetime.now(timezone.utc)

    if not ObjectId.is_valid(payload.studentId):
        raise HTTPException(status_code=400, detail="Invalid student ID")

    fee_doc = {
        "studentId": payload.studentId,
        "period": payload.period.strip(),
        "amount": round(float(payload.amount), 2),
        "dueDate": payload.dueDate,  # YYYY-MM-DD
        "description": payload.description.strip() if payload.description else "",
        "createdAt": now,
        "updatedAt": now
    }

    res = await db.fees.insert_one(fee_doc)
    fee_doc["id"] = str(res.inserted_id)
    return serialize_mongo(fee_doc)

@router.put("/{fee_id}")
async def update_fee(
    fee_id: str,
    payload: FeeUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    db = get_database()
    if not ObjectId.is_valid(fee_id):
        raise HTTPException(status_code=400, detail="Invalid fee ID")

    oid = ObjectId(fee_id)
    update_data = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "amount" in update_data:
        update_data["amount"] = round(float(update_data["amount"]), 2)
    update_data["updatedAt"] = datetime.now(timezone.utc)

    await db.fees.update_one({"_id": oid}, {"$set": update_data})
    updated = await db.fees.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    return serialize_mongo(updated)

@router.delete("/{fee_id}")
async def delete_fee(
    fee_id: str,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Delete a fee charge if no payments have been recorded against it"""
    db = get_database()
    if not ObjectId.is_valid(fee_id):
        raise HTTPException(status_code=400, detail="Invalid fee ID")

    # Check payments
    existing_payments = await db.payments.find_one({"feeId": fee_id})
    if existing_payments:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete fee with recorded payments. Reverse or adjust the payments first."
        )

    await db.fees.delete_one({"_id": ObjectId(fee_id)})
    return {"message": "Fee record deleted successfully", "id": fee_id}

# ==============================================================================
# PAYMENTS & REVERSALS
# ==============================================================================

@router.get("/payments")
async def list_payments(
    student_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List recorded payments.
    - Teacher: see all payments.
    - Student: see only their own payment history.
    """
    db = get_database()
    if current_user.get("role") != "teacher":
        s_id = str(current_user.get("studentId", ""))
        student_id = s_id

    query: Dict[str, Any] = {}
    if student_id:
        query["studentId"] = student_id

    payments = await db.payments.find(query).sort("paidAt", -1).to_list(500)

    # Attach student name and fee details
    student_cache = {}
    fee_cache = {}

    results = []
    for p in payments:
        p["id"] = str(p["_id"])
        sid = str(p.get("studentId"))
        fid = str(p.get("feeId", ""))

        if sid not in student_cache:
            st = await db.students.find_one({"_id": ObjectId(sid)}) if ObjectId.is_valid(sid) else None
            student_cache[sid] = st.get("name", "Student") if st else "Student"

        if fid and fid not in fee_cache:
            fee = await db.fees.find_one({"_id": ObjectId(fid)}) if ObjectId.is_valid(fid) else None
            fee_cache[fid] = fee.get("period", "Tuition Fee") if fee else "Tuition Fee"

        p["studentName"] = student_cache[sid]
        p["feePeriod"] = fee_cache.get(fid, "General")
        results.append(p)

    return serialize_mongo(results)

@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def record_payment(
    payload: PaymentCreate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Teacher records a manual payment (Cash, UPI, Bank Transfer, Other)"""
    db = get_database()
    now = datetime.now(timezone.utc)

    if not ObjectId.is_valid(payload.studentId):
        raise HTTPException(status_code=400, detail="Invalid student ID")

    payment_doc = {
        "studentId": payload.studentId,
        "feeId": payload.feeId or "",
        "amount": round(float(payload.amount), 2),
        "paidAt": payload.paidAt or now.strftime("%Y-%m-%d"),
        "method": payload.method,  # cash, upi, bank_transfer, other
        "reference": payload.reference.strip() if payload.reference else "",
        "note": payload.note.strip() if payload.note else "",
        "isReversal": False,
        "createdBy": current_user.get("name", "Teacher"),
        "createdAt": now
    }

    res = await db.payments.insert_one(payment_doc)
    payment_doc["id"] = str(res.inserted_id)
    return serialize_mongo(payment_doc)

@router.post("/payments/reverse")
async def reverse_payment(
    payload: PaymentReversal,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """Record a reversal/adjustment record rather than silently overwriting a payment.
    Preserves complete audit history.
    """
    db = get_database()
    if not ObjectId.is_valid(payload.paymentId):
        raise HTTPException(status_code=400, detail="Invalid payment ID")

    original = await db.payments.find_one({"_id": ObjectId(payload.paymentId)})
    if not original:
        raise HTTPException(status_code=404, detail="Original payment record not found")

    if original.get("isReversal"):
        raise HTTPException(status_code=400, detail="Cannot reverse an existing reversal entry")

    if original.get("reversed"):
        raise HTTPException(status_code=400, detail="This payment has already been reversed")

    now = datetime.now(timezone.utc)

    # 1. Create reversal record
    reversal_doc = {
        "studentId": original["studentId"],
        "feeId": original.get("feeId", ""),
        "amount": original["amount"],
        "paidAt": now.strftime("%Y-%m-%d"),
        "method": original.get("method", "other"),
        "reference": f"REVERSAL of {str(original['_id'])[:8]}",
        "note": f"Payment Reversal: {payload.reason.strip()}",
        "isReversal": True,
        "reversalOf": str(original["_id"]),
        "createdBy": current_user.get("name", "Teacher"),
        "createdAt": now
    }
    res = await db.payments.insert_one(reversal_doc)

    # 2. Mark original payment as reversed
    await db.payments.update_one(
        {"_id": original["_id"]},
        {"$set": {"reversed": True, "reversedAt": now, "reversalId": str(res.inserted_id)}}
    )

    reversal_doc["id"] = str(res.inserted_id)
    return serialize_mongo({
        "message": "Payment reversal recorded successfully and audit log preserved",
        "reversalRecord": reversal_doc
    })

@router.get("/student/{student_id}/summary")
async def get_student_fee_summary(
    student_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get full fee & payment ledger and balance for a student"""
    db = get_database()
    if current_user.get("role") != "teacher":
        if str(current_user.get("studentId", "")) != student_id:
            raise HTTPException(status_code=403, detail="Access denied.")

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    st = await db.students.find_one({"_id": ObjectId(student_id)})
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    fees = await db.fees.find({"studentId": student_id}).sort("dueDate", 1).to_list(100)
    payments = await db.payments.find({"studentId": student_id}).sort("paidAt", 1).to_list(200)

    total_fees = sum(float(f.get("amount", 0)) for f in fees)
    total_paid = 0.0
    for p in payments:
        amt = float(p.get("amount", 0))
        if p.get("isReversal"):
            total_paid -= amt
        else:
            total_paid += amt

    balance = max(0.0, total_fees - total_paid)

    # Payment details for direct UPI
    upi_info = {
        "upiId": settings.TEACHER_UPI_ID,
        "payeeName": settings.TEACHER_UPI_NAME,
        "balance": round(balance, 2),
        "currency": settings.CURRENCY_SYMBOL,
        # UPI URI format: upi://pay?pa=ID&pn=NAME&am=AMOUNT&cu=INR
        "upiUri": f"upi://pay?pa={settings.TEACHER_UPI_ID}&pn={settings.TEACHER_UPI_NAME.replace(' ', '%20')}&am={round(balance, 2)}&cu=INR",
        "notice": "Scan & pay via Google Pay, PhonePe, Paytm, or BHIM. Direct UPI payments must be confirmed by the teacher manually."
    }

    return serialize_mongo({
        "studentId": student_id,
        "studentName": st.get("name"),
        "grade": st.get("grade"),
        "totalFees": round(total_fees, 2),
        "totalPaid": round(total_paid, 2),
        "balance": round(balance, 2),
        "currency": settings.CURRENCY_SYMBOL,
        "upiInfo": upi_info,
        "feeCount": len(fees),
        "paymentCount": len(payments)
    })
