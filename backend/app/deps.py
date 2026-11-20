"""Auth + tenant-scoping dependencies. Every tenant-scoped route goes through these."""
import jwt
from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models import Chatbot, Role, User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def parse_object_id(value: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid or missing token", headers={"WWW-Authenticate": "Bearer"}
    )
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise unauthorized
    try:
        user = await User.get(PydanticObjectId(payload["sub"]))
    except (InvalidId, TypeError):
        raise unauthorized
    if user is None:
        raise unauthorized
    return user  # role and organization come from the DB, never from the token


def require_roles(*roles: Role):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return checker


async def get_owned_bot(bot_id: str, user: User = Depends(get_current_user)) -> Chatbot:
    """Load a bot only if it belongs to the caller's organization. 404 (not 403) so IDs don't leak."""
    bot = await Chatbot.find_one(
        Chatbot.id == parse_object_id(bot_id), Chatbot.organization_id == user.organization_id
    )
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")
    return bot


ADMIN = Role.ADMIN
MANAGER_UP = (Role.ADMIN, Role.MANAGER)
ANY_ROLE = (Role.ADMIN, Role.MANAGER, Role.VIEWER)
