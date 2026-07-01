import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Dynamically locate the project root directory
# This finds the directory containing your main application files.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """
    The central settings manager for the entire application.
    Pydantic automatically looks into the environment variables and the 
    specified .env file to fill these fields on application startup.
    """
    
    # --- Project Metadata Settings ---
    PROJECT_NAME: str = "Hackathon Context Engine"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # --- Secure API Keys & Credentials ---
    # These variables MUST exist in your .env file or environment, 
    # otherwise Pydantic will throw a clear validation error on boot.
    LLM_API_KEY: str
    NEWS_API_KEY: str

    # --- Infrastructure Database Settings ---
    # We assign clean defaults so the app runs smoothly out of the box.
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # --- Pydantic Engine Configuration Configuration ---
    # We tell Pydantic exactly how to discover the configuration files.
    model_config = SettingsConfigDict(
        # Point directly to the location of the live configuration file
        env_file=os.path.join(BASE_DIR, ".env"),
        # If the file is missing or some variables aren't found, check system variables
        env_file_encoding="utf-8",
        # Ignore extra variables written inside the .env file that aren't defined here
        extra="ignore",
        # Case-insensitive reading (e.g., reads 'llm_api_key' even if it's lowercase)
        case_sensitive=True
    )


# 2. Instantiate the class to create a single global settings object
settings = Settings()