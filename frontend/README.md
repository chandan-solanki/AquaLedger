# AquaLedger Frontend

The Next.js 15 frontend for AquaLedger — an ERP for the seafood trading industry. See the numbered planning documents in this directory (`01_PRODUCT_VISION.md` through `08_FRONTEND_IMPLEMENTATION_PLAN.md`) for the product, design, and architecture specification this codebase implements.

## Stack

Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS v4 · shadcn/ui (New York, Slate) · TanStack Query · TanStack Table v8 · Axios · React Hook Form + Zod · Recharts · next-themes · Sonner

## Prerequisites

- Node.js 20+
- The AquaLedger backend running locally (see `../backend`) or a reachable API URL

## Setup

```bash
npm install
cp .env.example .env.local   # then fill in real values
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Commands

| Command | Description |
|---|---|
| `npm run dev` | Start the dev server (Turbopack, hot reload) |
| `npm run build` | Production build — also runs type-checking and linting |
| `npm run start` | Start the production server (run `build` first) |
| `npm run lint` | Run ESLint |
| `npm run type-check` | Run the TypeScript compiler in `--noEmit` mode |

## Environment Variables

See `.env.example` for the full list with descriptions. Required:

- `NEXT_PUBLIC_API_URL` — base URL of the backend API, including the `/api/v1` prefix.
- `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_APP_ENV` — app identity/environment.

Environment variables are validated at server startup via `src/config/env.ts` (Zod schema, wired through `src/instrumentation.ts`) — the server refuses to start if a required variable is missing or invalid, rather than failing silently deep in a feature.

## Folder Structure

Follows `07_FRONTEND_ARCHITECTURE.md` §3 — feature-first, with a small set of shared top-level layers:

```
src/
  app/              # Next.js App Router — routes, layouts
  components/
    ui/               # shadcn/ui primitives (Button, Card, Input, Label, Sidebar, Popover, Command, Calendar, Switch, ...)
    layout/           # App Layout, Sidebar, Top Navigation, Breadcrumbs, Page Header — see "Application Shell" below
    data-display/     # MetricCard, TrendMetricCard, SummaryGrid, InfoCard, KeyValueList, DescriptionList
    feedback/         # Empty/Error/Offline states, Skeletons, Dialogs
    templates/        # List/Detail/Form/Settings/Report page templates — see "Page Templates" above
    data-table/       # Enterprise Data Table (Sprint 2, Session 1) — see below
    form/             # Enterprise Form Components (Sprint 2, Session 2) — see below
    filters/          # Filtering & Search System (Sprint 2, Session 3) — see below
    pagination/       # Pagination primitives (Sprint 2, Session 3) — see below
    charts/           # Charts + KPI/Trend cards (Sprint 2, Session 4) — see below
    reports/          # Report page building blocks (Sprint 2, Session 4) — see below
    dashboard/        # Dashboard grid + widgets (Sprint 2, Session 4) — see below
  features/
    auth/             # Login, session, permissions — see "Authentication" below
    # companies, invoices, trips, ... — empty until Sprint 4+
  hooks/            # Cross-feature shared hooks
  lib/              # Framework glue: api-client.ts (Axios), query-client.ts (TanStack Query), utils.ts (cn)
  services/         # Cross-cutting API clients not owned by one feature
  providers/        # React context providers composed in the root layout
  styles/           # Reserved for future non-global stylesheets
  types/            # Shared, cross-feature TypeScript types (API envelope/error shapes)
  config/           # Environment-driven configuration (env.ts)
  utils/            # Pure, cross-feature utility functions (formatting, permissions placeholder)
  constants/        # Cross-feature constants (storage keys, app config)
  schemas/          # Reserved for cross-feature Zod schemas
  assets/           # Reserved for imported static assets
```

`public/` (at the project root) holds assets served directly, per Next.js convention.

**Placement rule:** anything used by exactly one feature lives inside that feature's own folder; anything used by two or more is promoted to the shared folders above.

## Authentication

Full BFF (Backend-for-Frontend) pattern, per `07_FRONTEND_ARCHITECTURE.md` §10/§20 — **not** plain client-side token storage. The browser never holds an access or refresh token in JS-reachable storage; both live in `HttpOnly`, `Secure` (in production), `SameSite=Strict` cookies that only the Next.js server can read. This is the specific, documented reason Next.js was chosen over a pure SPA, and it's the primary XSS-token-theft mitigation for a system handling other people's money.

**Flow:**

```
Browser                     Next.js (BFF)                    FastAPI backend
   │  POST /api/auth/login  │                                    │
   ├────────────────────────▶  reads email/password              │
   │                        ├───────────────────────────────────▶ POST /auth/login
   │                        │◀─────────────────────────────────── {access, refresh, user}
   │                        │  sets al_access_token,               │
   │                        │  al_refresh_token as HttpOnly cookies│
   │◀──────────────────────── { user }  (tokens never leave here)  │
```

- **Route handlers** (`src/app/api/auth/{login,logout,session}/route.ts`) are the *only* code that talks to the real backend for auth — everything funnels through `src/lib/auth/backend-auth-client.ts` (one place, no duplicated request logic).
- **Session resolution** (`src/lib/auth/server-session.ts`'s `resolveSession()`) tries the access-token cookie first, and on a 401 falls back to a silent refresh (rotating the refresh token) before giving up — verified live against the real backend, including rotation.
- **Client side**, `src/features/auth/services/auth-service.ts` talks only to the BFF's own `/api/auth/*` routes (never the FastAPI backend directly — the browser has no token to attach). `src/features/auth/context/auth-context.tsx` wraps this in a TanStack Query-backed `AuthProvider`, exposed via `useAuth()` / `useCurrentUser()` / `useTenant()` / `usePermissions()`.
- **Session expiry**: any query in the cache failing with an `unauthorized` `ApiError` (not just the session query) triggers a global handler — clears the session, shows a toast, redirects to `/login` — so this will apply automatically to business queries once Sprint 3+ wires them up.
- **Route protection** is layered: `src/middleware.ts` is a fast, cookie-*presence*-only pre-filter (redirects before the app shell even loads); the authoritative check is `AuthGuard` (`src/features/auth/components/auth-guard.tsx`), rendered from `(authenticated)/layout.tsx`, backed by the real session query (which has already attempted a refresh). Middleware can't perform the authoritative check itself — Next.js only allows cookie *writes* (needed for refresh rotation) from Route Handlers/Server Actions, not from a Server Component render.
- **Permissions** are a read-only reflection of the backend's `resource:action` codes (`src/utils/permissions.ts`, pure functions; `usePermissions()` binds them to the current user) — never a security boundary on their own, since the backend re-validates every gated action regardless.

**Deviation from the session brief:** the brief described "token storage using Session 1's storage utilities," which implies `localStorage`. That would contradict `07_FRONTEND_ARCHITECTURE.md` §10/§20's explicit, detailed HttpOnly-cookie requirement, so the architecture doc won — Session 1's `STORAGE_KEYS` is used only for the non-sensitive "remember me" flag, never for a token.

## Application Shell & Navigation

The authenticated app shell (`src/components/layout/`) composes shadcn/ui's own Sidebar primitive (`src/components/ui/sidebar.tsx`) rather than a hand-rolled one — it already provides the icon-rail collapse, the mobile Sheet-based drawer, full keyboard/ARIA support, and cookie-persisted collapse state (`sidebar_state`), matching `06_COMPONENT_LIBRARY.md` §1 and `03_INFORMATION_ARCHITECTURE.md` §3/§14/§19 without reinventing any of it.

- **`AppLayout`** (`app-layout.tsx`) — a Server Component: reads the `sidebar_state` cookie and passes it as `SidebarProvider`'s `defaultOpen`, so the correct expanded/collapsed state renders on first paint (no flash). Composes `AppSidebar` + `AppHeader` + a scroll region (`SidebarInset` fixed-height with the header outside the scrolling div, so header and sidebar never scroll with page content).
- **`AppSidebar`** — renders `SidebarBrand`, then the navigation tree (`src/config/navigation.ts`) filtered through `filterNavigation()` (`src/utils/filter-navigation.ts`), and a footer with a placeholder Help & Support entry.
- **`AppHeader`** — sidebar trigger, Search placeholder (toast), Notifications placeholder (toast), `ThemeSwitcher`, `UserMenu`. Deliberately has **no breadcrumb** — per `06_COMPONENT_LIBRARY.md` §1's Top Navigation content list and `02_DESIGN_SYSTEM.md` §12, breadcrumbs belong to each page's own `PageHeader`, not the persistent topbar.
- **`Breadcrumbs`** — derives the chain purely from the current pathname matched against the static nav config (no business API calls, per this session's scope): no-ops on the Dashboard and on bare List pages (both per `03_INFORMATION_ARCHITECTURE.md` §7's explicit rules), resolves `new` to "New {Singular}" via each nav item's `singular` field, and resolves `edit` to "Edit". A Detail page's dynamic `{id}` segment needs the entity's real name (never a raw ID) — that's the owning page's job once it fetches data (Sprint 4+), not this component's.
- **Navigation config** (`src/config/navigation.ts`) — one static `NAVIGATION` tree (id, title, icon, href, permission, children) matching `03_INFORMATION_ARCHITECTURE.md` §2's seven groups exactly; `permission` on a leaf is a single code or (for Reports) an array meaning "any of." Nothing renders navigation ad hoc from a component — every menu reads this one source.
- **Permission-aware filtering** (`filterNavigation()`) — reuses Session 2's `hasPermission`/`hasAnyPermission`. A leaf is dropped if the user lacks its permission; a group is dropped only if *none* of its children survive, per §3's "group visible to any role with at least one accessible child" rule. Hidden, never disabled.
- **`PageHeader`** / **`PageContainer`** — the reusable per-page primitives (`06_COMPONENT_LIBRARY.md` §1: Page Header, Content Container) that future List/Detail/Form pages compose; `PageHeader` renders `Breadcrumbs` internally so pages never need to think about suppressing it.

**Known simplification:** `03_INFORMATION_ARCHITECTURE.md` §3 describes some groups (e.g. Finance) as default-expanded only for certain roles and collapsed for others (e.g. Administration always collapsed). This session renders every visible group always-expanded — no per-group accordion state — since that finer behavior wasn't in the explicit task list and would need its own persisted state design; noted as a candidate for a later session.

**Deviation:** the breadcrumb examples in `03_INFORMATION_ARCHITECTURE.md` §7 are inconsistent about whether a sidebar group name (e.g. "Administration") appears in the chain — most examples (Companies, Purchase Bills, Trips, Invoices) omit their group, one (Roles under Administration) includes it. The four numbered rules in that section never mention including the group at all, so this implementation omits it consistently everywhere, treating the one example as the outlier.

## Global UX Infrastructure

The shared, business-logic-free UX layer every future page/module builds on — `src/components/feedback/` (Skeletons, Empty/Error states, Dialogs), `src/lib/toast.ts`, `src/hooks/` (async/error handling), and a handful of additions to `src/components/layout/`. None of it is wired to real business data yet — it's the reusable substrate Sprint 4+ modules will consume.

**Loading strategy** (`06_COMPONENT_LIBRARY.md` §12): two layers, used for different things —
- **Route-level (`loading.tsx`)** — Next.js auto-wraps a segment's `children` in Suspense with this fallback during navigation. `src/app/(authenticated)/loading.tsx` covers every authenticated page: because the fallback only wraps `(authenticated)/layout.tsx`'s `children` slot, the Sidebar/Header shell rendered by that layout stays mounted and visible — only the content area shows a skeleton. It defaults to `PageSkeleton variant="list"`; an individual future route can drop its own `loading.tsx` with a more specific variant.
- **Section-level (`LoadingWrapper`)** — a plain `<Suspense>` wrapper for a part of an already-rendered page that loads independently of the rest (e.g. a slow-loading chart beside an otherwise-ready page). Not consumed by anything yet, since no page has independently-loading sections this session — reserved for Sprint 3+/4+.

**Deliberately not added: a true root `src/app/loading.tsx`.** It was built and then removed after live verification caught a real regression: it would only ever govern two routes — `app/page.tsx` (a pure `redirect()`, no visible content of its own) and the static `not-found.tsx` (which never suspends) — and empirically, adding a Suspense boundary above `app/page.tsx` changes how Next.js's App Router handles the `redirect()` inside it: instead of the clean `307` Session 3 specifically fixed (`app/page.tsx`'s `export const dynamic = "force-dynamic"` comment), the initial HTTP response becomes a streamed `200` with the destination content inlined and no `Location` header, because headers commit to the stream before the redirect resolves. The end content is still correct and a real browser's client router still lands on the right URL post-hydration, but the raw HTTP transaction stops being a clean redirect — a regression for any non-JS client (crawlers, health checks, `curl`) and a needless one, since neither route it would cover benefits from a skeleton. Confirmed via a build-with/build-without A/B test (`curl` against the authenticated root: `200`/no-`Location` with the file present, `307`/`Location: /dashboard` without it).

**Skeletons** (`src/components/feedback/skeletons/`) — `CardSkeleton`, `StatCardSkeleton`, `TableSkeleton`, `FormSkeleton`, `ListSkeleton`, `SidebarSkeleton`, `DashboardSkeleton`, and `PageSkeleton` (the composite, `variant: "list" | "form" | "detail" | "dashboard"` mirroring `05_PAGE_CATALOG.md` §0's three page templates). All wrap the shadcn `Skeleton` primitive rather than reinventing placeholder markup, per `06_COMPONENT_LIBRARY.md` §12/§18's naming convention. `SidebarSkeleton` isn't wired into `AppSidebar` — the real sidebar's navigation is derived synchronously from the already-resolved session and never suspends — it's reserved for a future server/role-driven nav source that would.

**Error handling** — `src/lib/http-error.ts` (Session 1/2) already normalizes every Axios/backend error into one `ApiError` shape at the transport layer. This session adds the layer above that: `src/utils/api-error.ts`'s `normalizeApiError()`/`getErrorMessage()` handle the non-`ApiError` edge cases a `catch` block can still see (a thrown `Error`, a non-Error value), and `src/hooks/use-async-action.ts` / `use-error-handler.ts` give pages two ways to consume it — a fully-wrapped `execute`/`isLoading`/`error` API (`useAsyncAction`) or a manual `handleError()` callback (`useErrorHandler`) — instead of each page hand-rolling its own try/catch/toast/loading-state boilerplate. `mapServerErrorsToForm` (Session 2) already covers field-level 422 mapping onto React Hook Form and isn't duplicated here.

**Empty & Error states** (`src/components/feedback/{empty-state,empty-states,error-state,error-states,offline-state}.tsx`) — each is one generic primitive (`EmptyState`, `ErrorState`) plus fixed-copy presets, mirroring how Status Badge configures into `Invoice Status`/`Trip Status`/etc. in `06_COMPONENT_LIBRARY.md` §7 — not separate implementations per case. `ErrorState` has a `page` variant (centered block, for NetworkError/ServerError/Unauthorized/Forbidden) and an `inline` variant (compact Alert, for Conflict/ValidationError), per §14's distinction between page-level and field/row-scoped errors. `OfflineState` is deliberately its own small component, not an `EmptyState` preset — the doc explicitly calls Offline a persistent low-key indicator, not a full-page state. Module-specific empty states ("No Companies yet" + its own Primary CTA) are Sprint 4+'s job, configuring `EmptyState`/`NoData` directly rather than this session adding one component per future entity.

**Dialog architecture** (`src/components/feedback/dialogs/`) — `ConfirmationDialog` is the base (built on Radix `AlertDialog`, not plain `Dialog` — a confirmation must be explicitly acted on, no backdrop-dismiss mid-decision). `DeleteConfirmationDialog` is a fixed preset (`variant="destructive"`, Delete-specific copy). `UnsavedChangesDialog` is a fixed preset for the Form Page Template's Cancel-with-dirty-form case — not wired to any real form yet, since none exist this session. `SessionExpiredDialog` is built as standalone, reusable infra but **not** wired into `AuthProvider`: the live session-expiry flow already satisfies `04_USER_FLOWS.md` §2 via an immediate toast + redirect, and swapping in a blocking modal wasn't asked for — this component is ready for a future session to adopt if that becomes the preferred UX. `ConfirmationDialog`'s confirm button calls `event.preventDefault()` before invoking `onConfirm` so Radix doesn't auto-close it — the caller is expected to call `onOpenChange(false)` itself once an async `onConfirm` resolves, which is what makes the `isLoading` prop meaningful.

**Toast conventions** (`src/lib/toast.ts`) — `toastSuccess()` / `toastError()` / `toastWarning()` / `toastInfo()` / `toastLoading()` / `toastPromise()` wrap the one Sonner `<Toaster>` already mounted by `providers/toast-provider.tsx` (Session 1). Every call site reaches for one of these instead of importing `sonner` directly, so styling/variant choice never drifts per call site.

**Shared page components** (`src/components/layout/`) — `SectionHeader` (a smaller sibling of `PageHeader`, for dividing a form/detail page's body — not a page's own title) and `ContentSection` (a title+content grouping composing it). `ActionBar` is a generic row-of-actions primitive; `PageActions` is the more specific "one Primary Button + supporting Secondary/Outline buttons" composer for a Page Header's action slot — built as a distinct, structured API (`{ primary, secondary }`) rather than a synonym of `ActionBar`, so the "exactly one Primary Button" rule (`06_COMPONENT_LIBRARY.md` §3) is enforced by the type, not left to page-author discipline. `SectionDivider` is a thin, documented wrapper over the existing `Separator` primitive (optionally with an inline label) — per §19's rule to prefer a variant of an existing component over a new one.

**Global error/not-found routes** — `src/app/error.tsx` (the root error boundary: Retry/Refresh/Go Home/Contact Support placeholder, never shows raw exception detail, only a `digest` reference), `src/app/global-error.tsx` (catches an error in the root layout itself; per Next.js's own requirement it renders its own bare `<html>/<body>` with inline styles and no dependency on `AppProviders`, since none of that is guaranteed mounted when this fires), and `src/app/not-found.tsx` (the route-level catch-all for an unmatched URL — distinct from a future Detail page's own "record not found" state, which will reuse `ErrorState` once Detail pages exist).

**Accessibility** — Dialogs inherit Radix's focus trap, Escape-to-close, and return-focus-to-trigger by construction; `ConfirmationDialog` additionally blocks dismissal (Escape/outside-click/Cancel) while `isLoading` is true, matching the "except mid-destructive-action states" category default. `EmptyState`/`ErrorState`/`OfflineState` carry `role="status"`/`role="alert"` so a state resolving to "confirmed empty" or "failed" is announced, not just visually updated. Every spinner (`Skeleton`'s pulse, every `LoaderCircle`/`Loader2` use across the app, including the two pre-existing ones in `AuthGuard` and `LoginForm`) now carries `motion-reduce:animate-none`, fixed once at the shared `Skeleton` primitive and consistently on every new spinner instance, per `02_DESIGN_SYSTEM.md` §14/§16's reduced-motion requirement.

**Known gap, flagged rather than worked around:** `06_COMPONENT_LIBRARY.md`/`02_DESIGN_SYSTEM.md` call for dedicated Success/Warning/Info semantic colors (e.g. an amber Warning treatment). `src/app/globals.css`'s theme tokens (Session 1) only define Primary/Secondary/Accent/Destructive/Muted — no `--warning`/`--success`/`--info` custom properties exist yet. Rather than inventing undeclared tokens ad hoc (which would silently fail in Tailwind v4's `@theme inline` model), every component built this session sticks to the existing token set — `OfflineState` uses a neutral `muted` treatment instead of amber, `ErrorState`'s presets use `destructive` only. Defining the missing semantic tokens belongs to a design-system session, not an inline addition here.

## Page Templates & Navigation Infrastructure

The reusable scaffolding every CRUD module (Sprint 4+) builds its actual pages from — `src/components/templates/`, three new Toolbar/Filter components in `src/components/layout/`, `PageTitle`, action button wrappers, and `src/components/data-display/`. None of it renders real data or calls the backend; it composes only the components already built in Sessions 3–4.

**Page Templates** (`src/components/templates/`) — one per `05_PAGE_CATALOG.md` §0's page-type templates, each owning the Loading/Error/Empty state switch so a future module gets "all four states defined explicitly" (`02_DESIGN_SYSTEM.md` §8) for free:
- **`ListPageTemplate`** — Page Header → Toolbar slot → Loading (`TableSkeleton`) / Error (`ErrorState`) / Empty (caller-supplied) / `children` (the future Enterprise Data Table). Full-width, the deliberate List-page exception to `PageContainer`'s max-width.
- **`DetailPageTemplate`** — Page Header → Loading (`CardSkeleton` pair) / Error / `children` (Overview Card, Related Records, Tabs). No Empty branch — per the doc, "a Detail page only exists for a record that exists"; Empty applies only to its own Related Records sub-tables, which is the owning page's concern.
- **`FormPageTemplate`** — Page Header → Loading (`FormSkeleton`, Edit only) / Error / `children` (field content) → an optional action row (`actions`, left as raw `ReactNode` rather than `PageAction` objects, since a real Save button needs `type="submit"` inside the owning `<form>`) with an opt-in `stickyActions` treatment for long forms.
- **`SettingsPageTemplate`** — composes `FormPageTemplate` rather than reimplementing it (Settings pages are `05_PAGE_CATALOG.md` §14's "single-record configuration forms," the same shape as a Form page); a distinct component only to fix Settings' own narrower conventions (no sticky footer) so a future Settings page doesn't have to think about Form's transaction-oriented options.
- **`ReportPageTemplate`** — Page Header → filters slot → summary slot → Loading / Error / Empty (defaults to `NoReports`, since most reports have no real data source until Sprint 3's reporting endpoints exist) / `children` (results table/chart), per `05_PAGE_CATALOG.md` §12's Filter Bar → Results → Export shape.

**Toolbars & Filters** (`src/components/layout/`) — three related-but-distinct rows, per `06_COMPONENT_LIBRARY.md` §1/§6:
- **`PageToolbar`** — the List page's own Search+Filters+Actions row directly under the header. Self-contained (an optional local title/description) so it can also serve as a smaller in-page toolbar without a full `PageHeader`.
- **`FilterBar`** — the structured-filter portion: a real, controlled search `Input`, plus **inert placeholder** triggers for Date Range and Status (toast "coming soon," the same established pattern as `AppHeader`'s Search/Notifications placeholders) until the real Date Range Picker / Select primitives exist, a `children` slot for module-specific filters, and an optional Reset action.
- **`TableToolbar`** — the row directly above the future Enterprise Data Table: search, a Filters trigger, and table-density controls (Column Selector, Export — both placeholders) plus Refresh, per `06_COMPONENT_LIBRARY.md` §6. Passing `selectedCount > 0` swaps the whole row for a Bulk Actions bar — unconsumed until a real table with row selection exists, built ahead of need the same way `AppSidebar`/`PageHeader` were in Session 3.

**`PageTitle`** (`src/components/layout/page-title.tsx`) — the title+icon+badge+actions row, factored out of `PageHeader` (which now composes it rather than duplicating its own copy) so it's available standalone wherever a smaller title treatment is needed without a breadcrumb — a Dialog header, a Card's own title region.

**Action buttons** (`src/components/layout/action-buttons.tsx`) — `PrimaryActionButton`/`SecondaryActionButton`/`DangerActionButton`/`ToolbarButton`/`IconActionButton` are fixed-variant wrappers over the existing `Button` (never a new button implementation) — named intent instead of remembering which `variant` string means "the destructive one," per `06_COMPONENT_LIBRARY.md` §3's variant-naming convention.

**Data display** (`src/components/data-display/`) —
- **`MetricCard`** / **`TrendMetricCard`** — the KPI/Stat Card and Trend Card primitives (`06_COMPONENT_LIBRARY.md` §9). Never formats or fetches its own value — the caller passes an already-formatted string (`formatCurrency`, etc.), keeping financial formatting logic in one place. `TrendMetricCard`'s down-trend color uses the existing `destructive` token only; up/neutral stays plain foreground rather than inventing a "success" green (see the Known Gap note below — unchanged from Session 4).
- **`SummaryGrid`** — the responsive KPI-row grid (2/3/4 columns, reflowing per `05_PAGE_CATALOG.md` §16) underlying the Dashboard Grid and Report Summary sections.
- **`InfoCard`** — a standardized title/icon/actions header over the base `Card`, for Overview Cards and other static reference content (`06_COMPONENT_LIBRARY.md` §5).
- **`KeyValueList`** vs **`DescriptionList`** — both render semantic `<dl>`/`<dt>`/`<dd>` markup (so a screen reader announces the label/value relationship either way) but differ in layout, not accessibility contract: `KeyValueList` is a stacked-card grid for an Overview Card's scannable fields; `DescriptionList` is a row-per-item, label-left/value-right list with row dividers, for a linear top-to-bottom summary read (a Settings recap, an Audit entry's field list).

**Dashboard rebuild** (`(authenticated)/dashboard/page.tsx`) — still no API call, no TanStack Query — the brief's "static mock values only" constraint. Rebuilt entirely from this session's and prior sessions' components (`PageHeader`, `SummaryGrid`, `MetricCard`/`TrendMetricCard`, `InfoCard`, `EmptyState`/`NoActivity`) instead of the one-off markup Session 3 shipped, so swapping the mock figures for a real query later is a data change, not a structural one. The 4 KPI labels match `05_PAGE_CATALOG.md` §2 exactly (Total Receivables/Payables Outstanding, Trips at Sea, Boats with Expiring Compliance).

**Known gap, unchanged from Session 4:** `globals.css` still has no `--success`/`--warning`/`--info` tokens. `TrendMetricCard` and every other component built this session stick to the existing Primary/Secondary/Destructive/Muted set for the same reason documented in Session 4 — inventing an undeclared Tailwind v4 `@theme` token would silently fail rather than error.

## Enterprise Data Table (Sprint 2, Session 1)

The single, standardized table implementation for every future List page and Related Records sub-table (`06_COMPONENT_LIBRARY.md` §6, `07_FRONTEND_ARCHITECTURE.md` §13) — reusable infrastructure only, built and verified against mock data. No business module (Companies/Fish/Boats/...), no CRUD page, and no real API call is wired to it this session; that starts at Sprint 4.

### Architecture

`src/components/data-table/` is built directly on **TanStack Table v8** (`@tanstack/react-table`, added this session) rather than a hand-rolled table, matching the "reuse an established primitive over inventing one" principle already applied to the Sidebar (Session 3). The split mirrors how the rest of the app separates server state from rendering:

- **`DataTable`** is a pure renderer over a `Table<TData>` instance — it never builds its own table and never calls an API. Sorting/pagination/filtering are **server-side by default** (`manualSorting`/`manualPagination`/`manualFiltering` all default to `true` in `useDataTable`): the table reports the sort/page the user wants via callbacks, and the owning feature's TanStack Query hook does the actual re-fetch, per `07_FRONTEND_ARCHITECTURE.md` §8's shared pagination contract.
- **`useDataTable`** is the hook a feature calls to build that `Table` instance from `columns` + `data` (+ whichever state slices it wants to control). Every controlled slice — sorting, column visibility, row selection, column pinning, column sizing — is genuinely optional: pass the state and its `onChange` to control a slice from outside (e.g. syncing sort to the URL, per `07_FRONTEND_ARCHITECTURE.md` §7's URL-State rule), or omit both and TanStack manages it internally. Getting this half-controlled behavior right matters: TanStack merges options as `{...defaults, ...options}`, so passing an explicit `sorting: undefined` (instead of omitting the key) would silently overwrite its internal state manager — `useDataTable` conditionally spreads every controlled key/callback for exactly this reason.
- **The table instance is lifted to the caller**, not hidden inside `DataTable`. This is what lets a `DataTableToolbar`'s `DataTableColumnToggle` (which needs `table.getAllColumns()`) and the `DataTable` body share one instance instead of the toolbar reaching for a table `DataTable` built for itself. A feature page's shape is: build `table` via `useDataTable` → pass it to `DataTable` → pass it to any toolbar piece that needs it.
- **Column widths are always explicit** (`column.getSize()`, defaulting to TanStack's own 150px), never left to the browser's natural `table-layout: auto`. Sticky/pinned columns compute their `left`/`right` offset from the *declared* sizes (`column.getStart()`/`getAfter()`); if the actually-rendered width ever drifted from the declared one, pinned columns would visually misalign. Give a column an explicit `size` when it needs to look tighter/wider than the default.
- **Sticky/pinned columns use one real mechanism**: TanStack's own `columnPinning` state (`{ left: string[], right: string[] }`), which is what genuinely "Pinned columns" means. `stickyFirstColumn`/`stickyActionColumn` are a convenience layer on top for the common single-column case (per `02_DESIGN_SYSTEM.md` §15's "identifying first column" rule) — they don't require the caller to manage pinning state at all. For anything beyond one pinned column per side, use `columnPinning` directly; both mechanisms compose (a `th`/`td` can be sticky via either path, and the sticky header + a pinned first column correctly form a "frozen corner" via CSS `position: sticky` with both `top` and `left` set).
- **Loading/Error/Empty/No-Results all render inside `<tbody>`** as a single full-width (`colSpan`) cell, not by replacing the whole table — so the header (and any sticky columns) stay visible and in place while a fetch resolves, per `06_COMPONENT_LIBRARY.md` §6's category default.

### Composition

```
DataTable
  toolbar   → DataTableToolbar (search / filters / viewOptions / export / refresh slots, or a Bulk Actions bar once selectedCount > 0)
  <table>
    <thead> → DataTableColumnHeader (per sortable column) + resize handle
    <tbody> → DataTableLoading | DataTableError | DataTableEmpty | DataTableNoResults | real rows (DataTableRowActions in the actions column)
  pagination → DataTablePagination
```

`column-helpers.tsx` factors out the two column shapes almost every table needs so no feature hand-rolls them: `createSelectionColumn()` (the select-all/indeterminate/per-row checkbox column, per the "avoid when no bulk action exists" rule — only added when a table actually needs it) and `createRowActionsColumn(actions)` (the kebab menu column, `actions` as a function of the row so RBAC filtering — `07_FRONTEND_ARCHITECTURE.md` §11 — happens where the feature already has the current permission set in scope).

### Usage

```tsx
"use client";

import {
  DataTable, DataTableToolbar, DataTableColumnHeader, DataTableColumnToggle,
  DataTablePagination, createSelectionColumn, createRowActionsColumn,
  useDataTable, useColumnVisibility, useRowSelection,
  type DataTableColumn,
} from "@/components/data-table";

const columns: DataTableColumn<Company>[] = [
  createSelectionColumn<Company>(),
  {
    accessorKey: "name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Company" />,
  },
  {
    accessorKey: "balance",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Balance" />,
    cell: ({ getValue }) => <MoneyDisplay value={getValue<number>()} />,
    meta: { align: "right" },
  },
  createRowActionsColumn<Company>((row) => [
    { label: "Edit", icon: Pencil, onClick: () => router.push(`/companies/${row.id}/edit`) },
    { label: "Deactivate", icon: Ban, variant: "destructive", separatorBefore: true, onClick: () => deactivate(row.id) },
  ]),
];

function CompaniesTable() {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 25 });
  const [columnVisibility, setColumnVisibility] = useColumnVisibility("companies-columns");
  const { rowSelection, setRowSelection, selectedCount, clearSelection } = useRowSelection();

  const query = useCompaniesQuery({ sorting, pagination }); // feature's own TanStack Query hook (Sprint 4+)

  const table = useDataTable({
    data: query.data?.items ?? [],
    columns,
    sorting, onSortingChange: setSorting,
    columnVisibility, onColumnVisibilityChange: setColumnVisibility,
    rowSelection, onRowSelectionChange: setRowSelection,
    enableRowSelection: true,
    pageCount: query.data?.pageCount,
  });

  return (
    <DataTable
      table={table}
      stickyFirstColumn
      stickyActionColumn
      onRowClick={(row) => router.push(`/companies/${row.id}`)}
      isLoading={query.isLoading}
      error={query.isError ? { title: "Couldn't load companies", onRetry: query.refetch } : null}
      isEmpty={query.data?.items.length === 0 && !hasActiveFilters}
      isNoResults={query.data?.items.length === 0 && hasActiveFilters}
      toolbar={
        <DataTableToolbar
          search={<SearchInput ... />}
          viewOptions={<DataTableColumnToggle table={table} />}
          selectedCount={selectedCount}
          bulkActions={<Button variant="destructive" onClick={() => bulkDeactivate(rowSelection)}>Deactivate</Button>}
        />
      }
      pagination={
        <DataTablePagination
          pageIndex={pagination.pageIndex}
          pageSize={pagination.pageSize}
          totalCount={query.data?.totalCount ?? 0}
          onPageChange={(pageIndex) => setPagination((p) => ({ ...p, pageIndex }))}
          onPageSizeChange={(pageSize) => setPagination({ pageIndex: 0, pageSize })}
          selectedCount={selectedCount}
        />
      }
    />
  );
}
```

### Future integration with CRUD modules (Sprint 4+)

A feature module only ever supplies **columns** and a **data source** — never a bespoke table:

1. Define the column array in `features/{module}/components/` (or colocated with the List page), composing `DataTableColumnHeader`, `createSelectionColumn`/`createRowActionsColumn`, and Status Badge/Money Display cell renderers.
2. Wire `sorting`/`pagination`/search-and-filter state to the URL (`07_FRONTEND_ARCHITECTURE.md` §7) and pass it into the feature's own TanStack Query list hook.
3. Build the `table` via `useDataTable`, render `DataTable` + `DataTableToolbar` + `DataTablePagination` as shown above.
4. `enableRowSelection`/`createSelectionColumn` are opt-in per module — only add them where a real Bulk Action exists (`06_COMPONENT_LIBRARY.md` §6), not for consistency's sake.

None of this session's components hardcode a module name, an entity shape, or an endpoint — that's the point of building it once, ahead of Sprint 4.

### Verified this session

Rendering, server-side sorting/pagination (via a mock in-memory "server"), multi-select with header indeterminate state, the row-actions kebab, `localStorage`-persisted column visibility (confirmed surviving a real page reload), sticky header + sticky first/last column together, the Loading/Error/Empty/No-Results states (header stays visible throughout), and both themes — checked live against a running dev server with a temporary harness page (removed before this session's work was considered done, per the "no CRUD pages this session" scope).

**Fixed along the way:** the shared `Checkbox` primitive (`src/components/ui/checkbox.tsx`, Session 1) only styled Radix's `checked` state, never `indeterminate` — a table with some-but-not-all rows selected rendered its header checkbox looking identically empty/unchecked. Added the `indeterminate` style variant and a distinct `Minus` icon so "some selected" is visually distinguishable from "none selected," fixed once at the shared component per `07_FRONTEND_ARCHITECTURE.md` §28.

## Form Components (Sprint 2, Session 2)

`src/components/form/` — every field a business form (Sprint 4+) will need, built once against `react-hook-form` + `zod` rather than per-module. Reusable infrastructure only: no business form, no API call, wired this session.

- **`FormField`** — the shared label/description/error/required wrapper every other field composes, via a render-prop (`children: (props: { id, describedBy, "aria-invalid" }) => ReactNode`) so each field wires its own input to the right `id`/`aria-describedby`/`aria-invalid` without duplicating that logic.
- **Numeric family** — `NumberInput` is the base (prefix/suffix affixes, `sanitizeNumericString()` exported standalone); `CurrencyInput`/`QuantityInput`/`RateInput`/`PercentageInput` are fixed-precision *configurations* of it (2/3/4/2 decimal places, matching the backend's `NUMERIC(14,2)`/`NUMERIC(12,3)`/`NUMERIC(12,4)` columns) — not separate implementations, the same "configure, don't reimplement" pattern as Status Badge.
- **Date family** — `DatePicker` (typed entry *and* a Calendar popover — parses/validates via `date-fns`) and `DateRangePicker` (two-ended, Clear in the popover footer). Both default to `DEFAULT_DATE_FORMAT` (`src/lib/date-format.ts`) rather than each hardcoding its own format string.
- **Selection family** — `Combobox` (generic, `ComboboxOption<TValue>`) underlies `SearchableSelect` (client-side filter) and `AsyncSelect` (server-side search — requires `onSearchChange`/`isLoading`, `shouldFilter={false}` so Command doesn't double-filter already-filtered results).
- **Text family** — `EmailInput`, `PhoneInput` (country-code prefix), `GSTINInput` (auto-uppercase, monospace), `TextArea`.
- **Layout** — `FormGrid` (responsive 1/2/3/4-column field grid, collapsing below the laptop breakpoint), `FormSection` (composes the shared `SectionHeader`), `FormActions` (primary/secondary/danger button slots).

```tsx
<FormGrid columns={2}>
  <CurrencyInput label="Invoice Amount" required value={amount} onChange={setAmount} />
  <DatePicker label="Due Date" required value={dueDate} onChange={setDueDate} />
  <SearchableSelect label="Company" options={companyOptions} value={companyId} onChange={setCompanyId} />
</FormGrid>
```

## Filtering, Search & Pagination (Sprint 2, Session 3)

`src/components/filters/`, `src/components/pagination/`, and three hooks in `src/hooks/` — every List/Report page's filter row and pagination bar, entirely props-driven: no internal business state, no API call, no URL sync (a future module wires that itself, per `07_FRONTEND_ARCHITECTURE.md` §7's URL-State rule).

- **Containers** — `FilterPanel` (Radix `Collapsible`, genuinely generic about its `children`), `AdvancedFilter` (Popover-based, `FilterBadge` on the trigger), `FilterSection`/`FilterGroup` (the latter a semantic `<fieldset>/<legend>`).
- **Fields** — `StatusFilter` (single or `multiple`), `DateRangeFilter` (thin wrapper over `form`'s `DateRangePicker`), `NumberRangeFilter` (wraps `form`'s `NumberInput` for both bounds), `MultiSelectFilter` (Popover+Command, `FilterChip` tags for selections), `BooleanFilter` (`Switch`, not `Checkbox` — a filter takes effect immediately), `TextFilter`.
- **Applied-state chrome** — `FilterChip`, `FilterBadge`, `AppliedFilters`, `ClearFiltersButton`, `FilterDivider`.
- **`SearchBar`** — the Toolbar's free-text field; composes the `useSearch` hook for its debounce timer rather than reimplementing it, both controlled and uncontrolled.
- **Pagination** (`src/components/pagination/`) — `Pagination` (First/Prev/[pages]/Next/Last, `getPaginationRange()` exported standalone for a consumer that wants the raw token sequence), `PageSizeSelector`, `PageJump`, `PaginationSummary` ("Showing X–Y of Z"). 1-based `page`, deliberately — the Data Table's own internal TanStack integration stays 0-based (TanStack's convention); a future session could rebuild `DataTablePagination` on top of these instead of its own inline markup.
- **Hooks** (`src/hooks/`) — `useSearch` (debounced value), `usePagination` (page/pageSize/from/to/next/previous, resets to page 1 on page-size change), `useFilters<TFilters>` (named-filter state, `activeCount`/`isActive` diffed against the hook's own initial values — `TFilters extends object`, not `Record<string, unknown>`, so a plain named interface without an index signature is accepted).

```tsx
const { filters, setFilter, clearFilters, activeCount } = useFilters({ status: "all", search: "" });
const pagination = usePagination({ totalCount: data?.total ?? 0 });

<FilterPanel actions={<ClearFiltersButton onClear={clearFilters} count={activeCount} />}>
  <StatusFilter value={filters.status} onChange={(v) => setFilter("status", v)} options={statusOptions} />
</FilterPanel>
<Pagination page={pagination.page} totalPages={pagination.totalPages} onPageChange={pagination.setPage} />
```

## Charts & Reporting Components (Sprint 2, Session 4)

`src/components/charts/`, `src/components/reports/`, `src/components/dashboard/` — Recharts-based charts and the surrounding Dashboard/Report page chrome. No business report, no dashboard API, no business calculation — every value arrives already computed/formatted.

- **Charts** (`src/components/charts/`) — `LineChart`, `BarChart` (grouped or `stacked`), `AreaChart` (gradient fill, gradient `id`s scoped per instance via `useId()` to avoid collisions between two charts on one page), `PieChart`, `DonutChart` (a `PieChart` with `innerRadius` pre-set — not a separate implementation). All `ResponsiveContainer`-wrapped, themed entirely off `--chart-1`…`--chart-5`/`--border`/`--muted-foreground` CSS custom properties (`globals.css`) rather than JS theme detection, so they repaint correctly across the dark-mode class toggle for free; Recharts v3's `accessibilityLayer` (keyboard nav + ARIA over the plotted data) is on by default. Each chart independently supports `isLoading`/`error`/empty-data (via the shared `ChartLoading`/`ChartError`/`ChartEmpty`, so it works standalone without `ChartCard`), plus a shared `ChartTooltip`/`Legend` passed to Recharts' own `content` prop.
- **`KpiCard`** / **`TrendCard`** — the chart-context Stat Card / trend indicator. Deliberately shares its shell with `data-display`'s pre-existing `MetricCard`/`TrendMetricCard` (this session's spec placed it in its own folder) — see Session 5's finalization notes below for the consolidation this sets up. `TrendCard`'s `positive`/`neutral` states stay plain foreground (no invented "success" green, matching the Known Gap noted throughout this doc); only `negative` borrows the existing `destructive` token.
- **`ChartCard`** — the reusable title/description/actions/loading/error wrapper any chart or widget renders inside.
- **Reports** (`src/components/reports/`) — `ReportHeader` (composes `PageTitle` + a "Generated at" caption), `ReportFilters` (a `FilterPanel` configuration), `ReportSummary` (`SummaryGrid` + `KpiCard`), `ReportSection` (composes `SectionHeader`), `ExportMenu` (CSV/Excel/PDF — UI only, `onExport(format)` callback, no file generation), `PrintButton` (`window.print()` by default), `DateRangeHeader` (read-only "covering {range}" caption).
- **Dashboard** (`src/components/dashboard/`) — `DashboardGrid` (12-column responsive), `MetricGrid` (a direct alias of `data-display`'s `SummaryGrid`), `RecentActivityCard`, `QuickActionsCard` (`next/link` for `href` actions, a plain callback otherwise), `SummarySection` (composes `SectionHeader` — the Dashboard-context sibling of `ReportSection`).

```tsx
<ReportSummary items={[{ key: "revenue", title: "Total Revenue", value: formatCurrency(total), icon: DollarSign }]} />
<ChartCard title="Revenue vs Expenses" isLoading={query.isLoading} error={query.error?.message}>
  <LineChart data={query.data ?? []} series={[{ dataKey: "revenue" }, { dataKey: "expenses" }]} xAxisKey="month" />
</ChartCard>
```

## Component Library Finalization (Sprint 2, Session 5)

A quality/consistency pass over every folder built in Sessions 1–4 — no new components, per this session's explicit scope. Findings and fixes:

- **Duplicated helper removed** — `DEFAULT_FORMAT = "dd/MM/yyyy"` was independently declared in `DatePicker`, `DateRangePicker`, and `DateRangeHeader`. Consolidated into `src/lib/date-format.ts`'s `DEFAULT_DATE_FORMAT`/`DEFAULT_DATETIME_FORMAT`, imported by all three plus `ReportHeader`.
- **Prop-consistency gaps closed** — `DataTableEmpty`/`DataTableError`/`DataTableNoResults` (Session 1) gained the `className` prop already present on their Session 4 chart equivalents (`ChartEmpty`/`ChartError`); `ExportMenu`/`PrintButton` (Session 4) gained `className`, matching every other action button in the library (`ClearFiltersButton`, `ToolbarButton`, ...).
- **Client-boundary fix** — `DataTableNoResults`, `ClearFiltersButton`, and `FilterChip` attach `onClick` handlers directly but were missing their own `"use client"` directive; they happened to always render under an already-client ancestor in every context exercised so far (masking the gap), but a component that attaches a DOM event handler should carry the directive itself rather than depend on an inherited boundary. Fixed; every other interactive leaf in the library already did this correctly.
- **Verified clean, no changes needed**: no hardcoded colors/hex values anywhere in the four new folders (every color is a semantic token, confirmed by grep); no duplicate barrel exports; Recharts' `accessibilityLayer` and the shared `Skeleton`'s `motion-reduce:animate-none` mean the charts/loading-states' accessibility and reduced-motion behavior came "for free" from the reuse-over-duplication approach followed all session; every icon-only button in the four new folders goes through `IconActionButton` (which requires a `label`) or carries an explicit `aria-label`; `Pagination`'s page buttons carry `aria-current="page"`.
- **Known, deliberately unresolved overlaps** (flagged for a future session, not fixed here since fixing either means redesigning pre-Sprint-2 code, out of this session's scope): `components/charts/KpiCard`+`TrendCard` duplicate the shell of `components/data-display/MetricCard`+`TrendMetricCard` by construction — this session's spec required the former in a new folder. `components/layout/FilterBar`/`TableToolbar`/`templates/list-page-template.tsx` (pre-Sprint-2) still describe their own Date Range/Status/Column-Selector/Export controls as "coming soon" placeholders — the real ones now exist in `filters/`/`charts/data-table`, but no current page imports these placeholder files, so nothing breaks either way; swapping them is Sprint 3+ integration work, not a Sprint 2 library concern.

### Extension guidelines

When a future session adds to this library:

1. **Reuse before building** — check `data-display/`, `form/`, `filters/`, `charts/` first; a new "Xyz Filter"/"Xyz Card" is very often a thin, pre-configured wrapper over an existing primitive (see `DonutChart` over `PieChart`, `CurrencyInput` over `NumberInput`, `MetricGrid` over `SummaryGrid`) rather than a new implementation.
2. **One folder per concern**, flat inside it (no nested subfolders beyond an occasional `hooks/`), each with a barrel `index.ts` re-exporting every public component *and* its prop type.
3. **Prop naming**: `isLoading` (not `loading`), `className` on every component (even a thin wrapper — forward it, don't drop it), `onXChange` for callbacks, `"aria-label"` as a literal-keyed prop only when it needs a caller-facing override.
4. **Theming**: only the existing `--chart-*`/semantic Tailwind tokens (`bg-muted`, `text-destructive`, ...) — never a hardcoded hex/named color, and never invent a new `--token` outside a dedicated design-system session (see the Known Gap notes on the missing `--success`/`--warning`/`--info` tokens above).
5. **Accessibility by default**: icon-only buttons go through `IconActionButton`, not a raw `<Button size="icon">`; anything attaching a DOM event handler needs its own `"use client"`; a spinner needs `motion-reduce:animate-none` (or reuse `Skeleton`, which already has it).
6. **State**: props/callbacks only — no internal business state, no API call, no URL sync — until the session's brief explicitly asks for it.

## Current Status

**Sprint 1 (Sessions 1–5)** — engineering foundation, authentication, the application shell, global UX infrastructure, and reusable page templates. **Sprint 2 (Sessions 1–5)** — the full reusable Component Library: Enterprise Data Table, Form Components, Filtering/Search/Pagination, Charts & Reporting, and this finalization pass. Still no business modules or CRUD pages (Sprint 4+ per the master roadmap) — every template/toolbar/data-table/form/filter/chart/data-display component built so far is deliberately unconsumed by real data until then.

- Project scaffold, TypeScript strict mode, ESLint, Tailwind v4.
- shadcn/ui configured (New York style, Slate base color, CSS variables).
- Theme system (light/dark/system via next-themes), now switchable via the topbar `ThemeSwitcher`.
- TanStack Query client + provider (dev-only devtools); retry only on network/server errors for reads, never for mutations.
- Two HTTP clients: `src/lib/api-client.ts` (direct-to-backend, reserved for future business data) and `src/lib/bff-client.ts` (same-origin, used by auth) — both share one error-normalization pipeline (`src/lib/http-error.ts`, `src/lib/create-http-client.ts`).
- Full authentication — see above.
- Full application shell — Sidebar, Top Navigation, Breadcrumbs, permission-aware navigation — see above.
- A mock-data Dashboard (`(authenticated)/dashboard`) proving the whole stack end-to-end: auth guard → shell → `SummaryGrid`/`MetricCard` KPIs → permission-filtered quick actions — not the real, backend-wired Dashboard (that's Sprint 3 in the master roadmap, once the backend's reporting endpoints exist).
- Formatting utilities matching the backend's Decimal precision (currency: 2dp, quantity: 3dp, rate: 4dp).
- Full global UX infrastructure — loading/skeletons, empty/error states, dialogs, toasts, shared page components, error-handling hooks — see above.
- Full reusable page templates and navigation infrastructure — List/Detail/Form/Settings/Report templates, Toolbars, Filter Bar, data-display primitives — see above.
- The Enterprise Data Table (`src/components/data-table/`) — see above. `@tanstack/react-table` added as a dependency in Session 1.
- Enterprise Form Components (`src/components/form/`) — see above. `react-day-picker`, `cmdk` added as dependencies in Session 2.
- Filtering, Search & Pagination (`src/components/filters/`, `src/components/pagination/`, three new hooks) — see above.
- Charts & Reporting Components (`src/components/charts/`, `src/components/reports/`, `src/components/dashboard/`) — see above. `recharts` already present as a dependency.
- Session 5's component library finalization pass — consistency/accessibility/dark-mode/documentation audit across all of the above — see above.

Next up: the first real business module (Companies, per `08_FRONTEND_IMPLEMENTATION_PLAN.md`'s Masters-first sequencing) — List/Create/Detail/Edit pages that finally instantiate the Data Table, Form Components, Filters, and page templates with real data instead of as unconsumed infra.
