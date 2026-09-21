from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Celeste Anilisys API"
    database_url: str = "postgresql+psycopg://celeste:celeste@localhost:5432/celeste"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
