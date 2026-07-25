# AquaLedger — User Flows

**The Complete Workflow & Interaction Specification for AquaLedger**

Version 1.0 · User Flows & Business Workflow Document

This document specifies every significant user journey in AquaLedger: the success path, validation rules, failure handling, and edge cases for each. It builds on `01_PRODUCT_VISION.md` (business rules, personas), `02_DESIGN_SYSTEM.md` (component behavior), and `03_INFORMATION_ARCHITECTURE.md` (routes, navigation) and contradicts none of them.

---

## 1. User Journey Philosophy

- **Task-Oriented Workflows** — every flow in this document is organized around a business task ("bill a customer," "log a trip," "pay a supplier"), never around a screen or a CRUD operation in isolation. A user should never have to translate their goal into "which page do I need."
- **Minimal Clicks** — the number of steps between intent and completion is minimized wherever it doesn't compromise correctness; where a task is inherently multi-step (issuing an invoice, allocating a payment), the steps are the *minimum necessary*, not padded with extra confirmation for its own sake.
- **Progressive Disclosure** — complex records default to their summary/overview state; detail (tax breakdowns, allocation history, audit timelines) is one click away, never all rendered at once by default.
- **Context Preservation** — navigating away and back (via breadcrumb, back button, or tab switch) never loses in-progress work or resets filters/scroll position, per `03_INFORMATION_ARCHITECTURE.md` §19.
- **Fast Navigation** — the Command Palette, Global Search, and Quick Actions (per `03_INFORMATION_ARCHITECTURE.md` §§9–12) are available from every flow described below as an implicit shortcut, not repeated in every section.
- **Error Prevention** — the system prevents invalid states from being reachable in the first place (e.g., an "Issue" button that simply isn't rendered on an already-issued invoice) rather than allowing an invalid action and then explaining why it failed.
- **Undo-First Philosophy** — where the business allows it (drafts, soft-deletable masters), the system favors reversible actions and a clear undo path over confirmation friction. Where the business does *not* allow it (issued invoices, posted bills — per `01_PRODUCT_VISION.md`'s "Issued invoices are immutable" rule), the system instead front-loads a clear, specific confirmation, because undo is not an option after the fact.
- **Keyboard-First Productivity** — every flow in this document is fully completable via keyboard alone (tab order, Enter-to-submit, Enter-to-add-row on line-item tables), consistent with `02_DESIGN_SYSTEM.md` §16, because these are flows performed dozens of times a day by the same users.

---

## 2. Authentication Flow

```
User visits application
        ↓
   Not authenticated? → Login page
        ↓
   Submit credentials
        ↓
   Authentication
        ↓
   Permission loading (role + permission set fetched)
        ↓
   Tenant loading (active company/tenant context resolved)
        ↓
   Dashboard
```

**Success path:** User lands on `/login`, enters email/password, submits. On success, the application loads the user's permission set and tenant context (silently, behind a brief loading state — see §20), then redirects to `/dashboard`. If the user had been redirected to `/login` from a specific deep link (e.g., they followed a shared link to an Invoice while logged out), authentication redirects back to that original destination instead of the Dashboard.

**Forgot Password:**
```
Login page → "Forgot password?" → Enter email → Confirmation shown
      → Email sent (reset link) → Reset Password page → New password
      → Confirmation → Redirect to Login
```
The confirmation shown after submitting an email is identical whether or not that email exists in the system, to avoid revealing which emails are registered. The reset link expires after a fixed window; an expired link leads to a clear "this link has expired" state with a direct path to request a new one.

**Session Expiry:** A session expiring *during* active use does not silently fail the next action. The system detects the expired session, preserves the user's current in-progress state where feasible (e.g., an unsaved draft form's field values held client-side), shows a clear "Your session has expired" message, and redirects to Login. On successful re-login, the user is returned to where they were, with any preserved draft state intact.

**Unauthorized:** A user who is authenticated but lacks permission for a route they've navigated to directly (e.g., a bookmarked Administration link) sees a dedicated "You don't have access to this page" state — never a blank page, a silent redirect, or a raw error — with a clear path back to the Dashboard.

**Logout:** Triggered from the user menu (per `03_INFORMATION_ARCHITECTURE.md` §3's Topbar). A lightweight confirmation is shown only if there is genuinely unsaved work in progress elsewhere in the session (per §22); otherwise logout is immediate, clearing session state and redirecting to `/login`.

---

## 3. Dashboard Flow

**Opening the Dashboard** — the default post-login destination and the sidebar's Dashboard item. Loads with skeleton placeholders for each section (KPIs, charts, activity feed) rather than a blocking full-page spinner, so the page's structure is visible immediately and sections populate independently as their data resolves (per §20).

**Refreshing KPIs** — KPI values reflect live data as of page load; a manual refresh affordance (or automatic background refresh on a reasonable interval) updates them without a full page reload, using the same skeleton-to-value transition as initial load, scoped to just the KPI row.

**Viewing Alerts** — the Pending Work and Outstanding sections (per `03_INFORMATION_ARCHITECTURE.md` §8) are the Dashboard's actionable core: each row (an overdue invoice, an expiring boat license) is a direct link into the relevant record's Detail page. There is no separate "alerts inbox" distinct from these sections and the Notification panel (§18) — the Dashboard surfaces the same underlying signals contextually.

**Opening Reports** — chart elements and the Reports shortcut both lead into the Reports module (`/reports`); until Reports ships, these links lead to the "Coming Soon" empty state described in §21.

**Recent Activity** — a reverse-chronological feed of recent invoices, payments, and trip status changes; each entry links to its record's Detail page and shows who performed the action and when, foreshadowing the fuller Timeline/Activity views on individual records (per `03_INFORMATION_ARCHITECTURE.md` §5).

**Quick Actions** — identical behavior to the topbar Quick Actions menu (§10 of the IA document), duplicated here for first-touch convenience.

---

## 4. Company Management Flow

```
Companies List
      ↓
   Search / Filter
      ↓
   + New Company
      ↓
   Fill form → Validation
      ↓
   Save
      ↓
   Company Details
      ↓
   Edit  /  Soft Delete
```

**List → Search → Filter:** The Companies list loads with a default view (active companies, most-recently-updated first). Free-text search matches name, code, and GSTIN. Structured filters include status (active/inactive) and company type (customer/supplier/both). Search and filters are debounced and reflected in the URL's query parameters (per `03_INFORMATION_ARCHITECTURE.md` §19), so a filtered view is shareable and survives navigation-and-back.

**Create → Validation → Save:** Selecting "+ New Company" opens the Create form (`/companies/new`). Required fields (name, company type) are marked per `02_DESIGN_SYSTEM.md` §10; GSTIN and PAN are validated for correct format inline, on blur, before submission. Credit limit and credit days accept only non-negative numeric values. On submit:
- **Validation failure** — inline field errors appear immediately beneath each offending field; the form does not submit and focus moves to the first invalid field.
- **Duplicate detection** — if the GSTIN (or another uniqueness-constrained field) already exists for the tenant, a specific inline error identifies the conflict on that field ("A company with this GSTIN already exists") rather than a generic save failure — this is a validation-path error, not a server crash, and is treated with the same inline-error UI as any other field validation.
- **Permission failure** — a user without create permission never reaches this form in the first place (per `03_INFORMATION_ARCHITECTURE.md` §13's "the absence of the button *is* the boundary" principle); this path exists only as a defensive server-side check, surfaced (if ever triggered) as a page-level Alert, not a field error.
- **Success** — the record saves, a success Toast confirms it, and the user is taken to the new Company's Details page (`/companies/{id}`).

**Details → Edit:** The Details page shows the company's profile, current outstanding balance, and its related Invoices (per the cross-linking in `03_INFORMATION_ARCHITECTURE.md` §6). "Edit" opens the same form pre-filled; the same validation rules apply, plus a stricter duplicate check that excludes the record's own current values.

**Details → Soft Delete:** A destructive action gated behind the Delete Confirmation pattern (§22). Soft delete is only reachable for companies with **no financial history that requires them to remain referenceable** — specifically, a company with issued invoices or purchase bills is not hard-blocked from deactivation, but the system reflects the Product Vision's business rule ("issued invoices are immutable" and reference their company permanently) by treating this as a **deactivation** (status → inactive) rather than a data-removal action: the company disappears from active-selection dropdowns (e.g., when creating a new Invoice) but its historical records remain fully intact and viewable. The confirmation dialog states this plainly: "ABC Fisheries will be deactivated and hidden from new transactions. Its existing invoices and payment history will not be affected."

---

## 5. Supplier Management Flow

Suppliers follows the identical List → Search/Filter → Create → Validation → Save → Details → Edit → Deactivate shape as Companies (§4), with the following supplier-specific content:

- **Create Supplier** — required fields mirror Companies (name, GSTIN validation, credit terms); no "company type" field, since Suppliers is already a single-purpose master.
- **Update** — same inline-validation and duplicate-detection behavior as Companies.
- **Deactivate** — same soft-deactivation behavior and confirmation copy pattern as Companies, adapted to reference Purchase Bills instead of Invoices.
- **Search** — matches name, code, and GSTIN, identical mechanics to Companies search.
- **Outstanding** — the Supplier Details page shows the current payable balance to that supplier, computed the same way (recomputed, not incrementally tracked) as a Company's receivable balance, per `01_PRODUCT_VISION.md`'s outstanding-reconciliation rule.
- **Purchase History** — the Supplier Details page lists related Purchase Bills and Supplier Payments (mirroring a Company's related-Invoices section), each linking directly to its own Detail page.

---

## 6. Fish Master Flow

```
Fish List → Search / Filter by Category → + New Fish → Validation → Save
      ↓
   Fish Details → Edit / Deactivate
```

**Create / Edit:** Required fields: name, category, unit of measure. Optional: local name, default purchase/sale rate, HSN code. Rate fields validate as non-negative numeric with the same decimal precision discipline used everywhere in the product (per `02_DESIGN_SYSTEM.md` §4) — a rate typed with excess precision is not silently truncated without the user seeing the value that will actually be saved.

**Deactivate:** Same soft-deactivation pattern as Companies/Suppliers. A deactivated fish item is hidden from the searchable fish selector used in Trip Catch and Invoice line-item entry, but remains fully visible on any historical Trip Catch or Invoice line that already references it.

**Search:** Matches name, local name, and code; **Category** acts as a structured filter alongside free-text search, since Fish records are naturally browsed by category (e.g., "show me all shrimp/prawn varieties") as often as searched by name.

**Validation:** The only Fish-specific validation edge case is uniqueness on the item code within the tenant — duplicate detection follows the identical inline-error pattern described in §4.

---

## 7. Boat Management Flow

```
Boats List → Search → + Register Boat → Validation → Save
      ↓
   Boat Details (registration, license/insurance status, trip history)
      ↓
   Edit / Deactivate
```

**Register Boat:** Required fields: name/registration number, ownership type. Optional: captain info, license/insurance expiry dates. Expiry-date fields are the one Boat-specific validation concern: a date entered in the past is accepted (the record may be created to document an already-lapsed license) but immediately renders a Warning-state indicator on the Boat's Details page and List row, feeding the Dashboard's "boats with expiring/expired compliance documents" KPI (per `03_INFORMATION_ARCHITECTURE.md` §8).

**Update:** Standard edit flow; changing license/insurance dates re-evaluates the compliance-status indicator immediately on save.

**Search:** Matches name and registration number; a status filter (active/inactive, and a "compliance expiring soon" quick filter) is available given how operationally important this signal is.

**Deactivate:** Same soft-deactivation pattern; a deactivated boat cannot be selected when creating a new Trip, but its trip history remains fully intact.

---

## 8. Trip Management Flow

```
Trips List → + New Trip
      ↓
Assign Boat → (Crew, if applicable)
      ↓
Trip created (status: planned)
      ↓
Departure → status: at_sea
      ↓
Return → status: returned
      ↓
Log Catch + Expenses (see §9, §10)
      ↓
Settle → status: settled
      (or Cancel → status: cancelled, from planned or at_sea only)
```

**Create Trip:** Required fields: boat selection, planned departure date. The boat selector only offers active boats (per §7); selecting a boat whose compliance documents are currently expired surfaces an inline warning ("This boat's insurance expired on [date]") without blocking creation — this is a visibility aid, not a hard stop, since the business decision to sail remains the operator's.

**Assign Boat / Crew:** Boat assignment is required at creation; crew assignment (if the tenant tracks individual crew members) is optional at creation and editable up until departure.

**Status Transitions — Departure, Return, Complete:** Each transition (`planned → at_sea`, `at_sea → returned`, `returned → settled`) is an explicit action on the Trip Details page, not an automatic date-based inference, because real-world departure/return timing doesn't always match plan. Each transition button is rendered only when the trip is in the state that transition applies from — mirroring the Invoice/Purchase Bill lifecycle-action pattern (per `03_INFORMATION_ARCHITECTURE.md` §13).

- Moving to **at_sea** requires only confirming the actual departure date/time (defaulting to now).
- Moving to **returned** requires confirming the actual return date/time; this is the point at which the Catches and Expenses tabs become the primary focus of the Trip Details page.
- Moving to **settled** is the trip's final state — reachable only after the trip has a `returned` status, and is treated as a soft "closing" action: the Catches and Expenses tabs remain editable-with-caution afterward only for correction purposes, with a page-level Alert noting the trip is settled and edits should be exceptional (a lighter-weight guard than the hard immutability enforced on issued invoices, since trip data is operational record-keeping rather than a legally-issued financial document).

**Validation:** A trip cannot move to `at_sea` without a boat assigned. A trip cannot be settled while it has Trip Catch quantities that don't reconcile (available + sold + waste must equal the caught quantity for every catch line) — this surfaces as a blocking validation message on the Settle action, listing exactly which catch line(s) are unreconciled.

**Errors:** Attempting a status transition out of order (e.g., settling a still-`planned` trip via a stale/bookmarked action link) is rejected with a clear message stating the trip's actual current status — this is a defensive path, since the UI itself never renders an out-of-order transition button.

**Cancel:** Available only from `planned` or `at_sea` (a `returned` or `settled` trip cannot be cancelled, only left as a completed record) — gated by the Cancel confirmation pattern (§22).

---

## 9. Trip Catch Flow

```
Trip Details → Catches tab → + Add Catch
      ↓
Select Fish → Enter Quantity (caught) → Grade
      ↓
Validation
      ↓
Save
      ↓
Row appears with available = caught, sold = 0, waste = 0
      ↓
Update (as catch is sold or spoils) / Delete (only while unreferenced)
```

**Create Catch:** Within a Trip's Catches tab, "+ Add Catch" adds an inline row (consistent with the Invoice line-item Enter-to-add-row pattern per `02_DESIGN_SYSTEM.md` §8) rather than a separate page — catch entry is high-frequency, per-trip, multi-line data entry, the same interaction shape as invoice line items.

**Fish:** Selected via the same searchable Fish combobox used in Invoice line entry (§11), scoped to active Fish records.

**Quantity:** Caught quantity is required, numeric, and must be greater than zero. Grade (A/B/C) is a required selection where the tenant's Fish setup uses graded tracking.

**Validation:** The system enforces, at every save, that `available + sold + waste = caught` for each catch line — this is the DB-enforced invariant described in `01_PRODUCT_VISION.md`'s architecture notes, surfaced in the UI as a live-computed "available" figure the user cannot directly overwrite; available is always derived (`caught − sold − waste`), never entered.

**Update:** As catch is sold (via being referenced on an Invoice line — see §11) or recorded as waste, the sold/waste quantities update and available recomputes live. Editing the original caught quantity downward is blocked if doing so would make caught less than already-sold-plus-waste, with a clear inline error explaining the conflict.

**Delete:** A catch line can be deleted only while it has not yet been referenced by any Invoice line (sold quantity = 0). Once any portion has been sold, the row's Delete action is not offered — only the waste-recording adjustment remains available — since deleting it would orphan the invoice reference it's linked to.

---

## 10. Trip Expense Flow

```
Trip Details → Expenses tab → + Add Expense
      ↓
Select Category → Enter Amount → (Attach Receipt — future)
      ↓
Validation
      ↓
Save
      ↓
Row appears in Expenses table, Profit tab recalculates
```

**Create Expense:** Same inline-row, Enter-to-add-row pattern as Trip Catch. Category is a required selection from the tenant's configured expense categories (diesel, ice, food, labour, harbour fees, etc. — configured in Settings per `03_INFORMATION_ARCHITECTURE.md` §3).

**Amount:** Required, numeric, non-negative, following the same tabular-numeral/exact-decimal display discipline as every other monetary field in the product.

**Receipt (future):** Reserved as an optional Attachment on each expense line, per the Attachments roadmap item in `03_INFORMATION_ARCHITECTURE.md` §5 — the expense-entry flow described here already reserves the interaction slot for it (an "Attach Receipt" affordance rendered as disabled/coming-soon until the Document Management module ships).

**Validation:** Amount must be greater than zero; category is required. No other business-rule validation applies to expenses beyond standard field-level checks — unlike Trip Catch, there is no reconciliation invariant to enforce.

**Save:** On save, the Trip's Profit tab recalculates immediately (revenue from sold catch minus total trip expenses), so a user adding an expense sees the trip's profitability update in the same session without navigating away.

---

## 11. Invoice Workflow

```
Invoices List → + New Invoice
      ↓
Select Company → Add Line Items (Fish / Trip Catch reference, qty, rate, tax)
      ↓
Financial Recalculation (live, on every line change)
      ↓
Save Draft  (repeatable — draft is freely editable)
      ↓
Issue  →  confirmation  →  Immutable, numbered
      ↓
Receive Payment (see §12)
      ↓
Allocate
      ↓
Partially Paid  →  (more payments/allocations)  →  Paid
      ↓
Outstanding Cleared
```

**Create → Add Items:** Selecting "+ New Invoice" opens the Invoice Editor (`/invoices/new`) with the Company selector focused first — the rest of the form (dates, line items) is only meaningfully entered once a company is chosen, since credit terms and outstanding context depend on it. Each line item's Fish selector optionally links to a specific Trip Catch record with available stock (per §9), pulling in that catch's remaining available quantity as a soft ceiling with a warning (not a hard block) if the entered quantity exceeds it — a trader may legitimately invoice against catch not yet logged in the system.

**Financial Recalculation:** Every change to a line item (quantity, rate, discount %, tax rate) triggers an immediate, client-visible recalculation of that line's total and the invoice-level totals panel (subtotal, discount, taxable amount, CGST/SGST/IGST breakdown, transport/other charges, round-off, grand total) — no separate "recalculate" action exists; the totals are always current with what's on screen.

**Save Draft:** A draft invoice can be saved and re-opened for editing an unlimited number of times; every field remains editable, including the company selection itself, while in draft.

**Issue:** The single most consequential action in the Invoice flow. Triggered by an explicit "Issue Invoice" button, gated by the Issue confirmation pattern (§22), which states plainly that the invoice will be assigned its permanent number and become uneditable. On confirmation:
- The invoice is atomically assigned its fiscal-year sequence number (this assignment happens only at issue, not at draft creation, per `01_PRODUCT_VISION.md`'s architecture notes) — the invoice number is not shown/predictable before this point.
- Status transitions to `issued`; every field on the Invoice Editor becomes read-only; the "Edit" route becomes unreachable for this record (per `03_INFORMATION_ARCHITECTURE.md` §5).
- **Issue restrictions:** Issue is blocked (button not rendered, or rendered-disabled with an inline reason if the state is only discoverable at that moment) if the invoice has zero line items, or if required company/date fields are incomplete — these are the same validation rules as Save Draft, just enforced at the higher bar Issue requires.

**Status Transitions:** `draft → issued → partially_paid → paid`, with `overdue` as a date-driven status applied to any `issued`/`partially_paid` invoice past its due date (a computed/derived status shown via badge, not a separate action a user triggers), and `cancelled` reachable from `issued`/`partially_paid` only through a Reversal Entry mechanism (per Product Vision's "financial corrections must use Credit Notes / Reversal Entries" rule) rather than a direct status edit.

**All Validation Rules (summary):**
- Company is required before any line item can be added.
- At least one line item is required to Issue (not to Save Draft).
- Each line item requires a fish/description, a positive quantity, and a non-negative rate.
- Discount % and tax rate must be within valid bounds (0–100%).
- Issue is only available from `draft` status; Payment allocation is only available from `issued`/`partially_paid` status; Edit is only available from `draft` status.

---

## 12. Customer Payment Workflow

```
Payments List → + New Payment
      ↓
Select Company → Enter Amount, Method, Reference
      ↓
Company's open Invoices load
      ↓
Allocate amount across one or more invoices (running "unallocated" balance shown)
      ↓
Partial Allocation (one invoice, less than full balance)
   or Multiple Allocation (spread across several invoices)
      ↓
Outstanding Update (each allocated invoice's balance recomputes)
      ↓
Save/Post  →  Immutable
```

**Create Payment:** Selecting a Company loads its currently open (issued/partially_paid/overdue) invoices into an allocation table. The payment amount is entered first; the allocation table shows each open invoice with its outstanding balance and an editable "allocate" field per row.

**Allocate / Partial / Multiple Allocation:** As the user allocates amounts across rows, a persistent "unallocated" figure (payment amount minus sum of allocations) updates live, per `01_PRODUCT_VISION.md` §6's design spec — this is the payment flow's equivalent of the Invoice Editor's live totals recalculation. A payment may be allocated to a single invoice in full, a single invoice partially (leaving the rest unallocated for later use — "on account"), or spread across multiple invoices in any combination the user chooses. Over-allocating beyond the payment amount, or beyond a single invoice's outstanding balance, is blocked inline with a clear error at the offending row.

**Outstanding Update:** On save, every invoice that received an allocation has its balance and status recomputed immediately (not incrementally decremented) — `partially_paid` if a balance remains, `paid` if fully cleared — consistent with the recompute-not-increment reconciliation principle stated in the Product Vision.

**Post / Immutable:** Once saved, a Customer Payment record itself follows the same immutability discipline as an Invoice — per `01_PRODUCT_VISION.md`'s "Payments are never deleted" rule. There is no Edit route for a saved payment.

**Allocation Editing / Deletion:** Because the payment record itself is immutable, correcting a misallocation is handled as a **reversal**, not an in-place edit: the user reverses (unwinds) the specific allocation from the Payment's Details page — gated by the Remove Allocation confirmation pattern (§22) — which recomputes the affected invoice(s)' outstanding balances back to their pre-allocation state, and the payment's own unallocated balance increases correspondingly, ready to be re-allocated. This preserves a full, auditable history rather than silently rewriting what happened.

**Reconciliation:** The Payment Details page shows, at all times, exactly which invoices received allocations from this payment and for how much — the same cross-linking described in `03_INFORMATION_ARCHITECTURE.md` §6 — so "what did this payment cover" is always answerable in one view without reconstructing it from the Invoices list.

---

## 13. Purchase Bill Workflow

```
Purchase Bills List → + New Purchase Bill
      ↓
Select Supplier → Add Line Items (description, qty, rate, tax — no fish/trip-catch link)
      ↓
Financial Calculation (live)
      ↓
Save Draft
      ↓
Post  →  confirmation  →  Immutable, numbered
      ↓
Supplier Outstanding updates
```

This flow mirrors the Invoice Workflow (§11) exactly in shape and rigor, with two deliberate differences: line items describe purchased goods/services directly (no Fish-master or Trip-Catch linkage, since purchase bills aren't necessarily fish-specific), and the finalizing action is named **Post** rather than **Issue** — matching the terminology distinction already established in `03_INFORMATION_ARCHITECTURE.md` §3, where the two actions are visually parallel but named to reflect the sales-vs-purchase direction. All other rules carry over unchanged: atomic sequence numbering assigned only at Post, full immutability and no Edit route afterward, and identical field-level and Post-blocking validation rules to Invoice's Issue-blocking rules.

**Supplier Outstanding:** Posting a bill immediately makes it appear in the Supplier's outstanding-payable total and in the bill-allocation table shown when creating a new Supplier Payment (§14) — the same live-linkage as an Issued Invoice appearing in the Customer Payment allocation table.

---

## 14. Supplier Payment Workflow

```
Supplier Payments List → + New Supplier Payment
      ↓
Select Supplier → Enter Amount, Method, Reference
      ↓
Supplier's open Purchase Bills load
      ↓
Allocate across one or more bills (running "unallocated" balance shown)
      ↓
Partial Allocation / Multiple Bills
      ↓
Outstanding Update
      ↓
Save/Post  →  Immutable
```

This flow is the exact mirror of the Customer Payment Workflow (§12) — same allocation-table interaction, same live unallocated-balance tracking, same over-allocation validation, same recompute-not-increment outstanding update, same immutability-plus-reversal correction model. It is documented as its own section only because it is a first-class sidebar/route destination (per `03_INFORMATION_ARCHITECTURE.md` §4), not because its interaction design differs in any respect from §12.

---

## 15. Reports Flow

```
Reports (section) → Select Report → Apply Filters
      ↓
   Results load
      ↓
Search within results (where applicable)
      ↓
Export  /  Print
      ↓
Save Filters (as a personal default for that report)
```

**Open Report:** Selecting a report type (Receivables Aging, Payables Aging, Trip Profitability, Sales Summary, Purchase Summary — per `03_INFORMATION_ARCHITECTURE.md` §4) loads that report with a sensible default filter (typically: current fiscal period, all companies/boats). Until this module ships, every entry point into Reports (sidebar, Dashboard charts) leads to the "Coming Soon" empty state (§21).

**Apply Filters / Search:** Each report exposes the structured filters relevant to it (date range always; company/supplier/boat where relevant) plus, for list-shaped reports, an in-page search — following the same filter-bar pattern established for module List pages in `02_DESIGN_SYSTEM.md` §9, so a report feels like a natural extension of the List page pattern rather than a separate paradigm.

**Export:** Respects whatever filters are currently applied (per the Table Design export rule in `02_DESIGN_SYSTEM.md` §9) — a filtered Receivables Aging view exports exactly what's on screen, not the full unfiltered dataset.

**Print:** A print-optimized rendering of the current filtered report, suitable for physical handoff (e.g., an aging report printed for a collections conversation) — a realistic need in a business still transitioning off paper.

**Save Filters:** A user can save their current filter combination as their personal default for that report, so a report they check daily (e.g., Receivables Aging with a specific date range) opens pre-filtered next time without re-entering the same filters.

---

## 16. User Administration Flow

```
Users List → + Invite User → Assign Role → Save → Invitation sent
      ↓
User Details → Edit Role / Deactivate

Roles List → + New Role → Assign Permissions (matrix) → Save
      ↓
Role Details → Edit Permissions → changes apply to all users with that role, immediately

Profile → Edit own details / Change Password / Security

Settings → Company Profile / Numbering Sequences / Categories
```

**Users:** Creating a user is an invitation flow (email-based), not direct account creation on their behalf — the invited user sets their own password on first access. Role assignment is required at invite time and editable afterward. Deactivating a user immediately revokes their session and access without deleting their historical audit trail (their past actions remain correctly attributed in Audit Logs).

**Roles:** A permission matrix (per `01_PRODUCT_VISION.md` §10) lets an Administrator toggle `resource:action` permissions per role. Changing a role's permissions takes effect immediately for every user holding that role — including, notably, altering what's visible in their sidebar on their next navigation, per the "sidebar generated from actual permission set" principle in `03_INFORMATION_ARCHITECTURE.md` §13.

**Profile:** A self-service area for the current user's own name, contact details, password, and (future) notification preferences — distinct from the Users administration flow, which is about managing *other* users.

**Settings:** Company Profile (tenant identity/GSTIN/branding), Numbering Sequences (view/configure the fiscal-year invoice/bill numbering behavior), and Categories (expense categories, fish categories) — each a focused, low-frequency configuration form following standard field validation, with no lifecycle-action complexity of their own.

---

## 17. Search Flow

```
⌘K or click search trigger → Palette opens
      ↓
Empty state: Recent Searches / Recently Visited
      ↓
Type query → Debounced search → Grouped results by entity type
      ↓
Select result → Navigate to Detail page
      (or) No matches → No Results state
```

**Global Search / Entity Search:** As specified in `03_INFORMATION_ARCHITECTURE.md` §9 — results grouped by entity type, each showing disambiguating context, permission-filtered to what the searching user can access.

**Recent Searches:** Shown when the palette opens with no query typed, alongside recently-visited records, so the palette is useful even before typing anything.

**Keyboard Shortcut:** `⌘K`/`Ctrl+K` opens the palette from anywhere; `Esc` closes it and returns focus to the triggering context; arrow keys navigate results, `Enter` selects.

**No Results:** A clear, specific empty state ("No results for 'xyz'") rather than a blank panel — distinguished from the palette's empty-query state, which shows Recent Searches instead of a "no results" message.

---

## 18. Notification Flow

```
Triggering event occurs (backend) → Notification created
      ↓
Bell icon badge count increments
      ↓
User opens panel → sees categorized notification
      ↓
Click notification → Open Entity (navigates to its Detail page, notification marked read)
      (or) Dismiss → marked read without navigating
      ↓
History: all past notifications remain browsable, read or not
```

**Trigger → Notification:** Categories and their triggering events are as defined in `03_INFORMATION_ARCHITECTURE.md` §11 (Invoices, Payments, Purchase Bills, Trips, System, Users, Approvals, future AI). A notification is created server-side when its triggering condition occurs (e.g., an invoice crossing its due date); the frontend's role is purely to display, badge, and route from it.

**Open Entity:** Clicking a notification's body navigates directly to the relevant record and marks it read; this is the single most common interaction with notifications and is optimized accordingly (one click, no intermediate confirmation).

**Dismiss:** A lighter action (an explicit dismiss/X control per notification, or "mark all read") that clears the unread state without navigating — for notifications the user has already handled by other means.

**History:** The notification panel is not purely a transient unread queue — read notifications remain visible/searchable for a reasonable retention window, so a user can answer "did I get notified about that" after the fact.

---

## 19. Error Handling Flow

Every error in AquaLedger falls into one of these categories, each with a distinct, consistent presentation:

- **Validation Error** — inline, at the specific field, in the Danger color, with corrective guidance (per `02_DESIGN_SYSTEM.md` §10). Never blocks the rest of the form from being reviewed.
- **Network Error** — a page-level or action-level Alert ("Couldn't reach the server — check your connection") with a Retry action; in-progress form data is preserved, never cleared by a failed submission.
- **Permission Error** — surfaced as the Unauthorized state (§2) for full-page navigation, or an inline Alert for an action attempted from a page the user could otherwise view but not act on (a defensive/edge-case path, since the UI otherwise hides unauthorized actions per `03_INFORMATION_ARCHITECTURE.md` §13).
- **Session Expired** — handled per §2's Session Expiry flow.
- **Server Error** — a generic, honest "Something went wrong on our end" page-level Alert with a Retry action and, where relevant, a reference/trace identifier the user can share with support — never exposing raw internal exception detail (per `01_PRODUCT_VISION.md`'s API standard: "never expose internal exceptions").
- **Conflict** — (e.g., attempting to allocate a payment against an invoice that was just fully paid by someone else in another session) surfaced as a specific inline error explaining the conflicting state, with the affected data automatically refreshed so the user is looking at current reality before retrying.
- **Not Found** — a dedicated "this record doesn't exist or you don't have access to it" page for a Detail-page route pointing at a deleted/inaccessible ID, deliberately not distinguishing "doesn't exist" from "no permission" in the message shown (avoiding leaking which is true), with a path back to the relevant List page.
- **Retry** — offered wherever the failure is plausibly transient (network, server errors); never offered for validation or permission errors, where retrying without changing anything would simply fail again identically.

---

## 20. Loading States

- **Skeleton** — the default loading treatment for any page or section whose layout is known in advance (List pages, Detail pages, Dashboard sections) — shaped to approximate the real content per `02_DESIGN_SYSTEM.md` §8, shown immediately with no delay-before-appearing.
- **Progress** — used for determinate, multi-step, or long-running operations (e.g., a future bulk import) where a percentage or step count is meaningful; not used for ordinary page loads.
- **Optimistic Updates** — used selectively, only for low-stakes, easily-reversible interactions (e.g., marking a notification read, toggling a table's density setting) — the UI updates immediately and reconciles silently with the server response. **Never used** for anything in the financial lifecycle (Issue, Post, Allocate, Save) — those always wait for genuine server confirmation before reflecting a changed state, given the correctness stakes involved.
- **Background Refresh** — Dashboard KPIs and list views may silently refresh their data on a reasonable interval or on window refocus, without disrupting the user's current scroll position, open dropdowns, or in-progress form input.

---

## 21. Empty States

- **No Data** — a module's List page with genuinely zero records shows a purposeful, action-oriented empty state (a short explanation plus the same "+ New [Entity]" affordance as the page header) — never a bare blank table, per `02_DESIGN_SYSTEM.md` §8.
- **No Search Results** — distinguished from "No Data": states that results didn't match the current search/filter, and offers a clear "clear filters" action, since the underlying data may well exist.
- **No Permissions** — where an entire section is inaccessible (rather than the individual Unauthorized page in §2), this manifests simply as the section not appearing in navigation at all (per `03_INFORMATION_ARCHITECTURE.md` §13) — there is no "empty state" for a section a user can't see, by design.
- **No Internet** — a distinct, low-key persistent indicator (not a blocking full-page state) when connectivity is lost, since a user may still be able to review already-loaded data; actions that require the network are disabled with an inline explanation rather than failing silently.
- **Coming Soon** (module-specific addition) — used for the Reports section and any other not-yet-shipped destination reachable from navigation (per `03_INFORMATION_ARCHITECTURE.md` §3), stating plainly that the feature is on the roadmap rather than presenting a broken or missing page.

---

## 22. Confirmation Flows

Every irreversible or hard-to-reverse action uses the same Confirmation Dialog pattern (per `02_DESIGN_SYSTEM.md` §8): a specific, plain-language statement of consequence, a clearly labeled destructive/primary action (styled per the action's actual severity), and a clearly labeled way out — never a generic "Are you sure?"

- **Delete** — used only for genuinely reversible-in-effect deletions (draft records, unreferenced master data). States what will be removed and confirms it can't be undone from the UI once confirmed.
- **Issue** (Invoice) — states that the invoice will be assigned its permanent number and become uneditable. This is the highest-stakes confirmation in the product and is worded to make that unambiguous.
- **Post** (Purchase Bill) — identical weight and wording pattern to Issue, substituting the correct terminology.
- **Cancel** (Trip, or a future Invoice/Bill cancellation via reversal) — states the specific effect (e.g., "This trip will be marked cancelled and cannot be reopened") distinctly from Delete, since cancellation preserves the record while Delete removes it.
- **Remove Allocation** — states which invoice/bill will have its balance restored and that the payment's unallocated amount will increase correspondingly.
- **Logout** — the lightest-weight confirmation in the system, shown only when there's detectable unsaved work; otherwise logout proceeds without a dialog at all, since an unnecessary confirmation on a fully reversible, low-stakes action (logging back in is trivial) is itself a UX cost per this document's Undo-First philosophy (§1).

---

## 23. Role-Based User Journeys

### Owner
- **Daily Workflow:** Opens the Dashboard first; scans KPIs and Outstanding sections; drills into Reports or specific Companies/Invoices only when a number looks off; rarely performs data entry.
- **Primary Screens:** Dashboard, Reports, read-only views across Finance and Operations.
- **Permissions:** Broad read access everywhere; typically full access to Administration and Settings as the tenant's ultimate owner.
- **Navigation:** Lightest, most Dashboard-centric usage pattern of any role.

### Administrator
- **Daily Workflow:** Mostly reactive — onboarding a new team member, adjusting a role's permissions, checking Audit Logs after a question arises. Low daily frequency, high-stakes when active.
- **Primary Screens:** Users, Roles & Permissions, Settings, Audit Logs.
- **Permissions:** Full access to Administration/Settings; transactional access varies by tenant.
- **Navigation:** Administration and Settings sections, otherwise similar breadth to Owner for oversight purposes.

### Manager
- **Daily Workflow:** Reviews Dashboard for anomalies, checks open Invoices/overdue accounts, monitors Trip status across the fleet, escalates exceptions rather than resolving them directly.
- **Primary Screens:** Dashboard, Invoices/Payments lists (read-only), Trips list, Companies.
- **Permissions:** Broad read access, no lifecycle actions (Issue/Post/Allocate) unless specifically elevated.
- **Navigation:** Sits between Owner's dashboard-only pattern and Accountant/Operator's deep transactional usage.

### Accountant
- **Daily Workflow:** The heaviest transactional user in the system — creating and issuing Invoices, recording and allocating Customer Payments, posting Purchase Bills, recording Supplier Payments, reconciling outstanding balances, essentially all day.
- **Primary Screens:** Invoice Editor, Payment allocation screens, Purchase Bill Editor, Supplier Payment screen, Companies/Suppliers (for outstanding review).
- **Permissions:** Full access to Finance and Masters; read-only on Operations for context; no Administration/Settings access.
- **Navigation:** Lives almost entirely within the Finance section, with the Command Palette's Quick Actions used heavily given the sheer transaction volume.

### Operator (Boat Manager / Field Staff)
- **Daily Workflow (Boat Manager):** Creates and manages Trips, assigns boats, transitions trip status, reviews Catches/Expenses/Profit per trip.
- **Daily Workflow (Field Staff):** Narrower — logs Trip Catch and Trip Expense entries dockside, without broader Trip or Boat management responsibility.
- **Primary Screens:** Boats, Trips list and Trip Details (Overview/Catches/Expenses/Profit tabs).
- **Permissions:** Full access to Operations (Boat Manager) or scoped Catch/Expense entry only (Field Staff); no Finance or Administration access.
- **Navigation:** Entirely within Operations; the shortest, most task-focused sidebar footprint of any role, especially for Field Staff.

---

## 24. Mobile User Flows

- **Login:** Identical flow to desktop (§2), laid out single-column; password managers/autofill are fully supported given how frequently field staff may re-authenticate on shared devices.
- **Dashboard:** KPI cards and sections stack vertically; the same content as desktop, reflowed rather than reduced, since Owner/Manager mobile Dashboard checks are a real, expected use case.
- **Search:** The Command Palette is reachable via a visible search icon in the mobile topbar (no keyboard shortcut equivalent); results and interaction behavior are otherwise identical to desktop (§17).
- **Tables:** Wide tables (Invoices, Trips lists) gain horizontal scroll with a sticky identifying first column, per `02_DESIGN_SYSTEM.md` §15 — not restructured into stacked cards, preserving scanability and consistency with the desktop mental model.
- **Forms:** Multi-column desktop forms collapse to single-column; the Trip Catch/Expense inline-row entry pattern remains the primary mobile entry method for Field Staff, since that is this role's core mobile use case.
- **Approvals:** Notification-driven — a Manager/Owner receiving an Approval notification (§18, roadmap) on mobile can open directly into the relevant record and act, without needing the full desktop navigation context.
- **Navigation:** Sidebar replaced by the off-canvas Drawer described in `03_INFORMATION_ARCHITECTURE.md` §14; breadcrumbs collapse to a single "back" affordance.

---

## 25. UX Best Practices

- **Undo:** Favored over confirmation wherever the business genuinely allows reversal (draft edits, soft-deactivation); where the business does not allow it (Issue, Post), the system relies on upfront, specific confirmation instead, per §1's Undo-First philosophy.
- **Autosave:** Used narrowly for low-stakes, easily-interrupted drafting (per `02_DESIGN_SYSTEM.md` §10) — never for the final Issue/Post/Allocate action of any lifecycle.
- **Validation:** Always inline and immediate for format-level checks; always specific and corrective in wording, never a generic "invalid input."
- **Drafts:** Visually distinguished from finalized records everywhere they appear (list rows, badges, page chrome) so a draft is never mistaken for a committed record.
- **Context Preservation:** Filters, sort order, scroll position, and sidebar state persist across navigation, per `03_INFORMATION_ARCHITECTURE.md` §19.
- **Keyboard Shortcuts:** `⌘K`/`Ctrl+K` as the universal entry point; Enter-to-add-row on every line-item table (Invoice, Purchase Bill, Trip Catch, Trip Expense); Enter-to-submit on standard forms.
- **Accessibility:** Every flow in this document is fully operable by keyboard alone and meets the contrast/ARIA/reduced-motion standards defined in `02_DESIGN_SYSTEM.md` §16 — accessibility is not a separate flow, it is a property of every flow described above.

---

## 26. Workflow Summary

The **Customer Lifecycle** (Company → Invoice → Issue → Payment → Allocation → Outstanding Cleared) and **Supplier Lifecycle** (Supplier → Purchase Bill → Post → Payment → Allocation → Outstanding Cleared) are deliberately symmetric end-to-end — same interaction shapes, same immutability discipline, same allocation mechanics — so mastering one teaches the other. The **Trip Lifecycle** (Boat → Trip → Catch → Expenses → Profit) is the one workflow with no direct analog elsewhere in the product, and is designed around fast, low-friction field entry rather than the deliberate, confirmation-heavy pace of the financial lifecycles, because it is operational record-keeping rather than a legally-issued document trail. The **Financial Lifecycle** that spans both Customer and Supplier sides is governed throughout by one non-negotiable rule, inherited directly from `01_PRODUCT_VISION.md`: once issued or posted, a record does not change — corrections happen through new, auditable actions (reversal, allocation adjustment), never through silent edits to history. The **Administration Lifecycle** (Users → Roles → Permissions) sits apart from all of the above as low-frequency, high-consequence configuration work, and its effects — what a user can see and do — are what make every other lifecycle in this document behave differently for different roles, as detailed in §23.
