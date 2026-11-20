from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.deps import ADMIN, parse_object_id, require_roles
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def add_member(body: UserCreate, admin: User = Depends(require_roles(ADMIN))):
    """Admin adds a teammate to their own organization."""
    try:
        user = await User(
            email=body.email.lower(), hashed_password=hash_password(body.password),
            role=body.role, organization_id=admin.organization_id,
        ).insert()
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    return UserOut.of(user)


@router.get("", response_model=list[UserOut])
async def list_members(admin: User = Depends(require_roles(ADMIN))):
    users = await User.find(User.organization_id == admin.organization_id).to_list()
    return [UserOut.of(u) for u in users]


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(user_id: str, admin: User = Depends(require_roles(ADMIN))):
    target = await User.find_one(
        User.id == parse_object_id(user_id), User.organization_id == admin.organization_id
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't remove yourself")
    await target.delete()
