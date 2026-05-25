import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)


def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(os.path.join(PROJECT_DIR, ".env"))
load_env_file(os.path.join(BASE_DIR, ".env"))


def env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


class Settings:
    APP_NAME = os.getenv("APP_NAME", "monitor-system")
    APP_ENV = os.getenv("APP_ENV", "dev")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = env_int("MYSQL_PORT", 3306)
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "monitor_db")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "monitor-app-dev-secret-key-change-me")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = env_int("JWT_EXPIRE_MINUTES", 60 * 24)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123456")

    AI_WORKER_USERNAME = os.getenv("AI_WORKER_USERNAME", "ai_worker")
    AI_WORKER_PASSWORD = os.getenv("AI_WORKER_PASSWORD", "ai_pass666")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

    ROLE_ADMIN = "admin"
    ROLE_OPERATOR = "operator"
    ROLE_VIEWER = "viewer"
    ROLE_AI_WORKER = "ai_worker"

    @property
    def cors_allow_origins(self):
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
