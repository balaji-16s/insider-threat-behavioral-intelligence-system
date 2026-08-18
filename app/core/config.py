from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Insider Threat Behavioral Intelligence System"
    env: str = "development"

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    database_url: str

    redis_host: str
    redis_port: int

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Google OAuth (create an OAuth 2.0 Client ID at
    # https://console.cloud.google.com/apis/credentials)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    frontend_url: str = "http://localhost:5173"

    # Notification & Escalation Settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "alerts@itbis.local"
    webhook_url: str = ""

    class Config:
        env_file = ".env"

settings = Settings()