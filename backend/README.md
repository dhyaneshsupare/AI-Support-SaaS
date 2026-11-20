# AI Customer Support SaaS - Backend (Phase 1-3)

FastAPI + MongoDB (Beanie) + ChromaDB + Hugging Face Inference API.

## Run it

```bash
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then fill in JWT_SECRET_KEY and HF_TOKEN
```

MongoDB: either `docker run -d -p 27017:27017 --name mongo mongo:7`, a local install, or a free Atlas cluster (put its URI in `.env`).

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs. Try, in order:
1. `POST /api/v1/auth/register` -> copy the `access_token`, click **Authorize** and paste it.
2. `POST /api/v1/bots` -> copy the bot `id`.
3. `POST /api/v1/bots/{bot_id}/documents` -> upload a PDF; poll `GET .../documents` until `status` is `ready`.
4. `POST /api/v1/public/bots/{bot_id}/chat` (no auth - this is what the widget calls) with `{"question": "..."}`; reuse the returned `session_id` for follow-ups.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q          # needs a MongoDB on localhost (or MONGODB_URI); uses a throwaway test database
```
The tests use real MongoDB and real ChromaDB, with fake embeddings and a fake LLM, so they need no network or token.

## Roles
| Role | Can do |
|---|---|
| ADMIN | everything, incl. add/remove users, delete bots |
| MANAGER | create/edit bots, upload/delete documents |
| VIEWER | read bots, documents, chat logs |

## Tenant isolation (how it works)
- The organization always comes from the logged-in user in the database, never from the URL or token.
- Bot routes load the bot through `get_owned_bot`: wrong org gives a 404.
- ChromaDB is only touched through `services/vectorstore.py`, which forces an `organization_id` + `chatbot_id` filter on every search and delete.
- The public chat endpoint derives the organization from the bot record.
