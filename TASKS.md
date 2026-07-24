# Sprint 12 – Supplier Payment Management

## Goal

Implement the complete **Supplier Payment Management** module, completing the **Accounts Payable (AP)** workflow.

This sprint mirrors the Customer Payment module (Sprint 10) while integrating with **Suppliers** and **Purchase Bills**.

---

# Scope

## In Scope

- Supplier Payment CRUD
- Supplier Payment Allocation
- Outstanding Reconciliation
- Payment Posting
- Concurrency-safe Payment Number Generation
- RBAC
- Tenant Isolation
- Swagger
- Unit / Repository / Integration / API Tests

## Out of Scope

- Ledger Entries
- Journal Entries
- PDF Receipts
- Email / Notifications
- Inventory
- Bank Reconciliation
- Cheque Bounce
- GST Filing

---

# Architecture Rules

- Router → Service → Repository
- Domain Layer for calculations
- Async SQLAlchemy
- Multi Tenant
- RBAC
- Soft Delete
- Audit Fields
- Decimal only
- ROUND_HALF_UP
- Never trust client financial values
- Never access another module's repository directly
- Cross-module communication only through services

---

# Session 1 – Supplier Payment Foundation

## Create Module

backend/app/modules/supplier_payments/

### Create

models.py

schemas.py (Response only)

constants.py

exceptions.py

permissions.py

dependencies.py

repository.py (constructor only)

service.py (constructor only)

router.py (0 endpoints)

domain/

__init__.py

allocation.py (placeholder)

numbering.py (placeholder)

reconciliation.py (placeholder)

---

## Database Models

### SupplierPayment

Fields

- id
- tenant_id
- supplier_id
- payment_number (nullable)
- payment_date
- payment_method
- reference_number
- bank_name
- amount
- allocated_amount
- unallocated_amount
- remarks
- status
- posted_at
- audit fields
- soft delete

---

### SupplierPaymentAllocation

Fields

- id
- tenant_id
- supplier_payment_id
- purchase_bill_id
- allocated_amount
- created_at
- created_by

Append-only.

No update/delete timestamps.

---

### SupplierPaymentSequence

Fields

- tenant_id
- prefix
- fiscal_year
- last_number

---

## Relationships

Supplier

↓

Supplier Payments

Supplier Payment

↓

Supplier Payment Allocations

Purchase Bill

↓

Supplier Payment Allocations

---

## Permissions

supplier_payment:view

supplier_payment:create

supplier_payment:edit

supplier_payment:delete

supplier_payment:post

Seed permissions.

Grant to

- super_admin
- admin
- manager
- accountant

---

## Migrations

Create

supplier_payments

supplier_payment_allocations

supplier_payment_sequences

permission seed

---

## Session 1 Deliverable

Foundation only.

No CRUD.

No allocation.

No posting.

---

# Session 2 – Supplier Payment CRUD

Implement

POST

GET

LIST

PUT

DELETE

for Supplier Payments.

---

## Request Schemas

SupplierPaymentCreateRequest

SupplierPaymentUpdateRequest

SupplierPaymentListParams

Client fields

- supplier_id
- payment_date
- payment_method
- reference_number
- bank_name
- amount
- remarks

Server owned

- payment_number
- allocated_amount
- unallocated_amount
- status
- posted_at

---

## Validation

Supplier exists

Supplier active

Supplier belongs to tenant

Only SupplierService

Never SupplierRepository

---

## Search

payment_number

reference_number

supplier_name

---

## Filters

status

supplier

payment_method

payment_date range

---

## Sorting

payment_date

payment_number

created_at

Default

-created_at

---

## Business Rules

Only DRAFT

update

delete

Soft delete only.

---

# Session 3 – Allocation Engine

Implement

POST

GET

PUT

DELETE

/payment/{id}/allocations

---

## Validation

Purchase Bill exists

Purchase Bill belongs to tenant

Purchase Bill status

POSTED

PARTIALLY_PAID

Allocation

<= payment.unallocated_amount

<= purchase_bill.balance_amount

---

## Allocation Rules

Support

Partial allocation

Multiple purchase bills

Multiple supplier payments

Recalculate payment allocation totals after every mutation.

Do not update Purchase Bill financials yet.

---

## Domain

Complete

allocation.py

---

# Session 4 – Outstanding Reconciliation

Implement

reconciliation.py

---

## Recalculate Purchase Bill

paid_amount

balance_amount

status

Transitions

POSTED

↓

PARTIALLY_PAID

↓

PAID

Reverse transitions allowed.

---

## Recalculate Supplier

Supplier.outstanding_amount

=

SUM(open purchase bill balances)

Never increment.

Always recompute.

---

## Domain

Complete

reconciliation.py

---

## Business Rules

Purchase Bill

paid_amount <= total_amount

balance >= 0

Outstanding >= 0

ROUND_HALF_UP

---

# Session 5 – Supplier Payment Posting

Implement

POST

/supplier-payments/{id}/post

---

## Workflow

Lock Supplier Payment

Validate

Must have allocations

Recalculate allocation totals

Allocate payment number

SPAY/{FY}/{00001}

Mark

POSTED

posted_at

Commit

Rollback on failure

---

## Numbering

Complete

numbering.py

Functions

fiscal_year_for()

format_payment_number()

---

## Concurrency

SELECT ... FOR UPDATE

Supplier Payment

Sequence

Prevent

duplicate posting

duplicate payment numbers

---

## Business Rules

Cannot post twice

Cannot post cancelled

Posted payment immutable

Existing draft guards enforce immutability

---

# Testing

Every session

Unit Tests

Repository Tests

Integration Tests

API Tests

---

## Verify

CRUD

RBAC

Tenant Isolation

Search

Filters

Sorting

Pagination

Allocation

Outstanding

Posting

Concurrency

Rollback

Swagger

---

# Quality Gates

Every Session

- Ruff clean
- Ruff format
- MyPy strict
- Pytest
- Alembic
- OpenAPI builds
- No migration drift
- No regressions

---

# Expected Outcome

At the end of Sprint 12 the ERP will have a complete Accounts Payable workflow.

Supplier

↓

Purchase Bill

↓

Supplier Payment

↓

Payment Allocation

↓

Outstanding Cleared

↓

Posted Payment

This completes the Procure-to-Pay financial lifecycle and mirrors the Order-to-Cash architecture already implemented for Companies, Invoices, and Customer Payments.