# Sprint 6 - Trip Management

## Sprint Goal

Build the Trip Management module.

A Trip represents one fishing journey performed by a boat.

A Trip belongs to one Boat.

No Catch Management.
No Trip Expenses.
No Invoice.
No Payment.

Only Trip Management.

---

# Session 1 - Database Foundation

## Module Structure

Create:

app/modules/trips/

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

Create Trip model.

Fields

- [ ] id (UUID v7)
- [ ] tenant_id
- [ ] boat_id (FK -> boats.id)
- [ ] trip_number
- [ ] trip_type
- [ ] captain_name
- [ ] departure_port
- [ ] arrival_port
- [ ] departure_datetime
- [ ] expected_return_datetime
- [ ] actual_return_datetime
- [ ] status
- [ ] notes
- [ ] is_active
- [ ] created_at
- [ ] updated_at
- [ ] deleted_at
- [ ] created_by
- [ ] updated_by
- [ ] deleted_by

---

## Enums

Trip Status

- [ ] PLANNED
- [ ] DEPARTED
- [ ] RETURNED
- [ ] CANCELLED

Trip Type

- [ ] FISHING
- [ ] TRANSPORT
- [ ] MAINTENANCE
- [ ] OTHER

---

## Constraints

- [ ] Unique trip_number per tenant
- [ ] FK to Boat
- [ ] Soft Delete
- [ ] Audit Fields
- [ ] Alembic Migration

---

## Session Deliverables

- Trip table
- Relationship with Boat
- Migration
- Repository skeleton
- Router skeleton
- Service skeleton

---

# Session 2 - CRUD APIs

Implement

- [ ] Create Trip
- [ ] Get Trip
- [ ] List Trips
- [ ] Update Trip
- [ ] Delete Trip

Requirements

- [ ] RBAC
- [ ] Tenant Isolation
- [ ] Soft Delete
- [ ] Audit Fields
- [ ] Boat validation

Endpoints

POST /api/v1/trips

GET /api/v1/trips

GET /api/v1/trips/{id}

PUT /api/v1/trips/{id}

DELETE /api/v1/trips/{id}

---

# Session 3 - Business Features

Implement

- [ ] Search
- [ ] Filtering
- [ ] Pagination
- [ ] Sorting
- [ ] Duplicate Validation
- [ ] Business Rules

Search

- Trip Number
- Boat Name
- Captain Name

Filters

- Boat
- Trip Status
- Trip Type
- Departure Date
- Return Date

Sorting

- Trip Number
- Departure Date
- Created At
- Updated At

Business Rules

- [ ] Boat must exist
- [ ] Boat must be active
- [ ] Boat must belong to current tenant
- [ ] Boat cannot have more than one active trip
- [ ] Actual return cannot be before departure
- [ ] Returned trips cannot change boat
- [ ] Deleted trips hidden
- [ ] Return HTTP 409 on duplicates

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
- Duplicate Validation
- Boat Validation
- Active Trip Validation
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

✅ Trip Management

✅ CRUD

✅ Search

✅ Filtering

✅ Pagination

✅ Sorting

✅ Validation

✅ Boat Relationship

✅ Active Trip Validation

✅ RBAC

✅ Tenant Isolation

✅ Soft Delete

✅ Tests

---

# Definition of Done

- [ ] Migration
- [ ] CRUD
- [ ] Search
- [ ] Filtering
- [ ] Pagination
- [ ] Sorting
- [ ] Validation
- [ ] Duplicate Validation
- [ ] Boat Validation
- [ ] Active Trip Validation
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

Implement one session at a time.

Explain the implementation plan first.

Run

- Ruff
- MyPy
- Pytest

after every session.

Stop after completing the requested session.