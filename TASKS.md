# Sprint 11 – Purchase Management

## Goal

Implement Purchase Management following the same architecture and quality standards as Invoice and Payment Management.

---

# Architecture Rules

- Router → Service → Repository
- Domain layer for calculations
- Multi-tenant
- RBAC
- Soft Delete
- Audit Fields
- Decimal only
- ROUND_HALF_UP
- Async SQLAlchemy
- No cross-module repository access
- Full Unit + Integration + API tests

---

# Session 1 – Supplier & Purchase Foundation

## Create Modules

modules/suppliers/

modules/purchase/

## Suppliers

Supplier

Fields

id

tenant_id

code

name

legal_name

gstin

phone

email

address

city

state

country

contact_person

credit_days

opening_balance

outstanding_amount

status

audit fields

soft delete

## Purchase Bills

PurchaseBill

Fields

id

tenant_id

supplier_id

bill_number

bill_date

due_date

subtotal

discount_amount

tax_amount

transport_charge

other_charge

round_off

total_amount

paid_amount

balance_amount

remarks

status

posted_at

audit fields

soft delete

PurchaseBillItem

Fields

id

purchase_bill_id

line_number

description

quantity

unit

rate

discount_percent

discount_amount

tax_rate

tax_amount

line_total

Create

Models

Schemas (Response)

Permissions

Constants

Exceptions

Repository skeleton

Service skeleton

Router skeleton

Migrations

Swagger registration

No CRUD

---

# Session 2 – Supplier CRUD + Purchase Bill CRUD

Implement

Supplier CRUD

Purchase Bill CRUD

Search

Filter

Sort

Pagination

Validate Supplier

Draft only edit/delete

Server owns

bill_number

financial fields

status

posted_at

---

# Session 3 – Purchase Bill Items

Implement

Add Item

List Items

Update Item

Delete Item

Validate

quantity > 0

rate >= 0

discount %

tax %

Server calculates nothing yet

Support

Multiple Items

Sequential line numbers

Draft only

---

# Session 4 – Financial Engine

Create

domain/totals.py

Calculate

Line

discount

tax

line_total

Purchase Bill

subtotal

discount

tax

charges

round_off

total

paid

balance

ROUND_HALF_UP

Recalculate

after every mutation

Never trust client totals

---

# Session 5 – Purchase Posting Workflow

POST

/purchase/{id}/post

Workflow

Lock Purchase Bill

Validate

Has Items

Recalculate

Generate Bill Number

POST

Commit

Rollback on failure

Supplier Outstanding

Recalculate

Posting makes Purchase Bill immutable

Use

SELECT FOR UPDATE

Implement

purchase_sequences

Concurrency safe numbering

Format

PUR/2026-27/00001

---

# Testing

Every session

Unit Tests

Repository Tests

Integration Tests

API Tests

Coverage

CRUD

RBAC

Tenant Isolation

Business Rules

Concurrency

Posting

Financial Accuracy

Swagger

---

# Quality Gates

Ruff

MyPy strict

Pytest

Alembic

Swagger

No regressions
