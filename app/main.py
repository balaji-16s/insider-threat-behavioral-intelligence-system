from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.employees import router as employees_router
from app.api.v1.activity_logs import router as activity_logs_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.risk_scores import router as risk_scores_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.anomaly import router as anomaly_router
from app.api.v1.reports import router as reports_router
from app.api.v1.ueba import router as ueba_router
from app.api.v1.notifications import router as notifications_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(activity_logs_router)
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(risk_scores_router)
app.include_router(dashboard_router)
app.include_router(anomaly_router)
app.include_router(reports_router)
app.include_router(ueba_router)
app.include_router(notifications_router)



@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
