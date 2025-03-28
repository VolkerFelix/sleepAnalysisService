from typing import List

from pydantic import AnyHttpUrl, BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Areum Sleep Analysis Service"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    SHOW_DOCS: bool = True
    ALLOWED_ORIGINS: List[AnyHttpUrl] = []
    ML_MODEL_PATH: str = "app/models/trained/sleep_model.joblib"

    # Threshold settings for sleep detection
    SLEEP_DETECTION_THRESHOLD: float = 0.25
    MOVEMENT_THRESHOLD: float = 0.15
    DEEP_SLEEP_THRESHOLD: float = 0.1
    REM_SLEEP_THRESHOLD: float = 0.2
    
    # Time thresholds (in minutes)
    MIN_SLEEP_DURATION: int = 60  # Minimum duration to be considered valid sleep
    MIN_SLEEP_STAGE_DURATION: int = 5  # Minimum duration for a sleep stage

    # API keys for external services (if needed)
    ANALYTICS_ENGINE_API_KEY: str = ""
    ANALYTICS_ENGINE_URL: str = "http://data-analytics-engine:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()