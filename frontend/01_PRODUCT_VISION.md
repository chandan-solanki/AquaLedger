# AquaLedger — Product Vision

**Modern Cloud ERP for Fisheries & Seafood Businesses**

Version 1.0 · Product Strategy Document · Foundation for Frontend Implementation

---

## 1. Product Vision

### Why AquaLedger Exists

The seafood trade runs on paper. A boat returns to harbor and its catch is logged in a notebook. A trader sells to a wholesaler on credit and tracks the balance in a diary. A supplier is paid partly in cash, partly against three different bills, and nobody is quite sure which bill is now clear. Multiply this across dozens of boats, hundreds of customers, and thousands of transactions a season, and the business is running on memory, trust, and stacks of paper that don't reconcile.

This isn't a bookkeeping problem — it's an operations-visibility problem. A fish trader doesn't just need "an accounting system." They need to know, in real time: which boat trips turned a profit, which customers are over their credit limit, which invoices are overdue, and what they owe their suppliers — all while every number is trustworthy enough to defend in a GST audit.

AquaLedger exists to replace that paper trail with a single digital source of truth, built around how a seafood business actually operates — from boat to invoice to payment — not around a generic chart of accounts.

### How AquaLedger Differs From a Generic ERP

Generic ERP systems (and their adapted "lite" variants sold into small trading businesses) model *goods* and *invoices*. They have no concept of a boat, a trip, a catch, or a grade of fish landed today and sold across three different invoices this week. Forcing a seafood business into a generic ERP means either leaving the operational reality (boats, trips, catch) outside the system entirely — back on paper — or bending inventory/manufacturing modules into an awkward, unnatural fit.

AquaLedger is built the other way around: the domain model *starts* from Boats → Trips → Catch, flows naturally into Invoices and Payments, and mirrors the same discipline on the purchasing side (Suppliers → Purchase Bills → Supplier Payments). Nothing is bolted on.

### How AquaLedger Differs From Accounting Software

Accounting software (Tally, QuickBooks, Zoho Books) is excellent at recording what already happened financially. It has no opinion on how a trip was staffed, what a boat's expenses were, or whether today's catch is still available to sell. AquaLedger is not a general ledger with a seafood skin — it is an **operations platform with a rigorous financial core**. The books are a byproduct of correctly modeling the operations, not the starting point.

### What Makes It Modern

- **Cloud-native, multi-tenant SaaS** — no per-branch installs, no manual backups.
- **API-first, modular monolith backend** — fast today, cleanly extractable tomorrow, without the operational cost of microservices before the business needs them.
- **Financially rigorous by construction** — exact decimal arithmetic, immutable issued invoices, append-only ledgers, and reconciled-not-assumed outstanding balances, so the numbers are audit-safe by default rather than by discipline.
- **Designed like modern SaaS, not legacy enterprise software** — the bar for look, feel, and speed is Linear and Stripe, not a decade-old on-premise ERP.

### Future Vision

AquaLedger's long-term trajectory extends the same rigor outward: automated document capture (OCR on catch slips and supplier bills), an AI assistant that can answer "what's my receivables aging by customer" in plain language, predictive insights on boat profitability and customer risk, and eventually a mobile companion for field staff logging catch and expenses dockside. None of this is built before the operational and financial core is solid — see [Section 11](#11-product-roadmap).

---

## 2. Product Goals

### Short Term Goals (Frontend MVP)

- Expose every backend capability already built (auth, companies, suppliers, fish, boats, trips/catch/expenses, invoices, payments, purchase bills, supplier payments) through a coherent, professional web UI.
- Replace the paper/spreadsheet workflow end-to-end for early customers: they should never need to leave AquaLedger to run daily operations.
- Ship a UI that a new user can operate correctly within their first day, with no training manual required for core flows (create invoice, record payment, log a trip).

### Medium Term Goals

- Reports & Analytics: receivables/payables aging, boat and trip profitability, sales and purchase summaries.
- PDF generation for invoices, purchase bills, and payment receipts.
- Document management for catch slips, supplier bills, and compliance documents.
- Notifications for overdue invoices, expiring boat licenses, and low-balance alerts.

### Long Term Goals

- OCR-assisted data entry (catch slips, supplier bills) to cut manual entry time.
- AI Assistant for natural-language business questions and guided workflows.
- Advanced analytics: forecasting, customer risk scoring, catch/price trend analysis.
- Mobile companion app for dockside and field data capture.

### Business Goals

- Become the system of record a seafood business trusts enough to run its GST filings and bank credit conversations off of.
- Reduce the time from "boat returns" to "invoice paid" — the core cash-cycle the business lives or dies by.
- Support the business as it scales from a single trading desk to a multi-company, multi-boat operation without re-platforming.

### Technical Goals

- Keep the modular monolith clean enough that new modules (Reports, Documents, OCR, AI) slot in without destabilizing the financial core.
- Zero tolerance for floating-point financial bugs — every money/weight/rate value is exact, everywhere, including in the UI layer.
- Sub-second interactions for the screens used dozens of times a day (invoice entry, payment allocation, trip logging).

### User Experience Goals

- A first-time user should recognize the mental model immediately: it mirrors how they already think about their business (boats, trips, bills, payments), not how an accountant's chart of accounts works.
- Data-dense screens (line items, ledgers, catch tables) should feel fast and controllable, not cramped or overwhelming.
- Every irreversible action (issuing an invoice, posting a bill, allocating a payment) should feel deliberate — never accidental, never ambiguous.

---

## 3. Target Customers

### Fish Trader
Buys catch from boats or suppliers, sells to wholesalers/retailers, often on running credit. **Needs:** fast invoice creation tied to available catch, clear view of who owes what. **AquaLedger helps by:** linking trip catch directly to invoice lines so stock-to-sale is traceable, and by giving a live receivables view instead of a diary.

### Fish Exporter
Sells internationally, deals in larger volumes, must meet compliance and traceability expectations. **Needs:** precise per-line tax handling, defensible audit trail, professional documentation. **AquaLedger helps by:** enforcing exact GST-per-line calculation, immutable issued invoices, and a full audit trail on every record.

### Wholesaler
Buys in bulk from traders/exporters, resells to retailers and processors, operates on thin margins at volume. **Needs:** speed and accuracy at high transaction counts, reliable outstanding balances across many counterparties. **AquaLedger helps by:** recomputed (not incrementally-drifting) outstanding balances and fast, keyboard-friendly data entry.

### Seafood Processing Company
Converts raw catch into processed/packaged product, tracks both procurement and sales sides. **Needs:** a mirrored view of the customer lifecycle (sales) and supplier lifecycle (purchasing) in one place. **AquaLedger helps by:** running Order-to-Cash and Procure-to-Pay as parallel, symmetric workflows in the same system.

### Boat Owner
Owns and operates one or more boats, needs to know if each trip is actually profitable after expenses. **Needs:** simple trip logging (catch, expenses) and a clear profit picture per trip and per boat. **AquaLedger helps by:** dedicated Trip → Catch → Expense → Profit Analysis workflow purpose-built for this exact question.

### Fishing Fleet
Manages multiple boats and crews, needs oversight across the whole fleet, not just one vessel. **Needs:** boat-level and fleet-level rollups, license/compliance tracking. **AquaLedger helps by:** the Boats module as a master record with per-boat trip history and roll-up potential in Reports (roadmap).

### Commission Agent
Facilitates trades between boats/suppliers and buyers, often handling money and goods they don't own. **Needs:** clear tracking of who is owed what, on whose behalf. **AquaLedger helps by:** the Companies model's customer/supplier/both typing and the allocation engine's ability to track partial, on-account settlements precisely.

### Cold Storage Operator
Stores goods on behalf of others or as part of their own trading cycle, bridges catch timing and sale timing. **Needs:** visibility into what's on hand awaiting sale versus what's already invoiced. **AquaLedger helps by:** the trip-catch model's available/sold/waste quantity tracking, which gives a live picture of unsold stock without a separate inventory system.

---

## 4. User Personas

### Owner
- **Responsibilities:** Overall business performance, key customer/supplier relationships, final financial accountability.
- **Daily Activities:** Reviews outstanding receivables/payables, checks trip profitability, approves large transactions.
- **Pain Points:** Historically had to ask the accountant or dig through registers for "where do we actually stand" answers.
- **Goals:** A single dashboard that answers "how is the business doing" without asking anyone.
- **Permissions:** Full access across all modules and companies; typically the only role that can manage users and system settings.
- **Typical Screens:** Dashboard, Reports (roadmap), Companies, Invoices, Payments — mostly in a read/oversight capacity.

### Accountant
- **Responsibilities:** Books accuracy, invoice issuance discipline, payment allocation, reconciliation, GST correctness.
- **Daily Activities:** Issues invoices, records and allocates payments, posts purchase bills, reconciles outstanding balances.
- **Pain Points:** Manual ledgers that don't reconcile, ambiguous partial payments, risk of editing an already-issued invoice.
- **Goals:** Confidence that every number is correct and that issued/posted records cannot be silently altered.
- **Permissions:** Full access to Invoices, Payments, Purchase Bills, Supplier Payments, including lifecycle actions (Issue, Post, Allocate); typically no user-management access.
- **Typical Screens:** Invoice Editor, Payment Allocation, Purchase Bill Editor, Supplier Payment screen, Companies (outstanding balances).

### Manager
- **Responsibilities:** Day-to-day oversight of sales/purchasing operations and trip performance within their scope.
- **Daily Activities:** Reviews open invoices and overdue accounts, checks trip status, approves exceptions.
- **Pain Points:** No mid-level visibility between the owner's dashboard and the accountant's transaction screens.
- **Goals:** Catch problems (an overdue customer, a stalled trip) before they become the owner's problem.
- **Permissions:** Broad read access, limited write access to lifecycle actions depending on configuration.
- **Typical Screens:** Dashboard, Invoices/Payments lists, Trips list, Companies.

### Operator (Boat Manager)
- **Responsibilities:** Boat and trip management — scheduling, crew, catch and expense logging.
- **Daily Activities:** Creates and updates trips, logs catch by grade and quantity, records trip expenses.
- **Pain Points:** Paper logbooks that don't connect to what's later sold, making trip profit a guessing game.
- **Goals:** Log a trip's catch and costs quickly, from a boat-centric view, without needing accounting knowledge.
- **Permissions:** Full access to Boats and Trips (including Catch and Expenses); typically no access to Finance modules.
- **Typical Screens:** Boats list, Trip detail (Overview / Catches / Expenses / Profit tabs).

### Field Staff
- **Responsibilities:** On-the-ground data capture — catch tallies, expense receipts, delivery confirmations.
- **Daily Activities:** Enters catch quantities by grade, records small cash expenses, confirms deliveries.
- **Pain Points:** Needs a fast, low-friction entry path; not a desk worker, often entering data between tasks.
- **Goals:** Minimal-friction, hard-to-get-wrong data entry.
- **Permissions:** Narrow, scoped write access — typically limited to Trip Catch and Trip Expense entry.
- **Typical Screens:** Trip Catch entry, Trip Expense entry (subset of the Operator's screens).

### Administrator
- **Responsibilities:** Tenant configuration, user and role management, system-level settings.
- **Daily Activities:** Onboards new users, assigns roles/permissions, configures numbering sequences and master data categories.
- **Pain Points:** Needs confidence that permission changes take effect predictably and safely.
- **Goals:** A clear, auditable permission model that maps directly to what appears in the UI.
- **Permissions:** Full access to Settings and Administration; may or may not have transactional access depending on the business.
- **Typical Screens:** Settings (tenant profile, users & roles, sequences, categories), Administration.

---

## 5. Business Modules

### Masters

**Companies** (customer/supplier/both master)
- *Purpose:* Central record for every business counterparty — customers, suppliers, or both — with credit terms and identity/compliance data (GSTIN, PAN).
- *Users:* Accountant (creates/maintains), Owner/Manager (reviews), all transactional modules (references).
- *Business Value:* One counterparty record eliminates duplicate/conflicting customer data and anchors every receivable and payable.
- *Dependencies:* Referenced by Invoices, Payments, and (for supplier-typed companies) Purchase Bills and Supplier Payments.

**Suppliers**
- *Purpose:* Vendor master used specifically for the purchasing lifecycle.
- *Users:* Accountant, Purchasing-responsible staff.
- *Business Value:* Keeps the purchase side (Procure-to-Pay) as rigorous and traceable as the sales side.
- *Dependencies:* Referenced by Purchase Bills and Supplier Payments.

**Fish**
- *Purpose:* Item master for every species/grade traded — code, category, unit of measure, default rates, HSN code.
- *Users:* Administrator (setup), Accountant/Operator (referenced constantly in catch and invoice entry).
- *Business Value:* Consistent naming and rates across the business; foundation for future reporting by species.
- *Dependencies:* Referenced by Trip Catch and Invoice line items.

### Operations

**Boats**
- *Purpose:* Registry of vessels — registration, license/insurance status, ownership, captain.
- *Users:* Boat Manager/Operator, Owner (fleet oversight).
- *Business Value:* Compliance visibility (expiring documents) and the anchor for trip history per vessel.
- *Dependencies:* Parent record for Trips.

**Trips**
- *Purpose:* A single fishing voyage, tracked through its lifecycle (planned → at sea → returned → settled/cancelled).
- *Users:* Boat Manager/Operator, Field Staff.
- *Business Value:* Converts "a boat went out and came back" from an informal event into a structured, costable, sellable record.
- *Dependencies:* Belongs to a Boat; parent to Trip Catch and Trip Expenses.

**Trip Catch**
- *Purpose:* Records what was landed, by fish and grade, with quantity tracked as available / sold / waste.
- *Users:* Field Staff, Operator.
- *Business Value:* The bridge between operations and sales — invoice lines can trace back to the exact catch they were sold from, and unsold catch is always visible.
- *Dependencies:* Belongs to a Trip; referenced by Invoice line items.

**Trip Expenses**
- *Purpose:* Records the costs of running a trip — diesel, ice, food, labour, harbour fees, etc.
- *Users:* Field Staff, Operator.
- *Business Value:* Without this, "profit per trip" is a guess. With it, it's a number.
- *Dependencies:* Belongs to a Trip; feeds trip profit analysis.

### Sales

**Invoices**
- *Purpose:* The customer-facing sales document — draft while being built, immutable once issued.
- *Users:* Accountant (primary), Manager/Owner (review).
- *Business Value:* Legally and financially defensible sales records with exact per-line GST and atomic fiscal-year numbering — no renumbering disputes, no post-issue edits.
- *Dependencies:* References Companies (customer), Fish, and optionally Trip Catch; feeds Payments and outstanding balances.

**Customer Payments**
- *Purpose:* Records money received and allocates it across one or more open invoices.
- *Users:* Accountant.
- *Business Value:* Supports the real-world pattern of partial and on-account payments without ever guessing which invoice a payment covers — allocations are explicit and recomputed correctly on every change.
- *Dependencies:* References Companies and Invoices; drives receivables outstanding.

### Purchasing

**Purchase Bills**
- *Purpose:* The mirror of Invoices on the buying side — bills received from suppliers.
- *Users:* Accountant.
- *Business Value:* Brings the same numbering discipline and posting rigor to payables that Invoices bring to receivables.
- *Dependencies:* References Suppliers; feeds Supplier Payments and payables outstanding.

**Supplier Payments**
- *Purpose:* Records money paid out and allocates it across one or more posted purchase bills.
- *Users:* Accountant.
- *Business Value:* Completes the Procure-to-Pay lifecycle with the same allocation rigor as the customer side — no more "did we already pay that bill" uncertainty.
- *Dependencies:* References Suppliers and Purchase Bills; drives payables outstanding.

### Reports *(Roadmap)*
- *Purpose:* Receivables/payables aging, trip and boat profitability, sales/purchase summaries.
- *Users:* Owner, Manager, Accountant.
- *Business Value:* Turns the transactional data already captured into the decisions it exists to support.
- *Dependencies:* Reads from every transactional module; builds nothing new, surfaces what exists.

### Administration

**Settings**
- *Purpose:* Tenant profile, users & roles, numbering sequences, fish/expense categories.
- *Users:* Administrator.
- *Business Value:* Lets each tenant configure identity and structure without engineering involvement.
- *Dependencies:* Underpins every other module's configuration.

---

## 6. Core Business Workflows

### Customer Lifecycle (Order-to-Cash)

```
Company (customer)
      ↓
Invoice created (draft — editable)
      ↓
Invoice Issued (locked, numbered, immutable)
      ↓
Payment recorded
      ↓
Payment Allocated (against one or more invoices)
      ↓
Outstanding Recomputed → Cleared / Partially Paid / Overdue
```

An invoice in draft is a work in progress — line items, discounts, and tax can all change freely. The moment it is **issued**, it is assigned its permanent sequence number and becomes immutable: no further edits, only future reversal/credit-note mechanisms for corrections. Payments are never matched to invoices by assumption — every allocation is an explicit, auditable link, which is what allows a single payment to clear part of one invoice and part of another, correctly, every time.

### Supplier Lifecycle (Procure-to-Pay)

```
Supplier
      ↓
Purchase Bill created
      ↓
Purchase Bill Posted (locked, numbered)
      ↓
Supplier Payment recorded
      ↓
Payment Allocated (against one or more bills)
      ↓
Outstanding Recomputed → Cleared / Partially Paid
```

This mirrors the customer lifecycle deliberately. A business that trusts its receivables process should trust its payables process the same way — same discipline, same allocation model, same immutability guarantees once posted.

### Fishing Workflow

```
Boat
   ↓
Trip (planned → at sea → returned → settled)
   ↓
Trip Catch (landed, by fish/grade — available / sold / waste)
   ↓
Trip Expenses (diesel, ice, labour, harbour, etc.)
   ↓
Profit Analysis (revenue from sold catch − trip expenses)
```

This is the workflow that has no equivalent in a generic ERP. It starts before any money changes hands — a boat goes out, catches fish, incurs costs — and only connects to the financial workflows above when catch is actually sold (a Trip Catch record becomes an Invoice line item). Until then, the system already knows what's available to sell and what a trip has cost, which is what makes real trip-level profitability possible.

---

## 7. Product Principles

- **Fast** — the screens used dozens of times a day (invoice entry, catch logging, payment allocation) must never feel like they're waiting on the user, or the user waiting on them.
- **Professional** — this is a tool people trust with their money and their GST filings; it should read as trustworthy on sight, not playful or decorative.
- **Minimal** — every element on screen earns its place; no ornamentation that doesn't help someone get their work done faster or more accurately.
- **Modern** — the visual and interaction language of current best-in-class SaaS, not the legacy enterprise software this replaces.
- **Enterprise Ready** — multi-tenant isolation, RBAC, and audit trails are not add-ons; they are load-bearing, and the UI must make them visible and trustworthy (e.g., showing who did what, when).
- **Keyboard Friendly** — high-volume data entry (invoice lines, catch entries) must support fast, mouse-optional flows.
- **Accessible** — usable by people with varying vision and motor ability; this is a daily-use business tool, not optional polish.
- **Responsive** — desktop-first (this is a data-dense operational tool), but functional down to tablet widths for field/dockside use.
- **High Performance** — snappy under real data volumes, not just demo data.
- **Simple** — the simplest interface that fully exposes the underlying model's power, never simpler than that.
- **Consistent** — one set of patterns (list pages, detail pages, status badges, lifecycle actions) applied everywhere, so learning one module teaches you all of them.

---

## 8. UX Principles

**Navigation** — a persistent, predictable structure (see [Section 9](#9-navigation-philosophy)) so users always know where they are and how to get to the next thing.

**Information Hierarchy** — the most decision-relevant information (status, amount due, next action) is always the most visually prominent; supporting detail is present but subordinate.

**Consistency** — list pages look like list pages everywhere; detail pages look like detail pages everywhere. A user who has learned the Invoices module should already understand 80% of the Purchase Bills module.

**Progressive Disclosure** — complex records (an invoice with tax breakdowns, a trip with catch and expenses) default to a clear summary view with detail available on demand, not everything exposed at once.

**Error Prevention** — irreversible actions (Issue, Post, Delete) are confirmed explicitly; the system should make the *safe* path the *easy* path, especially given that issued invoices and posted bills cannot be edited afterward.

**Data Density** — this is a professional tool for people entering data all day; err toward compact, information-rich layouts over generous whitespace, without becoming cramped or hard to scan.

**Large Tables** — line items, catch tables, and transaction lists must support fast scanning, sorting, and filtering at real-world volume (hundreds of rows), not just demo-sized data.

**Financial Accuracy** — every money, weight, and rate value displayed must reflect the backend's exact decimal precision; the UI must never introduce floating-point rounding that the backend explicitly avoids.

**Status Visibility** — lifecycle state (draft/issued/paid/overdue, posted/allocated/cleared, planned/at sea/settled) is always visible at a glance via consistent status indicators, since state is the single most important fact about most records in this system.

**Accessibility** — sufficient color contrast, keyboard navigability, and screen-reader-sensible structure across both themes.

**Dark Mode / Light Mode** — both are first-class, not an afterthought toggle; users work long hours in this tool and should be able to choose what's comfortable.

---

## 9. Navigation Philosophy

```
Dashboard → Masters → Operations → Finance → Reports → Administration → Settings
```

- **Dashboard** — the answer to "how are we doing right now," first thing a user sees.
- **Masters** — the stable reference data (Companies, Suppliers, Fish) that everything else points to; changed rarely, referenced constantly.
- **Operations** — the physical/operational reality of the business (Boats, Trips, Catch, Expenses) — where value is created, before any invoice exists.
- **Finance** — where operational reality becomes financial fact (Invoices, Customer Payments, Purchase Bills, Supplier Payments) — the Order-to-Cash and Procure-to-Pay lifecycles.
- **Reports** — where transactional data becomes decisions (roadmap).
- **Administration / Settings** — how the system is configured, scoped to the roles that need it.

This grouping is deliberate, not alphabetical or feature-driven: it follows the same sequence the business itself follows — a boat goes out (**Operations**) before it generates a sale (**Finance**), and both draw on the same stable counterparties and items (**Masters**). A user's mental model of their own business maps directly onto the navigation, which is why no separate "how to use this" explanation should be needed for the structure itself. It is also consistent with the interaction-design direction already explored for AquaLedger's UI (`DESIGN_PROMPT.md`), which groups the sidebar the same way (Masters / Operations / Finance / Insights / Settings).

---

## 10. Permission Philosophy

RBAC is not a backend-only concern — it must be visibly and consistently reflected in the UI, because a user should never discover a permission boundary by hitting an error.

- **Menu Visibility** — navigation items for modules or sections a user has no access to are not shown at all, not shown-then-blocked.
- **Hidden Buttons** — actions a user cannot perform (e.g., "Issue Invoice" for a Field Staff account) are not rendered, rather than rendered-and-disabled, to keep screens uncluttered for each role's actual job.
- **Read Only Pages** — where a user can view but not modify a record, the UI communicates this clearly (no edit affordances shown) rather than allowing an edit attempt to fail.
- **Lifecycle Actions** — the highest-stakes actions in the system map directly to permission codes at the service layer, and the UI must gate them identically:
  - **Issue** (lock an invoice) — typically Accountant and above.
  - **Post** (lock a purchase bill) — typically Accountant and above.
  - **Delete** — restricted to master data and draft-only records; issued invoices and posted bills are never deletable by anyone, in the UI or otherwise — only reversal/cancellation paths exist.
  - **Allocation** (matching payments to invoices/bills) — typically Accountant only.
  - **Approval** — reserved for exception flows as the product matures (e.g., large payment approval), gated to Manager/Owner roles.

Because permissions are expressed as `resource:action` codes at the backend and enforced at the route, service, and row level, the frontend's job is to faithfully mirror that same model — never to invent a looser or stricter version of it in the UI layer.

---

## 11. Product Roadmap

### Current Version
- **Backend:** Complete through the full Order-to-Cash and Procure-to-Pay lifecycles — Auth, Companies, Fish, Boats, Trips, Trip Catch, Trip Expenses, Invoices, Customer Payments, Suppliers, Purchase Bills, Supplier Payments — with multi-tenancy, RBAC, audit trail, and soft delete in place.
- **Frontend:** Not yet started; this document is the foundation for that work.

### Frontend (Immediate Next)
- Dashboard, and full UI coverage of every module listed above.

### Near-Term Roadmap
- Reports & Analytics (aging, profitability, summaries)
- PDF generation (invoices, bills, receipts)
- Document Management (catch slips, supplier bills, compliance docs)
- Notifications (overdue invoices, expiring licenses)

### Mid-Term Roadmap
- Accounting depth (chart of accounts / ledger reporting views on top of the existing append-only ledger)

### Long-Term Roadmap
- OCR (automated capture from catch slips and supplier bills)
- AI Assistant (natural-language business queries and guided workflows)
- Advanced Analytics (forecasting, risk scoring, trend analysis)

### Future
- Mobile companion app for dockside/field data capture

Consistent with the project's build discipline: nothing in the near-, mid-, or long-term roadmap is pulled forward ahead of a solid operational and financial core — the MVP replaces paper workflows first.

---

## 12. Success Metrics

- **Performance:** Sub-second response for common interactions (list loads, invoice line calculations, catch entry) under real transaction volumes.
- **User Productivity:** Time to create an invoice, log a trip, or allocate a payment should be measurably faster than the paper/spreadsheet process it replaces.
- **Learning Curve:** A new user should complete core daily tasks (invoice, payment, trip entry) correctly on their first day without a training session.
- **Financial Accuracy:** Zero tolerance for rounding drift or misallocation — every displayed total must match the backend's exact decimal computation, always.
- **Speed:** No perceptible lag in day-to-day data entry, even in line-item-heavy screens.
- **Reliability:** No data loss, no silent failures on irreversible actions (Issue, Post, Delete, Allocate).
- **Accessibility:** Meets WCAG AA at minimum across both light and dark themes.
- **Scalability:** UI performance and usability hold as a tenant grows from one boat/one desk to a multi-boat, multi-company operation.

---

## 13. Design Inspiration

AquaLedger should feel like it belongs next to:

- **Linear** — for speed, keyboard-first interaction, and restraint.
- **Stripe Dashboard** — for how financial data density and clarity coexist.
- **Mercury** — for how a serious financial tool can still feel calm and modern.
- **Ramp** — for making expense/transaction-heavy workflows feel effortless.
- **Vercel** — for clean information architecture and dark-mode execution.
- **Notion** — for approachable, uncluttered structure without sacrificing power.
- **GitHub** — for how status, activity, and permissions are made legible at a glance.

AquaLedger should explicitly avoid the visual and interaction language of:

- Generic Bootstrap admin templates
- Dated, decade-old ERP interfaces
- Legacy enterprise software conventions (dense unstyled grids, modal-heavy workflows, inconsistent iconography)

---

## 14. Product Summary

AquaLedger is what happens when a seafood business's actual operating reality — boats, trips, catch, grades, perishability, running credit with dozens of counterparties — is treated as the starting point for software design, rather than squeezed into a generic ERP or bolted onto accounting software after the fact. The backend already proves this out: a rigorous, decimal-exact financial core (immutable issued invoices, atomic numbering, explicit payment allocation, append-only ledgers) sitting directly on top of an operational model that understands what a trip is and what it costs to run one.

It is different because it is domain-native, not domain-adapted. It is valuable because it replaces fragmented paper and spreadsheet processes with a single trustworthy system — one a business owner can build a bank conversation or a GST audit around without flinching.

The long-term vision is a platform that not only records the business but actively helps run it: surfacing which trips were profitable, which customers are becoming a risk, and eventually answering those questions in plain language before anyone has to ask. That future is only credible because it is being built on a foundation — this document, and the backend it describes — that gets the fundamentals exactly right first.
