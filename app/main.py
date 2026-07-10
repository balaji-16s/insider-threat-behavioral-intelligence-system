from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.auth import router as auth_router

app = FastAPI(title=settings.app_name)
app.include_router(auth_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
