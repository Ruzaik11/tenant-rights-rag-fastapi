from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.core.config import settings


@lru_cache(maxsize=1)
def api_engine() -> Engine:
    return create_engine(settings.database_url_api, pool_pre_ping=True)


@lru_cache(maxsize=1)
def ingest_engine() -> Engine:
    return create_engine(settings.database_url_ingest, pool_pre_ping=True)
