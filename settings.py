from pydantic_settings import BaseSettings
from typing import Optional

class AppSettings(BaseSettings):
    # MongoDB settings
    MONGODB_URI: str = "mongodb://admin:password@mongodb:27017/"
    MONGODB_DB_NAME: str = "ticktick_mcp"
    
    # DeepSeek API settings
    DEEPSEEK_API_KEY: Optional[str] = None
    
    # Debug settings
    DEBUG_PROJECTS: str = ""  # Comma-separated list of project names to debug
    
    # Dida365 settings
    DIDA365_CLIENT_ID: Optional[str] = None
    DIDA365_CLIENT_SECRET: Optional[str] = None
    DIDA365_REDIRECT_URI: Optional[str] = "http://localhost:8080/callback"
    DIDA365_SERVICE_TYPE: Optional[str] = "ticktick"
    DIDA365_LOG_LEVEL: Optional[str] = "INFO"
    DIDA365_ACCESS_TOKEN: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the environment

# Create a global settings instance
settings = AppSettings() 