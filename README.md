# 🎓 T5 ERP SYSTEM - Tuition Student Management System

A simple, responsive, and robust student management web application designed for independent tuition teachers and private tutors to manage students, class schedules, attendance, homework, submissions, exams, and fee collections. Built with **FastAPI**, **MongoDB Atlas**, **Tailwind CSS**, and **JWT authentication**.

---

## 🌟 Key Features & Updates

### 1. Branding & Direct UPI Payments
- **App Name**: **T5 ERP SYSTEM** displayed across desktop & mobile headers, dashboard banners, modals, and metadata.
- **Direct UPI Details**: Displays teacher UPI ID **`sayan2008c@pthdfc`** and auto-generates dynamic UPI payment QR codes on student fee portals.
- **Manual Payment Confirmation**: Payments are recorded and confirmed manually by the teacher after verifying bank statements. Preserves immutable audit history with reversal tracking.

### 2. Schedule, Class Mode & Calendar Month View
- **Online vs Offline Modes**:
  - Each scheduled class clearly designates its mode: **🌐 Online** or **📍 Offline (In-Person)**.
  - **Online Classes**: Meeting links (Google Meet, Zoom, etc.) are optional and displayed only for Online classes.
  - **Offline Classes**: Never require or display a meeting link.
- **Calendar Month Navigation**:
  - Displays scheduled classes for the current calendar month.
  - Interactive previous (`<`) and next (`>`) month controls and a "Current Month" button to navigate between months easily.
  - Filter by subject within the selected month.

### 3. Homework & Multi-Format Submissions
- **Dedicated Student Assignment**:
  - Teacher can assign homework to **All Students** or choose **Dedicated Students** (multi-select one or multiple students).
  - Homework appears exclusively on the dashboard and homework feed of assigned students.
  - **Strict Student Privacy**: When viewing homework, students can only see their own name and assignment details; other assigned students are hidden.
- **Universal File Format Support**:
  - Students can submit homework by either **pasting a link** (Google Drive, GitHub, etc.) or **uploading a solution file**.
  - Allows uploads of **any file format**, including `.c`, `.java`, `.py`, `.pdf`, `.ppt`, `.pptx`, `.docx`, `.zip`, images, and more.
  - Enforces a clear **25 MB file size limit** with upload progress and status indicators.
- **Student Names Beside Files**:
  - Homework review interface and student submission cards clearly display the **student's full name and username directly beside the submitted file or link**.
- **Review & Grading**:
  - Shows submission timestamps and late/on-time status.
  - Teacher evaluation interface with marks/grade assignment and individualized feedback.

### 4. Secure Password Management
- **Teacher Controls**:
  - Teachers can change their own password while signed in.
  - Teachers can set/reset any student's password to a chosen temporary or permanent password.
- **Student Controls**:
  - Students can change their own password while signed in.
  - If a student forgets their password, they must contact the teacher for a reset.
- **Security & Privacy**:
  - Passwords are encrypted using salted `bcrypt` hashing and are never stored or displayed in plain text.
  - Server-side RBAC ensures students cannot access account management or reset passwords for other students.

### 5. Attendance & Class Remarks / Feedback
- **Attendance Roster**:
  - Teacher can mark each student **Present**, **Absent**, **Late**, or **Excused** for each class session.
  - Includes class-level attendance summary and student attendance percentage analytics.
- **Class Remarks & Feedback**:
  - Both teachers and students can submit feedback, questions, or conceptual remarks after any class (Online or Offline).
  - Feedback is linked directly to the class session and student.
  - **Privacy Enforcement**: Feedback is visible only to the teacher and the submitting student, unless the teacher explicitly toggles the remark to be shared.
  - Teacher can manage and review all class feedback entries.

### 6. Student Username & Dual-Mode Login
- **Username Creation**: Teachers can assign a unique `username` (e.g., `aarav`, `ishan_2026`) when registering or editing students.
- **Dual Login Support**: Students and teachers can log in seamlessly using **either their username or email address** paired with their password.
- **Auto-Provisioning**: Usernames are validated for alphanumeric characters and automatically linked to user authentication records.

### 7. Instant Refresh on Every Menu
- **Interactive Refresh Buttons**: Every view (Dashboard, Students, Classes, Homework, Exams, Fees Ledger, Settings) includes a dedicated Refresh button with live spin indicators to retrieve real-time database state without reloading the browser window.
- **Global Header Refresh**: A persistent header refresh action provides one-click synchronization at all times.

### 8. Teacher Payment Recording Options
- **Omnipresent Recording**: Teachers have quick, dedicated options to record received tuition payments:
  - Global header action button (**+ Record Payment**)
  - Fees & Billing ledger toolbar
  - Dashboard unpaid student action cards
  - Student directory profile actions and detail view modal
- **Flexible Association**: Payments can be linked to a specific monthly tuition fee or recorded as a general advance payment with full audit notes, payment method selection (UPI, Cash, Bank Transfer), and transaction references.

### 9. Role-Based Access Control (RBAC) & Parent Privacy
- **Teacher**: Full administrative access across all records.
- **Student**: Access strictly restricted on the server to their own profile, schedule, homework, exams, feedback, and fee ledger.
- **Protected Guardian Contacts**: Parent/guardian mobile numbers and email addresses are private and viewable only by the teacher.

---

## 🗄️ MongoDB Atlas Data Model

All collections are indexed on frequently queried keys:

| Collection | Key Fields | Indexes |
|---|---|---|
| `users` | `_id`, `email`, `username`, `passwordHash`, `role`, `studentId`, `createdAt` | `email` (unique), `username`, `studentId` |
| `students` | `_id`, `name`, `username`, `grade`, `course`, `subjects`, `email`, `mobile`, `guardian` {name, mobile, email, relationship}, `enrollmentStatus`, `notes` | `email` (unique), `username`, `enrollmentStatus`, `name` |
| `classes` | `_id`, `title`, `subject`, `grade`, `mode` (`Online`/`Offline`), `date`, `startTime`, `endTime`, `meetingLink`, `notes`, `assignedStudentIds`, `status` | `date`, `subject`, `assignedStudentIds`, `mode` |
| `attendance`| `_id`, `classId`, `studentId`, `status`, `remarks`, `recordedAt` | Compound unique `(classId, studentId)`, `studentId` |
| `class_feedback` | `_id`, `classId`, `studentId`, `studentName`, `authorId`, `authorName`, `authorRole`, `feedback`, `sharedWithStudent`, `createdAt` | `classId`, `studentId`, `authorId`, `createdAt` |
| `homework` | `_id`, `title`, `subject`, `instructions`, `assignedStudentIds`, `assignedDate`, `dueDate`, `attachmentUrl`, `totalMarks` | `dueDate`, `assignedDate`, `subject` |
| `submissions` | `_id`, `homeworkId`, `studentId`, `submissionText`, `attachmentUrl`, `attachmentName`, `status`, `grade`, `feedback`, `submittedAt` | Compound unique `(homeworkId, studentId)`, `studentId`, `status` |
| `exams` | `_id`, `title`, `subject`, `grade`, `date`, `startTime`, `durationMinutes`, `totalMarks`, `syllabus`, `formLink` | `date`, `subject` |
| `fees` | `_id`, `studentId`, `period`, `amount`, `dueDate`, `description`, `createdAt` | `studentId`, `dueDate` |
| `payments` | `_id`, `studentId`, `feeId`, `amount`, `paidAt`, `method`, `reference`, `note`, `isReversal`, `reversalOf`, `createdAt` | `studentId`, `feeId`, `paidAt`, `createdAt` |
| `settings` | `type`, `teacherName`, `teacherEmail`, `teacherPhone`, `tuitionName`, `tuitionAddress`, `teacherUpiId`, `teacherUpiName` | `type` |

---

## 🚀 Quick Start & Setup Instructions

### 1. Prerequisites
- Python 3.10+ (or Python 3.14)
- A free [MongoDB Atlas](https://www.mongodb.com/atlas) account (or local MongoDB)

### 2. Configure MongoDB Atlas
1. Sign in to MongoDB Atlas and create a cluster.
2. In **Database Access**, create a database user and password.
3. In **Network Access**, whitelist your IP address (or `0.0.0.0/0`).
4. Copy your MongoDB connection string.

### 3. Setup Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure `.env` contains:
```env
# MongoDB Atlas Connection
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.abcde.mongodb.net/tuition_db?retryWrites=true&w=majority
DATABASE_NAME=tuition_db

# JWT Security Key
JWT_SECRET_KEY=super_secret_jwt_key_tuition_teacher_prod_2026

# Teacher Details & Updated Branding
TEACHER_NAME=Sayan
TEACHER_EMAIL=sayan@t5erp.com
TEACHER_PHONE=+91 98765 43210
TUITION_NAME=T5 ERP SYSTEM
TUITION_ADDRESS=Tuition Center, Kolkata, West Bengal

# Direct UPI ID for Payments
TEACHER_UPI_ID=sayan2008c@pthdfc
TEACHER_UPI_NAME=Sayan

ENABLE_DEMO_SEED=true
```

> **Zero-Config In-Memory Fallback:** If MongoDB Atlas is not configured or temporarily unreachable, the app automatically switches to its built-in local database engine for seamless operation.

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Run the Application
```powershell
python run.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 👥 Demo Accounts

| Role | Name | Email | Password |
|---|---|---|---|
| **Teacher** | Sayan | `teacher@tuition.com` | `Teacher@123` |
| **Student** | Aarav Mehta (Class 10 ICSE) | `aarav.mehta@example.com` | `Student@123` |
| **Student** | Diya Sen (Grade 12 CBSE) | `diya.sen@example.com` | `Student@123` |
| **Student** | Rohan Verma (Class 10 CBSE) | `rohan.verma@example.com` | `Student@123` |
| **Student** | Ananya Iyer (Grade 12 CBSE) | `ananya.iyer@example.com` | `Student@123` |

Quick-login shortcut buttons are also provided on the sign-in screen for instant 1-click access.

---

## 🧪 Automated Test Suite

Run the comprehensive test suite verifying all 13 modules:
```powershell
python test_app.py
```
Verification covers:
- System health and database engine
- Branding ("T5 ERP SYSTEM") and UPI ID ("sayan2008c@pthdfc")
- Teacher & student authentication and RBAC boundary enforcement
- Student management and guardian contact privacy
- Online vs. Offline class modes and calendar month query navigation
- Attendance rosters & bulk attendance marking
- Post-class remarks and teacher feedback privacy controls
- Multi-format homework uploads (.c, .java, etc.) with 25 MB limit
- Teacher setting student passwords & students changing their own passwords
- Exam scheduling with Google Form links
- Direct UPI payments, balances, and audit-safe payment reversals
