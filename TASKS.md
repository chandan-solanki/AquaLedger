# Sprint 10 – Payment Management

## Sprint Goal

Implement the complete Payment Management module for FishERP.

This module manages:

- Customer Payments
- Payment Allocation
- Outstanding Balance
- Invoice Settlement
- Partial Payments
- Full Payments

This sprint integrates with:

- Authentication
- Company
- Invoice
- Future Ledger
- Future Reports

No Ledger implementation in this sprint.
No PDF generation.
No Dashboard.

---

# Module Structure

Create

app/modules/payments/

- router.py
- service.py
- repository.py
- models.py
- schemas.py
- dependencies.py
- permissions.py
- constants.py
- exceptions.py

Create

app/modules/payments/domain/

- allocation.py
- numbering.py

---

# Session 1
## Database Foundation

Create

Payment

PaymentAllocation

Models

Schemas

Constants

Exceptions

Permissions

Dependencies

Migration

Indexes

Relationships

Swagger Tag

---

## Payment Table

Fields

id

tenant_id

payment_number

company_id

payment_date

payment_method

reference_number

bank_name

amount

allocated_amount

unallocated_amount

remarks

status

created_at

updated_at

deleted_at

created_by

updated_by

deleted_by

---

## Payment Allocation Table

Fields

id

tenant_id

payment_id

invoice_id

allocated_amount

created_at

created_by

---

Relationships

Payment

↓

Payment Allocations

↓

Invoice

---

Indexes

payment_number

company_id

payment_date

status

Soft delete indexes

---

Status

Draft

Posted

Cancelled

---

Migration

Seed permissions

payment:view

payment:create

payment:edit

payment:delete

payment:post

---

Verification

Migration

Ruff

MyPy

Tests

---

# Session 2
## Draft Payment CRUD

Implement

Repository

Service

Router

CRUD

Create Draft Payment

Update Draft

Delete Draft

Get

List

Search

Filtering

Sorting

Pagination

RBAC

Tenant Isolation

Soft Delete

---

Search

payment_number

reference_number

company_name

---

Filtering

status

company

payment_method

payment_date

---

Sorting

payment_date

payment_number

amount

created_at

---

Business Rules

Draft only editable

Draft only deletable

No allocation yet

No posting yet

---

# Session 3
## Payment Allocation Engine

Implement

Payment Allocation CRUD

Allocate payment

Remove allocation

Update allocation

Validation

Invoice exists

Invoice belongs to tenant

Invoice status

Amount validation

Outstanding validation

Use

InvoiceService

Never InvoiceRepository

Business Rules

Allocated amount

<=

Invoice balance

Payment amount

>=

Total allocations

Support

Partial Allocation

Multiple allocations

Unallocated balance

Prepare allocation.py

No posting yet

---

# Session 4
## Outstanding Engine

Server updates

Invoice.paid_amount

Invoice.balance_amount

Invoice.status

Company.outstanding_amount

Rules

ISSUED

↓

PARTIALLY_PAID

↓

PAID

Recalculate after

Allocate

Update Allocation

Remove Allocation

Server owns calculations

Never trust client

Decimal only

ROUND_HALF_UP

---

# Session 5
## Post Payment Workflow

Endpoint

POST

/api/v1/payments/{payment_id}/post

Workflow

Lock Payment

FOR UPDATE

↓

Validate

↓

Lock Invoices

FOR UPDATE

↓

Apply Allocations

↓

Update Invoice

↓

Update Company

↓

Generate Payment Number

↓

Mark Posted

↓

Commit

Rollback

if anything fails

Business Rules

Cannot post twice

Cannot edit posted payment

Cannot delete posted payment

Payment must have allocations

No overpayment

No negative balance

Prepare

Ledger Hook

Receipt Hook

Outbox Hook

(No implementation)

---

# Session 6
## Testing

Unit Tests

Repository Tests

Integration Tests

API Tests

Concurrency Tests

Swagger

Architecture Review

Security Review

Performance Review

Definition of Done

---

# Verification

CRUD

Allocation

Outstanding

Invoice Status

Company Outstanding

Payment Number

Posting

RBAC

Tenant Isolation

Soft Delete

Concurrency

Rollback

---

# Deliverables

At end of Sprint 10

✓ Payment Module

✓ Payment Allocation

✓ Partial Payments

✓ Full Payments

✓ Outstanding Engine

✓ Invoice Settlement

✓ Payment Numbering

✓ Payment Posting Workflow

✓ Concurrency Protection

✓ Transaction Safety

✓ Swagger

✓ Tests

---

# Definition of Done

Ruff clean

MyPy strict clean

Pytest passing

Alembic migration successful

Swagger updated

RBAC complete

Tenant isolation verified

Soft delete verified

Payment allocation verified

Outstanding calculation verified

Posting workflow verified

Architecture review completed

Security review completed

Performance review completed

Sprint 10 complete