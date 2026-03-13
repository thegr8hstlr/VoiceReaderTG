from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    anthropic_api_key: str
    openai_api_key: str
    vapi_api_key: str
    vapi_public_key: str
    base_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
