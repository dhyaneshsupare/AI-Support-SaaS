from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config import get_settings
from app.models import ALL_MODELS


async def init_db() -> AsyncMongoClient:
    """Connect to MongoDB and register the Beanie models (creates indexes)."""
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb_uri)
    await init_beanie(database=client[settings.mongodb_db_name], document_models=ALL_MODELS)
    return client
