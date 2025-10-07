# filename: masfro-backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Define the variables you expect to be in your .env file
    GOOGLE_API_KEY: str
    DATABASE_URL: str  # Provide a default value
    TWITTER_EMAIL: str
    TWITTER_PASSWORD: str
    # This tells Pydantic to load variables from a file named .env
    model_config = SettingsConfigDict(env_file=".env")

# Create a single, reusable instance of the settings
settings = Settings()