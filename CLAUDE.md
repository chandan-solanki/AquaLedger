# CLAUDE.md

# FishERP - AI Development Guide

This file defines how Claude Code should work on this project.

Follow these instructions throughout development.

---

# Project Overview

FishERP is a modern ERP system for the seafood industry.

The goal is to replace paper-based business operations with a digital platform.

Primary users

- Fish Traders
- Wholesalers
- Exporters
- Boat Owners
- Seafood Companies

Core modules

- Authentication
- Company Management
- Fish Management
- Boat Management
- Trip Management
- Invoice Management
- Payment Management
- Expense Management
- Reports & Analytics
- Document Management
- OCR (Future)
- AI Assistant (Future)

---

# Source of Truth

Before implementing any feature always read

- ARCHITECTURE.md
- TASKS.md

ARCHITECTURE.md is the project's source of truth.

Never change architectural decisions unless explicitly instructed.

---

# Technology Stack

## Frontend

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui

## Backend

- Python 3.13
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic v2
- uv package manager

## Database

- PostgreSQL

## Cache

- Redis

## Background Jobs

- Celery

## Storage

- Cloudflare R2 (S3 Compatible)

---

# Development Principles

Always build

- Clean
- Maintainable
- Scalable
- Production-ready

Prefer readability over clever code.

Avoid unnecessary abstractions.

Never overengineer the MVP.

---

# Architecture Rules

Use

- Modular Monolith
- Clean Architecture
- SOLID Principles

Never introduce microservices.

Never bypass architecture layers.

Application flow

Router

↓

Service

↓

Repository

↓

Database

Business logic belongs only inside Services.

Repositories only communicate with the database.

---

# Module Structure

Every backend module should follow this structure.

```
module/

router.py
service.py
repository.py
schemas.py
models.py
exceptions.py
constants.py
```

Never place business logic inside router.py.

---

# Database Rules

Database

PostgreSQL

Always use

Decimal

Never use float for financial calculations.

Money

NUMERIC(14,2)

Weight

NUMERIC(12,3)

Rate

NUMERIC(12,4)

Always create Alembic migrations.

Never manually modify production migrations.

---

# API Standards

Version

/api/v1

Use REST conventions.

Use proper HTTP status codes.

Validate all requests with Pydantic.

Return consistent JSON responses.

Never expose internal exceptions.

---

# Security Rules

Use

- JWT
- Refresh Tokens
- RBAC

Always validate

- Authentication
- Permissions
- Tenant access
- Ownership

Never trust frontend validation.

Never commit secrets or .env files.

---

# Business Rules

Issued invoices are immutable.

Payments are never deleted.

Ledger entries are append-only.

Financial corrections must use

- Credit Notes
- Reversal Entries

Never modify financial history.

---

# Coding Standards

- Use Python type hints.
- Keep functions small.
- Write reusable code.
- Avoid duplication.
- Prefer explicit code over magic.
- Write clear names.
- Document complex business logic.

---

# Testing

Every feature should include

- Unit Tests
- Integration Tests
- API Tests

Critical calculations must always be tested.

Especially

- Invoice calculations
- Payment allocation
- Profit calculations

---

# Performance

Always

- Use pagination
- Prevent N+1 queries
- Use eager loading where appropriate
- Add indexes for frequently queried columns

Do not cache financial calculations.

---

# Current Development Roadmap

Build modules in this order

1. Project Foundation
2. Authentication
3. Company Management
4. Fish Management
5. Invoice Management
6. Payment Management
7. Reports
8. Boat Management
9. Trip Management
10. Expense Management
11. Document Management
12. OCR
13. AI Assistant

Do not skip modules unless instructed.

---

# Current Goal

Current objective

Build a production-ready MVP.

Focus on replacing paper-based workflows before implementing AI features.

---

# What NOT To Build Yet

Unless explicitly requested

Do NOT implement

- Microservices
- Kubernetes
- OCR
- AI Chat
- WhatsApp Integration
- Multi-tenant SaaS
- Advanced Analytics

These will be added after the MVP.

---

# Definition of Done

A feature is complete only when

- Backend API implemented
- Validation implemented
- Database migration created
- Tests added
- Error handling complete
- Documentation updated
- No lint errors
- No type errors

---

# Claude Code Workflow

For every task

1. Read ARCHITECTURE.md.
2. Read TASKS.md.
3. Explain the implementation plan.
4. Break the work into small milestones.
5. Implement one module at a time.
6. Keep code production-ready.
7. Follow existing project patterns.
8. Ask questions if requirements are unclear.

Never generate the entire application in one response.

Never change architecture without approval.

Quality is more important than speed.