# 🎓 T5 ERP SYSTEM - Tuition Student Management System

A simple, responsive, and robust student management web application designed for independent tuition teachers and private tutors to manage students, class schedules, attendance, homework, submissions, exams, and fee collections. Built with **FastAPI**, **MongoDB Atlas**, **Tailwind CSS**, and **JWT authentication**.

---

## 🌟 Key Features

### 1. Branding & Direct UPI Payments
- **App Name**: **T5 ERP SYSTEM** displayed across desktop & mobile headers, dashboard banners, modals, and metadata.
- **Direct UPI Details**: Displays teacher UPI ID **`sayan2008c@pthdfc`** and auto-generates dynamic UPI payment QR codes on student fee portals.
- **Manual Payment Recording**: Payments are recorded and confirmed manually by the teacher after verifying bank statements. Preserves immutable audit history with reversal tracking.

### 2. Schedule, Class Mode & Calendar Month View
- **Online vs Offline Modes**:
  - Each scheduled class clearly designates its mode: **🌐 Online** or **📍 Offline (In-Person)**.
  - **Online Classes**: Meeting links (Google Meet, Zoom, etc.) are optional and displayed only for Online classes.
  - **Offline Classes**: Never require or display a meeting link.
- **Dedicated Student Assignment**: Teacher can schedule classes for **All Students** or select **Dedicated Students**. Assigned students only see their own name and sessions.
- **Calendar Month Navigation**:
  - Displays scheduled classes for the current calendar month.
  - Interactive previous (`<`) and next (`>`) month controls and a "Current Month" button to navigate between months easily.

### 3. Homework & Multi-Format Submissions
- **Dedicated Student Assignment**: Assign homework to specific students or the entire class.
- **Universal File Format Support**:
  - Students can submit homework by either **pasting a link** (Google Drive, GitHub, etc.) or **uploading a solution file**.
  - Allows uploads of **any file format**, including `.c`, `.java`, `.py`, `.pdf`, `.ppt`, `.pptx`, `.docx`, `.zip`, images, and more.
  - Enforces a clear **25 MB file size limit** with upload progress and status indicators.
- **Student Names Beside Files**: Review interface displays student names directly alongside submitted code/documents.
- **Review & Grading**: Marks/grade evaluation with individualized feedback.

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
- **Attendance Roster**: Mark students **Present**, **Absent**, **Late**, or **Excused**.
- **Class Remarks & Feedback**: Both teachers and students can submit feedback after any class. Feedback remains private between teacher and student unless explicitly shared.

### 6. Student Username & Dual-Mode Login
- **Username Support**: Teachers can assign custom usernames (e.g., `aarav`, `ishan_2026`).
- **Dual Login Support**: Sign in using **either username or email address** with your password.

### 7. Instant Refresh on Every Menu
- Dedicated **Refresh** buttons with spin indicators on every view (Dashboard, Students, Classes, Homework, Exams, Fees, Settings) to retrieve live database state without reloading the browser.

---

## 🗄️ MongoDB Atlas Data Model

All collections are indexed on frequently queried keys:

| Collection | Key Fields | Indexes |
|---|---|---|
| `users` | `_id`, `email`, `username`, `passwordHash`, `role`, `studentId`, `isDemo`, `createdAt` | `email` (unique), `username`, `studentId` |
| `students` | `_id`, `name`, `username`, `grade`, `course`, `subjects`, `email`, `mobile`, `guardian` {name, mobile, email, relationship}, `enrollmentStatus`, `notes`, `isDemo` | `email` (unique), `username`, `enrollmentStatus`, `name` |
| `classes` | `_id`, `title`, `subject`, `grade`, `mode` (`Online`/`Offline`), `date`, `startTime`, `endTime`, `meetingLink`, `notes`, `assignedStudentIds`, `isDemo`, `status` | `date`, `subject`, `assignedStudentIds`, `mode` |
| `attendance`| `_id`, `classId`, `studentId`, `status`, `remarks`, `isDemo`, `recordedAt` | Compound unique `(classId, studentId)`, `studentId` |
| `class_feedback` | `_id`, `classId`, `studentId`, `studentName`, `authorId`, `authorName`, `authorRole`, `feedback`, `sharedWithStudent`, `createdAt` | `classId`, `studentId`, `authorId`, `createdAt` |
| `homework` | `_id`, `title`, `subject`, `instructions`, `assignedStudentIds`, `assignedDate`, `dueDate`, `attachmentUrl`, `totalMarks`, `isDemo` | `dueDate`, `assignedDate`, `subject` |
| `submissions` | `_id`, `homeworkId`, `studentId`, `submissionText`, `attachmentUrl`, `attachmentName`, `status`, `grade`, `feedback`, `submittedAt` | Compound unique `(homeworkId, studentId)`, `studentId`, `status` |
| `exams` | `_id`, `title`, `subject`, `grade`, `date`, `startTime`, `durationMinutes`, `totalMarks`, `syllabus`, `formLink`, `isDemo` | `date`, `subject` |
| `fees` | `_id`, `studentId`, `period`, `amount`, `dueDate`, `description`, `isDemo`, `createdAt` | `studentId`, `dueDate` |
| `payments` | `_id`, `studentId`, `feeId`, `amount`, `paidAt`, `method`, `reference`, `note`, `isReversal`, `reversalOf`, `isDemo`, `createdAt` | `studentId`, `feeId`, `paidAt`, `createdAt` |
| `settings` | `type`, `teacherName`, `teacherEmail`, `teacherPhone`, `tuitionName`, `tuitionAddress`, `teacherUpiId`, `teacherUpiName` | `type` |

---

## 💻 Local Quick Start

### 1. Prerequisites
- Python 3.10+
- MongoDB Atlas connection string (or local MongoDB, or automatic in-memory fallback)

### 2. Environment Setup
Copy the example environment configuration:
```powershell
Copy-Item .env.example .env
```

Edit `.env` with your settings:
```env
MONGODB_URI=mongodb+srv://<db_user>:<db_password>@cluster0.abcde.mongodb.net/tuition_db?retryWrites=true&w=majority
DATABASE_NAME=tuition_db
JWT_SECRET_KEY=your_secure_random_jwt_key_here
APP_ENV=development
APP_PORT=8000
ENABLE_DEMO_SEED=false
TEACHER_NAME=Sayan
TEACHER_EMAIL=sayan@t5erp.com
TEACHER_UPI_ID=sayan2008c@pthdfc
TEACHER_UPI_NAME=Sayan
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the Application
```powershell
python run.py
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

> **Zero-Config In-Memory Fallback:** If MongoDB Atlas is not configured or temporarily unreachable, the app automatically switches to its built-in local database engine for development and testing.

---

## 🛠️ Demo Data Management (`seed.py`)

A dedicated, safe, and repeatable CLI tool is provided to manage fictional demo data:

### 1. Seed Demo Data (Idempotent)
Populates fictional teacher, student, class, homework, attendance, fee, and payment records labeled with IANA reserved example emails (`student1@example.com`, `teacher@example.com`):
```powershell
python seed.py --seed
```
*Note: Running this command multiple times will NOT create duplicate records.*

### 2. Check Database Status
Inspect counts of demo records vs. real production records across all collections:
```powershell
python seed.py --status
```

### 3. Safely Remove Demo Data
Removes only records flagged with `{"isDemo": true}`. Real student records, user accounts, and billing data are completely preserved:
```powershell
python seed.py --remove
```

### Demo Accounts for Testing

| Role | Username | Email | Password |
|---|---|---|---|
| **Teacher** | `teacher` | `teacher@example.com` (or `teacher@tuition.com`) | `Teacher@123` |
| **Student** | `aarav` | `student1@example.com` (or `aarav.mehta@example.com`) | `Student@123` |
| **Student** | `diya` | `student2@example.com` (or `diya.sen@example.com`) | `Student@123` |
| **Student** | `rohan` | `student3@example.com` | `Student@123` |
| **Student** | `ananya` | `student4@example.com` | `Student@123` |
| **Student** | `kabir` | `student5@example.com` | `Student@123` |

---

## ☁️ Deploying on Render with MongoDB Atlas

Follow these step-by-step instructions to deploy T5 ERP SYSTEM on Render:

### Step 1: Set Up MongoDB Atlas

1. **Sign In**: Log in to [MongoDB Atlas](https://cloud.mongodb.com/).
2. **Create Database User**:
   - Navigate to **Security** → **Database Access**.
   - Click **Add New Database User**.
   - Select **Password Authentication**.
   - Enter a username (e.g. `tuition_admin`) and a strong password. *(Note: If your password contains special characters like `@`, `:`, or `/`, URL-encode them in the URI).*
   - In **Database User Privileges**, select **Built-in Role** → **Read and write to any database** (or restrict specifically to `readWrite` on `tuition_db`).
   - Click **Add User**.
3. **Configure Network Access**:
   - Navigate to **Security** → **Network Access**.
   - Click **Add IP Address**.
   - Select **Allow Access From Anywhere** (`0.0.0.0/0`).
   - *Why is 0.0.0.0/0 required?* Render Free and Standard web services use dynamic outbound IP addresses that change over time. Security is maintained through TLS encryption, strong database user passwords, and database-level permissions.
   - Click **Confirm**.
4. **Copy Connection String**:
   - Navigate to **Deployment** → **Database**.
   - Click **Connect** next to your cluster.
   - Choose **Drivers** (Python / 3.12 or later).
   - Copy the SRV connection URI. It will look like:
     ```
     mongodb+srv://<username>:<password>@cluster0.xxxxxx.mongodb.net/?retryWrites=true&w=majority
     ```
   - Append `/tuition_db` after `.mongodb.net`:
     ```
     mongodb+srv://<username>:<password>@cluster0.xxxxxx.mongodb.net/tuition_db?retryWrites=true&w=majority
     ```

### Step 2: Deploy to Render

You can deploy using either the **Render Blueprint (`render.yaml`)** or manual **Web Service** setup:

#### Option A: Deploy via Blueprint (`render.yaml`)
1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com/), click **New +** → **Blueprint**.
3. Connect your GitHub repository.
4. Render will parse `render.yaml` and prompt for the required environment variables:
   - `MONGODB_URI`: Paste your MongoDB Atlas URI.
5. Click **Apply**.

#### Option B: Deploy as a Web Service Manually
1. In the Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository (`Student-Management-System`).
3. Configure the service settings:
   - **Name**: `t5-erp-system` (or your preferred name)
   - **Region**: Choose a region closest to your users (e.g., `Singapore` or `Frankfurt`)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
4. Under **Environment Variables**, add the following:

| Key | Value | Description |
|---|---|---|
| `MONGODB_URI` | `mongodb+srv://<user>:<password>@cluster0.../tuition_db?...` | Your Atlas connection URI *(Never commit to git)* |
| `DATABASE_NAME` | `tuition_db` | Target MongoDB database |
| `JWT_SECRET_KEY` | *(Click 'Generate' or enter a 64-char random hex)* | JWT signing secret |
| `APP_ENV` | `production` | Production environment flag |
| `ENABLE_DEMO_SEED` | `false` | Ensures demo data is NEVER auto-seeded in production |
| `TEACHER_NAME` | `Sayan` | Teacher display name |
| `TEACHER_EMAIL` | `sayan@t5erp.com` | Teacher contact email |
| `TEACHER_UPI_ID` | `sayan2008c@pthdfc` | Teacher UPI ID for fee collections |
| `TEACHER_UPI_NAME` | `Sayan` | Teacher UPI Payee Name |
| `TIMEZONE` | `Asia/Kolkata` | Application timezone |
| `CURRENCY_SYMBOL` | `₹` | Application currency symbol |

5. Click **Create Web Service**.
6. Render will automatically build the container, install dependencies, bind to dynamic `PORT`, and monitor health via `/health`.

---

## 🔒 Security & Privacy Best Practices

1. **Credentials & Secrets**:
   - Credentials are stored strictly in server-side environment variables and are never transmitted to browser clients.
   - All connection URIs logged by the server are automatically masked (`***:***`).
   - `.env` is included in `.gitignore` to prevent accidental commits.
2. **Health Check (`/health`)**:
   - Performs a safe `db.command("ping")` to verify Atlas cluster connectivity.
   - Reports engine status (`MongoDB Atlas` or `Local/Memory Fallback`) and uptime without revealing credentials or hostnames.
3. **Safe Initialization**:
   - Indexes for all collections (`users`, `students`, `classes`, `attendance`, `fees`, `payments`, etc.) are created safely on application startup without dropping or modifying existing data.
4. **Data Isolation**:
   - Students can only view their own profile, schedule, homework, feedback, and fee transactions. Parent contact details are strictly redacted for student accounts.

---

## 🧪 Automated Test Suite

Run the comprehensive test suite verifying all 17 feature suites and security checks:
```powershell
python test_app.py
```

Verification covers:
- System health check & safe status reporting
- Updated branding ("T5 ERP SYSTEM") and UPI ID ("sayan2008c@pthdfc")
- Teacher & student authentication with dual-mode login (username & email)
- Server-side RBAC enforcement (blocking students from teacher routes)
- Student management & guardian contact privacy redaction
- Online vs Offline class modes and meeting link isolation
- Calendar month navigation and query filtering
- Bulk attendance marking
- Post-class remarks & private teacher feedback controls
- Universal multi-format file uploads (`.c`, `.java`, etc.) with 25 MB limit
- Teacher setting student passwords & students changing their own passwords
- Exam scheduling with Google Form integration
- Direct UPI payments, balances, and audit-safe payment reversals
- Dedicated student assignment for online classes & homework
- Student submission name badges beside files
