# Sprint 5 - Boat Management

## Sprint Goal

Build the Boat Management module.

This module manages fishing boats used for trips and fish catches.

A Boat belongs to a Company (Owner).

No Trip logic.
No Catch logic.
No Invoice logic.

Only Boat Master.

---

# Session 1 - Database Foundation

## Module Structure

Create:

app/modules/boats/

- [x] router.py
- [x] service.py
- [x] repository.py
- [x] models.py
- [x] schemas.py
- [x] dependencies.py
- [x] permissions.py
- [x] constants.py
- [x] exceptions.py

---

## Database Model

Create Boat model.

Fields

- [x] id (UUID v7)
- [x] tenant_id
- [x] company_id (FK -> companies.id)
- [x] code
- [x] name
- [x] registration_number
- [x] license_number
- [x] boat_type
- [x] capacity_kg
- [x] engine_number
- [x] engine_hp
- [x] captain_name
- [x] captain_phone
- [x] insurance_expiry
- [x] license_expiry
- [x] notes
- [x] is_active
- [x] created_at
- [x] updated_at
- [x] deleted_at
- [x] created_by
- [x] updated_by
- [x] deleted_by

---

## Constraints

- [x] Unique boat code per tenant
- [x] Unique registration number per tenant
- [x] FK to Company
- [x] Soft Delete
- [x] Audit Fields
- [x] Alembic Migration

---

## Session Deliverables

- Boat table
- Relationships
- Migration
- Repository skeleton
- Router skeleton
- Service skeleton

---

# Session 2 - CRUD APIs

Implement

- [x] Create Boat
- [x] Get Boat
- [x] List Boats
- [x] Update Boat
- [x] Delete Boat

Requirements

- [x] RBAC
- [x] Tenant Isolation
- [x] Soft Delete
- [x] Audit Fields
- [x] Company existence validation

Endpoints

POST /api/v1/boats

GET /api/v1/boats

GET /api/v1/boats/{id}

PUT /api/v1/boats/{id}

DELETE /api/v1/boats/{id}

---

# Session 3 - Business Features

Implement

- [x] Search
- [x] Filtering
- [x] Sorting
- [x] Pagination
- [x] Duplicate Validation

Search

- Boat Name
- Boat Code
- Registration Number
- Captain Name

Filters

- Boat Type
- Company
- Active
- Insurance Expired
- License Expired

Sorting

- Name
- Code
- Created At
- Updated At

Business Rules

- Boat code unique per tenant
- Registration number unique per tenant
- Company must exist
- Deleted boats hidden
- Cannot update deleted boat
- Return HTTP 409 on duplicates

---

# Session 4 - Testing & Documentation

Testing

- [x] Unit Tests
- [x] Repository Tests
- [x] Integration Tests
- [x] API Tests

Verify

- CRUD
- Search
- Filters
- Pagination
- Sorting
- Duplicate Validation
- Company FK
- RBAC
- Tenant Isolation
- Soft Delete

Documentation

- [x] Swagger
- [x] Example Requests
- [x] Example Responses

Quality

- [x] Ruff
- [x] MyPy
- [x] Pytest

---

# Sprint Deliverables

✅ Boat Master Module

✅ CRUD APIs

✅ Search

✅ Filtering

✅ Pagination

✅ Sorting

✅ Validation

✅ RBAC

✅ Tenant Isolation

✅ Soft Delete

✅ Company Relationship

✅ Tests

---

# Definition of Done

- [x] Migration created
- [x] CRUD APIs
- [x] Search
- [x] Filtering
- [x] Pagination
- [x] Sorting
- [x] Validation
- [x] Duplicate Handling
- [x] Company FK Validation
- [x] Tests Passing
- [x] Ruff Passing
- [x] MyPy Passing
- [x] Swagger Updated

---

# Claude Code Instructions

Read

- CLAUDE.md
- ARCHITECTURE.md
- TASKS.md

before coding.

Implement only one session at a time.

Explain implementation plan first.

Run

- Ruff
- MyPy
- Pytest

after every session.

Stop after completing the requested session.