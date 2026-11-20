from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.deps import get_current_user
from app.models import Organization, Role, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """Create a new organization and its first ADMIN user."""
    email = body.email.lower()
    if await User.find_one(User.email == email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    org = await Organization(name=body.organization_name).insert()
    try:
        user = await User(
            email=email, hashed_password=hash_password(body.password),
            role=Role.ADMIN, organization_id=str(org.id),
        ).insert()
    except DuplicateKeyError:
        await org.delete()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = await User.find_one(User.email == body.email.lower())
    if not verify_password(body.password, user.hashed_password if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.of(user)
