Here is the structured and formatted version of your sprint plan:

Sprint 9 — Invoice Management
Goal: Build the complete Invoice Management module. Invoices are the core financial document of FishERP.

This sprint introduces:

Draft invoices

Invoice items

Financial calculations

Invoice issue workflow

Inventory deduction

Invoice numbering

Immutable invoices

This module will integrate with:

Company

Fish

Trip Catch

Future Payment module

Future Ledger module

Session 1 — Module Foundation
Objective: Create the entire Invoice module structure.

1. Create Module Structure (modules/invoices/)

__init__.py

router.py

service.py

repository.py

models.py

schemas.py

exceptions.py

constants.py

permissions.py

dependencies.py

2. Database Tables
invoices

Core Fields: id, tenant_id, invoice_number, company_id, invoice_date, due_date

Status Options: Draft, Issued, Paid, Partially Paid, Cancelled

Financial Fields: subtotal, discount_amount, taxable_amount, tax_amount, transport_charge, other_charge, round_off, total_amount, paid_amount, balance_amount

Metadata: Audit fields, Soft delete

invoice_items

Fields: id, tenant_id, invoice_id, fish_id, trip_catch_id, description, quantity, unit, rate, discount_percent, discount_amount, taxable_amount, tax_rate, tax_amount, line_total

3. Implementation Checklist

Create Models, Schemas, Exceptions, Constants, Permissions, Dependencies, and Migration.

Setup Indexes, Foreign Keys, Relationships, and Swagger Tags.

4. Verify

Migration works and tables are created.

Code is MyPy clean and Ruff clean.

Session 2 — CRUD
Objective: Implement standard operations across the Repository, Service, and Router.

1. CRUD Operations

Create Draft Invoice

Update Draft

Delete Draft

Get Invoice

List Invoices

2. Query Features

Search: invoice_number, company

Filters: status, company, date_range

Sorting: invoice_date, invoice_number, total, created_at

Pagination: page, page_size

3. RBAC Permissions

invoice:view

invoice:create

invoice:edit

invoice:delete

4. Verify

CRUD, Search, Pagination, Filtering, Sorting, RBAC, Tenant Isolation, and Soft Delete functionality.

Session 3 — Invoice Items
Objective: Implement invoice_items lifecycle and validation.

1. CRUD Operations

Add Item, Edit Item, Delete Item, List Items

2. Validation Rules

Fish exists.

Trip Catch exists and belongs to the tenant.

Quantity > 0 and Rate ≥ 0.

Validate discounts and taxes.

Inventory: Quantity cannot exceed Trip Catch available quantity.

3. Service Rules

Must use FishService and TripCatchService (never directly access repositories).

4. Verify

Item CRUD, Trip Catch/Fish validation, Inventory validation, RBAC, and Tenant isolation.

Session 4 — Financial Engine
Objective: Server calculates everything. Ignore client totals.

1. Rules

Use decimals only (never floats).

Recalculate on every update.

Reject negative values.

2. Calculate

Line subtotal and Line discount

Taxable amount (GST, CGST, SGST, IGST)

Transport and Other Charges

Round Off

Invoice Total, Balance, and Paid Amount

3. Verify

Calculation accuracy, decimal precision, negative value rejection, rounding, and financial totals.

Session 5 — Issue Workflow
Objective: Execute the core invoice issuance logic. (Most important session)

Endpoint: POST /invoices/{id}/issue

1. Workflow Pipeline
Draft → Validate → Generate Number → Lock Invoice → Calculate Totals → Deduct Trip Catch Quantity → Update Balance → Issued → Immutable

2. Business Rules

Cannot issue twice.

Cannot edit or delete an issued invoice.

Must contain at least one item.

Company must be active.

Trip Catch quantity must be available.

3. Future Proofing (Prepare Hooks)

Future Payment, Future Ledger, Future PDF, Future Outbox (No implementation yet).

4. Verify

Issue endpoint, concurrency, Invoice Number generation, inventory deduction, immutability, and integrity errors.

Session 6 — Testing & Documentation
1. Testing Scope

Unit Tests: Exceptions, Schemas, Financial calculations, Service logic.

Integration Tests: Repository, Issue workflow, Invoice Items.

API Tests: CRUD, Issue endpoint, RBAC, Search, Pagination, Filtering, Tenant Isolation, Soft Delete, Immutable invoice rules, Inventory deduction.

2. Documentation & Review

Swagger: Add examples, expected responses, and error documentation.

Architecture Review: Check layering, security, performance, test coverage, and identify future improvements.

Definition of Done
The sprint is complete only if:

[ ] Ruff clean

[ ] MyPy strict clean

[ ] All tests pass

[ ] Alembic migration successful

[ ] Swagger updated

[ ] RBAC implemented

[ ] Tenant isolation verified

[ ] Soft delete verified

[ ] Financial calculations verified

[ ] Invoice issue workflow verified

[ ] Code matches project architecture