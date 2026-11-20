from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, EmailStr, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    ADMIN = "ADMIN"      # everything, including managing users and deleting bots
    MANAGER = "MANAGER"  # create/edit bots, upload/delete documents
    VIEWER = "VIEWER"    # read-only: bots, documents, chat logs


class Organization(Document):
    name: str
    plan_tier: str = "free"
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "organizations"


class User(Document):
    email: Annotated[EmailStr, Indexed(unique=True)]
    hashed_password: str
    role: Role = Role.VIEWER
    organization_id: Annotated[str, Indexed()]
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "users"


class Chatbot(Document):
    name: str
    system_prompt: str = "You are a polite, concise AI customer support agent for our company."
    temperature: float = 0.2
    organization_id: Annotated[str, Indexed()]
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "chatbots"


class KnowledgeDocument(Document):
    filename: str
    status: str = "processing"  # processing | ready | failed
    chunks_count: int = 0
    error: Optional[str] = None
    chatbot_id: Annotated[str, Indexed()]
    organization_id: Annotated[str, Indexed()]
    uploaded_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "knowledge_documents"


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    sources: list[str] = []
    timestamp: datetime = Field(default_factory=utcnow)


class ChatSession(Document):
    # "<bot_id>:<client session id>" - unique per bot, so two bots never share a session
    session_key: Annotated[str, Indexed(unique=True)]
    organization_id: Annotated[str, Indexed()]
    chatbot_id: Annotated[str, Indexed()]
    messages: list[ChatMessage] = []
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "chat_sessions"


ALL_MODELS = [Organization, User, Chatbot, KnowledgeDocument, ChatSession]
