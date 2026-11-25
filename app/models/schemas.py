from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

# User Models
class UserLogin(BaseModel):
    email: str = Field(..., description="Email or Username")
    username: Optional[str] = None
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str
    name: str
    role: str = "student"  # "teacher" or "student"
    studentId: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(..., min_length=6, description="New password (min 6 characters)")

class SetStudentPasswordRequest(BaseModel):
    newPassword: str = Field(..., min_length=6, description="Teacher-chosen student password (min 6 characters)")

class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    name: str
    role: str
    studentId: Optional[str] = None
    createdAt: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Guardian / Parent Info
class GuardianInfo(BaseModel):
    name: str
    mobile: str
    email: Optional[EmailStr] = None
    relationship: Optional[str] = "Parent"

# Student Models
class StudentCreate(BaseModel):
    name: str
    username: Optional[str] = Field(None, description="Username for student login")
    grade: str = Field(..., description="Class/Grade, e.g. Class 10 - ICSE")
    course: Optional[str] = "General Tuition"
    subjects: List[str] = Field(default_factory=list)
    email: EmailStr
    mobile: str
    guardian: GuardianInfo
    enrollmentStatus: str = "active"  # active, inactive, archived
    notes: Optional[str] = ""

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    grade: Optional[str] = None
    course: Optional[str] = None
    subjects: Optional[List[str]] = None
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    guardian: Optional[GuardianInfo] = None
    enrollmentStatus: Optional[str] = None
    notes: Optional[str] = None

# Class Schedule Models
class ClassCreate(BaseModel):
    title: str
    subject: str
    grade: Optional[str] = ""
    date: str  # YYYY-MM-DD
    startTime: str  # HH:MM
    endTime: str  # HH:MM
    mode: str = "Online"  # "Online" or "Offline"
    meetingLink: Optional[str] = ""
    notes: Optional[str] = ""
    assignedStudentIds: List[str] = Field(default_factory=list)

class ClassUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    mode: Optional[str] = None
    meetingLink: Optional[str] = None
    notes: Optional[str] = None
    assignedStudentIds: Optional[List[str]] = None
    status: Optional[str] = None

# Attendance Models
class AttendanceRecord(BaseModel):
    studentId: str
    status: str  # "present", "absent", "late", "excused"
    remarks: Optional[str] = ""

class AttendanceBulkUpdate(BaseModel):
    classId: str
    records: List[AttendanceRecord]

# Homework Models
class HomeworkCreate(BaseModel):
    title: str
    subject: str
    instructions: str
    assignedStudentIds: List[str] = Field(default_factory=list)  # Empty means all
    assignedDate: Optional[str] = None  # YYYY-MM-DD or now
    dueDate: str  # YYYY-MM-DD or ISO
    attachmentUrl: Optional[str] = ""
    attachmentName: Optional[str] = ""
    totalMarks: Optional[int] = 100

class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    instructions: Optional[str] = None
    assignedStudentIds: Optional[List[str]] = None
    dueDate: Optional[str] = None
    attachmentUrl: Optional[str] = None
    attachmentName: Optional[str] = None
    totalMarks: Optional[int] = None

# Submissions Models
class SubmissionCreate(BaseModel):
    homeworkId: str
    submissionText: Optional[str] = ""
    attachmentUrl: Optional[str] = ""
    attachmentName: Optional[str] = ""

class SubmissionReview(BaseModel):
    grade: str  # e.g., "92/100" or "A+"
    feedback: str

# Class Feedback Models
class ClassFeedbackCreate(BaseModel):
    feedback: str
    studentId: Optional[str] = None  # Optional target student ID or student's own ID
    sharedWithStudent: Optional[bool] = True

# Exam Models
class ExamCreate(BaseModel):
    title: str
    subject: str
    grade: Optional[str] = ""
    date: str  # YYYY-MM-DD
    startTime: Optional[str] = ""
    endTime: Optional[str] = ""
    durationMinutes: Optional[int] = 60
    totalMarks: Optional[int] = 100
    syllabus: Optional[str] = ""
    formLink: Optional[str] = ""  # Google Form link or assessment link

class ExamUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    durationMinutes: Optional[int] = None
    totalMarks: Optional[int] = None
    syllabus: Optional[str] = None
    formLink: Optional[str] = None

# Fee Models
class FeeCreate(BaseModel):
    studentId: str
    period: str  # e.g. "November 2026 Tuition"
    amount: float
    dueDate: str  # YYYY-MM-DD
    description: Optional[str] = ""

class FeeUpdate(BaseModel):
    period: Optional[str] = None
    amount: Optional[float] = None
    dueDate: Optional[str] = None
    description: Optional[str] = None

# Payment Models
class PaymentCreate(BaseModel):
    studentId: str
    feeId: Optional[str] = None
    amount: float
    paidAt: Optional[str] = None  # YYYY-MM-DD or ISO
    method: str = "upi"  # cash, upi, bank_transfer, other
    reference: Optional[str] = ""  # UTR / Receipt / Note
    note: Optional[str] = ""

class PaymentReversal(BaseModel):
    paymentId: str
    reason: str

# Teacher Settings Models
class SettingsUpdate(BaseModel):
    teacherName: Optional[str] = None
    teacherEmail: Optional[EmailStr] = None
    teacherPhone: Optional[str] = None
    teacherWhatsapp: Optional[str] = None
    tuitionName: Optional[str] = None
    tuitionAddress: Optional[str] = None
    teacherUpiId: Optional[str] = None
    teacherUpiName: Optional[str] = None
    teacherUpiQrUrl: Optional[str] = None
    timezone: Optional[str] = None
