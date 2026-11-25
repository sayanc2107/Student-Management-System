import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager, get_database
from app.seed_data import seed_demo_data_if_empty
from app.routers import (
    auth,
    dashboard,
    students,
    classes,
    attendance,
    homework,
    exams,
    fees,
    settings as settings_router
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("student_management")

async def run_safe_migrations(db):
    """Safely updates schema and configurations while preserving existing data"""
    try:
        # 1. Update settings profile with updated branding & UPI ID
        await db.settings.update_one(
            {"type": "tuition_profile"},
            {"$set": {
                "tuitionName": settings.TUITION_NAME,
                "teacherUpiId": settings.TEACHER_UPI_ID,
                "teacherUpiName": settings.TEACHER_UPI_NAME
            }}
        )

        # 2. Ensure existing classes have a mode (Online / Offline)
        classes_cursor = db.classes.find({"mode": {"$exists": False}})
        unmigrated_classes = await classes_cursor.to_list(1000)
        for c in unmigrated_classes:
            mode = "Online" if c.get("meetingLink") else "Offline"
            meeting_link = c.get("meetingLink", "") if mode == "Online" else ""
            await db.classes.update_one(
                {"_id": c["_id"]},
                {"$set": {"mode": mode, "meetingLink": meeting_link}}
            )

        # 3. Create index for class_feedback
        await db.class_feedback.create_index("classId")
        await db.class_feedback.create_index("studentId")
        await db.class_feedback.create_index("createdAt")

        # 4. Migrate existing users and students to have usernames
        import re
        # Teacher username
        teachers_without_uname = await db.users.find({"role": "teacher", "username": {"$exists": False}}).to_list(100)
        for t in teachers_without_uname:
            await db.users.update_one({"_id": t["_id"]}, {"$set": {"username": "teacher"}})

        # Student usernames
        students_without_uname = await db.students.find({"username": {"$exists": False}}).to_list(1000)
        for s in students_without_uname:
            s_name = s.get("name", "student")
            s_email = s.get("email", "")
            base_u = re.sub(r'[^a-zA-Z0-9_.]', '', s_name.lower().split()[0]) or s_email.split('@')[0].lower()
            if len(base_u) < 3:
                base_u = "student"
            candidate = base_u
            counter = 1
            while await db.users.find_one({"username": candidate, "studentId": {"$ne": str(s["_id"])}}):
                candidate = f"{base_u}{counter}"
                counter += 1
            await db.students.update_one({"_id": s["_id"]}, {"$set": {"username": candidate}})
            await db.users.update_one({"$or": [{"studentId": s["_id"]}, {"studentId": str(s["_id"])}, {"email": s_email}]}, {"$set": {"username": candidate}})

        logger.info("Safe database migrations executed successfully.")
    except Exception as e:
        logger.warning(f"Migration note: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB Atlas (or local fallback)
    logger.info("Initializing Tuition Student Management System...")
    await db_manager.connect()
    db = get_database()

    # Seed demo data if enabled
    if settings.ENABLE_DEMO_SEED:
        await seed_demo_data_if_empty(db)

    # Run safe schema and config migrations
    await run_safe_migrations(db)

    yield

    # Shutdown
    await db_manager.disconnect()
    logger.info("Shutdown complete.")

app = FastAPI(
    title="Tuition Student Management System",
    description="Simple, responsive web app for independent tuition teachers and students with MongoDB Atlas integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "uploads", "submissions"), exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Include Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(students.router)
app.include_router(classes.router)
app.include_router(attendance.router)
app.include_router(homework.router)
app.include_router(exams.router)
app.include_router(fees.router)
app.include_router(settings_router.router)

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "tuition_name": settings.TUITION_NAME,
            "teacher_name": settings.TEACHER_NAME,
            "currency_symbol": settings.CURRENCY_SYMBOL,
            "teacher_upi_id": settings.TEACHER_UPI_ID,
            "teacher_upi_name": settings.TEACHER_UPI_NAME
        }
    )

@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "databaseEngine": "MongoDB Atlas" if db_manager.is_atlas else "Local/Memory Fallback",
        "connectionStatus": db_manager.connection_status,
        "timezone": settings.TIMEZONE,
        "currency": settings.CURRENCY_SYMBOL
    }
