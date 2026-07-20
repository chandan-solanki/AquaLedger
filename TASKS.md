# TASKS.md

# Sprint 2 – Authentication & Authorization

**Sprint Goal**

Build a secure, production-ready authentication and authorization system that will serve as the foundation for every future FishERP module.

No business modules (Companies, Fish, Boats, Trips, Invoices, Payments, Expenses, Reports, Documents, OCR, AI) should be implemented in this sprint.

---

# Phase 1 – Authentication Module

## Goal

Create the complete authentication module following the project architecture.

Directory

app/modules/auth/

Required files

- [ ] router.py
- [ ] service.py
- [ ] repository.py
- [ ] models.py
- [ ] schemas.py
- [ ] security.py
- [ ] dependencies.py
- [ ] permissions.py
- [ ] constants.py
- [ ] exceptions.py

---

# Phase 2 – Database Models

## User

Create the User model.

Fields

- [ ] UUID Primary Key
- [ ] Email
- [ ] Username
- [ ] Full Name
- [ ] Phone Number
- [ ] Password Hash
- [ ] Account Status
- [ ] Last Login
- [ ] Password Changed At
- [ ] Created At
- [ ] Updated At

Account Status

- ACTIVE
- INACTIVE
- LOCKED
- PASSWORD_EXPIRED

---

## Role

Create Role model.

Default Roles

- [ ] Super Admin
- [ ] Admin
- [ ] Manager
- [ ] Accountant
- [ ] Operator

---

## Permission

Create Permission model.

Examples

- manage_users
- manage_companies
- manage_fish
- manage_boats
- manage_trips
- manage_invoices
- manage_payments
- manage_reports

---

## Mapping Tables

- [ ] UserRole
- [ ] RolePermission

---

## Refresh Token

Store refresh tokens securely.

Fields

- [ ] User
- [ ] Token Hash
- [ ] Expires At
- [ ] Revoked At

---

## Audit Log

Create audit log table.

Track

- Login
- Logout
- Failed Login
- Password Change
- User Creation

---

# Phase 3 – Security

Implement

- [ ] JWT Access Token
- [ ] Refresh Token
- [ ] Secure Token Generation
- [ ] Token Validation
- [ ] Token Expiration
- [ ] Argon2 Password Hashing
- [ ] Password Verification
- [ ] Login Rate Limiting
- [ ] Password Policy

Password Policy

- Minimum 8 characters
- Uppercase
- Lowercase
- Number
- Special Character

Configuration should come from .env

---

# Phase 4 – Authentication APIs

## Login

POST /api/v1/auth/login

---

## Refresh Token

POST /api/v1/auth/refresh

---

## Logout

POST /api/v1/auth/logout

---

## Current User

GET /api/v1/auth/me

---

## Change Password

POST /api/v1/auth/change-password

---

# Phase 5 – Authorization

Implement RBAC.

- [ ] Current User Dependency
- [ ] Authentication Dependency
- [ ] Role Validation
- [ ] Permission Validation
- [ ] Protected Routes

---

# Phase 6 – Middleware

Implement

- [ ] Authentication Middleware
- [ ] Request User Context
- [ ] Unauthorized Handler
- [ ] Forbidden Handler

---

# Phase 7 – Validation

Validate

- [ ] Email
- [ ] Username
- [ ] Password
- [ ] Login Request
- [ ] Refresh Token
- [ ] API Responses

---

# Phase 8 – Error Handling

Create custom exceptions.

- [ ] Invalid Credentials
- [ ] Invalid Token
- [ ] Expired Token
- [ ] Unauthorized
- [ ] Forbidden
- [ ] User Not Found
- [ ] Account Locked
- [ ] Account Disabled

Return consistent JSON responses.

---

# Phase 9 – Database

Create Alembic migration.

Seed

- [ ] Default Roles
- [ ] Default Permissions
- [ ] Initial Super Admin

Default Super Admin

Email

admin@fisherp.local

Password

Admin@123

Password must be changed after first login.

---

# Phase 10 – Testing

Write

- [ ] Unit Tests
- [ ] Login Tests
- [ ] Logout Tests
- [ ] Refresh Token Tests
- [ ] Current User Tests
- [ ] RBAC Tests
- [ ] Middleware Tests
- [ ] API Tests

Verify

- Ruff
- MyPy
- Pytest

All must pass.

---

# Phase 11 – Documentation

Update Swagger.

Include

- Example Requests
- Example Responses
- Authentication Flow
- JWT Usage

---

# Sprint Deliverables

At the end of Sprint 2 the project must have

✅ User Management

✅ Secure Login

✅ JWT Authentication

✅ Refresh Tokens

✅ Argon2 Password Hashing

✅ Role Based Access Control

✅ Permission System

✅ Authentication Middleware

✅ Protected APIs

✅ Current User Endpoint

✅ Change Password

✅ Audit Logs

✅ Default Roles

✅ Initial Super Admin

No Company Module

No Fish Module

No Invoice Module

No Payment Module

No Business Logic

---

# Definition of Done

Sprint 2 is complete only when

- [ ] Login works
- [ ] Logout works
- [ ] Refresh Token works
- [ ] JWT works
- [ ] RBAC works
- [ ] Middleware works
- [ ] Audit Logging works
- [ ] Alembic Migration created
- [ ] Default Roles seeded
- [ ] Default Permissions seeded
- [ ] Super Admin seeded
- [ ] Tests pass
- [ ] Ruff passes
- [ ] MyPy passes
- [ ] Swagger updated

---

# Out of Scope

Do NOT implement

- User Registration
- Forgot Password
- Email Verification
- Google Login
- GitHub Login
- OTP
- MFA
- OAuth
- Company Management
- Fish Management
- Boat Management
- Trip Management
- Invoice Management
- Payment Management
- Expense Management
- Reports
- OCR
- AI Assistant

---

# Claude Code Instructions

Before coding

1. Read CLAUDE.md
2. Read ARCHITECTURE.md
3. Explain the implementation plan
4. Work phase by phase
5. Run Ruff after each phase
6. Run MyPy after each phase
7. Run Pytest after each phase
8. Wait for approval before starting the next phase

Do not generate the entire sprint in one response.

Implement incrementally.

Never modify project architecture without approval.