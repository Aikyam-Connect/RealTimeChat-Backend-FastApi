from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "RealTimeChat"
    
    # Allow DATEBASE_URL to be None initially
    DATABASE_URL: Optional[str] = None
    
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE_CHANGE_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Database fields from user's .env (allowing lowercase aliases automatically via Pydantic or manual mapping if needed)
    # The error showed keys like 'db_user', 'db_password' etc.
    # Pydantic Settings is case-insensitive by default.
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = None
    DB_NAME: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL:
            # Handle user provided postgres:// which sqlalchemy might redundant
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            return url
        
        # Construct from components if available
        if self.DB_USER and self.DB_HOST:
            # Heuristic for TiDB/MySQL
            # If port is 4000 or host has tidbcloud => MySQL
            is_mysql = False
            if self.DB_PORT and str(self.DB_PORT) == "4000":
                is_mysql = True
            if "tidbcloud" in (self.DB_HOST or "").lower():
                is_mysql = True
            
            if is_mysql:
                # TiDB requires specific SSL settings sometimes, but let's try basic pymysql first.
                # Often standard pymysql works.
                # Format: mysql+pymysql://user:password@host:port/dbname
                return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?ssl_verify_cert=true&ssl_verify_identity=true"
            else:
                 return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
        # Final Fallback
        return "sqlite:///./sql_app.db"

settings = Settings()
