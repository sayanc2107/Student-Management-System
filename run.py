import os
import uvicorn
from app.config import settings

if __name__ == "__main__":
    port = settings.server_port
    host = settings.APP_HOST or "0.0.0.0"
    print(f"Starting T5 ERP SYSTEM on http://{host}:{port} (Env: {settings.APP_ENV})")
    print(f"Currency: {settings.CURRENCY_SYMBOL} | Timezone: {settings.TIMEZONE} | Database: {settings.DATABASE_NAME}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False
    )
