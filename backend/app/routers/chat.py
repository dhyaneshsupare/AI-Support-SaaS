import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from app.deps import parse_object_id
from app.models import Chatbot, ChatMessage, ChatSession, utcnow
from app.schemas import ChatRequest, ChatResponse
from app.services import rag
from app.services.embeddings import ConfigError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public/bots", tags=["public chat"])


@router.post("/{bot_id}/chat", response_model=ChatResponse)
async def chat(bot_id: str, body: ChatRequest):
    """Unauthenticated endpoint used by the customer-facing widget.

    The organization is looked up from the bot record, never taken from the request.
    """
    bot = await Chatbot.get(parse_object_id(bot_id))
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")
    org_id, bid = bot.organization_id, str(bot.id)

    session_id = body.session_id or uuid.uuid4().hex
    session_key = f"{bid}:{session_id}"
    session = await ChatSession.find_one(ChatSession.session_key == session_key)
    history = [{"role": m.role, "content": m.content} for m in (session.messages if session else [])]

    try:
        result = await run_in_threadpool(
            rag.answer_question, org_id=org_id, bot_id=bid, system_prompt=bot.system_prompt,
            temperature=bot.temperature, question=body.question, history=history,
        )
    except ConfigError:
        logger.error("Server is missing required AI configuration")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Assistant is not configured")
    except Exception:
        logger.exception("Chat generation failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The assistant is unavailable, try again shortly")

    if session is None:
        try:
            session = await ChatSession(session_key=session_key, organization_id=org_id, chatbot_id=bid).insert()
        except DuplicateKeyError:  # two first messages raced
            session = await ChatSession.find_one(ChatSession.session_key == session_key)

    new_messages = [
        ChatMessage(role="user", content=body.question).model_dump(),
        ChatMessage(role="assistant", content=result["answer"], sources=result["sources"]).model_dump(),
    ]
    await ChatSession.find_one(ChatSession.id == session.id).update(
        {"$push": {"messages": {"$each": new_messages}}, "$set": {"updated_at": utcnow()}}
    )
    return ChatResponse(session_id=session_id, answer=result["answer"], sources=result["sources"])
