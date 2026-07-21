# Sprint 4 - Fish Management

## Sprint Goal

Build the Fish Master module.

This module stores all fish master data used throughout the ERP.

No Inventory.
No Purchase.
No Sales.
No Boat Trips.

Only the Fish Master.

---

# Session 1 - Database Foundation

## Module Structure

Create:

app/modules/fish/

- [ ] router.py
- [ ] service.py
- [ ] repository.py
- [ ] models.py
- [ ] schemas.py
- [ ] dependencies.py
- [ ] permissions.py
- [ ] constants.py
- [ ] exceptions.py

---

## Database Model

Create Fish model.

Fields

- [ ] id (UUID v7)
- [ ] tenant_id
- [ ] code
- [ ] name
- [ ] local_name
- [ ] scientific_name
- [ ] category
- [ ] unit
- [ ] default_purchase_rate
- [ ] default_sale_rate
- [ ] hsn_code
- [ ] description
- [ ] is_active
- [ ] created_at
- [ ] updated_at
- [ ] deleted_at
- [ ] created_by
- [ ] updated_by
- [ ] deleted_by

---

## Constraints

- [ ] Unique code per tenant
- [ ] Unique name per tenant
- [ ] Soft Delete
- [ ] Audit Fields
- [ ] Alembic Migration

---

## Session Deliverable

- Fish table created
- Migration completed
- Repository skeleton
- Router skeleton
- Service skeleton

---

# Session 2 - CRUD APIs

Implement

- [ ] Create Fish
- [ ] Get Fish
- [ ] List Fish
- [ ] Update Fish
- [ ] Delete Fish

Use

- [ ] RBAC
- [ ] Tenant Isolation
- [ ] Soft Delete
- [ ] Audit Fields

---

## Endpoints

POST /api/v1/fish

GET /api/v1/fish

GET /api/v1/fish/{id}

PUT /api/v1/fish/{id}

DELETE /api/v1/fish/{id}

---

# Session 3 - Business Features

Implement

- [ ] Search
- [ ] Filter
- [ ] Pagination
- [ ] Sorting
- [ ] Duplicate Validation

Search

- Code
- Name
- Local Name
- Scientific Name

Filter

- Category
- Unit
- Active Status

Sort

- Name
- Code
- Created At
- Updated At

Pagination

- page
- page_size

Business Rules

- Code unique per tenant
- Name unique per tenant
- Deleted fish hidden
- Cannot update deleted fish
- Return HTTP 409 on duplicates

---

# Session 4 - Testing & Documentation

Testing

- [ ] Unit Tests
- [ ] Repository Tests
- [ ] Integration Tests
- [ ] API Tests

Verify

- CRUD
- Search
- Filter
- Sorting
- Pagination
- Duplicate Validation
- Soft Delete
- RBAC
- Tenant Isolation

Documentation

- [ ] Swagger
- [ ] Example Requests
- [ ] Example Responses

Quality

- [ ] Ruff
- [ ] MyPy
- [ ] Pytest

---

# Sprint Deliverables

At the end of Sprint 4

✅ Fish Master Module

✅ CRUD APIs

✅ Search

✅ Filter

✅ Pagination

✅ Sorting

✅ Validation

✅ RBAC

✅ Tenant Isolation

✅ Soft Delete

✅ Tests

---

# Definition of Done

- [ ] Database Migration
- [ ] CRUD APIs
- [ ] Search
- [ ] Filtering
- [ ] Pagination
- [ ] Sorting
- [ ] Validation
- [ ] Duplicate Handling
- [ ] Tests Passing
- [ ] Ruff Passing
- [ ] MyPy Passing
- [ ] Swagger Updated

---

# Claude Code Instructions

Read

- CLAUDE.md
- ARCHITECTURE.md
- TASKS.md

before coding.

Implement only one session at a time.

Explain implementation plan.

Run

- Ruff
- MyPy
- Pytest

after every session.

Stop after completing the requested session.