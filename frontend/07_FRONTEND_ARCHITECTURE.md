# AquaLedger — Frontend Architecture

**The Definitive Engineering Guide for Building the AquaLedger Frontend**

Version 1.0 · Frontend Engineering Architecture Document

This document specifies how AquaLedger's frontend is engineered — folder structure, state management, data layer, and cross-cutting engineering concerns. It implements `01_PRODUCT_VISION.md` through `06_COMPONENT_LIBRARY.md` in code terms without writing code: every architectural decision here exists to make those five documents buildable by a team, consistently, without engineers each inventing their own conventions.

---

## 1. Frontend Philosophy

- **Feature-First Architecture** — code is organized by business capability (`invoices/`, `trips/`, `suppliers/`) rather than by technical layer (`all-hooks/`, `all-components/`). This mirrors `03_INFORMATION_ARCHITECTURE.md`'s own module-first structure: a developer working on Trips should find everything Trips-related in one place, the same way a user finds everything Trips-related under one sidebar section.
- **Component Reuse** — no page reaches for a bespoke UI element when `06_COMPONENT_LIBRARY.md` already defines one; this is enforced architecturally (a `components/` and `features/*/components/` split, §5–6) as much as by convention.
- **Composition Over Inheritance** — complex UI (the Invoice Editor, the Allocation Table) is built by composing small, single-purpose components per `06_COMPONENT_LIBRARY.md` §17, never through component subclassing or deep prop-driven "god components" that try to handle every case internally.
- **Server as Source of Truth** — the backend owns business state (invoice totals, outstanding balances, permission sets); the frontend never re-derives or locally recomputes anything the backend has already computed and returned, especially financial figures — this directly serves `01_PRODUCT_VISION.md`'s "financial accuracy" principle. Client state exists only for things the server has no opinion on (an open dropdown, a draft form's unsaved keystrokes, the current theme).
- **Type Safety** — every boundary the frontend crosses (API responses, form inputs, route params) is typed and validated, not assumed; a change in the backend's contract should surface as a compile-time or validation-time failure, not a silent runtime bug in a production ERP handling other people's money.
- **Accessibility-First** — the accessibility guarantees in `02_DESIGN_SYSTEM.md` §16 and `06_COMPONENT_LIBRARY.md` §15 are treated as architectural requirements (radix-based primitives, tested keyboard flows), not a pass applied at the end.
- **Performance-First** — this is a tool used for hours a day by high-volume data-entry users (`01_PRODUCT_VISION.md`'s Accountant/Operator personas); performance budgets and patterns (§19) are a first-class architectural concern, not an optimization phase.

---

## 2. Technology Stack

| Technology | Role | Why |
|---|---|---|
| **Next.js 15** | Application framework, routing, rendering | App Router gives nested layouts that map directly onto `03_INFORMATION_ARCHITECTURE.md`'s Sidebar-group structure; Server Components reduce client bundle size for a data-dense app; acts as the BFF layer holding refresh tokens in HttpOnly cookies (per the backend architecture's security model), keeping tokens out of reach of any XSS vector in client JS. |
| **React 19** | UI runtime | Concurrent rendering and Actions reduce the boilerplate around pending/optimistic states that a form-heavy ERP needs constantly (Invoice Editor, Allocation Table). |
| **TypeScript** | Language | Non-negotiable for a financial system — every Decimal-backed money/quantity/rate value, every permission code, every status enum is a typed value, not a stringly-typed guess. |
| **Tailwind CSS v4** | Styling | Utility-first styling implements the design tokens from `02_DESIGN_SYSTEM.md` §19 directly as a config layer, keeping visual consistency enforced by the toolchain rather than by convention alone. |
| **shadcn/ui** | Component primitives | Matches the "new-york"-style, Radix-based component language already established as AquaLedger's visual vocabulary; components are copied into the codebase (not an opaque dependency), which is what makes them safely extensible to the `06_COMPONENT_LIBRARY.md` variants AquaLedger needs (e.g., Currency Input as a specialized Input). |
| **Radix UI** | Unstyled accessible primitives (underlying shadcn/ui) | Gives Dialog/Popover/Dropdown/Tabs correct focus management and ARIA behavior out of the box, satisfying `06_COMPONENT_LIBRARY.md` §15's accessibility defaults without the team re-implementing them. |
| **TanStack Query** | Server-state management | The correct tool for "server is the source of truth" (§1): caching, invalidation, and background refresh for every entity list/detail view, replacing hand-rolled `useEffect` fetching entirely. |
| **React Hook Form** | Form state management | Uncontrolled-by-default performance model suits AquaLedger's largest forms (Invoice/Purchase Bill line-item editors with dozens of fields) without per-keystroke re-renders across the whole form. |
| **Zod** | Schema validation | A single schema definition drives both TypeScript types and runtime validation for every form and API response shape, preventing the type and the validation rule from drifting apart. |
| **Axios** | HTTP client | Interceptor model (§8) gives one place to attach auth headers, handle 401 refresh flows, and normalize error shapes across every API call. |
| **Recharts** | Charting | Matches `02_DESIGN_SYSTEM.md` §11's chosen library; React-native composition model fits the component-composition philosophy in §1. |
| **Lucide React** | Icons | Matches `02_DESIGN_SYSTEM.md` §7's chosen icon system exactly. |
| **date-fns** | Date manipulation | Lightweight, tree-shakeable, immutable-by-default — avoids the footguns of native `Date` mutation in a system where date correctness (invoice due dates, fiscal-year boundaries) has real financial consequences. |
| **clsx** | Conditional className composition | The standard, minimal utility for composing Tailwind classes conditionally (e.g., Status Badge color variants) without ad hoc string concatenation. |

---

## 3. Folder Structure

```
src/
  app/                      # Next.js App Router — routes, layouts, route-level loading/error boundaries
  components/                # Shared, cross-feature UI (the shadcn/ui-based primitives from 06_COMPONENT_LIBRARY.md)
    ui/                       # Base primitives: Button, Input, Card, Dialog, Table, etc.
    layout/                   # App Layout, Sidebar, Top Navigation, Page Header (06_COMPONENT_LIBRARY.md §1)
    data-display/             # Status Badge, KPI Card, Money Display, etc. (§5, §7, §9)
    feedback/                 # Toast, Alert, Empty/Error/Loading states (§8, §12–14)
  features/                  # Feature-first business modules — see §5 for internal shape
    auth/
    dashboard/
    companies/
    suppliers/
    fish/
    boats/
    trips/
    invoices/
    payments/
    purchase-bills/
    supplier-payments/
    reports/
    administration/          # users, roles, audit-logs
    settings/
  hooks/                     # Cross-feature shared hooks only (e.g., useDebounce, useMediaQuery)
  lib/                       # Framework glue: TanStack Query client, Axios instance, Zod helpers
  services/                  # Cross-cutting API clients not owned by one feature (e.g., a shared search service)
  providers/                 # React context providers composed in the root layout (Theme, Auth, Query)
  styles/                    # Tailwind config, design tokens (02_DESIGN_SYSTEM.md §19), global CSS
  types/                     # Shared, cross-feature TypeScript types (API envelope shapes, permission codes)
  config/                    # Environment-driven configuration (API base URL, feature flags)
  utils/                     # Pure, cross-feature utility functions (currency formatting, date formatting)
  constants/                 # Cross-feature constants (status vocabularies, route paths, permission codes)
```

**Placement rule:** anything used by exactly one feature lives inside that feature's own folder (§5); anything used by two or more features is promoted to the top-level shared folders above. This mirrors the reuse-over-duplication rule in `06_COMPONENT_LIBRARY.md` §19 — promotion happens only once a real second usage exists, never speculatively.

---

## 4. App Router Structure

Route groups map directly onto the sidebar/permission structure defined in `03_INFORMATION_ARCHITECTURE.md` §2–3, using Next.js route groups to separate public, authenticated, and layout-distinct sections without affecting the URL shape defined in `03_INFORMATION_ARCHITECTURE.md` §17.

```
app/
  (public)/
    login/
    forgot-password/
    reset-password/
  (authenticated)/                 # wrapped in the App Layout (Sidebar + Top Navigation)
    layout.tsx                      # composes App Layout, resolves auth/permission/tenant context
    dashboard/
    companies/
      page.tsx                      # List
      new/page.tsx                  # Create
      [id]/
        page.tsx                    # Details
        edit/page.tsx                # Edit
    suppliers/ ...                  # identical shape to companies/
    fish/ ...
    boats/ ...
    trips/
      page.tsx
      new/page.tsx
      [id]/
        page.tsx                     # Overview tab (default)
        edit/page.tsx
        catches/
          page.tsx
          new/page.tsx
          [catchId]/edit/page.tsx
        expenses/ ...
        profit/page.tsx
    invoices/ ...                    # identical CRUD shape to companies/, plus lifecycle actions
    payments/ ...
    purchase-bills/ ...
    supplier-payments/ ...
    reports/
      page.tsx
      receivables-aging/page.tsx
      payables-aging/page.tsx
      ...
    users/ ...
    roles/ ...
    audit-logs/ ...
    settings/
      company/page.tsx
      sequences/page.tsx
      categories/page.tsx
    profile/
      page.tsx
      security/page.tsx
  unauthorized/page.tsx             # rendered in place of a route, not linked in nav (03_INFORMATION_ARCHITECTURE.md §2)
  not-found.tsx                     # global 404
  error.tsx                         # global error boundary
  loading.tsx                       # global fallback (rarely hit — route segments define their own below)
```

**Public Routes:** everything under `(public)`, rendered outside the authenticated shell entirely (no Sidebar/Top Navigation), matching `05_PAGE_CATALOG.md` §1's Login/Forgot/Reset specs.

**Protected Routes:** everything under `(authenticated)`; the group's shared `layout.tsx` is the single enforcement point for "must be logged in" — no individual page re-implements this check.

**Nested Layouts:** the Trip detail route's Tabs (Overview/Catches/Expenses/Profit) are implemented as a nested layout at `trips/[id]/layout.tsx` composing the Tabs component (`06_COMPONENT_LIBRARY.md` §2) around the tab-specific child routes, so the Overview Card and Trip status header render once and persist across tab switches rather than remounting.

**Loading Pages:** each route segment with a meaningful data dependency (every List and Detail page) defines its own `loading.tsx` rendering the matching Skeleton variant from `06_COMPONENT_LIBRARY.md` §12, so React Suspense boundaries align exactly with the page-level Loading States defined in `05_PAGE_CATALOG.md`.

**Error Pages:** route-segment `error.tsx` boundaries catch rendering/data errors per segment, rendering the Error State components from `06_COMPONENT_LIBRARY.md` §14 (500/Network/Timeout), with Retry wired to the segment's own re-fetch.

**Not Found Pages:** a route-segment `not-found.tsx` under each `[id]` dynamic segment renders the 404 Not Found spec (`05_PAGE_CATALOG.md` / `06_COMPONENT_LIBRARY.md` §14) when a record ID resolves to nothing, distinct from the global 404 for a genuinely invalid path.

---

## 5. Feature Module Structure

Every entry under `features/` follows the same internal shape, so a developer who has worked in `invoices/` already knows the shape of `trips/`:

```
features/invoices/
  components/        # Feature-owned UI composed from shared components/ — e.g., InvoiceLineEditor,
                      # InvoiceTotalsPanel, InvoiceStatusBadge (a configured Status Badge, per 06 §7)
  hooks/              # Feature-scoped hooks — e.g., useInvoiceQuery, useIssueInvoiceMutation
  services/           # API client functions for this feature's backend module (invoices router)
  schemas/            # Zod schemas — form input schema, API response schema
  types/               # Feature-scoped TypeScript types derived from schemas/
  constants/          # Feature-scoped constants — e.g., INVOICE_STATUS enum/labels/colors
  utils/               # Feature-scoped pure functions — e.g., invoice line-total calculation for
                        # live UI recalculation (mirrors, never overrides, the backend's own calculation)
  pages/               # The page-level components rendered by app/ route files (kept separate from
                        # app/ itself so route files stay thin and pages remain testable in isolation)
```

**Rule:** a feature never imports another feature's `components/`, `hooks/`, or `services/` directly. Cross-feature needs (e.g., Invoices needing a Company Entity Selector) either use a shared `components/` primitive (§3) or, if the need is genuinely domain-specific to Companies, the Companies feature exposes a narrow, explicit public surface (e.g., `features/companies/index.ts` re-exporting just the `CompanySelector` component) rather than reaching into its internals.

---

## 6. Component Architecture

Four tiers, matching `06_COMPONENT_LIBRARY.md`'s own organization:

- **Shared Components (`components/ui`)** — the base primitives (Button, Input, Card, Dialog, Data Table) from `06_COMPONENT_LIBRARY.md` §3–8, §12–14: framework-level, zero business logic, usable by any feature or even outside AquaLedger entirely.
- **Layout Components (`components/layout`)** — App Layout, Sidebar, Top Navigation, Page Header (§1 of the component library): structural, aware of navigation/permission state but not of any single feature's business data.
- **Feature Components (`features/*/components`)** — business-aware composites (Invoice Line Editor, Allocation Table, Trip Catch table) that assemble shared components into the domain-specific patterns cataloged in `06_COMPONENT_LIBRARY.md` §10.
- **Business Components** — a subset of Feature Components that encode business *rules*, not just business *data shapes* — e.g., the component that renders Issue/Post buttons only for the correct status (per `03_INFORMATION_ARCHITECTURE.md` §13) or that blocks over-allocation inline (`04_USER_FLOWS.md` §12). These are deliberately kept as thin as possible around the shared primitives, so a business-rule change touches one small component, not a scattered set of conditionals across a page.

**Atomic Principles:** components compose upward strictly — `ui` components never import from `layout` or `features`; `layout` components never import from `features`; `features` components import from both `ui` and `layout` freely. This one-directional dependency rule is what keeps `components/ui` genuinely reusable and prevents circular coupling as the module count grows (per `03_INFORMATION_ARCHITECTURE.md` §15's expectation of significant future growth).

---

## 7. State Management

State is categorized by *ownership*, not by tool — each category has exactly one correct home:

- **Server State** (invoice data, company lists, permission sets, outstanding balances) — owned by **TanStack Query** exclusively (§9). Never duplicated into component state or a global store; components read it directly from query hooks.
- **Client State** (an open Dropdown, a Command Palette's open/closed state, a table's column-visibility selection) — owned by local component state (`useState`/`useReducer`) or, where genuinely cross-component within one feature, a narrowly-scoped React context. No global client-state library (Redux/Zustand/etc.) is introduced — TanStack Query plus local state covers AquaLedger's actual needs, and adding a global store would duplicate the "single source of truth" TanStack Query already provides for the data that matters most.
- **URL State** (active List page filters, sort, pagination, the current Report's filter combination) — owned by the URL's query parameters, per `03_INFORMATION_ARCHITECTURE.md` §19's "remember filters" requirement — this makes filtered views bookmarkable/shareable as a structural property, not an added feature.
- **Form State** (in-progress Invoice Editor line items, any Create/Edit form) — owned by **React Hook Form**, validated by **Zod** (§12), scoped entirely to the form's lifetime; never lifted into global state.
- **Theme State** (light/dark/system) — owned by a dedicated Theme Provider (§17), persisted to `localStorage`, read via a small hook available anywhere.
- **Authentication State** (current user, permission set, tenant context) — owned by a dedicated Auth Provider (§10) sourced from the session established via the Next.js BFF layer; treated as a special case of Server State (it comes from the backend) but exposed through its own provider/hook rather than a raw TanStack Query hook everywhere, since nearly every component needs to read it and a dedicated hook (`useAuth()`) keeps that ergonomic.

---

## 8. API Layer

A single configured Axios instance (`lib/api-client.ts`) is the only way any feature talks to the backend — no feature ever calls `fetch` or constructs its own HTTP client.

- **Configuration** — base URL from environment config (§26), default headers, timeout tuned to this product's data-entry-heavy interactions (long enough for a large Invoice save, short enough to fail fast on a genuinely dead connection).
- **Interceptors** — a request interceptor attaches the current auth context (via the Next.js BFF-held session, not a client-readable token, per §20); a response interceptor normalizes every backend error response into one consistent internal error shape, so every feature's error handling (§15) works against one predictable structure regardless of which backend module produced it.
- **Error Handling** — the response interceptor classifies errors into the categories defined in `06_COMPONENT_LIBRARY.md` §14 (401, 403, 404, 409, 422, 500, network/timeout) at the transport layer, so feature code never re-implements status-code branching — it receives an already-typed error category.
- **Token Refresh** — handled at the BFF layer (Next.js server-side), not in client-side Axios logic, consistent with the backend architecture's HttpOnly-cookie refresh-token model (§20) — the client never sees or manages a refresh token directly; a 401 from the API triggers a silent server-side refresh attempt, falling back to the Session Expired flow (`04_USER_FLOWS.md` §2) only if that refresh itself fails.
- **Request Cancellation** — every query/mutation is issued with an `AbortController` wired to TanStack Query's built-in cancellation, so navigating away from a page (e.g., leaving a slow-loading Report) cancels its in-flight request rather than letting it resolve into an unmounted component.
- **Retry Policy** — network/timeout/5xx failures retry automatically with backoff, a small, fixed number of times, only for **read** requests (queries); **mutations** (Save, Issue, Post, Allocate) never auto-retry, since retrying a financial write blindly risks duplicate side effects — a failed mutation always surfaces to the user via the Retry action pattern (`04_USER_FLOWS.md` §19), which is an explicit, user-initiated re-attempt, not a silent background one.
- **Pagination Support** — a shared request/response typing convention (page, page size, total count) used identically by every List page's service function, so the Enterprise Data Table (`06_COMPONENT_LIBRARY.md` §6) can be wired to any feature's list endpoint through one consistent contract.

---

## 9. TanStack Query Strategy

- **Query Keys** — a consistent, hierarchical key structure per feature: `['invoices', 'list', filters]`, `['invoices', 'detail', id]`, `['companies', 'list', filters]` — structured so that invalidating `['invoices']` broadly invalidates every invoice-related query, while `['invoices', 'detail', id]` allows surgical invalidation of just one record.
- **Caching** — list queries cache with a moderate stale time (data that's fine to be a few seconds old, like a Companies list); detail queries for records mid-workflow (a draft Invoice being edited) use a shorter or zero stale time, since correctness matters more than cache-hit rate for data actively being worked on.
- **Invalidation** — every mutation declares exactly which query keys it affects and invalidates them on success: issuing an Invoice invalidates that invoice's detail query, the Invoices list, and the parent Company's detail query (its outstanding balance changed) — invalidation lists are explicit per mutation, never a broad "invalidate everything" fallback, so unrelated screens don't unnecessarily refetch.
- **Prefetching** — List pages prefetch the likely-next Detail page's data on row hover/focus where the interaction pattern supports it (e.g., hovering an Invoice row prefetches that invoice), so navigating in feels instant.
- **Background Refresh** — Dashboard KPIs and List pages refetch on window refocus and on a reasonable polling interval where staleness genuinely matters (Dashboard, per `04_USER_FLOWS.md` §3), without disrupting open dropdowns/scroll position (`04_USER_FLOWS.md` §20).
- **Optimistic Updates** — used narrowly, per the rule in `04_USER_FLOWS.md` §20: only for low-stakes, easily-reversible interactions (marking a notification read, a UI-only preference toggle). **Never** for Issue/Post/Allocate/Save on financial records — those always wait for genuine server confirmation, matching the "server as source of truth" principle in §1.
- **Mutations** — every Create/Edit/lifecycle-action (Save, Issue, Post, Allocate, Deactivate) is a typed mutation hook (`useIssueInvoiceMutation`, `useAllocatePaymentMutation`) living in the owning feature's `hooks/`, never an inline `axios.post` call inside a component — this keeps invalidation logic, error handling, and success-Toast behavior consistent and testable in one place per action.

---

## 10. Authentication

Implements the flow specified in `04_USER_FLOWS.md` §2 and the security model implied by the backend's JWT + refresh-token architecture:

```
Not authenticated → (authenticated) layout redirects to /login
        ↓
   Login submits credentials → BFF exchanges for session (HttpOnly cookie)
        ↓
   Auth Provider resolves current user, permission set, tenant context
        ↓
   (authenticated) layout renders App Layout, Sidebar generated from permission set
```

- **JWT** — access/refresh tokens are held server-side by the Next.js BFF in HttpOnly cookies, never exposed to client-side JavaScript — this is the specific architectural reason Next.js (with its server capabilities) was chosen over a pure SPA, per §2, and is the frontend's primary XSS-token-theft mitigation (§20).
- **Protected Routes** — enforced once, at the `(authenticated)` route group's layout (§4), which checks for a valid session before rendering any child route or its data queries.
- **Role Loading / Tenant Loading** — the Auth Provider fetches the current user's role, full permission set, and active tenant context immediately after authentication resolves, before the Dashboard (or any deep-linked destination) renders, matching the Permission-loading → Tenant-loading → Dashboard sequence in `04_USER_FLOWS.md` §2. This data is cached by TanStack Query under a dedicated `['auth', 'session']` key and treated as the single source every permission check (§11) reads from.
- **Logout** — clears the BFF session (server-side cookie invalidation) and all client-side query cache, then redirects to `/login`; per `04_USER_FLOWS.md` §2, a confirmation is shown only when unsaved work is detectable.
- **Session Expiration** — a 401 that survives the Axios interceptor's silent refresh attempt (§8) triggers the Session Expired flow: in-progress form state is preserved client-side (React Hook Form's state isn't cleared, just the mutation is halted) while the user is routed through re-authentication and back.

---

## 11. RBAC

The frontend's permission layer is a **read-only reflection** of the backend's `resource:action` permission-code model (`01_PRODUCT_VISION.md` §10) — it never invents its own looser or stricter permission logic, per that document's explicit warning.

- **Permission Checking** — a single `usePermission('invoice:issue')` hook (and a corresponding `<Can permission="invoice:issue">` component wrapper) is the one mechanism used everywhere a permission gate is needed; it reads from the cached auth-session permission set (§10), never re-derives permission logic from role names.
- **Route Guards** — each route segment under `(authenticated)` declares the permission(s) required to view it; the layout checks this before rendering the segment and redirects to the Unauthorized page (`05_PAGE_CATALOG.md` §1) on failure — this is a defensive check, since the Sidebar (§7 below) already prevents a user from navigating to a page they lack permission for through normal use.
- **Button Guards** — lifecycle-action buttons (Issue, Post, Delete, Allocate) are wrapped in the same `<Can>` component; per `03_INFORMATION_ARCHITECTURE.md` §13, the button is not rendered at all when the permission check fails — never rendered-and-disabled.
- **Field Guards** — individual form fields that only certain roles may edit (rare, but present for select Administration/Settings fields) use the same `usePermission` hook to switch between an editable Input and a read-only Money-Display-style rendering of the same value.
- **Table Action Guards** — Row Actions (`06_COMPONENT_LIBRARY.md` §6) filter their available menu items through the same permission hook, so a Manager's kebab menu on an Invoice row shows only "View," never "Edit"/"Issue," consistent with the read-only role journey in `04_USER_FLOWS.md` §23.
- **Sidebar Generation** — the Sidebar itself (§6/§7) is generated by filtering the full navigation tree against the current permission set at render time, per `03_INFORMATION_ARCHITECTURE.md` §13's "the sidebar is generated from the actual permission set" principle — it is not a static menu with visibility toggles bolted on.

---

## 12. Forms

Every form in AquaLedger — from Create Company to the Invoice Line Editor — follows one pattern: **React Hook Form for state and submission, Zod for schema and validation**, with no exceptions.

- **React Hook Form** — chosen for its uncontrolled-input performance model, essential for AquaLedger's largest forms (an Invoice with dozens of line-item fields) where per-keystroke re-rendering the whole form would be a measurable performance problem.
- **Zod** — each feature's `schemas/` defines one Zod schema per form, which does triple duty: runtime validation, the TypeScript type for the form's values (via inference), and — where the shape matches — the type for the corresponding API payload, keeping the three from drifting apart.
- **Validation** — field-level format validation (GSTIN pattern, email format, currency precision) runs on blur, matching `04_USER_FLOWS.md` §10; cross-field/business-rule validation (over-allocation, catch-quantity reconciliation) runs via Zod's refinement/superRefine capability at submission time, or, for genuinely live-recalculated concerns (Invoice totals), via a dedicated feature `utils/` calculation function driving inline UI feedback rather than a form-validation error.
- **Error Mapping** — server-side validation errors (422 responses, §8/§15) are mapped back onto the exact React Hook Form field they correspond to via a shared `mapServerErrorsToForm()` utility, so a duplicate-GSTIN error from the backend appears as an inline field error identical in presentation to a client-side format error, per `04_USER_FLOWS.md` §4's requirement that these look the same to the user.
- **Reusable Form Fields** — every input in `06_COMPONENT_LIBRARY.md` §4 (Currency Input, Percentage Input, Entity Selector, Date Picker, etc.) has exactly one React-Hook-Form-integrated implementation in `components/ui`, used identically across every feature's forms — a feature never wraps its own bespoke version of Currency Input.

---

## 13. Tables

A single **Enterprise Data Table** component (`06_COMPONENT_LIBRARY.md` §6) underlies every List page and every Related Records sub-table; feature code supplies only its **column definitions** and **data source**, never a bespoke table implementation.

- **Columns** — each feature declares a typed column-definition array (accessor, header label, cell renderer — e.g., Status Badge for a status column, Money Display for an amount column) matching the exact column lists specified per module in `05_PAGE_CATALOG.md`.
- **Sorting** — server-side for List pages backed by paginated API endpoints (sorting a full Invoices list client-side would require fetching every invoice); the table component sends the active sort as a query parameter and TanStack Query re-fetches, matching the URL-State pattern in §7.
- **Filtering** — likewise server-side for List pages, driven by the Toolbar/Filter Panel components (`06_COMPONENT_LIBRARY.md` §6) reading/writing URL query parameters directly.
- **Pagination** — server-side, standard page/page-size parameters per §8's shared pagination contract, never client-side "load more" pseudo-pagination for financially significant lists.
- **Selection** — an opt-in table feature (checkbox column) enabled only for entities with a real Bulk Action defined, per `06_COMPONENT_LIBRARY.md` §6's explicit "avoid when no bulk action exists" guidance.
- **Bulk Actions** — implemented as a feature-level action set passed into the table, replacing the Toolbar with a contextual action bar when selection is active, per the same component spec.

---

## 14. Charts

A thin **Chart Wrapper** layer sits between Recharts and every feature that renders a chart, so no feature configures Recharts' lower-level API directly.

- **Reusable Chart Wrappers** — one wrapper per chart type used in `06_COMPONENT_LIBRARY.md` §11 (Line, Bar, Area, Pie/Donut, Sparkline), each accepting simple, typed data-plus-config props and internally applying AquaLedger's series-color mapping, axis formatting, and tooltip styling — a feature never hand-configures a Recharts `<XAxis>`/`<Tooltip>` directly.
- **Themes** — wrappers read the current theme (§17) and apply the light/dark-tuned palette described in `02_DESIGN_SYSTEM.md` §17 automatically; a chart never needs feature-level theme-awareness code.
- **Responsive Charts** — every wrapper is built on Recharts' `ResponsiveContainer` internally, so charts resize correctly within their Card/Grid container at every breakpoint without feature-level responsive logic.
- **Loading** — the Chart Skeleton (`06_COMPONENT_LIBRARY.md` §12) renders while chart data is loading, matching the wrapper's own loading prop rather than each feature building its own placeholder.
- **Empty** — an explicit "no data for this period/filter" empty variant, distinct from a loading or error state, shown when a query resolves successfully but returns no data points.

---

## 15. Error Handling

Error handling is layered, matching the categories in `06_COMPONENT_LIBRARY.md` §14 and `04_USER_FLOWS.md` §19:

- **API Errors** — classified once by the Axios response interceptor (§8) into a consistent internal error type carrying a category (`validation | permission | conflict | not_found | server | network`) and, for validation errors, a field-error map.
- **Validation Errors (422)** — routed through the Forms error-mapping utility (§12) to the offending field(s); never shown as a generic page-level Alert if a field-level home exists for them.
- **Network Errors** — surfaced via a shared `<ErrorState variant="network">` component with Retry, at the smallest boundary that can meaningfully retry (a section, not always the whole page).
- **Conflict Errors (409)** — surfaced as an inline message at the specific action that conflicted (e.g., an Allocation Table row), paired with an automatic silent re-fetch of the affected query so the user is looking at current state before retrying, per `04_USER_FLOWS.md` §19.
- **404** — handled at the route level via each `[id]` segment's `not-found.tsx` (§4), not via a generic in-component check.
- **500** — surfaced via the nearest `error.tsx` route boundary (§4), rendering the generic Server Error state with Retry and an optional trace identifier, never raw error/stack detail.
- **Retry** — a single shared `<RetryableError>` pattern wraps Network/Timeout/Server error presentations, re-invoking the exact failed query/mutation on click, consistent everywhere it appears per `06_COMPONENT_LIBRARY.md` §14.

---

## 16. Loading Strategy

- **Skeletons** — every route segment with a data dependency defines a `loading.tsx` (§4) rendering the matching Skeleton (`06_COMPONENT_LIBRARY.md` §12); Suspense boundaries are placed at the same granularity as the Loading States defined in `05_PAGE_CATALOG.md` (e.g., the Dashboard's independently-loading sections each get their own boundary, not one page-wide spinner).
- **Lazy Loading** — feature modules and heavy dependencies (the Recharts wrapper bundle, a future rich-text editor for Notes) are dynamically imported (`next/dynamic`) so their code is not part of the initial bundle for users who never touch that feature.
- **Suspense** — used as the standard mechanism for data-dependent loading states throughout, in place of manual `isLoading` boolean checks scattered through component trees, keeping loading UI declarative and colocated with the route structure rather than duplicated per component.
- **Code Splitting** — route-based splitting is automatic via the App Router (§4); additional manual splitting is applied to genuinely large, infrequently-used surfaces (the Command Palette's full entity-search index, Report-specific chart configurations) so the common data-entry path (Invoice creation, Trip logging) stays as lean as possible.

---

## 17. Theming

- **Dark Mode / Light Mode / System Mode** — implemented via a `next-themes`-style Theme Provider wrapping the root layout, applying a `data-theme` attribute consumed by the Tailwind token layer (`02_DESIGN_SYSTEM.md` §3, §17); System Mode follows the OS-level `prefers-color-scheme` media query and updates live if the OS setting changes mid-session.
- **Theme Persistence** — the user's explicit choice (light/dark/system) is persisted to `localStorage` and re-applied on load before first paint (via a small inline script in the root layout) to avoid a flash of the wrong theme — a correctness detail that matters for a tool used in long working sessions per `02_DESIGN_SYSTEM.md` §17.
- **Duplication with Appearance Settings** — the topbar theme toggle and the Appearance settings page (`05_PAGE_CATALOG.md` §14) both read/write the same underlying Theme Provider state; there is exactly one source of truth for the current theme, surfaced through two entry points.

---

## 18. Internationalization

AquaLedger's frontend MVP targets a single locale (India-based seafood trade), but formatting is architected for future localization rather than hard-coded inline:

- **Date Formatting** — all dates render through a single shared `formatDate()` utility (built on date-fns) rather than ad hoc formatting per component, so a future locale change is a one-place update.
- **Currency Formatting** — all money values render through the Money Display component (`06_COMPONENT_LIBRARY.md` §9), itself backed by a shared `formatCurrency()` utility that enforces the backend's exact `NUMERIC(14,2)` decimal precision and the tenant's configured currency symbol/placement (`05_PAGE_CATALOG.md` §14 Business Settings) — never a raw `toFixed(2)` scattered through feature code.
- **Number Formatting** — quantities and rates likewise route through shared formatters matching the backend's weight/rate precision (`NUMERIC(12,3)` / `NUMERIC(12,4)`), always rendered with tabular numerals per `02_DESIGN_SYSTEM.md` §4.
- **Timezone Strategy** — all timestamps are stored and transmitted in UTC by the backend and converted to the tenant's configured timezone only at display time via the shared date-formatting utility, never stored or compared in local time client-side, to avoid the class of bugs where a trip's or invoice's "date" shifts depending on the viewer's machine.
- **Future Localization Support** — because every user-facing string in every feature is expected to flow through the component library rather than being hand-written inline per page, introducing an i18n string-catalog layer later is a mechanical migration (wrapping existing strings) rather than a structural rewrite — this is architected for, not built, in the MVP.

---

## 19. Performance

- **Memoization** — applied deliberately, not reflexively: expensive derived calculations (Invoice line-total recalculation across dozens of rows, chart data transforms) are memoized; simple presentational components are not wrapped in `memo` by default, since React 19's compiler-assisted optimization reduces the need for manual memoization boilerplate — manual memoization is reserved for measured bottlenecks, not applied speculatively everywhere.
- **Lazy Loading** — see §16; applied at the feature/route level as the primary lever, since AquaLedger's module count (§4) makes route-based splitting the highest-leverage performance decision available.
- **Virtualization** — applied to the Enterprise Data Table (§13) once a list's row count crosses a threshold where full DOM rendering becomes the bottleneck (e.g., a large Audit Log or Invoice history) — implemented as an opt-in table mode, not a universal default, since most of AquaLedger's paginated lists (page size ~50) never need it.
- **Image Optimization** — `next/image` used for any raster assets (future tenant logos, future document/receipt attachments), with responsive sizing and lazy loading below the fold by default.
- **Bundle Splitting** — enforced by the folder structure itself (§3): feature isolation means a feature's code is naturally split at the route boundary; shared `components/ui` stays small and framework-adjacent so it doesn't become a hidden monolith imported everywhere.
- **Dynamic Imports** — used for genuinely heavy, conditionally-needed code: the Command Palette's full cross-entity search logic, the Recharts wrapper bundle (only needed on Dashboard/Reports), and any future OCR/file-processing client code.

---

## 20. Security

- **JWT Storage Strategy** — access and refresh tokens never touch client-side JavaScript or `localStorage`/`sessionStorage`; they are held exclusively in HttpOnly, Secure, SameSite cookies managed by the Next.js server layer, per the backend architecture's explicit design goal of eliminating XSS-based token theft (§2, §10). The client only ever holds a lightweight, non-sensitive session indicator.
- **XSS Protection** — React's default escaping is relied upon for all rendered content; `dangerouslySetInnerHTML` is not used anywhere in the current feature set (there is no rich-text/HTML-rendering requirement in the MVP) — if a future feature (e.g., rich Notes) requires it, content is sanitized server-side before ever reaching the client, never trusted raw.
- **CSRF Considerations** — mitigated structurally by the BFF cookie model (SameSite cookies plus the Next.js server layer mediating all backend calls) rather than requiring per-request CSRF tokens threaded through every feature's mutation calls.
- **Permission Validation** — the frontend's RBAC layer (§11) is explicitly a UX convenience, never a security boundary — every permission-gated action is re-validated by the backend on every request, matching `01_PRODUCT_VISION.md` §10's "never trust frontend validation" architecture rule; the frontend hiding a button is about not confusing users with actions they can't complete, not about actually preventing the request.
- **Sensitive Data Handling** — no financial or personally-identifying data is logged to the browser console or to any client-side analytics payload (§23); error-reporting integrations are configured to scrub request/response bodies of monetary and identity fields before transmission.

---

## 21. Accessibility

The frontend's accessibility implementation is the direct execution of the standards already defined in `02_DESIGN_SYSTEM.md` §16 and `06_COMPONENT_LIBRARY.md` §15 — this section states the *engineering* mechanism, not new rules:

- **Keyboard Navigation** — guaranteed structurally by building on Radix UI primitives (§2) for every interactive composite (Dialog, Dropdown, Tabs, Combobox), rather than hand-rolling keyboard handling per component.
- **ARIA** — Radix primitives supply correct ARIA roles/states by default; feature code is responsible only for supplying correct labels/descriptions (e.g., an Invoice's Status Badge `aria-label`), not for implementing ARIA mechanics from scratch.
- **Focus Management** — Radix's built-in focus-trap and focus-return behavior handles Dialogs/Drawers/Popovers automatically; route-level navigation focus (moving to the new page's heading on navigation) is handled by a small shared layout-level effect.
- **Screen Readers** — dynamic announcements (Toast appearing, inline validation firing) use a shared ARIA-live-region utility rather than each feature implementing its own announcement mechanism.
- **Color Contrast** — enforced at the design-token layer (§17, `02_DESIGN_SYSTEM.md` §3) — because every component consumes tokens rather than ad hoc colors, a contrast audit of the token set covers the entire application at once.

---

## 22. Testing Strategy

- **Unit Tests** — pure functions in `utils/` and feature `utils/` (currency formatting, invoice line-total calculation, permission-check logic) — the highest-value, cheapest tests in the suite, and mandatory for anything touching financial calculation, per `01_PRODUCT_VISION.md`'s testing rule that "critical calculations must always be tested."
- **Component Tests** — shared `components/ui` primitives and feature components tested in isolation (rendering, interaction, accessibility assertions) with mocked data, ensuring `06_COMPONENT_LIBRARY.md`'s documented states (loading/empty/error/disabled) are all genuinely implemented, not just specified.
- **Integration Tests** — feature-level flows exercising a page against a mocked API layer (§22's Mocking Strategy below) — e.g., "filling the Invoice Editor and clicking Issue shows the confirmation dialog and, on confirm, calls the issue mutation with the correct payload."
- **E2E Tests** — a focused set of true end-to-end tests (real or near-real backend) covering the highest-stakes user journeys verbatim from `04_USER_FLOWS.md`: the full Customer Lifecycle (create → issue → pay → allocate → cleared), the full Supplier Lifecycle, and the Trip → Catch → Expense → Profit flow — not an attempt to E2E-test every page, which is what Component/Integration tests are for.
- **Mocking Strategy** — API responses are mocked at the network layer (an MSW-style service-worker mock) rather than by mocking individual service functions, so tests exercise the real Axios/TanStack Query stack (§8–9) and catch integration bugs that function-level mocking would hide; mock data fixtures live alongside each feature's tests and mirror the backend's actual response shapes.

---

## 23. Logging & Monitoring

- **Frontend Logging** — a thin, environment-aware logging utility (`lib/logger.ts`) replaces raw `console.log` usage throughout the codebase, so logging verbosity and destination (console in development, a monitoring service in production) are controlled centrally.
- **Error Reporting** — uncaught errors reaching a route-level `error.tsx` boundary (§4, §15) are automatically reported to an error-tracking service with enough context (route, user role, non-sensitive request metadata) to reproduce the issue, scrubbed per §20's sensitive-data rule.
- **Performance Monitoring** — Core Web Vitals and route-transition timings are captured via Next.js's built-in reporting hooks, with particular attention to the interactions this product's own principles flag as performance-critical (`01_PRODUCT_VISION.md` §7, §12): Invoice Editor line-item entry responsiveness, List page load time under realistic data volume.
- **Analytics Placeholders** — the architecture reserves a single, centralized analytics-event utility (currently a no-op/console-only implementation) that features call for significant business events (invoice issued, trip settled), so a real analytics provider can be wired in later without touching feature code — consistent with `01_PRODUCT_VISION.md` §11 not building analytics ahead of the operational core.

---

## 24. Coding Standards

- **Naming Conventions** — components in `PascalCase`; hooks in `camelCase` prefixed `use`; utility functions in `camelCase`; constants in `SCREAMING_SNAKE_CASE`; types/interfaces in `PascalCase` (no `I`-prefix convention). Naming for anything user-facing (a component representing "Invoice Status") matches the canonical name in `06_COMPONENT_LIBRARY.md` §18 exactly — `InvoiceStatusBadge`, never `StatusChip` or `InvoiceStateTag`.
- **File Naming** — component files match their default export's `PascalCase` name (`InvoiceLineEditor.tsx`); hook files `camelCase` (`useIssueInvoiceMutation.ts`); everything else `kebab-case` (`format-currency.ts`).
- **Folder Naming** — always `kebab-case` (`purchase-bills/`, `supplier-payments/`), matching the URL segment naming convention in `03_INFORMATION_ARCHITECTURE.md` §17 exactly, so a feature's folder name and its route are visually identical.
- **Import Order** — a fixed, lint-enforced order: (1) external packages, (2) shared `components/`/`hooks/`/`lib/`/`utils/`, (3) feature-local imports, (4) relative imports, (5) type-only imports — enforced by tooling, not code review discretion.
- **Hooks Rules** — standard React Rules of Hooks enforced via lint; feature hooks never call another feature's hooks directly (only shared hooks or their own feature's), per the feature-isolation rule in §5.
- **Component Rules** — one component per file; props typed explicitly (no implicit `any`); a component that grows business logic beyond simple composition is a signal to extract that logic into a feature hook (§5), keeping components focused on rendering.

---

## 25. Git Strategy

- **Feature Branches** — one branch per feature-module or page slice (mirroring the sprint-based delivery pattern already used for the backend — e.g., a `frontend/invoices-module` branch), branched from `main`, never worked on directly on `main`.
- **Commit Conventions** — Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `chore:`) scoped to the feature touched where useful (`feat(invoices): add line item editor`), matching the clarity expected of a system that will eventually need a readable history for a financial-software audit trail.
- **Pull Request Guidelines** — a PR corresponds to one coherent unit of work (one feature's List+Detail pages, not a sprawling multi-module change); PR descriptions reference the relevant page(s) from `05_PAGE_CATALOG.md` and confirm which document(s) (01–07) the change implements, so reviewers can check against the specification rather than against the author's memory of it.
- **Code Review Checklist** — every PR is checked against: does it introduce a new component when `06_COMPONENT_LIBRARY.md` already has one (§19 of that document)? Does it reuse the shared Data Table/Form/Chart patterns (§13–14 here) rather than a bespoke implementation? Are permission gates applied per §11? Are loading/empty/error states implemented per the page's `05_PAGE_CATALOG.md` spec? Is there a test for any new calculation logic?

---

## 26. Build & Deployment

- **Environment Variables** — a strict, validated (Zod-parsed) environment schema (`config/env.ts`) fails fast at build/start time if a required variable is missing, rather than surfacing as a runtime `undefined` deep in a feature; variables are namespaced by concern (API base URL, auth/session secrets held server-side only, feature-flag toggles).
- **Development** — local development points at a local or shared development backend instance; hot-reload via Next.js dev server; mocked API mode (§22) available for frontend-only work when the backend isn't running.
- **Staging** — a tenant-isolated staging environment mirroring production configuration, used for pre-release validation of each module against real (non-production) data volumes, particularly for performance-sensitive surfaces (large Invoice lists, the Dashboard).
- **Production** — built via Next.js's standard production build (static optimization where routes allow it, server rendering for authenticated/data-dependent routes), deployed behind the same environment-variable validation as staging with production-scoped secrets.
- **Build Process** — CI runs type-checking, linting, unit/component tests, and a production build on every PR before merge; the build itself is treated as a gate — a change that doesn't type-check or doesn't build cleanly is never merged, consistent with `01_PRODUCT_VISION.md`'s "no type errors" Definition-of-Done rule.

---

## 27. Scalability Guidelines

- **Adding New Modules** — a new business module (e.g., a future Documents module per `01_PRODUCT_VISION.md` §11) gets a new `features/{module}/` folder following the exact shape in §5, a new route segment under `app/(authenticated)/` following §4's pattern, a new entry in `03_INFORMATION_ARCHITECTURE.md`'s reserved navigation slots (§15 of that document), and new page specs added to `05_PAGE_CATALOG.md` before implementation begins — architecture documentation is updated *before* code, not after, so this document set stays authoritative rather than drifting from reality.
- **Adding New Pages** — every new page is built from the List/Detail/Form templates in `05_PAGE_CATALOG.md` §0 and composed exclusively from existing `06_COMPONENT_LIBRARY.md` components wherever possible (§6 of this document, §19 of the component library) — a new page is very rarely an excuse to introduce new UI patterns.
- **Adding New APIs** — a new backend endpoint gets one new function in the owning feature's `services/`, one new (or extended) TanStack Query hook in that feature's `hooks/` following the query-key conventions in §9, and, if it returns a new shape, a new Zod schema in that feature's `schemas/` — never a raw inline Axios call inside a component.
- **Adding New Components** — governed entirely by the decision rule in `06_COMPONENT_LIBRARY.md` §19: reuse or configure an existing component first; a genuinely new component is added to the correct tier in §6 of this document (shared/layout/feature/business) and documented in `06_COMPONENT_LIBRARY.md` before or alongside its implementation, so the component catalog never falls out of sync with what actually exists in `components/`.

---

## 28. Summary

This architecture translates six documents of product, design, and UX specification into an engineering structure with exactly one correct place for everything: one folder shape per feature (§5), one state-management home per kind of state (§7), one table implementation (§13), one form pattern (§12), one permission-checking mechanism (§11). That singularity is the whole point — it is what makes the system **maintainable** (a bug or improvement in Currency Input, the Allocation Table, or the RBAC hook fixes or improves every place it's used, simultaneously) and **scalable** (§27's guidelines make adding the next module a matter of following an established pattern, not inventing a new one).

It also makes the system a good one to work in: a **developer experience** where the folder you're in tells you what conventions apply, where "is there already a component for this" has a single place to check (`06_COMPONENT_LIBRARY.md`), and where the specification documents (01–06) and the code they produce stay in lockstep because the architecture itself — feature-first folders mirroring the Information Architecture, component tiers mirroring the Component Library, route structure mirroring the Page Catalog — makes drifting apart the harder path, not the easier one.
