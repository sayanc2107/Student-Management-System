import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_ENV: str = "development"
    PORT: Optional[int] = None  # Render sets PORT dynamically
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"

    JWT_SECRET_KEY: str = "dev_secret_key_tuition_student_mgmt_change_in_production_9876543210"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    MONGODB_URI: str = "mongodb://localhost:27017/tuition_db"
    DATABASE_NAME: str = "tuition_db"

    TIMEZONE: str = "Asia/Kolkata"
    CURRENCY_SYMBOL: str = "₹"
    CURRENCY_CODE: str = "INR"

    TEACHER_NAME: str = "Dr. Rajesh Sharma"
    TEACHER_EMAIL: str = "rajesh.sharma.tuitions@gmail.com"
    TEACHER_PHONE: str = "+91 98765 43210"
    TEACHER_WHATSAPP: str = "+91 98765 43210"
    TUITION_NAME: str = "T5 ERP SYSTEM"
    TUITION_ADDRESS: str = "Flat 302, Sunrise Heights, 15th Cross, Malleshwaram, Bengaluru 560003"

    TEACHER_UPI_ID: str = "sayan2008c@pthdfc"
    TEACHER_UPI_NAME: str = "Sayan"
    TEACHER_UPI_QR_URL: Optional[str] = ""

    # Never seed demo data automatically in production. Default is False.
    ENABLE_DEMO_SEED: bool = False

    @property
    def server_port(self) -> int:
        """Returns port provided by environment (e.g. Render PORT) or configured APP_PORT"""
        env_port = os.environ.get("PORT")
        if env_port:
            try:
                return int(env_port)
            except ValueError:
                pass
        return self.PORT or self.APP_PORT or 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
