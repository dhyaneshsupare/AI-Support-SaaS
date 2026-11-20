from fastapi import APIRouter, Depends, status
from starlette.concurrency import run_in_threadpool

from app.deps import ADMIN, ANY_ROLE, MANAGER_UP, get_owned_bot, parse_object_id, require_roles
from app.models import Chatbot, ChatSession, KnowledgeDocument, User
from app.schemas import BotCreate, BotOut, BotUpdate, SessionDetail, SessionSummary
from app.services.vectorstore import get_vector_store
from fastapi import HTTPException

router = APIRouter(prefix="/bots", tags=["bots"])


@router.post("", response_model=BotOut, status_code=status.HTTP_201_CREATED)
async def create_bot(body: BotCreate, user: User = Depends(require_roles(*MANAGER_UP))):
    data = body.model_dump(exclude_none=True)
    bot = await Chatbot(organization_id=user.organization_id, **data).insert()
    return BotOut.of(bot)


@router.get("", response_model=list[BotOut])
async def list_bots(user: User = Depends(require_roles(*ANY_ROLE))):
    bots = await Chatbot.find(Chatbot.organization_id == user.organization_id).to_list()
    return [BotOut.of(b) for b in bots]


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(bot: Chatbot = Depends(get_owned_bot)):
    return BotOut.of(bot)


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(
    body: BotUpdate, bot: Chatbot = Depends(get_owned_bot),
    _: User = Depends(require_roles(*MANAGER_UP)),
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(bot, field, value)
    await bot.save()
    return BotOut.of(bot)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(bot: Chatbot = Depends(get_owned_bot), _: User = Depends(require_roles(ADMIN))):
    """Deletes the bot plus its documents, vectors and chat logs."""
    org_id, bot_id = bot.organization_id, str(bot.id)
    await run_in_threadpool(get_vector_store().delete_bot, org_id, bot_id)
    await KnowledgeDocument.find(KnowledgeDocument.chatbot_id == bot_id).delete()
    await ChatSession.find(ChatSession.chatbot_id == bot_id).delete()
    await bot.delete()


# ---- chat logs (read-only, any role) ----

@router.get("/{bot_id}/sessions", response_model=list[SessionSummary])
async def list_sessions(
    skip: int = 0, limit: int = 50,
    bot: Chatbot = Depends(get_owned_bot), _: User = Depends(require_roles(*ANY_ROLE)),
):
    limit = max(1, min(limit, 100))
    sessions = await (
        ChatSession.find(ChatSession.chatbot_id == str(bot.id))
        .sort(-ChatSession.updated_at).skip(max(skip, 0)).limit(limit).to_list()
    )
    return [SessionSummary.of(s) for s in sessions]


@router.get("/{bot_id}/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    bot: Chatbot = Depends(get_owned_bot), _: User = Depends(require_roles(*ANY_ROLE)),
):
    s = await ChatSession.find_one(
        ChatSession.id == parse_object_id(session_id), ChatSession.chatbot_id == str(bot.id)
    )
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return SessionDetail.of(s)
