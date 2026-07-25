# AquaLedger — Frontend Implementation Plan

**The Master Execution Plan for AquaLedger Frontend Development**

Version 1.0 · Project Implementation Roadmap

This document sequences the build of everything specified in `01_PRODUCT_VISION.md` through `07_FRONTEND_ARCHITECTURE.md` into ten sprints. It answers what to build, in what order, sprint by sprint, with dependencies, deliverables, and acceptance criteria — it introduces no new product, design, or architecture decision; it only sequences the ones already made.

---

## Overall Roadmap

**Project Phases**

1. **Foundation** (Sprint 1) — infrastructure, auth, app shell.
2. **Shared Foundation** (Sprint 2) — the full component library, built once, reused for the rest of the project.
3. **Dashboard** (Sprint 3) — the first real feature, deliberately early because it exercises the API/state/chart layers every later module depends on.
4. **Core Business Modules** (Sprints 4–7) — Master Data, Trips, Sales, Purchasing, in the same dependency order the business itself follows (per `03_INFORMATION_ARCHITECTURE.md` §1: Masters feed Operations and Finance).
5. **Reports & Administration** (Sprints 8–9) — capabilities that consume data produced by Phase 4, so they are sequenced after it, not before.
6. **Production Readiness** (Sprint 10) — hardening, auditing, and closing every quality gate before release.

**Estimated Sprint Count:** 10 sprints (matching the backend's own two-week sprint cadence evidenced in its git history), roughly 20 weeks / ~5 months for MVP scope. This assumes a team capable of the parallelization noted per-sprint below; a smaller team should treat sprint numbers as sequential milestones rather than fixed two-week boxes.

**Major Milestones**
- **M1 (end of Sprint 2):** Foundation and full component library complete — every subsequent sprint is pure feature assembly, no further primitive-building.
- **M2 (end of Sprint 3):** First end-to-end vertical slice (login → Dashboard, live-data) demonstrable to stakeholders.
- **M3 (end of Sprint 7):** Full Order-to-Cash and Procure-to-Pay lifecycles operable end-to-end — this is the point at which AquaLedger has functionally replaced the paper workflow per `01_PRODUCT_VISION.md` §1.
- **M4 (end of Sprint 9):** Full feature-complete MVP per `05_PAGE_CATALOG.md`'s scope.
- **M5 (end of Sprint 10):** Production release.

**Critical Dependencies**
- **Backend reporting/dashboard aggregation endpoints do not yet exist.** Every other backend module needed for Sprints 4–7 and 9 is confirmed complete, but Dashboard (Sprint 3) and Reports (Sprint 8) require aggregation endpoints (KPIs, aging buckets, profitability rollups) that are not part of the backend's current module set. This is the single largest cross-team dependency in this plan — see Risk Areas and the Sprint 3/8 entries below for the mitigation.
- Every feature sprint (4–9) depends on Sprint 1 (auth/shell) and Sprint 2 (component library) being fully complete first — no feature work starts against a partial shared foundation, per the Implementation Principles.
- Sprint 6 (Sales) and Sprint 7 (Purchasing) both depend on Sprint 4 (Companies/Suppliers) and, for Sales specifically, on Sprint 5 (Trips, for the Trip-Catch-to-Invoice-line linkage per `04_USER_FLOWS.md` §11).

**Risk Areas**
- **Backend reporting gap** (above) — highest risk; requires an explicit conversation with the backend team before Sprint 3 planning locks.
- **Line-item editor complexity** (Sprint 6/7) — the Invoice/Purchase Line Editor is this project's most interaction-heavy component (live recalculation, Trip Catch linkage, inline validation); it is the most likely sprint to run long and should be the first task started within its sprint, not the last.
- **Permission-matrix UI** (Sprint 9) — the Roles & Permissions page is the one page in `05_PAGE_CATALOG.md` with no close analog elsewhere in the catalog (no other page is a matrix editor); budget extra design-review time.
- **Table performance at real data volume** — Companies/Invoices/Audit Logs lists must be validated against realistic row counts (hundreds to low thousands), not just demo data, before Sprint 10 sign-off, per `07_FRONTEND_ARCHITECTURE.md` §19's virtualization guidance.

**Success Criteria**
- Every page in `05_PAGE_CATALOG.md` is implemented, wired to its real backend endpoint, and passes its page-specific acceptance criteria.
- Every component in `06_COMPONENT_LIBRARY.md` is implemented exactly once and reused everywhere it's specified — zero duplicate/bespoke implementations discovered during Sprint 10's audit.
- Zero P1 (data-loss, incorrect-financial-figure, or security) bugs open at release.
- All Final Release Checklist items (below) are satisfied.

---

## Sprint 1 — Project Foundation

**Sprint Goal:** Stand up the application shell, authentication, and every piece of cross-cutting infrastructure so that Sprint 2 onward is pure feature work on a stable base.

**Estimated Duration:** 2 weeks.

**Features:** Login, Forgot/Reset Password, Session Expiry, Unauthorized, App Layout shell, theme toggle (infrastructure only — full Appearance page is Sprint 9).

**Pages:** All of `05_PAGE_CATALOG.md` §1 (Login, Forgot Password, Reset Password, Unauthorized, Session Expired). Dashboard route exists as a placeholder shell only (real content is Sprint 3).

**Components:** App Layout, Sidebar (static shell, permission-filtering logic present but few real nav items to filter yet), Top Navigation, Page Header — the Layout-tier components from `06_COMPONENT_LIBRARY.md` §1, built as real, final implementations (not placeholders), since every later sprint depends on them.

**Backend APIs:** `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` (current user, role, permission set, tenant context).

**Dependencies:** None — this is the first sprint.

**Risks:** Underestimating the Axios/TanStack Query/Auth Provider wiring, since it's genuinely cross-cutting infrastructure rather than a feature with a clear visual finish line — track this sprint's completion against the Definition of Done below, not against "it looks done."

**Deliverables:**
- Next.js 15 project initialized per `07_FRONTEND_ARCHITECTURE.md` §3 folder structure.
- Working authentication flow end-to-end against the real backend (`04_USER_FLOWS.md` §2).
- Route protection enforced at the `(authenticated)` layout (`07_FRONTEND_ARCHITECTURE.md` §4, §10).
- App Layout, Sidebar, Top Navigation rendering, theme (light/dark/system) switching live.
- Axios instance with interceptors, TanStack Query client, all providers composed in the root layout (`07_FRONTEND_ARCHITECTURE.md` §8–9, §17).
- Environment configuration schema and validation (`07_FRONTEND_ARCHITECTURE.md` §26).
- ESLint, Prettier, TypeScript strict mode configured and passing.
- Testing infrastructure installed and running (unit/component test runner, E2E runner scaffolded with one smoke test: login succeeds and reaches the Dashboard shell).

**Acceptance Criteria:**
- A user can log in with valid credentials and land on `/dashboard`; invalid credentials show the correct inline error (`05_PAGE_CATALOG.md` §1).
- A logged-out user hitting any `(authenticated)` route is redirected to `/login` and, after logging in, is returned to their original destination.
- Forgot Password / Reset Password flows work end-to-end including the expired-token state.
- Session expiry mid-session correctly triggers the Session Expired flow and preserves recoverable state, per `04_USER_FLOWS.md` §2.
- Theme toggle persists across reload.

**Definition of Done:** All acceptance criteria pass in CI E2E; zero TypeScript or lint errors; PR reviewed against the Code Review Checklist in `07_FRONTEND_ARCHITECTURE.md` §25.

---

## Sprint 2 — Shared Component Library

**Sprint Goal:** Build every shared, reusable component from `06_COMPONENT_LIBRARY.md` Sections 1–14 exactly once, in isolation from any business feature, so every sprint from here forward composes rather than invents.

**Estimated Duration:** 3 weeks (the longest sprint in the plan — this is the deliberate up-front investment the Implementation Principles call for: "build reusable components before feature pages").

**Features:** None (no business feature ships this sprint) — this is infrastructure by design.

**Pages:** None.

**Components:** The full `components/ui` and `components/layout` tiers per `07_FRONTEND_ARCHITECTURE.md` §6: Buttons (all 12 variants, §3), Form inputs (all 23 variants, §4 — Currency Input and Percentage Input treated as the highest-priority items given `01_PRODUCT_VISION.md`'s financial-accuracy stakes), Cards (all 9 variants, §5), Dialogs/Drawers/Popovers/Tooltips/Toasts (§8), the Enterprise Data Table shell with Toolbar/Filter Panel/Pagination/Row Actions (§6, built and tested against mock data — real API wiring happens per-feature from Sprint 4 on), Chart wrappers (§11), all Skeleton variants (§12), Empty and Error State components (§13–14), Status Badge (§7, base component only — entity-specific vocabularies are configured per feature as they're built).

**Backend APIs:** None consumed directly; components are built and tested against typed mock data.

**Dependencies:** Sprint 1's providers, theme system, and folder structure.

**Risks:** Scope creep — it is tempting to over-build variants "just in case." Build exactly what `06_COMPONENT_LIBRARY.md` specifies, no more; anything not yet specified there is deferred per that document's own §19 rule, not added speculatively here.

**Deliverables:** Every component in `06_COMPONENT_LIBRARY.md` §1–14 implemented, documented in code comments/Storybook-equivalent isolation, and unit/component-tested for its documented states (default, loading, empty, error, disabled) per `07_FRONTEND_ARCHITECTURE.md` §22.

**Acceptance Criteria:**
- Every component renders correctly in both light and dark theme.
- Every form input enforces its documented validation behavior in isolation (e.g., Currency Input rejects invalid precision).
- The Enterprise Data Table correctly sorts, paginates, and filters against mock data, including its Empty and Loading states.
- Full keyboard-navigability verified per `06_COMPONENT_LIBRARY.md` §15 for every interactive component.

**Definition of Done:** 100% of `06_COMPONENT_LIBRARY.md` §1–14 components implemented and tested; no feature sprint from Sprint 4 onward is permitted to add a new shared `components/ui` primitive without an explicit, documented exception (a genuinely new need discovered mid-feature is added here retroactively and back-filled with the same test coverage, not built inline in the feature).

---

## Sprint 3 — Dashboard

**Sprint Goal:** Ship the first real, live-data feature — the Executive Dashboard — validating the full API/state/chart stack end-to-end on real (if still-sparse) backend data before the team fans out into the larger Sprint 4–7 modules.

**Estimated Duration:** 2 weeks, **contingent on the backend reporting-gap mitigation below** — see Risks.

**Features:** Executive Dashboard (`04_USER_FLOWS.md` §3), Notification Panel (basic — categories wired, real triggers arrive as later sprints ship the modules that produce them), Quick Actions.

**Pages:** `05_PAGE_CATALOG.md` §2 (Executive Dashboard) — its final, complete implementation.

**Components:** KPI Card / Outstanding Card (`06_COMPONENT_LIBRARY.md` §9), Line/Bar Chart wrappers wired to real data, Activity Feed, Notification Panel (`06_COMPONENT_LIBRARY.md` §2, §10).

**Backend APIs:** KPI/aggregation endpoints for receivables outstanding, payables outstanding, trips-at-sea count, boat-compliance alerts; a recent-activity feed endpoint.

**Dependencies:** Sprint 1 (shell), Sprint 2 (KPI Card, Chart wrappers, Activity Feed primitives already built).

**Risks — Backend Reporting Gap:** As flagged in Overall Roadmap, dedicated dashboard-aggregation endpoints are not part of the backend's currently-shipped module set. **Mitigation, in priority order:** (1) coordinate with the backend team to schedule these endpoints ahead of this sprint — the preferred path, since server-side aggregation is both more correct and more performant than client-side rollups over large datasets; (2) if that isn't feasible on this sprint's timeline, implement an interim client-side composition (deriving KPIs from the already-complete Companies/Invoices/Payments list endpoints) clearly marked as a temporary measure to be replaced once the real endpoints ship, tracked as tech debt rather than silently accepted as final. This decision must be made explicitly before Sprint 3 starts, not discovered mid-sprint.

**Deliverables:** Live Dashboard showing real KPIs, charts, recent activity, and Quick Actions; Notification Panel UI complete (even if only a subset of trigger categories are live this early, since most triggering modules ship in later sprints).

**Acceptance Criteria:**
- KPI cards show real, correctly-formatted (`07_FRONTEND_ARCHITECTURE.md` §18) figures and link through to their source views.
- Charts render real trend/aging data and match `02_DESIGN_SYSTEM.md` §11's styling.
- Every Dashboard section has independent, correctly-sequenced loading and error states per `04_USER_FLOWS.md` §20.
- Dashboard is fully responsive per `04_USER_FLOWS.md` §24.

**Definition of Done:** Acceptance criteria pass; the KPI data source (real vs. interim-composed) is explicitly documented in the PR description so Sprint 8 planning knows exactly what needs replacing.

---

## Sprint 4 — Master Data

**Sprint Goal:** Ship full CRUD for every Masters-group entity, establishing the List → Create → Detail → Edit pattern that every later transactional module will repeat verbatim.

**Estimated Duration:** 2 weeks.

**Features:** Companies, Suppliers, Fish, Boats — full lifecycle per `04_USER_FLOWS.md` §4–7.

**Pages:** `05_PAGE_CATALOG.md` §3–6 in full (16 pages: List/Create/Detail/Edit × 4 modules).

**Components:** Entity Selector (`06_COMPONENT_LIBRARY.md` §10) built here for the first time and reused by every subsequent module; Company/Supplier/Fish/Boat-specific Status Badges configured from the base Status Badge.

**Backend APIs:** Full CRUD for `companies`, `suppliers`, `fish`, `boats`.

**Dependencies:** Sprint 1–2 complete.

**Risks:** Low — this is the most template-driven sprint in the plan (four near-identical modules); the main risk is under-investing in Companies specifically, since its Entity Selector and Overview Card patterns are reused everywhere from Sprint 5 onward. **Recommendation:** build Companies first and treat it as the reference implementation the other three modules are built against, rather than building all four in parallel from a blank slate.

**Deliverables:** Four fully functional Masters modules; the Entity Selector component, validated against real search/select behavior for the first time.

**Acceptance Criteria:**
- Every module's List page supports search, the documented filters, sort, and pagination against real data.
- Create/Edit forms enforce all validation rules from `04_USER_FLOWS.md` §4–7, including duplicate-GSTIN detection.
- Deactivation (soft-delete) works correctly and deactivated records disappear from Entity Selectors while remaining visible on historical records.
- RBAC button/field guards correctly hide Create/Edit/Deactivate for read-only roles (`07_FRONTEND_ARCHITECTURE.md` §11).

**Definition of Done:** Acceptance criteria pass for all four modules; Companies' implementation reviewed and confirmed as the template other modules (and future ones) should match.

---

## Sprint 5 — Trips

**Sprint Goal:** Ship the Operations module — the one workflow with no analog elsewhere in the product (`04_USER_FLOWS.md` §26) — including its nested Catch/Expense entry and lifecycle state machine.

**Estimated Duration:** 2.5 weeks (longer than Sprint 4 due to the Tabs-based Detail page and two nested inline-entry tables).

**Features:** Trips, Trip Catch, Trip Expenses, Trip Profit, Trip lifecycle transitions (planned → at_sea → returned → settled/cancelled).

**Pages:** `05_PAGE_CATALOG.md` §7 in full (List, Create, Details with 4 tabs, Edit).

**Components:** Tabs (nested layout per `07_FRONTEND_ARCHITECTURE.md` §4), Status Timeline, the inline Enter-to-add-row table pattern (shared groundwork for the Sprint 6/7 Line Editors — build this pattern carefully here since it's reused, not reinvented, next sprint).

**Backend APIs:** Full CRUD for `trips`, `trip_catches`, `trip_expenses`; status-transition endpoints.

**Dependencies:** Sprint 4 (Boats master, Fish master for the Catch table's Fish selector).

**Risks:** The available/sold/waste quantity invariant on Trip Catch (`04_USER_FLOWS.md` §9) is the first genuinely business-rule-heavy validation in the frontend; budget explicit test-writing time for it, not just happy-path implementation.

**Deliverables:** Full Trip lifecycle operable end-to-end, including catch and expense logging and the live Profit tab calculation.

**Acceptance Criteria:**
- Trip status transitions render only the single valid next action per current status (`03_INFORMATION_ARCHITECTURE.md` §13) and correctly block Settle when catch quantities don't reconcile.
- Trip Catch inline entry correctly derives Available as `caught − sold − waste` and prevents direct entry of Available.
- Trip Expense inline entry correctly feeds the Profit tab's live recalculation.
- Boat compliance-expiry warning shown (not blocking) on Trip creation when applicable.

**Definition of Done:** Acceptance criteria pass; the reconciliation-invariant and status-transition logic both have dedicated unit tests per `07_FRONTEND_ARCHITECTURE.md` §22's rule that critical calculations must always be tested.

---

## Sprint 6 — Sales Module

**Sprint Goal:** Ship the Order-to-Cash lifecycle end-to-end — the single highest-stakes workflow in the product, given invoice immutability and the payment-allocation engine.

**Estimated Duration:** 3 weeks (the Invoice Line Editor is this plan's flagged highest-complexity component; see Risk Areas).

**Features:** Invoices (full lifecycle, `04_USER_FLOWS.md` §11), Customer Payments and Allocation (`04_USER_FLOWS.md` §12), Dashboard KPI wiring upgraded from Sprint 3's interim state to real receivables data.

**Pages:** `05_PAGE_CATALOG.md` §8 (Invoice List/Create/Details/Edit/Issue Confirmation) and §9 (Payment List/Create/Details/Allocation Dialog/Posting Confirmation).

**Components:** Invoice Line Editor and Allocation Table (`06_COMPONENT_LIBRARY.md` §10) — both built here for the first time; **Invoice Line Editor should be the first task started in this sprint**, per the Risk Areas note in Overall Roadmap.

**Backend APIs:** Full CRUD + Issue lifecycle action for `invoices`; full CRUD + allocation actions for `payments`.

**Dependencies:** Sprint 4 (Companies, Fish), Sprint 5 (Trip Catch, for the optional catch-to-invoice-line linkage).

**Risks:** Financial-correctness risk is highest in this sprint of the whole plan — the live totals recalculation (subtotal → tax breakdown → grand total) and the allocation over-allocation guards must exactly mirror backend behavior, per `07_FRONTEND_ARCHITECTURE.md` §1's "never re-derive what the backend has already computed" principle wherever a server round-trip is feasible, and must be unit-tested exhaustively wherever live client-side recalculation is unavoidable for UX responsiveness.

**Deliverables:** Full Invoice and Customer Payment lifecycle operable end-to-end; Dashboard receivables KPI now backed by real invoice/payment data.

**Acceptance Criteria:**
- Invoice Editor's totals panel recalculates correctly and matches backend-computed totals on save, for every documented line-item combination (discount, multiple tax rates, transport/other charges, round-off).
- Issue correctly locks the invoice, assigns its number, and removes the Edit route, with the Issue Confirmation dialog behaving exactly per `05_PAGE_CATALOG.md` §8.
- Payment allocation correctly blocks over-allocation at both the payment-total and per-invoice level, updates outstanding balances correctly, and supports partial/multi-invoice allocation.
- Remove Allocation correctly reverses balances per `04_USER_FLOWS.md` §12.

**Definition of Done:** Acceptance criteria pass, including a dedicated test suite comparing client-computed totals against backend-returned totals across a matrix of line-item scenarios; E2E test covering the full Company → Invoice → Issue → Payment → Allocation → Cleared journey passes.

---

## Sprint 7 — Purchase Module

**Sprint Goal:** Ship the Procure-to-Pay lifecycle by mirroring Sprint 6's components and patterns exactly, validating the reuse strategy the whole plan is built on.

**Estimated Duration:** 1.5 weeks (deliberately shorter than Sprint 6 — this sprint should be substantially a mirroring exercise, not new invention, and its actual duration is a direct signal of how well Sprint 6 was built for reuse).

**Features:** Purchase Bills (full lifecycle, `04_USER_FLOWS.md` §13), Supplier Payments and Allocation (`04_USER_FLOWS.md` §14).

**Pages:** `05_PAGE_CATALOG.md` §10–11.

**Components:** Purchase Line Editor as an explicit variant of Invoice Line Editor (`06_COMPONENT_LIBRARY.md` §10 — Fish/Trip-Catch selector swapped for a free-text description field, nothing else); the Allocation Table reused unchanged from Sprint 6, scoped to Purchase Bills.

**Backend APIs:** Full CRUD + Post lifecycle action for `purchase_bills`; full CRUD + allocation actions for `supplier_payments`.

**Dependencies:** Sprint 4 (Suppliers), Sprint 6 (Invoice Line Editor and Allocation Table to mirror from).

**Risks:** Low, provided Sprint 6 was built cleanly — the main risk is discovering Sprint 6's components were built with Invoice-specific assumptions baked in rather than genuinely reusable; if so, this sprint should fix that generalization rather than duplicate the component, per `06_COMPONENT_LIBRARY.md` §19.

**Deliverables:** Full Purchase Bill and Supplier Payment lifecycle operable end-to-end. **M3 milestone reached: full Order-to-Cash and Procure-to-Pay operable.**

**Acceptance Criteria:** Identical shape to Sprint 6's, scoped to Suppliers/Purchase Bills/Supplier Payments; E2E test covering the full Supplier → Purchase Bill → Post → Payment → Allocation → Cleared journey passes.

**Definition of Done:** Acceptance criteria pass; a short retrospective note in the PR confirming what fraction of Sprint 6's components were reused unchanged vs. required generalization, feeding the Sprint 10 audit.

---

## Sprint 8 — Reports

**Sprint Goal:** Ship the analytical layer that turns Sprints 4–7's transactional data into decisions, per `01_PRODUCT_VISION.md` §11's near-term roadmap.

**Estimated Duration:** 2 weeks, **contingent on the same backend reporting-gap dependency flagged for Sprint 3.**

**Features:** Sales Report, Purchase Report, Trip Profitability, Receivable Aging, Payable Aging, Financial Summary, Inventory (Coming Soon placeholder only).

**Pages:** `05_PAGE_CATALOG.md` §12 in full.

**Components:** Report filter bar (an application of the List Page Toolbar pattern to a non-tabular context), Export action, the remaining Chart wrapper variants not yet exercised by Dashboard.

**Backend APIs:** Dedicated reporting/aggregation endpoints — **this sprint is the point by which the backend reporting gap flagged in Overall Roadmap must be resolved.** If Sprint 3 used an interim client-side composition, this sprint replaces it with real backend aggregation for both Dashboard and Reports simultaneously, closing out that tech debt.

**Dependencies:** Sprints 4–7 fully complete (Reports has no independent data of its own — it reads everything from the modules built in those sprints), and the backend reporting endpoints.

**Risks:** If the backend reporting gap is not resolved by this point, this sprint is at risk of slipping in its entirety — this should be escalated well before Sprint 8 planning, not discovered at its start.

**Deliverables:** All six live reports plus the Inventory placeholder; Dashboard's KPI data source finalized on real aggregation endpoints if it wasn't already by Sprint 3.

**Acceptance Criteria:**
- Every report's filters, results, Export, and Print function correctly against real data.
- Aging reports correctly bucket by the documented ranges and link through to source Companies/Suppliers.
- Trip Profitability figures match the per-trip Profit tab figures built in Sprint 5 exactly (a direct cross-check, since both derive from the same underlying data).

**Definition of Done:** Acceptance criteria pass; Dashboard KPIs re-verified against the now-final reporting endpoints.

---

## Sprint 9 — Administration

**Sprint Goal:** Ship the low-frequency, high-consequence configuration layer, completing the MVP's full feature scope.

**Estimated Duration:** 2 weeks.

**Features:** Users, Roles & Permissions, Audit Logs, Settings (Company Profile, Numbering, Categories, Tax), Profile, Notification Preferences, Appearance.

**Pages:** `05_PAGE_CATALOG.md` §13–14 in full.

**Components:** The Permissions matrix editor (flagged in Overall Roadmap as the one page-type with no close analog elsewhere in the catalog — expect this to be a genuinely new component built here, not a composition of existing ones, though it should still compose from base `Checkbox`/`Table` primitives per `06_COMPONENT_LIBRARY.md` §19's reuse rule).

**Backend APIs:** Full CRUD for `users`, `roles`; read for `audit_logs`; read/update for tenant `settings`.

**Dependencies:** Sprint 1's auth/permission-loading infrastructure (this sprint builds the *management UI* for roles/permissions; the underlying permission-checking mechanism has been live since Sprint 1, consuming the backend's already-complete RBAC system).

**Risks:** The Permissions matrix must be validated against a live re-check: changing a role's permissions here must be immediately reflected in that role's users' visible Sidebar on next navigation, per `03_INFORMATION_ARCHITECTURE.md` §13 — this cross-cutting effect is easy to build the static UI for and miss the live-propagation requirement.

**Deliverables:** Full Administration and Settings module set. **M4 milestone reached: feature-complete MVP.**

**Acceptance Criteria:**
- User invitation flow works end-to-end including pending-invitation state.
- Editing a role's permissions immediately changes what its users can see/do, verified with a live test (not just a database-state check).
- Audit Logs are genuinely read-only throughout, with correct filtering.
- All Settings forms save correctly and Numbering Settings correctly prevents any renumbering of already-issued records.

**Definition of Done:** Acceptance criteria pass; every page in `05_PAGE_CATALOG.md` is now implemented — cross-check the full catalog against the deployed app as this sprint's closing task.

---

## Sprint 10 — Production Readiness

**Sprint Goal:** Close every quality gate — performance, accessibility, responsiveness, security, documentation — before release, and clear the backlog of tech debt flagged across Sprints 1–9.

**Estimated Duration:** 2 weeks.

**Features:** None new — this sprint hardens what exists.

**Pages/Components:** All of them, audited.

**Backend APIs:** None new; this sprint validates existing integrations under realistic load/data volume.

**Dependencies:** Sprints 1–9 complete.

**Risks:** The temptation to treat this sprint as a buffer for slipped feature work rather than genuine hardening — protect its scope; if Sprints 1–9 slipped, that should extend the timeline, not consume Sprint 10.

**Deliverables:**
- **Performance:** every item in the Performance Plan below audited and passing budget.
- **Accessibility:** full audit against the Accessibility Plan below.
- **Responsive Audit:** every page in `05_PAGE_CATALOG.md` manually verified at Desktop/Laptop/Tablet/Mobile breakpoints.
- **Animations:** motion audit against `02_DESIGN_SYSTEM.md` §14, including reduced-motion verification.
- **Error Handling:** every error category in `06_COMPONENT_LIBRARY.md` §14 deliberately triggered and verified in a staging environment (simulated network failure, simulated 409 conflict, simulated 500).
- **Loading States:** every page's Skeleton verified to match its real content shape.
- **Offline Handling:** the Offline empty-state behavior verified.
- **SEO (where applicable):** correct metadata on the public Login/Forgot-Password pages (the only pages search-engine-relevant in an authenticated B2B tool); `robots` configuration ensuring authenticated routes are never indexable.
- **Documentation:** this document set (01–08) reconciled against the shipped application — any drift discovered during this sprint's audits is corrected in the docs, not left to rot.
- **Bug Fixes:** full backlog triage and closure of all P1/P2 issues.

**Acceptance Criteria:** all items in the Final Release Checklist below are satisfied.

**Definition of Done:** Final Release Checklist fully checked off; production deployment executed per the Deployment Plan below.

---

## Testing Strategy

- **Unit Tests** — every pure calculation function (currency formatting, invoice/purchase-bill totals, trip-catch reconciliation, permission checks) — written in the same sprint the logic is introduced, never deferred to Sprint 10.
- **Component Tests** — every `06_COMPONENT_LIBRARY.md` component, written in Sprint 2 and extended per-feature as feature-specific configurations (Invoice Status, Trip Status) are added.
- **Integration Tests** — one per feature sprint (4–9), covering that sprint's primary create/edit/lifecycle-action flow against a mocked API.
- **E2E Tests** — the three flagged critical journeys (Customer Lifecycle, Supplier Lifecycle, Trip lifecycle), written by the end of Sprints 6, 7, and 5 respectively, plus the Sprint 1 login smoke test — run in CI on every PR from Sprint 1 onward.
- **Accessibility Tests** — automated axe-core-style checks integrated into Component Tests from Sprint 2 onward, plus a manual screen-reader pass in Sprint 10.
- **Visual Regression** — snapshot testing on the Sprint 2 component library (catching unintended visual drift in shared primitives is highest-leverage there) and on the Sprint 8 Reports/Charts (where visual correctness of data is itself a correctness concern).
- **Manual QA** — a full pass through every `05_PAGE_CATALOG.md` page against its documented acceptance criteria in Sprint 10, plus lighter manual verification at the end of every feature sprint.

---

## Performance Plan

- **Lazy Loading** — feature-module and heavy-dependency dynamic imports, applied from Sprint 4 onward as each module ships (`07_FRONTEND_ARCHITECTURE.md` §16, §19).
- **Suspense** — route-level loading boundaries verified per-page as each page ships, not retrofitted in Sprint 10.
- **Caching** — TanStack Query key/invalidation strategy (`07_FRONTEND_ARCHITECTURE.md` §9) implemented per-feature as its mutations are built; audited holistically in Sprint 10 for any over-fetching discovered once the full module set is live together.
- **Memoization** — applied only where Sprint 10's profiling identifies a measured bottleneck, per the "not applied speculatively" principle in `07_FRONTEND_ARCHITECTURE.md` §19.
- **Bundle Optimization** — bundle-size budget checked in CI from Sprint 2 onward (the component library is the highest-risk place for silent bundle bloat); full bundle audit in Sprint 10.
- **Virtualization** — added to the Enterprise Data Table specifically for Invoices, Companies, and Audit Logs once Sprint 10's realistic-data-volume testing confirms it's needed (per the Risk Areas note in Overall Roadmap).
- **Image Optimization** — minimal in MVP scope (no user-uploaded images until the future Documents module); `next/image` configured correctly regardless, in Sprint 1's foundation.

---

## Security Plan

- **Authentication** — HttpOnly-cookie session model, built in Sprint 1, per `07_FRONTEND_ARCHITECTURE.md` §20.
- **Authorization / Permission Checks** — the `usePermission`/`<Can>` mechanism built in Sprint 1, consumed by every feature sprint's button/field/table guards from Sprint 4 onward.
- **Protected Routes** — enforced at the `(authenticated)` layout in Sprint 1; every new route added in Sprints 3–9 inherits this automatically by virtue of the folder structure.
- **Secure Storage** — no sensitive token ever reaches client-side storage, verified as part of Sprint 1's Definition of Done and re-verified in Sprint 10's security pass.
- **API Validation** — the frontend never treats its own validation as sufficient; every feature sprint's acceptance criteria include verifying that server-side validation errors (422/409) map correctly to the UI, confirming the frontend isn't the only line of defense.
- **Sprint 10 Security Review** — a dedicated pass verifying no sensitive data reaches logs/analytics/error-reporting payloads (`07_FRONTEND_ARCHITECTURE.md` §20, §23), and a final confirmation that every lifecycle action (Issue, Post, Allocate, Delete) is truly backend-enforced, not just frontend-hidden.

---

## Accessibility Plan

- **Keyboard Navigation** — verified per-component in Sprint 2, per-page as each page ships in Sprints 3–9, and holistically in Sprint 10.
- **Screen Readers** — a manual screen-reader pass scheduled explicitly in Sprint 10, covering at minimum the Invoice Editor, Allocation Table, and Command Palette as the most interaction-dense surfaces.
- **ARIA** — inherited from Radix primitives by construction (`07_FRONTEND_ARCHITECTURE.md` §21); verified, not (re)implemented, per component in Sprint 2.
- **Focus Management** — verified for every Dialog/Drawer/Popover introduced from Sprint 2 onward, and for route-level navigation focus in Sprint 1.
- **Color Contrast** — audited once at the design-token layer (`02_DESIGN_SYSTEM.md` §3) in Sprint 2, since every component consumes the same tokens; spot-checked again in Sprint 10 for any feature-specific color usage (chart series, status badges) introduced later.
- **Reduced Motion** — verified in Sprint 10 across every animated interaction cataloged in `02_DESIGN_SYSTEM.md` §14.

---

## Deployment Plan

- **Development** — live from Sprint 1, pointed at a shared development backend; every engineer works against real APIs from day one, not a fully-mocked environment, to surface integration issues early.
- **Staging** — stood up by Sprint 3 (needed for the first live-data milestone) and used for every subsequent sprint's demo/review.
- **Production** — first deployed at the end of Sprint 10; earlier sprints do not deploy to production.
- **CI/CD** — configured in Sprint 1: type-check, lint, unit/component tests, and build run on every PR; E2E suite runs on merge to the main integration branch; staging deploys automatically on merge; production deploys are a manual, explicit gate.
- **Build Validation** — the production build itself is a CI gate from Sprint 1 onward, per `07_FRONTEND_ARCHITECTURE.md` §26 — no PR merges on a broken build at any point in the plan, not just at the end.
- **Smoke Testing** — the Sprint 1 login-to-Dashboard E2E test doubles as the production smoke test, re-run immediately post-deploy.
- **Rollback Plan** — production deployment supports immediate rollback to the prior build; the Sprint 10 release runbook documents the exact rollback trigger conditions (smoke test failure, elevated error rate in the first hour) and owner.
- **Monitoring** — error reporting and performance monitoring (`07_FRONTEND_ARCHITECTURE.md` §23) enabled from the first production deploy, not added after the fact.

---

## Project Metrics

Tracked from Sprint 1 onward, reviewed at the end of every sprint:

- **Sprint Velocity** — story points or task count completed vs. planned, tracked to catch the kind of slippage the Risk Areas above call out (Sprint 6's Line Editor, Sprint 9's Permissions matrix) early rather than at sprint-end.
- **Bug Count** — opened vs. closed per sprint, with severity breakdown; a P1 (financial-correctness or security) bug halts new feature work in that module until resolved, regardless of sprint boundary.
- **Coverage** — unit/component/integration test coverage, tracked per feature module, with the calculation-critical code paths (`07_FRONTEND_ARCHITECTURE.md` §22) held to a stricter bar than general UI code.
- **Performance** — Core Web Vitals and route-transition timings, tracked from Sprint 3 (first live-data page) onward.
- **Accessibility Score** — automated axe-core score tracked from Sprint 2 onward.
- **Lighthouse** — run against the Dashboard and Invoice Editor (the two most representative and most complex pages) starting Sprint 3/6 respectively, and against the full page set in Sprint 10.
- **Bundle Size** — tracked in CI from Sprint 2 onward with a defined budget; any PR that grows the bundle past budget requires explicit justification.

---

## Final Release Checklist

- [ ] All Features Complete — every page in `05_PAGE_CATALOG.md` implemented and matches its spec.
- [ ] All APIs Integrated — no page relies on the Sprint 3 interim client-side KPI composition; the backend reporting gap is fully closed.
- [ ] Responsive Verified — every page audited at all four breakpoints per `05_PAGE_CATALOG.md` §16.
- [ ] Accessibility Passed — Accessibility Plan fully executed, automated score at target, manual screen-reader pass complete.
- [ ] Performance Targets Met — Performance Plan budgets satisfied, Lighthouse scores at target across the full page set.
- [ ] Security Review Passed — Security Plan's Sprint 10 review complete, no sensitive data leakage found.
- [ ] Testing Complete — all three E2E critical journeys passing, coverage targets met.
- [ ] Documentation Updated — documents 01–08 reconciled against the shipped application.
- [ ] Production Build Successful — clean production build, zero type/lint errors.
- [ ] Monitoring Enabled — error reporting and performance monitoring live and verified receiving data pre-launch.

---

## Future Roadmap

Explicitly out of scope for this ten-sprint MVP plan, reserved per `01_PRODUCT_VISION.md` §11 and `03_INFORMATION_ARCHITECTURE.md` §15 for post-MVP delivery:

- **Inventory / Warehouse** — extending beyond Trip Catch's available/sold/waste model.
- **OCR** — automated capture for catch slips and supplier bills.
- **PDF Generation** — Invoice/Purchase Bill/Payment receipt documents.
- **Notifications (full)** — email/SMS delivery channels beyond the in-app panel shipped in Sprint 9.
- **Mobile App** — a native shell consuming the same route/permission model per `03_INFORMATION_ARCHITECTURE.md` §15.
- **Analytics (advanced)** — forecasting, customer risk scoring, trend analysis beyond Sprint 8's Reports.
- **Forecasting** — predictive modeling on top of the transactional data captured in the MVP.
- **AI Assistant** — natural-language business queries, per `01_PRODUCT_VISION.md`'s long-term vision.
- **Offline Mode** — genuine offline-capable field data entry, beyond the Sprint 10 Offline *state* (which only handles connectivity-loss gracefully, not offline-first data capture).

Each of these, when scheduled, is expected to follow the same discipline as this plan: architecture/component-catalog updates before implementation, built from existing primitives wherever possible, sequenced by real dependency rather than convenience.

---

## Summary

**Implementation Philosophy:** build the foundation once (Sprints 1–2), then never again — every sprint from 3 onward is pure vertical-slice feature delivery composed from a shared, finished base, exactly as the Implementation Principles require. The plan deliberately front-loads cost (a 3-week component-library sprint before a single business feature ships) because that investment is what makes Sprint 7 possible in 1.5 weeks instead of 3.

**Engineering Standards:** every sprint's Definition of Done inherits the same non-negotiables — type safety, test coverage for calculation logic, accessibility, and permission-guard correctness — from Sprint 1 through Sprint 10, per `01_PRODUCT_VISION.md`'s Definition of Done and `07_FRONTEND_ARCHITECTURE.md`'s engineering standards. Nothing is "quality from Sprint 10" — production quality is the bar from Sprint 1.

**Delivery Strategy:** sequenced by genuine business dependency (Masters before Operations before Finance before Reports before Administration, mirroring `03_INFORMATION_ARCHITECTURE.md` §1's own navigation philosophy) rather than by convenience or team preference, with the one identified cross-team risk — the backend reporting gap — surfaced explicitly and early rather than discovered mid-sprint.

**Long-Term Maintainability:** because every sprint composes from the Sprint 2 component library and the Sprint 1 architecture rather than reinventing patterns, the codebase this plan produces is exactly the one `06_COMPONENT_LIBRARY.md` §20 and `07_FRONTEND_ARCHITECTURE.md` §28 describe — one where the next module, whenever it's scheduled from the Future Roadmap above, is built by following an established pattern, not by starting over.
