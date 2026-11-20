from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import ChatMessage, Chatbot, ChatSession, KnowledgeDocument, Role, User


def _check_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(v.encode()) > 72:  # bcrypt's hard limit
        raise ValueError("Password must be at most 72 bytes")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    organization_name: str = Field(min_length=1, max_length=100)

    _pw = field_validator("password")(_check_password)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Role = Role.VIEWER

    _pw = field_validator("password")(_check_password)


class UserOut(BaseModel):
    id: str
    email: str
    role: Role
    organization_id: str

    @classmethod
    def of(cls, u: User) -> "UserOut":
        return cls(id=str(u.id), email=u.email, role=u.role, organization_id=u.organization_id)


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    system_prompt: Optional[str] = Field(default=None, max_length=4000)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)


class BotUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    system_prompt: Optional[str] = Field(default=None, max_length=4000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.5)


class BotOut(BaseModel):
    id: str
    name: str
    system_prompt: str
    temperature: float
    created_at: datetime

    @classmethod
    def of(cls, b: Chatbot) -> "BotOut":
        return cls(id=str(b.id), name=b.name, system_prompt=b.system_prompt,
                   temperature=b.temperature, created_at=b.created_at)


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    chunks_count: int
    error: Optional[str]
    uploaded_at: datetime

    @classmethod
    def of(cls, d: KnowledgeDocument) -> "DocumentOut":
        return cls(id=str(d.id), filename=d.filename, status=d.status,
                   chunks_count=d.chunks_count, error=d.error, uploaded_at=d.uploaded_at)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None, min_length=8, max_length=100)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str]


class SessionSummary(BaseModel):
    id: str
    message_count: int
    preview: str
    updated_at: datetime

    @classmethod
    def of(cls, s: ChatSession) -> "SessionSummary":
        first_user = next((m.content for m in s.messages if m.role == "user"), "")
        return cls(id=str(s.id), message_count=len(s.messages),
                   preview=first_user[:120], updated_at=s.updated_at)


class SessionDetail(BaseModel):
    id: str
    messages: list[ChatMessage]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, s: ChatSession) -> "SessionDetail":
        return cls(id=str(s.id), messages=s.messages, created_at=s.created_at, updated_at=s.updated_at)
