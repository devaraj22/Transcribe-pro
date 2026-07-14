from pydantic_settings import BaseSettings

class FrontendSettings(BaseSettings):
    BACKEND_URL: str = "http://127.0.0.1:8000"

settings = FrontendSettings()
