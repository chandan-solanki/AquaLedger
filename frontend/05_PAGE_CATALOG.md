# AquaLedger — Page Catalog

**The Master UI Specification for AquaLedger**

Version 1.0 · Page Catalog Document

This document specifies every page in AquaLedger. It builds directly on `01_PRODUCT_VISION.md` (business rules), `02_DESIGN_SYSTEM.md` (component behavior), `03_INFORMATION_ARCHITECTURE.md` (routes, navigation, breadcrumbs), and `04_USER_FLOWS.md` (interaction/validation behavior), and introduces no new business rule or navigation decision that contradicts them — it exists to enumerate and pin down every screen those documents already imply.

## How to Read This Catalog

To stay both complete and scannable across ~70 pages, this catalog defines each **page type's** standard field set once (§0), then documents every individual page as a **compact spec against that template** — only the fields that vary page-to-page are written out (URL, permission, columns/fields, page-specific actions, deltas from the standard). A field is omitted from an individual page's entry when it doesn't apply to that page type (e.g., a Create page has no Timeline) rather than repeated as "N/A" on every entry — §0 states which fields apply to which page type by default.

---

## 0. Page Layout Standard & Page Type Templates

### Global Layout Standard (applies to every page)

- **Header** — page title (entity name on Detail pages, module name on List pages), optional Status Badge, optional Breadcrumb directly above it.
- **Toolbar** — sits directly below the header on List pages: Search + Filters on the left, Primary CTA (and, space permitting, Secondary CTAs) on the right, per `02_DESIGN_SYSTEM.md` §8 Action Bar standard.
- **Filters** — a consistent filter bar (free-text search plus the small set of structured filters relevant to that entity), never hidden behind an extra click for the filters used constantly, per `02_DESIGN_SYSTEM.md` §9.
- **Search** — page-scoped search lives in the Toolbar; it is distinct from Global Search/Command Palette (`03_INFORMATION_ARCHITECTURE.md` §9, §12), which remains reachable from every page via the topbar/`⌘K` regardless of what's documented per-page below.
- **Primary CTA** — the single main action for the page (e.g., "+ New Company"), styled as the Primary Button variant, top-right of the header/toolbar.
- **Secondary CTA(s)** — supporting actions (e.g., Export), styled as Outline/Ghost buttons beside the Primary CTA.
- **Content Area** — the page's main body: a Data Table (List pages), a Form (Create/Edit pages), or a set of Cards/Tabs (Detail pages).
- **Sidebar** — not used as a page-level layout element anywhere in AquaLedger; the persistent application sidebar (`03_INFORMATION_ARCHITECTURE.md` §3) is the only sidebar in the product. Pages that need supplementary context (e.g., a Company's outstanding balance) surface it as a Card within the content area, not a page-local sidebar.
- **Bottom Actions** — used on Form pages only: a persistent or end-of-form action row (Cancel, Save Draft, primary Submit/Issue/Post) per `02_DESIGN_SYSTEM.md` §8 Form Layout standard.
- **Dialogs** — Confirmation Dialogs (`04_USER_FLOWS.md` §22), Allocation dialogs, and any other in-context modal are layered per `02_DESIGN_SYSTEM.md` §6 elevation rules and never replace a full page for anything the URL-Standards document (`03_INFORMATION_ARCHITECTURE.md` §17) defines as its own route.

### List Page Template

Applies to every `{module}` list route. Standard field set: **Purpose, URL, Permission, Breadcrumb, Header, Primary/Secondary Actions, Filters, Search, Table Spec (Columns, Sorting, Filtering, Pagination, Bulk Actions, Inline Actions, Status Badges, Export, Saved Views), Loading State, Empty State, Error State, Responsive Behavior, Accessibility Notes, Future Enhancements.**

Default mechanics common to every List page (stated once, not repeated per page below):
- **Sorting** — click any sortable column header; one active sort at a time; indicator shows column and direction.
- **Pagination** — standard paginated (not infinite-scroll) footer with page-size control and total count, per `02_DESIGN_SYSTEM.md` §9.
- **Bulk Actions** — a row-selection checkbox column appears only where a genuine bulk action exists for that entity; a contextual action bar replaces the toolbar when rows are selected.
- **Inline Actions** — a kebab menu in the last column (View / Edit / Delete or Deactivate, scoped to permission) on every list row.
- **Status Badges** — rendered per `04_USER_FLOWS.md` and `02_DESIGN_SYSTEM.md` §13 wherever the entity has lifecycle/active state.
- **Export** — respects active filters, per `02_DESIGN_SYSTEM.md` §9.
- **Saved Views (Future)** — reserved capability to save a named filter/sort/column combination as a personal or shared preset; not in the MVP scope for any list below unless noted.
- **Loading State** — skeleton rows matching the table's column structure, per `04_USER_FLOWS.md` §20.
- **Empty State** — purposeful "No [Entity] yet" state with the page's own Primary CTA, distinct from "No Search Results," per `04_USER_FLOWS.md` §21.
- **Error State** — page-level Alert with Retry, per `04_USER_FLOWS.md` §19.
- **Responsive Behavior** — horizontal scroll with sticky identifying first column below the tablet breakpoint; Toolbar filters collapse into a single "Filters" drawer trigger; the Primary CTA remains visible, per `04_USER_FLOWS.md` §24 / `02_DESIGN_SYSTEM.md` §15.
- **Accessibility Notes** — table is fully keyboard-navigable (row focus, action-menu access via keyboard); column headers expose sort state to assistive technology; status badges carry a text label, not color alone.

### Detail Page Template

Applies to every `{module}/{id}` route. Standard field set: **Purpose, URL, Permission, Breadcrumb, Header, Primary/Secondary Actions, Overview Card/Summary, Related Records, Tabs (where applicable), Timeline/Activity, Audit Information, Attachments (Future), Notes (Future), Loading State, Error State, Responsive Behavior, Accessibility Notes, Future Enhancements.**

Default mechanics common to every Detail page:
- **Overview Card / Summary** — the record's key identifying and status fields, always visible above any tabs/sections.
- **Related Records** — cross-linked tables per `03_INFORMATION_ARCHITECTURE.md` §6 (e.g., a Company's Invoices).
- **Timeline / Activity** — chronological record of status changes and key events, per `03_INFORMATION_ARCHITECTURE.md` §5, present on every Finance-lifecycle entity and Trips; omitted on simple master-data pages with no lifecycle (Fish, Boats) unless noted.
- **Audit Information** — created-by/at, last-updated-by/at, always shown in a consistent, low-emphasis position (footer of the Overview Card), sourced from the tamper-evident audit log described in `01_PRODUCT_VISION.md`.
- **Attachments (Future)** — reserved tab/section wherever `04_USER_FLOWS.md` §9 flags it (Invoices, Purchase Bills, Trips); shown as a disabled/"coming soon" tab in the interim rather than omitted, so its eventual arrival requires no navigation restructuring.
- **Notes (Future)** — reserved section on Companies, Suppliers, and Trips, same treatment as Attachments.
- **Loading State** — skeleton matching the Overview Card and section/tab structure.
- **Empty State** — not applicable at the page level (a Detail page only exists for a record that exists); applies instead to its Related Records sub-tables, which follow the List Page Template's Empty State rules in miniature.
- **Error State** — Not Found state (`04_USER_FLOWS.md` §19) if the ID is invalid/inaccessible; standard Error Alert for a data-load failure on an otherwise-valid record.
- **Responsive Behavior** — Overview Card fields stack single-column; tabs become a horizontally-scrollable tab strip; Related Record tables follow List Page responsive rules.
- **Accessibility Notes** — tab strip is keyboard-navigable (arrow keys between tabs); lifecycle action buttons are labeled with their exact verb (never icon-only) for screen-reader clarity.

### Form Page Template (Create / Edit)

Applies to every `{module}/new` and `{module}/{id}/edit` route. Standard field set: **Purpose, URL, Permission, Breadcrumb, Header, Primary/Secondary Actions, Form Sections/Field Groups, Validation, Autosave, Draft Handling, Loading State, Error State, Responsive Behavior, Accessibility Notes, Future Enhancements.**

Default mechanics common to every Form page:
- **Validation** — inline, on-blur for format checks; submission-time for cross-field/business-rule checks; per `04_USER_FLOWS.md` §19's Validation Error category.
- **Autosave** — off by default for standard master-data forms; used only where `04_USER_FLOWS.md` explicitly calls for it (none of the master-data Create/Edit forms below use autosave — see Invoice/Purchase Bill Editors' own entries for their Save Draft behavior, which is explicit-save, not autosave).
- **Draft Handling** — applies only to Invoice and Purchase Bill; all other Create forms are single-step submissions with no draft concept.
- **Cancel** — always returns to the record's Detail page (Edit) or the module's List page (Create) without saving, with a lightweight "discard changes?" confirmation only if the form has been modified.
- **Save** — a single, unambiguous Primary Button labeled with the specific outcome ("Save Company," never generic "Submit").
- **Loading State** — the form itself renders immediately (it has no server data dependency on Create); Edit forms show a skeleton matching the field layout while the existing record loads.
- **Error State** — Validation and Server error categories per `04_USER_FLOWS.md` §19; a failed save never clears entered field values.
- **Responsive Behavior** — multi-column field groups collapse to single-column below the laptop breakpoint, per `04_USER_FLOWS.md` §24.
- **Accessibility Notes** — every field has a programmatically associated label; error messages are announced to assistive technology when they appear; tab order follows visual/logical field order.

---

## 1. Authentication

### Login
- **Purpose:** Authenticate a user into their tenant.
- **URL:** `/login`
- **Permission:** Public (unauthenticated).
- **Breadcrumb:** None (pre-application shell).
- **Header:** AquaLedger identity mark, no page title chrome — this is the one page outside the standard app shell.
- **Primary Actions:** Log In.
- **Secondary Actions:** "Forgot password?" link.
- **Page Sections:** Email field, password field, Log In button; error region for authentication failure (generic "Invalid email or password" — never reveals which field was wrong).
- **Loading State:** Log In button shows its loading state (per `02_DESIGN_SYSTEM.md` §8) while authenticating; form fields disable during submission.
- **Error State:** Inline, generic credential-failure message above the form; Network/Server error categories per `04_USER_FLOWS.md` §19.
- **Responsive Behavior:** Single-column, centered card layout at every width; identical behavior desktop to mobile per `04_USER_FLOWS.md` §24.
- **Accessibility Notes:** Autofill/password-manager compatible; error message announced on failed submit; Enter submits the form from either field.
- **Future Enhancements:** SSO/OAuth login options; "remember this device."

### Forgot Password
- **Purpose:** Initiate a password reset.
- **URL:** `/forgot-password`
- **Permission:** Public.
- **Breadcrumb:** None.
- **Header:** "Reset your password."
- **Primary Actions:** Send Reset Link.
- **Secondary Actions:** "Back to login" link.
- **Page Sections:** Single email field; on submit, replaces the form with a confirmation message (identical wording regardless of whether the email exists, per `04_USER_FLOWS.md` §2).
- **Loading/Error State:** Standard button-loading and Network/Server error handling.
- **Responsive Behavior:** Same centered single-column card as Login.
- **Accessibility Notes:** Confirmation message is announced to assistive technology on appearance.
- **Future Enhancements:** None planned — intentionally minimal.

### Reset Password
- **Purpose:** Set a new password from a valid reset link.
- **URL:** `/reset-password?token={token}`
- **Permission:** Public, valid-token-gated.
- **Breadcrumb:** None.
- **Header:** "Choose a new password."
- **Primary Actions:** Save New Password.
- **Secondary Actions:** None.
- **Page Sections:** New password field, confirm-password field (inline match validation), password-strength guidance text; on invalid/expired token, the entire form is replaced by an expired-link state with a direct link back to Forgot Password (`04_USER_FLOWS.md` §2).
- **Validation:** Minimum password strength rules enforced inline; mismatch between the two fields blocks submission with an inline error.
- **Responsive Behavior:** Same centered single-column card pattern.
- **Accessibility Notes:** Password strength feedback is exposed as text, not color alone.
- **Future Enhancements:** None planned.

### Unauthorized
- **Purpose:** Inform an authenticated user they lack access to a page they navigated to directly.
- **URL:** Rendered in place of any route the user's permission set excludes (no dedicated URL of its own; not linked to from navigation, per `04_USER_FLOWS.md` §2).
- **Permission:** Shown to any authenticated user lacking the target permission.
- **Breadcrumb:** None (the page itself couldn't be reached legitimately via breadcrumb).
- **Header:** "You don't have access to this page."
- **Primary Actions:** Return to Dashboard.
- **Page Sections:** Explanatory message; no data content.
- **Responsive Behavior:** Centered single-column message, identical at every width.
- **Accessibility Notes:** Message is the page's primary landmark content, immediately focusable.
- **Future Enhancements:** A "request access" contact-administrator action.

### Session Expired
- **Purpose:** Handle an authentication session lapsing mid-use.
- **URL:** Intercepts the current route; redirects to `/login` after acknowledgment, per `04_USER_FLOWS.md` §2.
- **Permission:** N/A (transitional state).
- **Header:** "Your session has expired."
- **Primary Actions:** Log In Again (redirects to `/login`, returns the user to their prior route on success).
- **Page Sections:** Explanatory message; any recoverable in-progress form state is preserved client-side across the re-login round trip per `04_USER_FLOWS.md` §2.
- **Responsive Behavior:** Same centered card pattern.
- **Future Enhancements:** Silent token refresh to avoid this interruption entirely for still-active users.

---

## 2. Dashboard

### Executive Dashboard
- **Purpose:** Single-page, role-scoped overview of business health and an entry point into every other module.
- **URL:** `/dashboard` (also `/`, which redirects here).
- **Permission:** All authenticated roles; content scoped per `04_USER_FLOWS.md` §23.
- **Breadcrumb:** None (root of every breadcrumb chain per `03_INFORMATION_ARCHITECTURE.md` §7).
- **Header:** "Dashboard," no status badge; a date/period indicator if KPIs are period-scoped.
- **Primary Actions:** Quick Actions trigger (§15).
- **Secondary Actions:** Manual KPI refresh.
- **Page Sections:**
  - **KPIs:** Total Receivables Outstanding, Total Payables Outstanding, Trips Currently at Sea, Boats with Expiring/Expired Compliance — each a Metric/KPI Card, each clickable through to its filtered source view, per `03_INFORMATION_ARCHITECTURE.md` §8.
  - **Charts:** Revenue trend (Line), Receivables aging (Bar) — Recharts per `02_DESIGN_SYSTEM.md` §11; each links through to the corresponding Report.
  - **Recent Activity:** reverse-chronological feed of recent Invoices/Payments/Trip status changes, each row linking to its Detail page.
  - **Pending Work:** draft invoices awaiting Issue, unallocated payments, trips awaiting settlement — scoped to the current user's role and, where relevant, their own created/assigned records.
  - **Outstanding:** top overdue customers / top-due suppliers mini-lists, linking to filtered Companies/Suppliers views.
  - **Quick Actions:** duplicated Quick Create surface (§15).
- **Loading State:** Each section (KPIs, Charts, Activity, Pending Work, Outstanding) loads and skeletons independently — the page never blocks entirely on the slowest section, per `04_USER_FLOWS.md` §3/§20.
- **Empty State:** Each section defines its own minimal empty variant (e.g., "No pending work" rather than an empty card) — never an empty Dashboard as a whole, since KPIs always render (as zero values) even with no data.
- **Error State:** Per-section Alert with Retry if that section's data fails to load; other sections remain functional.
- **Responsive Behavior:** KPI row wraps to 2-then-1 columns; charts stack full-width; Recent Activity/Pending Work/Outstanding stack vertically in a fixed priority order (Pending Work and Outstanding before Recent Activity, since they're actionable) per `04_USER_FLOWS.md` §24.
- **Accessibility Notes:** KPI cards expose their value and label as readable text (not chart-only); charts include a text-equivalent summary for screen readers.
- **Future Enhancements:** Customizable/reorderable widget layout; AI-surfaced insight cards (`03_INFORMATION_ARCHITECTURE.md` §11).

---

## 3. Companies

### Companies List
- **URL:** `/companies` · **Permission:** `company:read`.
- **Breadcrumb:** Dashboard > Companies.
- **Header:** "Companies."
- **Primary Actions:** + New Company. **Secondary Actions:** Export.
- **Filters:** Status (Active/Inactive), Company Type (Customer/Supplier/Both). **Search:** name, code, GSTIN.
- **Columns:** Code · Name · Type · GSTIN · Credit Limit · Outstanding Balance · Status · Updated.
- **Bulk Actions:** Bulk deactivate (permission-gated).
- **Inline Actions:** View, Edit, Deactivate.
- **Status Badges:** Active / Inactive.
- **Future Enhancements:** Saved Views; column customization for credit-team vs. sales-team users.

### Create Company
- **URL:** `/companies/new` · **Permission:** `company:create`.
- **Breadcrumb:** Dashboard > Companies > New Company.
- **Header:** "New Company."
- **Primary Actions:** Save Company. **Secondary Actions:** Cancel.
- **Form Sections:** Identity (Name, Code, Company Type, GSTIN, PAN) · Address · Credit Terms (Credit Limit, Credit Days) · Status (defaults Active).
- **Validation:** Required: Name, Company Type. GSTIN/PAN format validation. Duplicate-GSTIN detection surfaced as a field-level error per `04_USER_FLOWS.md` §4.
- **Future Enhancements:** Bulk import from CSV.

### Company Details
- **URL:** `/companies/{id}` · **Permission:** `company:read`.
- **Breadcrumb:** Dashboard > Companies > {Company Name}.
- **Header:** Company name, Active/Inactive status badge.
- **Primary Actions:** Edit, New Invoice (pre-filled with this company). **Secondary Actions:** Deactivate.
- **Overview Card:** Name, Code, Type, GSTIN, PAN, Address, Credit Limit, Credit Days, current Outstanding Balance (prominently displayed, tabular numerals).
- **Related Records:** Invoices issued to this company (table, linking per `03_INFORMATION_ARCHITECTURE.md` §6).
- **Timeline/Activity:** Status changes (activated/deactivated), credit-limit changes.
- **Attachments (Future) / Notes (Future):** reserved tabs.
- **Future Enhancements:** Contact log; document uploads (GST certificate, agreements).

### Edit Company
- **URL:** `/companies/{id}/edit` · **Permission:** `company:update`.
- **Breadcrumb:** Dashboard > Companies > {Company Name} > Edit.
- Identical field structure to Create Company, pre-filled; duplicate check excludes the record's own current GSTIN value.

---

## 4. Suppliers

Follows the identical List / Create / Details / Edit structure as Companies (§3), with these deltas:

### Suppliers List
- **URL:** `/suppliers` · **Permission:** `supplier:read`. **Breadcrumb:** Dashboard > Suppliers.
- **Columns:** Code · Name · GSTIN · Credit Days · Outstanding Balance (payable) · Status.
- **Filters:** Status. **Search:** name, code, GSTIN.

### Create Supplier
- **URL:** `/suppliers/new` · **Permission:** `supplier:create`.
- **Form Sections:** Identity (Name, Code, GSTIN, Contact) · Credit Terms (Credit Days) · Status. No Company-Type field (single-purpose master).

### Supplier Details
- **URL:** `/suppliers/{id}` · **Permission:** `supplier:read`.
- **Primary Actions:** Edit, New Purchase Bill. **Secondary Actions:** Deactivate.
- **Overview Card:** Name, Code, GSTIN, Contact, Credit Days, current Outstanding (payable) Balance.
- **Related Records:** Purchase Bills and Supplier Payments for this supplier.

### Edit Supplier
- **URL:** `/suppliers/{id}/edit` · **Permission:** `supplier:update`. Mirrors Edit Company.

---

## 5. Fish

### Fish List
- **URL:** `/fish` · **Permission:** `fish:read`. **Breadcrumb:** Dashboard > Fish.
- **Filters:** Category, Status. **Search:** name, local name, code.
- **Columns:** Code · Name · Local Name · Category · Unit · Default Purchase Rate · Default Sale Rate · Status.
- **Inline Actions:** View, Edit, Deactivate.

### Create Fish
- **URL:** `/fish/new` · **Permission:** `fish:create`.
- **Form Sections:** Identity (Name, Local Name, Code, Category) · Unit & Rates (Unit of Measure, Default Purchase Rate, Default Sale Rate, HSN Code) · Status.
- **Validation:** Required: Name, Category, Unit. Rates non-negative, exact-decimal entry per `02_DESIGN_SYSTEM.md` §4. Duplicate code detection.

### Fish Details
- **URL:** `/fish/{id}` · **Permission:** `fish:read`.
- **Overview Card:** Name, Local Name, Code, Category, Unit, Default Rates, HSN Code, Status.
- **Related Records:** none surfaced by default (Fish is referenced heavily but reverse-lookup of every Trip Catch/Invoice line using it is deferred to Reports rather than shown on this page).
- **Timeline/Activity:** omitted (no lifecycle beyond active/inactive).
- **Future Enhancements:** "Recently sold at" rate-history mini-chart.

### Edit Fish
- **URL:** `/fish/{id}/edit` · **Permission:** `fish:update`. Mirrors Create Fish, pre-filled.

---

## 6. Boats

### Boats List
- **URL:** `/boats` · **Permission:** `boat:read`. **Breadcrumb:** Dashboard > Boats.
- **Filters:** Status, "Compliance expiring soon" quick filter. **Search:** name, registration number.
- **Columns:** Name/Registration No. · Ownership Type · Captain · License Expiry · Insurance Expiry · Compliance Status · Status.
- **Status Badges:** Active/Inactive plus a separate Compliance indicator (OK / Expiring Soon / Expired) per `04_USER_FLOWS.md` §7.

### Create Boat
- **URL:** `/boats/new` · **Permission:** `boat:create`.
- **Form Sections:** Identity (Name, Registration Number, Ownership Type, Captain) · Compliance (License Expiry, Insurance Expiry).
- **Validation:** Required: Name/Registration, Ownership Type. Past-dated expiry fields accepted with an inline warning, not blocked, per `04_USER_FLOWS.md` §7.

### Boat Details
- **URL:** `/boats/{id}` · **Permission:** `boat:read`.
- **Primary Actions:** Edit, New Trip (pre-filled with this boat). **Secondary Actions:** Deactivate.
- **Overview Card:** Name/Registration, Ownership Type, Captain, License/Insurance Expiry with Compliance Status badge.
- **Related Records:** Trip history for this boat.
- **Future Enhancements:** Crew roster management.

### Edit Boat
- **URL:** `/boats/{id}/edit` · **Permission:** `boat:update`. Mirrors Create Boat.

---

## 7. Trips

### Trips List
- **URL:** `/trips` · **Permission:** `trip:read`. **Breadcrumb:** Dashboard > Trips.
- **Filters:** Status (planned/at_sea/returned/settled/cancelled), Boat. **Search:** trip number.
- **Columns:** Trip Number · Boat · Planned Departure · Actual Departure · Return Date · Status · Est./Actual Profit (once Catch+Expenses logged).
- **Status Badges:** per the Trip lifecycle in `04_USER_FLOWS.md` §8.

### Create Trip
- **URL:** `/trips/new` · **Permission:** `trip:create`.
- **Form Sections:** Assignment (Boat selector, Planned Departure Date) · Crew (optional, if tenant tracks crew).
- **Validation:** Boat required; expired-compliance boat selectable with inline warning, not blocked, per `04_USER_FLOWS.md` §8.

### Trip Details
- **URL:** `/trips/{id}` · **Permission:** `trip:read`.
- **Header:** Trip Number, lifecycle Status Badge.
- **Primary Actions:** the single valid next lifecycle action for the trip's current status only (Depart / Return / Settle), per `03_INFORMATION_ARCHITECTURE.md` §13's "button rendered only when valid" rule. **Secondary Actions:** Edit (while `planned`), Cancel (while `planned`/`at_sea`).
- **Overview Card:** Boat, Captain, Planned/Actual Departure, Return Date, Status.
- **Tabs:**
  - **Overview** — the Overview Card content plus a summary strip (total catch value, total expenses, net profit) once data exists.
  - **Catch** — Trip Catch table (Fish, Grade, Caught/Available/Sold/Waste Qty) with inline "+ Add Catch" row entry, per `04_USER_FLOWS.md` §9.
  - **Expenses** — Trip Expense table (Category, Amount, Date, Receipt-future) with inline "+ Add Expense" row entry, per `04_USER_FLOWS.md` §10.
  - **Profit** — computed summary: Revenue from Sold Catch − Total Expenses = Net Profit, presented as a small set of KPI-style figures, not a separate report.
- **Timeline:** status transitions (planned→at_sea→returned→settled/cancelled) with who performed each and when.
- **Related Records:** Invoice lines that reference this trip's catch (cross-linked per `03_INFORMATION_ARCHITECTURE.md` §6).
- **Future Enhancements:** Attachments (catch slips), crew performance notes.

### Edit Trip
- **URL:** `/trips/{id}/edit` · **Permission:** `trip:update`. Reachable only while `planned`, per `03_INFORMATION_ARCHITECTURE.md` §5. Edits Boat assignment, Planned Departure, Crew.

---

## 8. Invoices

### Invoice List
- **URL:** `/invoices` · **Permission:** `invoice:read`. **Breadcrumb:** Dashboard > Invoices.
- **Filters:** Status (draft/issued/partially_paid/paid/overdue/cancelled), Company, Date Range. **Search:** invoice number, company name.
- **Columns:** Invoice Number · Company · Issue Date · Due Date · Grand Total · Balance Due · Status.
- **Inline Actions:** View; Edit (draft only); Issue (draft only, from row-level kebab as a shortcut to the same action on Details).
- **Future Enhancements:** Saved Views per user (e.g., "My overdue invoices").

### Create Invoice
- **URL:** `/invoices/new` · **Permission:** `invoice:create`.
- **Header:** "New Invoice," Draft status badge (assigned implicitly on first save).
- **Form Sections:**
  - **Header** — Company selector (searchable, focused first), Invoice Date, Due Date.
  - **Line Items** — dynamic table: Fish selector (optionally linked to a Trip Catch record), Quantity, Unit, Rate, Discount %, Tax Rate, live Line Total; Enter-to-add-row.
  - **Totals Panel** — Subtotal, Discount, Taxable Amount, CGST/SGST/IGST breakdown, Transport Charge, Other Charges, Round-off, Grand Total — all live-recalculating per `04_USER_FLOWS.md` §11.
- **Primary Actions:** Save Draft, Issue Invoice. **Secondary Actions:** Cancel.
- **Validation:** Company required before line items are meaningful; at least one line item required to Issue (not to Save Draft); each line requires fish/description, positive quantity, non-negative rate; discount/tax within 0–100%.
- **Draft Handling:** Freely re-editable indefinitely while in draft; explicit Save Draft action (not autosave).
- **Future Enhancements:** Line-item templates for repeat customers; bulk line-item import from a Trip's unsold catch.

### Invoice Details
- **URL:** `/invoices/{id}` · **Permission:** `invoice:read`.
- **Header:** Invoice Number (blank/pending until Issued), Status Badge.
- **Primary Actions:** Issue (draft only); Record Payment shortcut (issued/partially_paid only). **Secondary Actions:** Edit (draft only), Cancel/Reverse (issued+, via reversal mechanism).
- **Overview Card:** Company, Issue Date, Due Date, Grand Total, Amount Paid, Balance Due.
- **Page Sections:** Line items table (read-only once issued); Totals Panel (read-only mirror of the Editor's).
- **Related Records:** Customer Payments allocated to this invoice, each linking to its own Detail page, per `04_USER_FLOWS.md` §12.
- **Timeline/Activity:** Draft created → Issued (by whom, when, assigned number) → each Payment allocation event → status changes to Partially Paid/Paid/Overdue.
- **Audit Information:** created-by/at, issued-by/at.
- **Attachments (Future):** reserved tab.
- **Future Enhancements:** PDF preview/download (near-term roadmap per `01_PRODUCT_VISION.md` §11); email-to-customer action.

### Edit Draft Invoice
- **URL:** `/invoices/{id}/edit` · **Permission:** `invoice:update`. Identical layout to Create Invoice, pre-filled; reachable only while status = draft, per `03_INFORMATION_ARCHITECTURE.md` §5.

### Invoice Issue Confirmation
- **Type:** Confirmation Dialog (not a route), triggered from the Issue action on Create/Edit/Details.
- **Purpose:** Final, explicit checkpoint before an invoice becomes permanently numbered and immutable.
- **Page Sections:** States plainly: "This invoice will be assigned its permanent number and locked — it cannot be edited after issuing." Shows the company name and grand total for final visual confirmation.
- **Primary Actions:** Issue Invoice (Primary Button, not pre-focused per `02_DESIGN_SYSTEM.md` §22 pattern... note: Issue is the intended action here and *is* the primary/default action, unlike a Delete dialog — the dialog exists to inform, not to discourage). **Secondary Actions:** Cancel.
- **Error State:** If Issue fails server-side (e.g., a concurrent numbering conflict), the dialog surfaces the error inline and remains open rather than closing into a broken state.
- **Future Enhancements:** None — intentionally minimal, single-purpose.

---

## 9. Customer Payments

### Payment List
- **URL:** `/payments` · **Permission:** `payment:read`. **Breadcrumb:** Dashboard > Customer Payments.
- **Filters:** Company, Date Range, Method. **Search:** payment reference number, company name.
- **Columns:** Payment Ref · Company · Date · Amount · Allocated · Unallocated · Method.
- **Inline Actions:** View.

### Create Payment
- **URL:** `/payments/new` · **Permission:** `payment:create`.
- **Form Sections:** Header (Company selector, Amount, Method, Reference/Date) · Allocation Table (see Allocation Dialog below — embedded directly in this page, not a separate modal, since it's the core of the task).
- **Primary Actions:** Save Payment. **Secondary Actions:** Cancel.
- **Validation:** Sum of allocations cannot exceed payment amount; a single allocation cannot exceed that invoice's outstanding balance; both enforced inline at the offending row per `04_USER_FLOWS.md` §12.
- **Future Enhancements:** Auto-allocate (oldest-invoice-first) suggestion button.

### Payment Details
- **URL:** `/payments/{id}` · **Permission:** `payment:read`.
- **Header:** Payment Reference, no lifecycle status badge beyond "Posted" (payments have no draft state — see `04_USER_FLOWS.md` §12).
- **Primary Actions:** none (immutable once saved). **Secondary Actions:** Remove Allocation (per-row, gated by confirmation).
- **Overview Card:** Company, Date, Amount, Method, Reference, current Unallocated balance.
- **Page Sections:** Allocation table — every invoice this payment covers, with amount allocated to each, each row linking to its Invoice Details page.
- **Timeline/Activity:** Payment recorded → each allocation event → any allocation removal event.
- **Audit Information:** recorded-by/at.
- **Future Enhancements:** Receipt PDF generation.

### Allocation Dialog
- **Type:** Embedded page section on Create Payment (not a separate modal in the primary flow); reused as a modal specifically for the **add/adjust allocation** interaction on an existing Payment's Details page when adding a new allocation to a payment that still has unallocated balance.
- **Purpose:** Let the user distribute a payment amount across one or more open invoices.
- **Page Sections:** Open-invoices table for the selected company (Invoice Number, Due Date, Outstanding Balance, editable Allocate-Amount field per row), running Unallocated total.
- **Validation:** As specified under Create Payment above.
- **Primary Actions:** Apply Allocation. **Secondary Actions:** Cancel.

### Posting Confirmation
- **Type:** Confirmation Dialog, triggered from Save on Create Payment (functions as this workflow's equivalent of Invoice's Issue Confirmation, since saving a Payment is itself the immutable-committing action).
- **Purpose:** Final checkpoint before the payment and its allocations become permanent.
- **Page Sections:** States plainly which invoices will be updated and by how much, and that the payment record cannot be edited afterward (only reversed via Remove Allocation, per `04_USER_FLOWS.md` §12).
- **Primary/Secondary Actions:** Confirm & Save / Cancel.

---

## 10. Purchase Bills

Mirrors §8 (Invoices) exactly in page structure, substituting Supplier for Company and Post for Issue.

### Purchase Bill List
- **URL:** `/purchase-bills` · **Permission:** `purchase_bill:read`.
- **Columns:** Bill Number · Supplier · Bill Date · Due Date · Grand Total · Balance Due · Status.
- **Filters:** Status (draft/posted/partially_paid/paid), Supplier, Date Range.

### Create Purchase Bill
- **URL:** `/purchase-bills/new` · **Permission:** `purchase_bill:create`.
- **Form Sections:** Header (Supplier selector, Bill Date, Due Date) · Line Items (Description, Quantity, Rate, Tax — no Fish/Trip-Catch linkage, per `04_USER_FLOWS.md` §13) · Totals Panel (same live-recalculation structure as Invoices).
- **Primary Actions:** Save Draft, Post Bill.

### Purchase Bill Details
- **URL:** `/purchase-bills/{id}` · **Permission:** `purchase_bill:read`.
- **Primary Actions:** Post (draft only); Record Supplier Payment shortcut (posted+). **Secondary Actions:** Edit (draft only).
- **Related Records:** Supplier Payments allocated to this bill.
- **Timeline/Activity:** Draft → Posted (numbered) → allocation events → status changes.

### Edit Draft Purchase Bill
- **URL:** `/purchase-bills/{id}/edit` · **Permission:** `purchase_bill:update`. Reachable only while status = draft.

### Posting Confirmation
- **Type:** Confirmation Dialog, identical purpose and structure to the Invoice Issue Confirmation (§8), worded for "Post" terminology per `04_USER_FLOWS.md` §13.

---

## 11. Supplier Payments

Mirrors §9 (Customer Payments) exactly, substituting Supplier for Company and Purchase Bills for Invoices.

### Supplier Payment List
- **URL:** `/supplier-payments` · **Permission:** `supplier_payment:read`.
- **Columns:** Payment Ref · Supplier · Date · Amount · Allocated · Unallocated · Method.

### Create Supplier Payment
- **URL:** `/supplier-payments/new` · **Permission:** `supplier_payment:create`. Same header + embedded allocation table structure as Create Payment (§9), against open Purchase Bills instead of Invoices.

### Supplier Payment Details
- **URL:** `/supplier-payments/{id}` · **Permission:** `supplier_payment:read`. Same structure as Payment Details (§9).

### Allocation Dialog
Same purpose/structure as §9's, scoped to Purchase Bills.

### Posting Confirmation
Same purpose/structure as §9's.

---

## 12. Reports

All Report pages share a common shape: Filter Bar → Results (table and/or chart) → Export/Print, per `04_USER_FLOWS.md` §15. Individual entries below specify only what's report-specific.

### Sales Report
- **URL:** `/reports/sales-summary` · **Permission:** `report:read`.
- **Filters:** Date Range, Company, Fish/Category.
- **Page Sections:** Summary KPIs (total sales, invoice count, average invoice value) · trend Chart · itemized results table.
- **Future Enhancements:** Breakdown by sales rep once a rep field exists.

### Purchase Report
- **URL:** `/reports/purchase-summary` · **Permission:** `report:read`.
- **Filters:** Date Range, Supplier.
- **Page Sections:** Summary KPIs (total purchases, bill count) · trend Chart · itemized results table.

### Trip Profitability
- **URL:** `/reports/trip-profitability` · **Permission:** `report:read`.
- **Filters:** Date Range, Boat, Status.
- **Page Sections:** Per-trip table (Trip Number, Boat, Revenue, Expenses, Net Profit, Margin %) sortable by Net Profit; each row links to its Trip Details page.
- **Future Enhancements:** Per-boat rollup summary view.

### Receivable Aging
- **URL:** `/reports/receivables-aging` · **Permission:** `report:read`.
- **Filters:** As-of Date, Company.
- **Page Sections:** Aging-bucket table (Current, 1–30, 31–60, 61–90, 90+ days) per company, each row linking to that Company's Details page; total row.
- **Future Enhancements:** Aging-bucket chart visualization.

### Payable Aging
- **URL:** `/reports/payables-aging` · **Permission:** `report:read`. Mirrors Receivable Aging, scoped to Suppliers/Purchase Bills.

### Inventory (Future)
- **URL:** `/reports/inventory` (reserved) · **Permission:** `report:read`.
- **Purpose:** Placeholder for a future available-catch-on-hand report once inventory tracking extends beyond Trip Catch's available/sold/waste model, per `03_INFORMATION_ARCHITECTURE.md` §15.
- **Page Sections:** Rendered as the "Coming Soon" empty state (`04_USER_FLOWS.md` §21) until built.

### Financial Summary
- **URL:** `/reports/financial-summary` · **Permission:** `report:read`.
- **Filters:** Date Range (fiscal period selector).
- **Page Sections:** High-level KPI set (Revenue, Purchases, Gross Trip Profit, Net Receivables Movement, Net Payables Movement) — the report-page equivalent of the Dashboard's KPI row, but period-comparable (this-period vs. last-period deltas) rather than live/current-moment.

---

## 13. Administration

### Users
- **URL:** `/users` · **Permission:** `user:read` (Administrator).
- **Breadcrumb:** Dashboard > Administration > Users.
- **Filters:** Role, Status. **Search:** name, email.
- **Columns:** Name · Email · Role · Status · Last Active.
- **Inline Actions:** View, Edit Role, Deactivate.
- **Primary Actions:** + Invite User.

### Create User
- **URL:** `/users/new` · **Permission:** `user:create`.
- **Header:** "Invite User."
- **Form Sections:** Identity (Name, Email) · Role Assignment (required).
- **Primary Actions:** Send Invitation.
- **Validation:** Valid email format; duplicate-email detection; Role required.
- **Description:** This is an invitation flow, not direct account creation — the invited user sets their own password on first access, per `04_USER_FLOWS.md` §16.

### User Details
- **URL:** `/users/{id}` · **Permission:** `user:read`.
- **Primary Actions:** Edit Role. **Secondary Actions:** Deactivate, Resend Invitation (if invitation pending).
- **Overview Card:** Name, Email, Role, Status, Last Active, invitation status.
- **Timeline/Activity:** Role changes, activation/deactivation events, login history summary.
- **Audit Information:** invited-by/at.

### Roles
- **URL:** `/roles` · **Permission:** `role:read` (Administrator).
- **Breadcrumb:** Dashboard > Administration > Roles.
- **Columns:** Role Name · Description · User Count · Permission Count.
- **Primary Actions:** + New Role.
- **Detail/Edit (`/roles/{id}`, `/roles/{id}/edit`):** Role name/description fields plus the Permissions matrix (below) embedded directly on the same page — Roles and Permissions are one page pair, not two, since a role's permissions are its entire substance.

### Permissions
- **Page Sections (embedded within Role Details/Edit, not a standalone route):** A `resource:action` permission matrix — modules down the left, actions (read/create/update/delete/issue/post/allocate/approve as applicable) across the top, toggleable per cell — per `01_PRODUCT_VISION.md` §10.
- **Description:** Changing a role's permissions here takes effect immediately for every user holding that role, including their visible sidebar on next navigation, per `04_USER_FLOWS.md` §16.
- **Future Enhancements:** Permission templates/presets for common role archetypes; a "preview as this role" mode for Administrators.

### Audit Logs
- **URL:** `/audit-logs` · **Permission:** `audit:read` (Administrator).
- **Breadcrumb:** Dashboard > Administration > Audit Logs.
- **Filters:** Date Range, User, Entity Type, Action Type. **Search:** entity reference (e.g., invoice number).
- **Columns:** Timestamp · User · Action · Entity Type · Entity Reference.
- **Detail (`/audit-logs/{id}`):** full before/after change detail for a single audit entry, read-only.
- **Description:** Read-only throughout; this page surfaces the tamper-evident, hash-chained audit trail described in `01_PRODUCT_VISION.md` — nothing here is ever editable or deletable.
- **Future Enhancements:** Export for compliance review.

---

## 14. Settings

All Settings pages are single-record configuration forms (no List/Detail split), reachable only by Administrators, under `/settings/*`.

### Company Profile
- **URL:** `/settings/company` · **Permission:** `settings:update`.
- **Form Sections:** Tenant identity (Legal Name, GSTIN, Address), branding placeholder (logo — future), fiscal year configuration.

### Business Settings
- **URL:** `/settings/business` · **Permission:** `settings:update`.
- **Form Sections:** Default currency/locale display formatting, default credit terms applied to new Companies/Suppliers.

### Numbering
- **URL:** `/settings/sequences` · **Permission:** `settings:update`.
- **Page Sections:** View (and, within safe bounds, configure) the fiscal-year invoice/purchase-bill numbering pattern and current sequence position, per `01_PRODUCT_VISION.md`'s atomic-numbering architecture — presented as a read-mostly configuration surface given how consequential changing an active sequence is.
- **Description:** This page never allows renumbering or editing already-issued numbers — only forward-looking configuration (prefix/pattern for the *next* fiscal year).

### Categories
- **URL:** `/settings/categories` · **Permission:** `settings:update`.
- **Page Sections:** Tabbed or sectioned management of Expense Categories (used in Trip Expenses) and Fish Categories (used in the Fish master) — simple add/rename/deactivate list management for each.

### Tax Settings
- **URL:** `/settings/tax` · **Permission:** `settings:update`.
- **Form Sections:** Default CGST/SGST/IGST rates available for selection on Invoice/Purchase Bill line items; HSN-code-to-default-rate mapping.

### Profile
- **URL:** `/profile` · **Permission:** self (any authenticated user).
- **Breadcrumb:** Dashboard > Profile.
- **Form Sections:** Name, contact details, avatar (future).
- **Description:** Self-service, distinct from the Users administration page — a user always has access to their own Profile regardless of role.

### Notification Preferences
- **URL:** `/profile/notifications` (or a tab within Profile) · **Permission:** self.
- **Page Sections:** Per-category toggle (Invoices, Payments, Purchase Bills, Trips, System, Approvals — matching `03_INFORMATION_ARCHITECTURE.md` §11's categories) for which notifications the user receives and through which channel (in-app now; email/SMS reserved for future).

### Appearance
- **URL:** `/profile/appearance` (or a tab within Profile) · **Permission:** self.
- **Page Sections:** Theme selection (Light/Dark/System), density preference (Comfortable/Compact for tables, per `02_DESIGN_SYSTEM.md` §9).
- **Description:** Duplicates the topbar theme toggle's function as a persisted, explicit setting rather than a separate mechanism.

---

## 15. Global Components

These are not routes; they are persistent or overlay UI available from every page, specified here because their behavior spans the whole application.

### Command Palette
- **Trigger:** `⌘K` / `Ctrl+K`, or the mobile search icon.
- **Purpose:** Unified search, navigation, and action-execution surface, per `03_INFORMATION_ARCHITECTURE.md` §12 and `04_USER_FLOWS.md` §17.
- **Page Sections:** Empty state (Recent Searches/Recently Visited); grouped, typed results as the user types; keyboard-navigable result list.
- **Accessibility Notes:** Full keyboard operability is this component's core requirement, not an enhancement.

### Global Search
- Functionally the same surface as the Command Palette when a search term is entered — see above; not a separate UI element.

### Notification Center
- **Trigger:** Bell icon, topbar, persistent badge count.
- **Purpose:** Categorized, actionable notification feed, per `03_INFORMATION_ARCHITECTURE.md` §11 and `04_USER_FLOWS.md` §18.
- **Page Sections:** Category-grouped list, each item linking to its entity; mark-read / mark-all-read actions; History view of past (read) notifications.

### User Menu
- **Trigger:** Avatar, topbar, top-right.
- **Purpose:** Access to Profile, Notification Preferences, Appearance, and Logout.
- **Page Sections:** Simple dropdown list per `02_DESIGN_SYSTEM.md` §8 Dropdown standard.

### Quick Actions
- **Trigger:** "+ Quick Create" topbar control, and the Dashboard's own Quick Actions section.
- **Purpose:** One-hop access to the highest-frequency Create routes, permission-scoped, per `03_INFORMATION_ARCHITECTURE.md` §10.
- **Page Sections:** A simple list (New Company, New Supplier, New Trip, New Invoice, New Customer Payment, New Purchase Bill, New Supplier Payment), each navigating to that module's Create route.

### Help Center
- **Trigger:** Reserved topbar/user-menu entry point (not detailed in prior documents; included here for completeness since it is a standard expectation of an enterprise SaaS product at this design tier).
- **Purpose:** Entry point to documentation/support — out of scope for detailed specification in this catalog beyond reserving its place; treated as a **Future Enhancement** for the frontend MVP rather than a required launch surface, consistent with `01_PRODUCT_VISION.md`'s "replace paper workflows first" prioritization.

---

## 16. Responsive Design Summary

Every page in this catalog inherits the responsive rules defined once in `04_USER_FLOWS.md` §24 and `02_DESIGN_SYSTEM.md` §15, restated here as the governing defaults rather than repeated per page:

- **List pages** — table gains horizontal scroll with a sticky identifying column; filter bar collapses into a drawer trigger; Primary CTA stays visible.
- **Detail pages** — Overview Card fields stack single-column; tabs become a horizontally-scrollable strip; Related Record tables follow the List page rule above.
- **Form pages** — multi-column field groups collapse to single column; line-item tables (Invoice/Purchase Bill/Trip Catch/Trip Expense) retain their inline-row entry pattern, scrolling horizontally rather than restructuring.
- **Dashboard** — KPI row wraps 2-then-1 columns; charts and feed sections stack full-width in the fixed priority order defined in §2.
- **Global components** (Command Palette, Notification Center, User Menu, Quick Actions) — render as full-width overlays/drawers on mobile rather than anchored popovers, consistent with the Drawer-based mobile navigation model in `03_INFORMATION_ARCHITECTURE.md` §14.

No page in this catalog defines a bespoke mobile layout outside these shared rules — consistency across the catalog is what keeps ~70 pages implementable without a per-page mobile design pass.

---

## 17. Catalog Summary

This catalog enumerates every page implied by `01_PRODUCT_VISION.md` through `04_USER_FLOWS.md`: 5 authentication pages, 1 dashboard, 4 pages each for 8 core transactional/master modules (Companies, Suppliers, Fish, Boats, Trips, Invoices, Customer Payments, Purchase Bills, Supplier Payments — Trips and the two payment modules carrying additional tab/dialog specifications), 7 reports, 6 administration pages, 8 settings pages, and 6 global components — roughly 70 distinct, individually addressable surfaces in total.

Every page was specified against one of three fixed templates (§0), so implementing any new page follows a pattern already proven by an existing one: a List page looks like Companies List, a Detail page looks like Company Details, a Form page looks like Create Company — regardless of module. This is what makes the catalog complete without being exhaustive prose: the templates carry the repetitive 90%, and each page's entry carries only the 10% that's actually unique to it. A frontend engineer building any page in this list has, by the time they've built two or three, already seen every layout pattern the rest of the application will ever ask of them.
