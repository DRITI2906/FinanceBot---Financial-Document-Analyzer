from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    langsmith_api_key: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///./finance_chatbot.db"
    
    # LangSmith (optional for monitoring)
    langsmith_project: str = "finance-genai-chatbot"
    
    # File upload settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "./uploads"
    
    # Model settings
    default_llm: str = "gpt-4"
    temperature: float = 0.1
    
    # Risk analysis thresholds
    high_risk_transaction_amount: float = 100000  # ₹1L
    fraud_detection_enabled: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

def get_settings() -> Settings:
    return Settings()
