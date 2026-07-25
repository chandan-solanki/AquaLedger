# AquaLedger — Information Architecture

**The Complete Navigation & Structural Blueprint for AquaLedger**

Version 1.0 · Information Architecture Specification

This document defines every page, route, menu, and navigational relationship in AquaLedger. It builds directly on `01_PRODUCT_VISION.md` (business modules, personas, workflows) and `02_DESIGN_SYSTEM.md` (component and navigation-element standards) and contradicts neither — it is the structural layer between them and the eventual UI build.

---

## 1. Navigation Philosophy

AquaLedger's navigation is organized around **how a seafood business actually moves through its work**, not around database tables or engineering module boundaries. A trader doesn't think "I need the Invoice entity" — they think "I need to bill ABC Fisheries for last week's catch." Navigation is built to match that sequence of thought.

Three forces shape the structure:

1. **The business's own operating sequence.** Value is created before it is sold: a boat goes out, catches fish, and only later does that catch become an invoice line. Navigation groups reflect this order — Operations sits before Finance, not because of alphabetical convention, but because that's the order the business itself follows.
2. **Reference data vs. transactional flow.** Companies, Suppliers, and Fish are stable, low-frequency-change data that everything else points to. They are grouped separately (**Masters**) from the high-frequency transactional work (**Operations**, **Finance**) so the two very different rhythms of use — "set up once, rarely revisit" vs. "touch dozens of times a day" — don't compete for the same visual space.
3. **Role-shaped frequency.** An Accountant lives in Finance; a Boat Manager lives in Operations; an Owner lives in the Dashboard and Reports. The top-level grouping is designed so each persona's daily work sits under one or two sidebar sections, not scattered across the whole menu.

Modules are grouped by **business function**, never by technical implementation. Trip Catch and Trip Expenses, for instance, are not separate sidebar destinations — they are contextual children of a Trip, because no one ever thinks about a catch in isolation from the trip that produced it. This same principle — surface an entity where the user's mental model expects it, not where its database table happens to live — governs every grouping decision in this document.

---

## 2. Global Application Structure

The application's top-level structure is fixed and identical for every tenant:

```
Dashboard
Masters
  ├─ Companies
  ├─ Suppliers
  └─ Fish
Operations
  ├─ Boats
  └─ Trips
Finance
  ├─ Invoices
  ├─ Customer Payments
  ├─ Purchase Bills
  └─ Supplier Payments
Reports
Administration
  ├─ Users
  ├─ Roles & Permissions
  └─ Audit Logs
Settings
  ├─ Company Profile
  ├─ Numbering Sequences
  └─ Categories
```

- **Dashboard** — the single entry point after login; answers "how is the business doing right now" and routes to everything else via shortcuts.
- **Masters** — stable reference data referenced by every transactional record. Set up early, edited rarely.
- **Operations** — the physical/operational reality of the business, tracked before any money changes hands.
- **Finance** — where operational reality becomes financial fact: the Order-to-Cash and Procure-to-Pay lifecycles.
- **Reports** — where transactional data becomes decisions (near-term roadmap per Product Vision §11; present in the IA now so its place is reserved).
- **Administration** — who can do what, and the system's accountability trail. Restricted to Administrator/Owner roles.
- **Settings** — how this tenant is configured. Restricted to Administrator role.

This ordering is permanent. New modules are inserted *into* one of these seven groups (see §15), never appended as a new top-level group, so the top-level shape of the sidebar stays stable as the product grows.

---

## 3. Sidebar Architecture

The sidebar is the single persistent primary-navigation surface, always visible on desktop (collapsible to an icon-only rail per `02_DESIGN_SYSTEM.md` §12).

### Dashboard
- **Purpose:** Landing page and cross-module overview.
- **Children:** None (single page).
- **Icon:** Home/layout-dashboard glyph.
- **Permissions:** Visible to all authenticated roles; content scoped by role (see §13).
- **Expanded/Collapsed:** Always a single top-level item, never expands.
- **Future Expansion:** None — the Dashboard stays a single page; new widgets are added to it, not new pages under it.

### Masters
- **Purpose:** Group entry point for stable reference data.
- **Children:** Companies, Suppliers, Fish.
- **Icon:** Database/layers glyph on the group header.
- **Permissions:** Group visible to any role with read access to at least one child; individual children hidden per-permission (e.g., a Boat Manager may not see Suppliers).
- **Expanded/Collapsed:** Expanded by default for roles with Masters access; collapses to just its icon in the rail view, expanding as a flyout on hover/click.
- **Future Expansion:** Reserves room for a future **Expense Categories** or **Item Groups** master if the product grows beyond Fish as the only item type.

  **Companies**
  - *Purpose:* Customer (and customer/supplier-combined) master — the counterparty record for sales.
  - *Icon:* Building glyph.
  - *Permissions:* Read for most transactional roles (needed to select a customer on an invoice); write restricted to Accountant/Administrator.

  **Suppliers**
  - *Purpose:* Vendor master used by the purchasing lifecycle.
  - *Icon:* Truck/handshake glyph.
  - *Permissions:* Read for Accountant and purchasing-involved roles; write restricted to Accountant/Administrator.

  **Fish**
  - *Purpose:* Item master for every species/grade traded.
  - *Icon:* Fish glyph — the one deliberate literal icon in the system, reserved for this single, unambiguous case.
  - *Permissions:* Read broadly (needed across Trip Catch and Invoice entry); write restricted to Accountant/Administrator.

### Operations
- **Purpose:** Group entry point for the physical fishing/operational lifecycle.
- **Children:** Boats, Trips.
- **Icon:** Anchor/waves glyph on the group header.
- **Permissions:** Primary section for Boat Manager/Operator/Field Staff roles; visible read-only to Owner/Manager for oversight.
- **Expanded/Collapsed:** Expanded by default for Operations-primary roles.
- **Future Expansion:** Reserves room for **Crew Management** as a dedicated child if crew records outgrow being a sub-section of Boats.

  **Boats**
  - *Purpose:* Vessel registry and compliance status.
  - *Icon:* Ship glyph.
  - *Permissions:* Full access for Boat Manager/Administrator; read-only for Owner/Manager.

  **Trips**
  - *Purpose:* Voyage records and their nested Catch/Expense/Profit detail.
  - *Icon:* Route/map-pin glyph.
  - *Permissions:* Full access for Boat Manager/Operator; scoped create/edit for Field Staff (catch and expense entry only, via the Trip detail page); read-only for Owner/Manager/Accountant.

### Finance
- **Purpose:** Group entry point for the Order-to-Cash and Procure-to-Pay lifecycles.
- **Children:** Invoices, Customer Payments, Purchase Bills, Supplier Payments.
- **Icon:** Wallet/receipt glyph on the group header.
- **Permissions:** Primary section for Accountant; read-only for Owner/Manager; hidden entirely for Operator/Field Staff.
- **Expanded/Collapsed:** Expanded by default for Accountant; collapsed by default (but present) for read-only roles.
- **Future Expansion:** Reserves room for a future **Credit Notes / Reversals** child once financial-correction workflows are built (per Product Vision's "Financial corrections must use Credit Notes / Reversal Entries" rule).

  **Invoices** — *Purpose:* Sales documents, draft-through-paid. *Icon:* File-text glyph. *Permissions:* Full for Accountant; read-only for Owner/Manager.

  **Customer Payments** — *Purpose:* Receipts and their allocation against invoices. *Icon:* Arrow-down-to-line / inbound-payment glyph. *Permissions:* Full for Accountant; read-only for Owner/Manager.

  **Purchase Bills** — *Purpose:* Vendor bills, draft-through-posted. *Icon:* File-text glyph (mirrors Invoices intentionally — same concept, opposite direction). *Permissions:* Full for Accountant; read-only for Owner/Manager.

  **Supplier Payments** — *Purpose:* Payments out and their allocation against bills. *Icon:* Arrow-up-from-line / outbound-payment glyph (mirrors Customer Payments). *Permissions:* Full for Accountant; read-only for Owner/Manager.

### Reports
- **Purpose:** Cross-module analytical views.
- **Children:** (roadmap — see §15) Receivables Aging, Payables Aging, Trip/Boat Profitability, Sales Summary, Purchase Summary.
- **Icon:** Bar-chart glyph.
- **Permissions:** Owner/Manager/Accountant; hidden for Operator/Field Staff.
- **Expanded/Collapsed:** Present in the sidebar from the frontend MVP as a single item (linking to a "Coming Soon" state per `02_DESIGN_SYSTEM.md` empty-state standard) until its children ship; expands once reports exist.
- **Future Expansion:** Primary growth point for Product Vision §11's medium-term roadmap.

### Administration
- **Purpose:** Group entry point for who-can-do-what and accountability.
- **Children:** Users, Roles & Permissions, Audit Logs.
- **Icon:** Shield glyph.
- **Permissions:** Administrator only; entirely hidden for every other role.
- **Expanded/Collapsed:** Collapsed by default even for Administrators (a low-frequency section).
- **Future Expansion:** Reserves room for a future **Tenant Billing / Subscription** child if AquaLedger exposes self-service billing.

  **Users** — *Purpose:* Team member accounts and role assignment. *Icon:* Users glyph.

  **Roles & Permissions** — *Purpose:* Define/edit role-to-permission mappings. *Icon:* Key glyph.

  **Audit Logs** — *Purpose:* Read-only, tamper-evident activity trail. *Icon:* History/clock-rotate glyph.

### Settings
- **Purpose:** Group entry point for tenant-level configuration.
- **Children:** Company Profile, Numbering Sequences, Categories.
- **Icon:** Gear glyph.
- **Permissions:** Administrator only.
- **Expanded/Collapsed:** Collapsed by default.
- **Future Expansion:** Reserves room for future **Notification Preferences** and **Integrations** children.

---

## 4. Route Structure

All routes are namespaced under the authenticated application shell; the pattern is uniform across every module: **list → new → detail → edit**, with nested resources living under their parent's detail route.

```
/                                   → redirects to /dashboard
/login
/dashboard

# Masters
/companies
/companies/new
/companies/{id}
/companies/{id}/edit

/suppliers
/suppliers/new
/suppliers/{id}
/suppliers/{id}/edit

/fish
/fish/new
/fish/{id}
/fish/{id}/edit

# Operations
/boats
/boats/new
/boats/{id}
/boats/{id}/edit

/trips
/trips/new
/trips/{id}                         → Overview tab (default)
/trips/{id}/edit
/trips/{id}/catches                 → Catches tab
/trips/{id}/catches/new
/trips/{id}/catches/{catchId}/edit
/trips/{id}/expenses                → Expenses tab
/trips/{id}/expenses/new
/trips/{id}/expenses/{expenseId}/edit
/trips/{id}/profit                  → Profit Analysis tab

# Finance — Sales
/invoices
/invoices/new
/invoices/{id}
/invoices/{id}/edit                 → only reachable while status = draft
/payments
/payments/new
/payments/{id}

# Finance — Purchasing
/purchase-bills
/purchase-bills/new
/purchase-bills/{id}
/purchase-bills/{id}/edit           → only reachable while status = draft
/supplier-payments
/supplier-payments/new
/supplier-payments/{id}

# Reports
/reports
/reports/receivables-aging
/reports/payables-aging
/reports/trip-profitability
/reports/sales-summary
/reports/purchase-summary

# Administration
/users
/users/new
/users/{id}
/users/{id}/edit
/roles
/roles/new
/roles/{id}
/roles/{id}/edit
/audit-logs
/audit-logs/{id}

# Settings
/settings/company
/settings/sequences
/settings/categories

# Account
/profile
/profile/security
```

### Route Naming Rules

- Every list route is a **plural noun** (`/companies`, `/trips`, `/purchase-bills`).
- `new` is always the literal segment for creation, never `create` or `add`.
- `{id}` is always the entity's identifier segment for its detail page; `edit` is always appended as a final segment, never a query parameter, so edit state is bookmarkable and shareable.
- Nested resources (`trips/{id}/catches`) are only used when the child is meaningless outside its parent's context — this applies to Trip Catch and Trip Expenses, and to nothing else in the current module set.
- `Customer Payments` and `Supplier Payments` intentionally use **different** route nouns (`/payments` vs. `/supplier-payments`) rather than a shared `/payments?direction=in|out` pattern, because they are distinct entities with distinct forms, lists, and permissions — the URL should say so plainly.

---

## 5. Page Hierarchy

Every transactional module follows the same four-page shape, with the same purpose in every module:

- **List Page** — filterable, sortable, paginated table (per `02_DESIGN_SYSTEM.md` §9); the default landing page for the module; entry point for Create.
- **Create Page** — a focused form (or, for Invoices/Purchase Bills, the full line-item editor) for a new record; on save, redirects to the new record's Detail page.
- **Details Page** — the canonical view of a single record: header with status badge and lifecycle actions, sectioned/tabbed body, and related-record tables where applicable.
- **Edit Page** — reachable only while a record is in an editable state (draft, or master data generally); locked/finalized records (issued invoices, posted bills) have no reachable Edit route — their detail page instead shows lifecycle actions (Cancel, Reverse) in place of Edit.

**Related Pages** present on Details pages, per module:

- **Timeline / Activity** — a chronological view of status changes and key events for the record (status transitions, who issued/posted it, when payments were allocated to it). Present on every Finance-lifecycle entity (Invoices, Purchase Bills, Payments) and on Trips.
- **Attachments** *(future)* — reserved tab/section on Invoice, Purchase Bill, and Trip detail pages for the Document Management module (Product Vision §11 near-term roadmap) — catch slips, signed bills, compliance documents.
- **Notes** *(future)* — reserved section on Companies, Suppliers, and Trip detail pages for free-text internal notes, once that capability is built.

Master-data modules (Companies, Suppliers, Fish, Boats) additionally show a **related-records** section on their Detail page (e.g., a Company's detail page lists its recent Invoices and current outstanding balance) — this is how cross-module relationships (§6) surface without requiring separate navigation.

---

## 6. Navigation Between Modules

Navigation follows the same three lifecycles defined in `01_PRODUCT_VISION.md` §6, made concrete as clickable paths:

### Fishing Workflow
```
Boats → Trip detail → Catches tab → Expenses tab → Profit tab
                              ↓
                    (catch referenced when building an Invoice line item)
```
A Trip Catch row that has been sold links directly to the Invoice it was sold on; an Invoice line item built from catch stock links back to the source Trip Catch. This is the one explicit cross-group link between Operations and Finance, and it is always rendered as a clickable reference in both directions.

### Customer Lifecycle (Order-to-Cash)
```
Company detail → [New Invoice] → Invoice detail → Issue
                                        ↓
                        Customer Payment detail (allocation)
                                        ↓
                        Invoice detail (balance recomputed, status updated)
```
A Company's detail page links out to its Invoices and its current outstanding balance. An Invoice's detail page links to every Payment allocated against it. A Payment's detail page links to every Invoice it was allocated to. This three-way cross-linking means a user can always answer "what does this company owe" or "what does this payment cover" in one click, regardless of which record they started from.

### Supplier Lifecycle (Procure-to-Pay)
```
Supplier detail → [New Purchase Bill] → Purchase Bill detail → Post
                                              ↓
                            Supplier Payment detail (allocation)
                                              ↓
                            Purchase Bill detail (balance recomputed, status updated)
```
Identical shape and cross-linking to the Customer Lifecycle above — deliberately, so a user who has learned one already understands the other.

### Administration
```
Users list → User detail → Role assignment → Roles & Permissions detail
                                                        ↓
                                            (permission changes reflected
                                             immediately in that user's
                                             visible navigation)
```
Audit Logs are reachable both from the Administration section directly and contextually — every Detail page's Timeline/Activity section links to the corresponding full Audit Log entries for that record.

---

## 7. Breadcrumb Strategy

Breadcrumbs appear on every Detail, Edit, and Create page (never on List pages or the Dashboard, which are themselves the top of their own path). Rules:

1. The trailing segment is always the current page; it is not a link.
2. The segment immediately before it is always the module's List page.
3. Entity names, not IDs, are shown as breadcrumb labels wherever a human-readable name exists (a company's name, an invoice's number) — raw UUIDs are never shown in a breadcrumb.
4. Nested resources include their parent in the chain.

**Examples:**

```
Dashboard
Dashboard  >  Companies
Dashboard  >  Companies  >  ABC Fisheries
Dashboard  >  Companies  >  ABC Fisheries  >  Edit
Dashboard  >  Purchase Bills  >  PUR-2026-00045
Dashboard  >  Trips  >  TRP-2026-0142  >  Catches
Dashboard  >  Invoices  >  New Invoice
Dashboard  >  Administration  >  Roles  >  Accountant
```

The Dashboard is always the root of every breadcrumb chain, even though it isn't a parent of any module in the sidebar — this reflects that it is the actual entry point of every user's session, not the entity hierarchy.

---

## 8. Dashboard Navigation

The Dashboard is a single page composed of role-scoped sections (content varies per §13, structure does not):

- **KPIs** — a row of Metric/KPI Cards (per `02_DESIGN_SYSTEM.md` §8): total receivables outstanding, total payables outstanding, trips currently at sea, boats with expiring compliance documents. Each KPI card is clickable, deep-linking to the relevant filtered list (e.g., the receivables KPI links to `/companies?filter=has-outstanding-balance` or a future Receivables Aging report).
- **Charts** — revenue trend and receivables aging visualizations (Recharts, per `02_DESIGN_SYSTEM.md` §11), each linking through to the full Report page once Reports ships.
- **Recent Activity** — a short, reverse-chronological feed of recent invoices, payments, and trip status changes, each row linking directly to that record's Detail page.
- **Pending Work** — items awaiting the current user's action, scoped by role: draft invoices awaiting issue, unallocated payments, trips awaiting settlement. This section is what makes the Dashboard a genuine work surface, not just a status readout.
- **Outstanding** — a compact summary of top overdue customers / top due suppliers, linking to Companies/Suppliers filtered views.
- **Quick Actions** — the same Quick Actions surface described in §10, duplicated here for immediate access on landing.

No section on the Dashboard is a dead end — every KPI, chart, and list row is a navigational shortcut into the module that owns that data. The Dashboard's job is to be the fastest path to whatever the user needs next, not a static report.

---

## 9. Global Search

A single search surface, reachable from the topbar (persistent search input, styled as a command-palette trigger) and via keyboard shortcut, searching across entities system-wide.

**Searchable Entities:** Companies, Suppliers, Invoices (by number or company name), Purchase Bills (by number or supplier name), Trips (by trip number or boat name), Fish, Boats, Customer Payments, Supplier Payments, Users.

**Search Behavior:**
- Results are grouped by entity type (a "Companies" group, an "Invoices" group, etc.), never a single flat undifferentiated list.
- Each result shows enough context to disambiguate without opening it — an entity name plus its most relevant secondary attribute (a company's outstanding balance, an invoice's status and amount, a trip's boat and date).
- Selecting a result navigates directly to that record's Detail page.
- Results respect the searching user's role permissions — an entity type the user cannot access does not appear as a search group at all.
- Search is scoped to the current tenant only; cross-tenant results are architecturally impossible, not merely filtered.

**Recent Searches:** The search surface, when opened empty, shows a short list of the user's own recent searches/visited records, so returning to something looked at minutes ago never requires retyping.

**Keyboard Shortcut:** `⌘K` / `Ctrl+K` opens the same surface described fully in §12 — Global Search and the Command Palette are the same entry point, not two separate UI elements, differentiated only by what the user types (a search term vs. an action name).

---

## 10. Quick Actions

A Quick Actions menu surfaces the highest-frequency creation tasks from anywhere in the product, so common work never requires a full navigation hop to a module's List page first.

**Contents:** New Company, New Supplier, New Trip, New Invoice, New Customer Payment, New Purchase Bill, New Supplier Payment — the exact set of "new record" actions a busy Accountant or Owner needs multiple times a day, scoped by the current user's create permissions (an Operator sees New Trip but not New Invoice).

**Where It Appears:**
- A persistent "+ Quick Create" trigger in the topbar, available on every page.
- Duplicated as a dedicated section on the Dashboard (§8) for first-touch convenience after login.
- Reachable within the Command Palette (§12) by typing an action name (e.g., "new invoice").
- Each module's own List page additionally has its own single, primary "+ New [Entity]" button in the page header (per `02_DESIGN_SYSTEM.md` Page Header standard) — the global Quick Actions menu supplements this, it does not replace it.

Selecting any Quick Action navigates directly to that module's Create route (e.g., `/invoices/new`), never to an inline modal for full-form entities — Invoices and Purchase Bills in particular need the full editor's screen space.

---

## 11. Notifications

The notification bell (topbar, per `02_DESIGN_SYSTEM.md` §12) surfaces categorized, actionable events. Each category links directly to the relevant record or filtered list.

- **Invoices** — newly overdue, approaching due date.
- **Payments** — payment received and auto/partially allocated, unallocated payment awaiting action.
- **Purchase Bills** — newly due, approaching due date.
- **Trips** — trip returned and awaiting settlement, boat license/insurance expiring soon.
- **System** — maintenance notices, sequence/numbering issues requiring attention.
- **Users** — a new user invited, a role changed (visible to Administrators).
- **Approvals** — items awaiting the current user's sign-off (reserved for the approval-workflow roadmap item in `01_PRODUCT_VISION.md` §10).
- **Future AI Notifications** — reserved category for AI Assistant-surfaced insights (e.g., "Customer X's payment pattern suggests rising risk") once that capability ships (Product Vision §11 long-term roadmap) — present in the category model now so it requires no restructuring later.

Notifications are per-user and per-tenant, respect the same role-based visibility as the rest of the product (an Operator never receives an Invoice-overdue notification), and are marked read individually or in bulk from the notification panel.

---

## 12. Command Palette

`⌘K` (macOS) / `Ctrl+K` (Windows/Linux) opens a single global palette — the fastest path through the entire application, and the natural home for keyboard-first users.

The palette supports four intent types, disambiguated by lightweight typed prefixes/patterns but discoverable by typing naturally:

- **Search** — typing an entity name/number searches exactly as described in §9, grouped by entity type.
- **Navigate** — typing a section or page name (e.g., "settings," "reports," "audit logs") jumps directly to that page, covering every sidebar destination without requiring the mouse.
- **Run Actions** — typing an action verb (e.g., "new invoice," "new trip") surfaces the matching Quick Action (§10) and, on selection, navigates to the corresponding Create route.
- **Open Pages** — recently visited and frequently visited pages surface as suggestions when the palette is opened empty, mirroring Recent Searches (§9).
- **Create Entities** — a shortcut path identical to Run Actions, listed here because it is the palette's single most common use case for Accountant and Operator roles during high-volume work.
- **Theme Switching** — typing "dark mode," "light mode," or "theme" toggles the application theme without leaving the keyboard, consistent with `02_DESIGN_SYSTEM.md` §17 treating theme as a first-class, always-accessible setting.

The palette is styled per the Dialog/overlay elevation standard in `02_DESIGN_SYSTEM.md` §6, is available identically from every page in the product, and always closes on selection or `Esc`, returning focus to wherever it was opened.

---

## 13. Role Based Navigation

Menu visibility and action availability are driven directly by the permission-code RBAC model described in `01_PRODUCT_VISION.md` §10 — the sidebar is not a static menu with permission checks bolted on; it is *generated from* the current user's actual permission set.

| Role | Primary Sections | Hidden | Read-Only |
|---|---|---|---|
| **Owner** | Dashboard, Reports, all sections for oversight | Nothing (broad visibility by design) | Most transactional detail pages (views without lifecycle-action buttons) |
| **Administrator** | Administration, Settings, Users/Roles | — | May or may not have transactional access depending on tenant configuration |
| **Accountant** | Finance (full), Masters (full) | Administration, Settings | Operations (read-only, for context on trips feeding invoices) |
| **Manager** | Dashboard, broad read access | Administration, Settings | Finance and Operations lifecycle actions (visibility without action buttons) |
| **Boat Manager / Operator** | Operations (full: Boats, Trips, Catch, Expenses) | Finance, Administration, Settings | Masters (read-only, needed to reference Fish/Companies contextually) |
| **Field Staff** | Trip Catch entry, Trip Expense entry only (via Trip detail) | Finance, Administration, Settings, Boats/Trips list-level management | Everything outside their scoped entry tasks |

**Hidden Menus** — a sidebar item for a section/module the role cannot read at all is not rendered, not shown-and-disabled. A Field Staff user's sidebar is visibly and deliberately shorter than an Accountant's.

**Read Only Menus** — where a role can view but not modify (e.g., Manager viewing Invoices), the page renders with no Edit/Issue/Post/Delete affordances present — the absence of the button *is* the permission boundary, communicated visually rather than via a failed action.

**Restricted Actions** — lifecycle actions (Issue, Post, Delete, Allocate, Approve) are individually permission-gated even within a section a role can otherwise access — e.g., a Manager might see the Invoices list and open any Invoice detail page, but never see an "Issue" button there.

---

## 14. Mobile Navigation

Mobile is a **secondary, review-and-light-entry context** (per `02_DESIGN_SYSTEM.md` §15), not a full parity target — its navigation is simplified accordingly.

- **Sidebar** — replaced entirely by an off-canvas **Drawer**, triggered by a hamburger control in the mobile topbar; contains the same section/child structure as desktop, just presented as a full-height slide-out rather than a persistent rail.
- **Bottom Navigation** — not used. A bottom tab bar would imply a small, fixed set of top-level destinations equally weighted, which misrepresents this product's actual usage pattern (most mobile sessions are Trips/Catch/Expense entry for Field Staff, or Dashboard/quick lookups for Owner/Manager) — the Drawer's full hierarchy serves both better than a compressed tab bar would.
- **Responsive Behavior** — the topbar persists (search trigger, notifications, user menu, hamburger); breadcrumbs collapse to just a "back to parent" affordance rather than the full chain, since horizontal space for a multi-segment breadcrumb is scarce; Quick Actions remain reachable via the topbar's Quick Create trigger.
- **Command Palette** — remains available on mobile (triggered by a visible search icon rather than a keyboard shortcut, since `⌘K` has no mobile equivalent), preserving Global Search access even without a keyboard.

---

## 15. Future Expansion

The structure defined in §§2–4 explicitly reserves space for modules not yet built, so their eventual addition requires no restructuring of what already exists:

| Future Module | Reserved Location |
|---|---|
| **Inventory / Warehouse** | New child under **Masters** or a new **Inventory** group inserted between Masters and Operations, once stock tracking extends beyond Trip Catch's available/sold/waste model |
| **Accounting / Ledger / Journal** | New children under **Finance**, surfacing the existing append-only ledger entries as a first-class Ledger/Journal view |
| **GST** | A dedicated compliance view under **Reports** or **Finance**, built on the per-line tax data already captured on Invoices/Purchase Bills |
| **Payroll** | A new top-level group (crew/staff compensation is distinct enough from the current seven groups to warrant one), inserted after Operations |
| **Documents** | New children on relevant Detail pages (Attachments, §5) plus a dedicated **Documents** module under a new group or under Administration |
| **OCR** | Not a navigation destination itself — surfaces as an input *method* on existing Create pages (e.g., "Scan Bill" alongside manual entry on Purchase Bill creation) |
| **AI Assistant** | A persistent, globally-accessible entry point (likely topbar-anchored, alongside Global Search) rather than a sidebar destination, consistent with how Command Palette-style tools are surfaced today |
| **Analytics** | Expands the **Reports** section's children; does not require a new top-level group |
| **CRM** | New children under **Masters** (Companies) or a new group, if relationship/pipeline tracking extends beyond the current Company record |
| **Mobile App** | Does not add web routes; consumes the same route/permission model described here via a native shell |

The seven-group top-level structure (§2) is designed to absorb all of the above as new *children*, with at most one or two new top-level groups (Payroll, possibly Inventory) added over the product's lifetime — the architecture is deliberately not exhausted by the current module set.

---

## 16. Information Hierarchy Principles

- **Primary Navigation** — the sidebar's seven groups and their children (§2, §3). Always visible (or one collapse-toggle away), represents the full set of destinations a user can reach.
- **Secondary Navigation** — in-page navigation within a single entity's Detail page: tabs (Overview/Catches/Expenses/Profit on a Trip), section anchors. Scoped to one record, never used to reach a different record.
- **Contextual Navigation** — links that appear only because of a specific relationship (a Company detail page linking to *its* Invoices; an Invoice linking to the Payment(s) allocated to it). Not present in the sidebar; discovered by drilling into a record, per the cross-linking described in §6.
- **Temporary Navigation** — breadcrumbs (§7), the Command Palette (§12), and Recent Searches/Activity (§9) — all describe "how did I get here" or "where was I recently," and none persist as a permanent structural element the way Primary and Secondary navigation do.

Each type answers a different question: Primary answers "what can I do in this product," Secondary answers "what can I see about this one record," Contextual answers "what else relates to this record," and Temporary answers "where have I been." Conflating these (e.g., putting a contextual link in the sidebar) is the specific failure mode this hierarchy is designed to prevent.

---

## 17. URL Standards

- **Plural nouns** for every collection/list route: `/companies`, `/invoices`, `/purchase-bills` — never singular (`/company`), never a verb (`/list-companies`).
- **REST-style** resource nesting: `/trips/{id}/catches`, never a flat unnested alternative like `/trip-catches?tripId={id}`.
- **Readable, hyphenated multi-word segments**: `/purchase-bills`, `/supplier-payments`, `/roles`, — never camelCase or underscores in the URL itself.
- **Consistent action segments**: `new` and `edit` are the only two action segments used anywhere in the route tree; no module invents its own variant (`/companies/create` is incorrect; `/companies/new` is correct).
- **IDs, not slugs**, for the detail-page identifier segment (`/companies/{id}`), since AquaLedger's entities (companies, invoices) can share names or be renamed, and stable linking matters for a financial system — human-readable identification happens via the breadcrumb label and page title, not the URL.

**Examples:**
```
/companies                      → Companies list
/companies/new                  → New Company form
/companies/8f21.../edit         → Edit Company
/purchase-bills                 → Purchase Bills list
/purchase-bills/8f21...          → Purchase Bill detail
/trips/8f21.../catches/new       → New Trip Catch entry, nested under its Trip
/reports/receivables-aging       → Receivables Aging report
```

---

## 18. Naming Conventions

A single vocabulary is used consistently across menus, page titles, buttons, and entity references — anywhere the product names something.

- **Menu Names** — always the plural entity name exactly as it appears in the sidebar (`Companies`, `Purchase Bills`), matching the List page's title precisely so a user never wonders if a menu item and a page are "the same place."
- **Page Titles** — List pages use the plural module name (`Purchase Bills`); Detail pages use the record's own identifying name/number (`ABC Fisheries`, `PUR-2026-00045`); Create pages use `New [Singular Entity]` (`New Purchase Bill`); Edit pages use `Edit [Entity Name]` (`Edit ABC Fisheries`).
- **Buttons** — primary creation buttons always read `+ New [Singular Entity]` (`+ New Invoice`), never `Add`, `Create New`, or other variants; lifecycle action buttons use the exact verb that names the state transition (`Issue`, `Post`, `Allocate`, `Cancel`) — never a vaguer synonym (`Submit`, `Confirm`) that obscures which specific transition is about to happen.
- **Entity Names** — the canonical singular/plural pair for every entity is fixed and used identically in every surface (sidebar, breadcrumbs, page titles, search result groups, notifications): Company/Companies, Supplier/Suppliers, Fish (invariant plural), Boat/Boats, Trip/Trips, Trip Catch/Trip Catches, Trip Expense/Trip Expenses, Invoice/Invoices, Customer Payment/Customer Payments, Purchase Bill/Purchase Bills, Supplier Payment/Supplier Payments, User/Users, Role/Roles.

No synonyms are introduced anywhere — "Bill" is never used interchangeably with "Purchase Bill," "Client" never substitutes for "Company," "Vendor" never substitutes for "Supplier" — one name, one meaning, everywhere, mirroring the naming discipline established for components in `02_DESIGN_SYSTEM.md` §18.

---

## 19. Navigation Best Practices

- **Keyboard Shortcuts** — `⌘K`/`Ctrl+K` for the Command Palette (§12) is the one global shortcut every user is expected to learn; module-specific shortcuts (e.g., `n` for "new" while on a list page) are a future enhancement layered on top of, never a replacement for, full mouse/touch operability.
- **Back Button** — every route is a real, addressable URL (§17), so the browser back button always behaves correctly and predictably — no client-side navigation that breaks history, no route that silently swallows back-navigation.
- **Open in New Tab** — every navigational element that leads to a Detail page (table rows, search results, breadcrumbs, cross-links) is a real link, supporting standard middle-click/Ctrl-click "open in new tab" behavior — never a click-handler-only row that defeats this.
- **State Persistence** — a List page's active filters, sort order, and pagination position are preserved when a user navigates into a Detail page and back (e.g., via browser back or the breadcrumb), so returning to a filtered Invoices list doesn't silently reset to the unfiltered default.
- **Remember Filters** — the same persistence applies within a session even across a full navigation away and back (e.g., leaving Invoices to check a Company and returning) — filters live in the URL's query parameters wherever practical, making filtered views bookmarkable and shareable as a byproduct.
- **Remember Sidebar** — the sidebar's expanded/collapsed state (full vs. icon rail, per `02_DESIGN_SYSTEM.md` §12) is a persisted user preference, not reset on every session.

---

## 20. Architecture Summary

This Information Architecture gives AquaLedger a navigation structure that is **scalable** because every future module (§15) has an explicit, pre-designated home rather than requiring the top-level structure to be renegotiated each time the product grows. It is **maintainable** because every module follows one page-hierarchy pattern (§5) and one URL pattern (§17) — a developer who has built the Companies module already knows the shape of the Suppliers module before writing a line of it. It is **future-proof** because the seven-group top-level structure (§2) was derived from the business's own operating logic, not from today's feature list, so it will not need to be reinvented as AquaLedger adds Reports, Documents, OCR, and AI over its roadmap.

Above all, it is **consistent**: one navigation model (sidebar + breadcrumb + command palette), one relationship model (Masters feed Operations and Finance; Operations feeds Finance; everything is reachable from the Dashboard), and one naming vocabulary (§18) — applied without exception across every module, current and future. A frontend architect building from this document can implement any module by pattern-matching against any other, and a user who has learned one corner of AquaLedger has, by construction, already learned most of the rest of it.
