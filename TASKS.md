# Sprint 8 - Trip Expense Management

## Sprint Goal

Build the Trip Expense Management module.

A Trip Expense records every operational expense incurred during a fishing trip.

Each expense belongs to exactly one Trip.

Trip Expenses are later used to calculate Trip Profitability.

No Sales.
No Invoice.
No Payment.

Only Expense Management for Trips.

---

# Session 1 - Database Foundation

## Module Structure

Create:

app/modules/trip_expenses/

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

Create TripExpense model.

Fields

- [ ] id (UUID v7)
- [ ] tenant_id
- [ ] trip_id (FK -> trips.id)

- [ ] expense_type
- [ ] amount
- [ ] expense_date
- [ ] description
- [ ] vendor_name
- [ ] receipt_number

- [ ] created_at
- [ ] updated_at
- [ ] deleted_at

- [ ] created_by
- [ ] updated_by
- [ ] deleted_by

---

## Expense Types

Enum

- [ ] DIESEL
- [ ] ICE
- [ ] FOOD
- [ ] LABOUR
- [ ] HARBOUR
- [ ] MAINTENANCE
- [ ] REPAIR
- [ ] PERMIT
- [ ] OTHER

---

## Constraints

- [ ] FK Trip
- [ ] Audit Fields
- [ ] Soft Delete
- [ ] Alembic Migration

---

## Session Deliverables

- Expense table
- Migration
- Relationships
- Repository Skeleton
- Service Skeleton
- Router Skeleton

---

# Session 2 - CRUD APIs

Implement

- [ ] Create Expense
- [ ] Get Expense
- [ ] List Expenses
- [ ] Update Expense
- [ ] Delete Expense

Requirements

- [ ] RBAC
- [ ] Tenant Isolation
- [ ] Trip Validation
- [ ] Soft Delete
- [ ] Audit Fields

Endpoints

POST /api/v1/trip-expenses

GET /api/v1/trip-expenses

GET /api/v1/trip-expenses/{id}

PUT /api/v1/trip-expenses/{id}

DELETE /api/v1/trip-expenses/{id}

---

# Session 3 - Business Features

Implement

- [ ] Search
- [ ] Filtering
- [ ] Sorting
- [ ] Pagination
- [ ] Business Rules

Search

- Vendor Name
- Receipt Number

Filters

- Trip
- Expense Type
- Expense Date

Sorting

- Expense Date
- Amount
- Created At

Business Rules

- [ ] Trip must exist
- [ ] Trip belongs to tenant
- [ ] Amount > 0
- [ ] Expense date cannot be before Trip departure
- [ ] Expense date cannot be after Trip return
- [ ] Returned and Cancelled trips cannot be modified if business rules require closure
- [ ] Prevent duplicate receipt numbers for the same vendor within a trip (optional uniqueness)

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
- Amount Validation
- Date Validation
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

✅ Trip Expense Module

✅ CRUD APIs

✅ Search

✅ Filtering

✅ Pagination

✅ Sorting

✅ Validation

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

before coding.

Implement one session at a time.

Explain implementation plan before coding.

Run

- Ruff
- MyPy
- Pytest

after every session.

Stop after the requested session.