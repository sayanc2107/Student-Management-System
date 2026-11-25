import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting Tuition Student Management System on http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"Currency: {settings.CURRENCY_SYMBOL} | Timezone: {settings.TIMEZONE}")
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False
    )
