# Sprint 7 - Trip Catch Management

## Sprint Goal

Build the Trip Catch Management module.

A Trip Catch records the fish caught during a fishing trip.

Each Trip Catch belongs to:

- One Trip
- One Fish

This module becomes the inventory source for Sales Invoices.

No Sales.
No Invoice.
No Payment.

Only Catch Management.

---

# Session 1 - Database Foundation

## Module Structure

Create:

app/modules/trip_catches/

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

Create TripCatch model.

Fields

- [ ] id (UUID v7)
- [ ] tenant_id
- [ ] trip_id (FK -> trips.id)
- [ ] fish_id (FK -> fish.id)

- [ ] grade
- [ ] quantity_caught
- [ ] available_quantity
- [ ] sold_quantity
- [ ] waste_quantity

- [ ] landing_date
- [ ] landing_port

- [ ] remarks

- [ ] created_at
- [ ] updated_at
- [ ] deleted_at

- [ ] created_by
- [ ] updated_by
- [ ] deleted_by

---

## Grade Enum

- [ ] A
- [ ] B
- [ ] C

---

## Constraints

- [ ] FK Trip
- [ ] FK Fish
- [ ] Audit Fields
- [ ] Soft Delete
- [ ] Alembic Migration

---

## Session Deliverables

- Trip Catch table
- Relationships
- Migration
- Repository skeleton
- Router skeleton
- Service skeleton

---

# Session 2 - CRUD APIs

Implement

- [ ] Create Catch
- [ ] Get Catch
- [ ] List Catches
- [ ] Update Catch
- [ ] Delete Catch

Requirements

- [ ] RBAC
- [ ] Tenant Isolation
- [ ] Trip validation
- [ ] Fish validation
- [ ] Soft Delete
- [ ] Audit Fields

Endpoints

POST /api/v1/trip-catches

GET /api/v1/trip-catches

GET /api/v1/trip-catches/{id}

PUT /api/v1/trip-catches/{id}

DELETE /api/v1/trip-catches/{id}

---

# Session 3 - Business Features

Implement

- [ ] Search
- [ ] Filtering
- [ ] Sorting
- [ ] Pagination
- [ ] Business Rules

Search

- Trip Number
- Fish Name

Filters

- Trip
- Fish
- Grade
- Landing Date

Sorting

- Landing Date
- Quantity
- Created At

Business Rules

- [ ] Trip must exist
- [ ] Fish must exist
- [ ] Trip must be RETURNED
- [ ] Boat belongs to tenant
- [ ] quantity_caught > 0
- [ ] available_quantity starts equal to quantity_caught
- [ ] sold_quantity starts at 0
- [ ] waste_quantity starts at 0
- [ ] available + sold + waste must always equal quantity_caught
- [ ] Prevent negative quantities

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
- Filtering
- Sorting
- Pagination
- Trip Validation
- Fish Validation
- Quantity Validation
- Grade Validation
- RBAC
- Tenant Isolation
- Soft Delete

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

✅ Trip Catch Module

✅ CRUD

✅ Search

✅ Filtering

✅ Pagination

✅ Sorting

✅ Quantity Validation

✅ Trip Validation

✅ Fish Validation

✅ RBAC

✅ Tenant Isolation

✅ Soft Delete

✅ Tests

---

# Definition of Done

- [ ] Migration
- [ ] CRUD APIs
- [ ] Search
- [ ] Filtering
- [ ] Pagination
- [ ] Sorting
- [ ] Business Rules
- [ ] Tests Passing
- [ ] Ruff Passing
- [ ] MyPy Passing
- [ ] Swagger Updated

---

# Claude Code Instructions

Read:

- CLAUDE.md
- ARCHITECTURE.md
- TASKS.md

Implement one session at a time.

Explain the implementation plan first.

Run:

- Ruff
- MyPy
- Pytest

after every session.

Stop after completing the requested session.