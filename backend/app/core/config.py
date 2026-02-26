from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    rate_limit_rpm: int = 15
    daily_limit: int = 1500
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llama3"
    max_file_size_mb: int = 10
    queue_max_size: int = 100

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def rate_limit_string(self) -> str:
        return f"{self.rate_limit_rpm}/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
