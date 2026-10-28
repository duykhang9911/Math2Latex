# Backend guide

- `app/api/`: HTTP route, validation, transaction, enqueue.
- `app/core/`: database/Redis configuration and dependencies.
- `app/models/`: SQLAlchemy mappings.
- `app/schemas/`: Pydantic API contracts.
- `app/services/`: render/detect/crop/OCR use cases.
- `alembic/versions/`: immutable schema history; create a new revision.
- `tests/` is proposed; it is not currently a formal suite.

Keep model inference in RQ worker processes. Keep DB state canonical. Job functions need importable module paths and serializable arguments. Validate upload, bbox and document/formula ownership in API. Test queue unavailable, duplicate enqueue, worker restart and model failure.