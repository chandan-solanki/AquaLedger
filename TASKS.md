# TASKS.md

# Sprint 1 - Backend Foundation

**Sprint Goal**

Build a production-ready FastAPI backend foundation. No business modules should be implemented in this sprint.

---

# Phase 1 - Project Initialization

## Project Setup

- [ ] Create backend directory
- [ ] Initialize project using `uv`
- [ ] Create Python virtual environment
- [ ] Configure `pyproject.toml`
- [ ] Create `.python-version`
- [ ] Create `.gitignore`
- [ ] Create `.env`
- [ ] Create `.env.example`
- [ ] Verify project runs correctly

---

# Phase 2 - Install Dependencies

## Core

- [ ] FastAPI
- [ ] Uvicorn
- [ ] Pydantic v2
- [ ] Pydantic Settings

## Database

- [ ] SQLAlchemy 2
- [ ] Alembic
- [ ] asyncpg

## Development

- [ ] Ruff
- [ ] Pytest
- [ ] HTTPX
- [ ] Python Dotenv

---

# Phase 3 - Project Structure

Create production-ready folder structure.

```
backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── middleware/
│   ├── utils/
│   ├── common/
│   └── main.py
│
├── migrations/
├── tests/
├── scripts/
└── logs/
```

- [ ] Create folders
- [ ] Create `__init__.py`
- [ ] Create main.py

---

# Phase 4 - Configuration

## Environment

- [ ] Environment loader
- [ ] Settings class
- [ ] Development configuration
- [ ] Production configuration

---

# Phase 5 - Database

- [ ] Configure PostgreSQL connection
- [ ] Configure SQLAlchemy
- [ ] Configure Async Session
- [ ] Configure Base Model
- [ ] Configure Alembic
- [ ] Generate initial migration
- [ ] Verify migration works

---

# Phase 6 - API Foundation

- [ ] Create FastAPI application
- [ ] Configure lifespan
- [ ] Configure API versioning
- [ ] Configure CORS
- [ ] Register routers
- [ ] Create health endpoint

Health endpoint

GET /api/v1/health

Response

```json
{
  "status": "healthy"
}
```

---

# Phase 7 - Logging

- [ ] Configure structured logging
- [ ] Console logging
- [ ] File logging
- [ ] Error logging

---

# Phase 8 - Error Handling

- [ ] Global exception handler
- [ ] Validation error handler
- [ ] HTTP exception handler
- [ ] Standard error response

---

# Phase 9 - Testing

- [ ] Configure pytest
- [ ] Create first API test
- [ ] Test health endpoint

---

# Phase 10 - Code Quality

- [ ] Configure Ruff
- [ ] Configure formatting
- [ ] Verify lint passes
- [ ] Verify type checking

---

# Sprint Deliverables

At the end of Sprint 1 the project should have:

- FastAPI running
- PostgreSQL connected
- Alembic working
- Environment configuration
- Logging
- Error handling
- Health endpoint
- Testing setup
- Production-ready folder structure

No authentication.

No users.

No companies.

No invoices.

No business logic.

---

# Claude Code Instructions

Implement this sprint incrementally.

Before writing code:

1. Explain the implementation plan.
2. Create the folder structure.
3. Configure dependencies.
4. Configure database.
5. Configure FastAPI.
6. Configure testing.
7. Stop after Sprint 1 is complete.

Do not implement Authentication or any ERP modules.