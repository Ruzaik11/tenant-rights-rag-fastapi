from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the project root
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database: read-only role for the API, write role for ingestion
    database_url_api: str
    database_url_ingest: str

    # Claude. SecretStr hides the value when printed or logged
    anthropic_api_key: SecretStr
    claude_model: str = "claude-sonnet-5"

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    max_chunk_tokens: int = 480  # stays under the model's 512 limit

    # Paths
    frontend_dir: Path = ROOT_DIR / "frontend"
    data_dir: Path = ROOT_DIR / "backend" / "data"
    raw_dir: Path = ROOT_DIR / "backend" / "data" / "raw"

    # Limits
    max_question_chars: int = 1000


def mask_url(url: str) -> str:
    """Hide the password in a connection URL so it's safe to print."""
    parts = urlsplit(url)
    if parts.password:
        netloc = parts.netloc.replace(f":{parts.password}@", ":****@")
        parts = parts._replace(netloc=netloc)
    return urlunsplit(parts)


settings = Settings()


if __name__ == "__main__":
    pdf = settings.raw_dir / "ON" / "rta-2006.pdf"

    print("Project root :", ROOT_DIR)
    print("API DB       :", mask_url(settings.database_url_api))
    print("Ingest DB    :", mask_url(settings.database_url_ingest))
    print("Claude key   :", settings.anthropic_api_key)
    print("Claude model :", settings.claude_model)
    print("Embeddings   :", settings.embedding_model, f"({settings.embedding_dim} dims)")
    print("Max tokens   :", settings.max_chunk_tokens)
    print("Frontend dir :", "exists" if settings.frontend_dir.exists() else "MISSING", settings.frontend_dir)
    print("RTA PDF      :", "exists" if pdf.exists() else "MISSING", pdf)