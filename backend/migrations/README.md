This directory is reserved for Alembic migrations.

The SQLAlchemy models for the multi-tenant SaaS layer live under
`backend/app/db_models.py` and are registered on the shared `Base` in
`backend/app/db.py`.

To generate migrations (once Alembic is installed and configured in your
environment), you can run commands similar to:

    alembic init migrations
    # Edit migrations/env.py to import `backend.app.db.Base` as target_metadata
    alembic revision --autogenerate -m "initial schema"
    alembic upgrade head

For local development, the FastAPI app calls `init_db()` on startup, which
invokes `Base.metadata.create_all`. In production, prefer Alembic migrations
instead of relying on `create_all`.

