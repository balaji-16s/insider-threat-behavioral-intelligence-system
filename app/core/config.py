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

    class Config:
        env_file = ".env"

settings = Settings()