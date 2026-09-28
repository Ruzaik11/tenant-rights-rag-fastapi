from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    # The API connects as a read-only user; only ingestion can write.
    database_url_api: str
    database_url_ingest: str

    anthropic_api_key: SecretStr
    claude_model: str

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    # bge-small reads at most 512 tokens, leave some headroom
    max_chunk_tokens: int = 480

    data_dir: Path = BASE_DIR / "data"

    # Origins the browser may call the API from (where the frontend is served)
    cors_origins: list[str] = ["null"]

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


settings = Settings()
