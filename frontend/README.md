# AquaLedger Frontend

The Next.js 15 frontend for AquaLedger — an ERP for the seafood trading industry. See the numbered planning documents in this directory (`01_PRODUCT_VISION.md` through `08_FRONTEND_IMPLEMENTATION_PLAN.md`) for the product, design, and architecture specification this codebase implements.

## Stack

Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS v4 · shadcn/ui (New York, Slate) · TanStack Query · TanStack Table v8 · nuqs · Axios · React Hook Form + Zod · Recharts · next-themes · Sonner

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

## Companies Module (Sprint 3) — Complete

The first real business module — full CRUD (List/Create/Edit/Detail/Delete) against the live backend, `features/companies/` (mirrors `app/modules/companies/` on the backend). Built across five sessions (Sessions 1–4 plus a final QA/hardening pass); this section documents the module as it stands now, not session-by-session. **Status: production-ready for its stated scope** — see "Explicitly out of scope" below for what's deliberately not built.

### Architecture

```
features/companies/
  types/company.ts            # BackendCompany (snake_case, wire shape) + Company (camelCase, client shape)
                               # + mapBackendCompany() + CompanyCreateRequest/CompanyUpdateRequest/CompanyListParams
  services/company-service.ts # listCompanies / getCompany / createCompany / updateCompany / deleteCompany
  hooks/                      # useCompanies, useCompany, useCreateCompany, useUpdateCompany, useDeleteCompany,
                               # useCompanyFilters (URL state, see below)
  schemas/
    company-filters.ts        # CompanyFilters shape + toCompanyListParams() mapper
    company-form-schema.ts    # zod schema, CompanyFormValues, form <-> Company/request payload mappers
  constants/                  # company-status.ts, company-type.ts, query-keys.ts (companyKeys)
  components/                 # company-columns.tsx, company-row-actions.tsx, company-form.tsx
  pages/                      # company-list-page.tsx, company-detail-page.tsx, company-create-page.tsx, company-edit-page.tsx
  index.ts                    # barrel — the module's public surface
```

`app/(authenticated)/companies/{page.tsx, new/page.tsx, [id]/page.tsx, [id]/edit/page.tsx}` are thin route wrappers that just render the matching page component — all real logic lives in `features/companies/`.

**The BFF-proxy decision.** `ARCHITECTURE.md` describes the browser calling the backend "directly via TanStack Query," but the access token is an `HttpOnly` cookie the browser's JS can never read, and the backend runs on a different origin — so a client-side `apiClient` call literally cannot authenticate. `company-service.ts` therefore talks only to the Next.js BFF's own routes (`app/api/companies/**`, same pattern as `auth-service.ts`), which attach the caller's token server-side and forward to FastAPI. `lib/auth/authenticated-backend-request.ts`'s `authenticatedBackendRequest()` is the one place that does this (GET/POST/PUT/DELETE all reuse it, including the silent-refresh-on-401 retry `resolveSession()` already gives page loads) — every future module's BFF routes should reuse it rather than re-implementing token attachment.

**Field-name convention.** `Company` (the type `useCompany`/`useCompanies` return) is camelCase, matching the rest of the client. `CompanyFormValues` (the Create/Edit form's RHF schema) is deliberately **snake_case**, matching `CompanyCreateRequest`/`CompanyUpdateRequest` exactly — this lets `mapServerErrorsToForm` map a 422's `field_errors` straight onto the right form field with zero translation layer, and the submitted values need no remapping to become the POST/PUT body.

**Known deviation:** `CompanyCreateRequest.company_type` has no backend default (required), even though it wasn't in the brief's stated Create/Edit field list — omitting it would make every Create submission fail with a 422, so the form includes it as a required "Company Type" select, defaulting to Customer.

### Permission Model

Four permission codes gate the module: `company:view`, `company:create`, `company:edit`, `company:delete` — the same `resource:action` codes the backend's RBAC model already defines (`ARCHITECTURE.md` §9), read via `usePermissions()`. Every page and action checks its own permission independently rather than inheriting from a parent gate:

- **List** (`company:view` implied by being able to reach the page — see `AuthGuard`) — `company:create` hides "New Company" (header action + genuinely-empty-state's CTA); `company:view`/`company:edit`/`company:delete` each independently hide their respective row action, and `company:view` additionally gates whether a row click navigates at all.
- **Detail/Create/Edit pages** check their own required permission (`company:view`/`company:create`/`company:edit`) *before* rendering anything else, returning a plain `ErrorState` ("You don't have permission to …") instead of the page body — hooks are still called unconditionally above that check, per the Rules of Hooks.
- **Delete** is gated the same way everywhere it appears (List row action, Detail page action).

This is **cosmetic only** — every gated backend route re-validates the same permission server-side regardless of what the UI shows or hides (`ARCHITECTURE.md` §9.3's UI-layer note: "Cosmetic only. Never the security boundary"). Hiding a control here is a UX courtesy, not the enforcement point.

### URL State

Every list control — `search`, `status`, `city`, `page`, `pageSize`, `sort`, `direction` — lives in the URL via `useCompanyFilters()` (`features/companies/hooks/use-company-filters.ts`), built on **nuqs** (`useQueryStates`), per `07_FRONTEND_ARCHITECTURE.md`'s locked "URL/filter state → nuqs" decision. `nuqs` wasn't installed before this session (added here) and needs `<NuqsAdapter>` mounted once at the root (`providers/app-providers.tsx`).

- `history: "push"` — every filter/sort/page change gets its own browser history entry, so Back/Forward actually step through the list's previous states rather than just leaving the page.
- `shallow: true` (nuqs's default) — URL updates stay client-side, no Next.js server round trip; TanStack Query's `useCompanies` is what reacts to the new state and refetches.
- A refresh, a pasted URL, or a shared link all restore the exact list state, since none of it lives in component state.
- The backend's `sort` query param is a single combined string (`-created_at` = descending); the URL keeps `sort`/`direction` as two separate, readable params instead — `toCompanyListParams()` recombines them into the wire format only when calling the API.

**Debounced fields, and the focus-loss trap.** `history: "push"` means a naive controlled `<input>` writing to the URL on every keystroke would push one history entry per character — Back would need to be pressed once per letter typed. `search` and `city` are therefore debounced *before* they reach `useCompanyFilters`: `SearchBar` already debounces internally (composes `useSearch`), and `CityFilterField` (a small local wrapper in `company-list-page.tsx`) does the same for the City filter. Both need to remount when the filter value changes from *outside* typing (Clear All, a removed filter chip, Back/Forward), since neither underlying input re-reads its initial value after mount otherwise — but naively keying them off the raw value (`key={filters.search}`) remounts the input on **every** debounced write too, including the component's own, which unmounts it mid-keystroke and drops focus. `src/hooks/use-external-value-key.ts`'s `useExternalValueKey()` is the fix: the input's own debounced handler calls `report(value)` right before writing out, so that resulting value change is recognized as self-inflicted and doesn't remount — only a value change *without* a matching `report()` call first (a genuine external change) bumps the key. `status` writes immediately, no debounce needed (one click = one deliberate action = one correct History stop).

### Search

`SearchBar` (Sprint 2) already provided debounce, a clear button, and a loading-spinner slot — this module wires the loading slot to `listQuery.isFetching` (spins during any in-flight fetch, not just the very first one) and, when a search yields zero rows, `DataTableNoResults` shows a description naming the actual search term (`No companies match "acme". Try a different search or clear your filters.`) rather than a generic message. `SearchBar` takes `flex-1` (plus a `min-w-56` floor) in the toolbar row so it's the dominant, widest control — not shrink-to-fit beside a wide empty gap.

### Filters

The Filters trigger is `AdvancedFilter` (Sprint 2) — a compact Popover button with an active-count badge, holding Status + City — **not** `FilterPanel`, which is an always-expanded collapsible *section* and visually far too heavy sitting beside a single search box in a toolbar row (this was tried first, then corrected after review: `FilterPanel` is the right choice for a dedicated filters sidebar/section, `AdvancedFilter` is the right one for a Toolbar trigger). `AppliedFilters` renders each active filter (search/status/city) as a removable chip below the toolbar plus one "Clear All" — the popover's own footer also gets a "Clear all" (`onReset`), scoped to when the popover is open, so there is exactly one Clear-All per visible context rather than two competing ones stacked on top of each other. Removing a single chip clears just that filter (and resets to page 1); Clear All resets every filter, sort, and page back to its default in one URL update (`setFilters(null)`).

### Sorting

Column headers use TanStack Table's own toggle, but the table's `sorting` state is fully controlled from `filters.sort`/`filters.direction` (there's no client-side "unsorted" concept — the backend always sorts by *something*, defaulting to `-created_at`). TanStack's default toggle is a 3-state cycle per column (ascending → descending → **unsorted**); the "unsorted" step is intercepted in `onSortingChange` and turned into a direction flip on the current column instead of being applied, because clearing the sort here would silently stop responding to further clicks — since the controlled `sorting` array would never change from that empty state again, every subsequent click recomputes the exact same "clear" transition. The "Created At" column also needs an explicit column `id: "created_at"` (distinct from its `accessorKey: "createdAt"`, which drives cell rendering) — without it, TanStack defaults the column's sort-`id` to the camelCase accessor key, and clicking the header would send `sort=createdAt` straight to a backend that only recognizes snake_case `created_at`/`updated_at`, 422ing every time.

### CRUD Flow

```
List (search/filter/sort/paginate)
  ├─ row action / row click "View" ──────────▶ Detail (read-only)
  ├─ row action "Edit" ───────────────────────▶ Edit (CompanyForm, pre-filled)
  ├─ row action "Delete" ─────────────────────▶ DeleteConfirmationDialog ──▶ useDeleteCompany()
  └─ primary action "New Company" ────────────▶ Create (CompanyForm, empty)

Detail
  ├─ primary action "Edit" ───────────────────▶ Edit
  └─ secondary action "Delete" ───────────────▶ DeleteConfirmationDialog ──▶ useDeleteCompany()
```

`CompanyForm` is the single shared form for both Create and Edit — same fields, same zod validation, same submit/error handling (422 → `mapServerErrorsToForm`, anything else → `toastError`). `useCreateCompany`/`useUpdateCompany`/`useDeleteCompany` each invalidate `companyKeys.lists()` on success so the List page's cache never goes stale after a mutation; `useUpdateCompany` also invalidates the specific `companyKeys.detail(id)`, and `useDeleteCompany` removes it outright. `useDeleteCompany` owns the *entire* delete outcome (invalidate, `toastSuccess`, navigate to `/companies`) so the Detail page's Delete button and the List page's row-action Delete get identical behavior — the List page's dialog just adds a per-call `onSuccess` to also close itself.

**Stale-page correction.** Deleting the last row on the last page (or a filter narrowing the result set) can leave `filters.page` pointing past the new last page — the query would return an empty page even though earlier pages still have data, showing a misleading "no results." The List page watches `totalCount`/`filters.page` once a fetch completes and steps `page` back to the new last page if it's out of range.

Every action is permission-gated — see "Permission Model" above.

**Explicitly out of scope** (per the Sprint 3 brief): Activity Timeline, Audit History, Attachments/Documents, Change Log, Export/PDF. None of these are wired to the Companies module.

### Final QA Pass (Sprint 3 Session 5)

A dedicated review pass over the whole module — CRUD audit, responsive/dark-mode/accessibility/performance review, code cleanup — with a directive to fix only what was found, not add scope. Real issues found and fixed:

- **Missing accessible label** — the Notes field (`CompanyForm`) rendered a bare `TextArea` with no `label`; the `FormSection` title above it is a heading, not a `<label for>` — a screen reader user tabbing into the field heard nothing identifying it. Fixed by passing `label="Notes"` through, matching every other field in the form.
- **Stale page after delete**, **the sort-toggle 3-state trap**, **the debounced-input focus-loss bug**, and **the `FilterPanel`-vs-`AdvancedFilter` toolbar mismatch** — all documented inline above where they're now fixed, since they materially describe how the module behaves today, not just what changed.
- **Verified clean, no changes needed:** no hardcoded colors/hex values anywhere in `features/companies/` (grepped); no dead code, unused exports, or duplicate constants/mappings; every icon-only affordance carries a visible label or `aria-label`; every spinner already carries `motion-reduce:animate-none`; responsive collapsing (table horizontal scroll, form grid to single-column, detail cards to single-column) all inherited correctly from the already-audited Sprint 2 component library since this module never overrides their breakpoint behavior.
- **Not done:** no live browser/screen-reader session was run for this pass — findings above came from static code review (reading every file in `features/companies/` plus its call sites) and the two prior rounds of live user-reported bugs (sidebar collapse alignment [app-shell, not part of this module], search width, sort toggling, filter popover layout), not fresh empirical testing of every breakpoint/theme combination. Flagging this rather than claiming full manual QA coverage.

## Fish Module (Sprint 4) — Complete

The second business module — full CRUD (List/Create/Edit/Detail/Delete) against the live backend, `features/fish/` (mirrors `app/modules/fish/` on the backend). Built by deliberately copying the Companies module's architecture session-for-session rather than redesigning anything, per this sprint's explicit brief; this section documents the module as it stands now. **Status: production-ready for its stated scope** — see "Explicitly out of scope" below.

### Architecture

```
features/fish/
  types/fish.ts              # BackendFish (snake_case, wire shape) + Fish (camelCase, client shape)
                              # + mapBackendFish() + FishCreateRequest/FishUpdateRequest/FishListParams
                              # + FISH_UNIT_LABELS/FISH_UNIT_OPTIONS (shared by the List page's filter and the Form's select)
  services/fish-service.ts   # listFish / getFish / createFish / updateFish / deleteFish
  hooks/                     # useFishes, useFish, useCreateFish, useUpdateFish, useDeleteFish,
                              # useFishFilters (URL state, see below)
  schemas/
    fish-filters.ts          # FishFilters shape + toFishListParams() mapper
    fish-form-schema.ts      # zod schema, FishFormValues, form <-> Fish/request payload mappers
  constants/                 # fish-status.ts, query-keys.ts (fishKeys)
  components/                # fish-columns.tsx, fish-row-actions.tsx, fish-form.tsx
  pages/                     # fish-list-page.tsx, fish-detail-page.tsx, fish-create-page.tsx, fish-edit-page.tsx
  index.ts                   # barrel — the module's public surface
```

`app/(authenticated)/fish/{page.tsx, new/page.tsx, [id]/page.tsx, [id]/edit/page.tsx}` are thin route wrappers, same as Companies. `app/api/fish/{route.ts, [id]/route.ts}` are the BFF proxy routes — GET/POST on the collection route, GET/PUT/DELETE on the `[id]` route, all built on the same `authenticatedBackendRequest()` Companies already established rather than re-implementing token attachment.

**One real structural difference from Companies: the permission model.** The backend's fish permissions are a coarse `fish:view` / `fish:manage` split (`app/modules/fish/permissions.py`), not four separate `create`/`edit`/`delete` codes like Companies (`app/modules/companies/router.py`). This is a genuine, intentional backend design choice for master-data modules with no per-action business rules to distinguish — not an oversight to work around. Every Fish page/action gate below uses `fish:manage` everywhere Companies would use `company:create`/`company:edit`/`company:delete`.

**`status` is a form/filter-only concept.** The backend has no `status` column on `fish` — only `is_active` (boolean). Rather than exposing a raw boolean toggle (worse UX, and inconsistent with every other status-bearing module), `fish-status.ts` defines a client-only `FishStatus = "active" | "inactive"` vocabulary with a `toFishStatus(isActive)` mapper, reused identically by the List page's Status filter, `FishForm`'s Status select, and the Detail/List page's status Badge. The conversion back to `is_active` happens at exactly two boundaries: `toFishListParams()` (filter → query param) and `toFishRequestPayload()` (form → request body) — nowhere else needs to know the boolean exists.

### BFF Integration

Same proxy pattern as Companies, no new mechanism: `features/fish/services/fish-service.ts` talks only to the Next.js BFF's own routes (`/api/fish/*`), never the FastAPI backend directly — the browser holds no bearer token to attach, since the access token lives in an `HttpOnly` cookie only the Next.js server can read (`ARCHITECTURE.md` §1.2/§8.1). `app/api/fish/route.ts` (GET list, POST create) and `app/api/fish/[id]/route.ts` (GET one, PUT update, DELETE) are thin handlers that each do nothing but call `authenticatedBackendRequest()` and forward the JSON response — the same function every other module's BFF routes already reuse, including its silent-refresh-on-401 retry. No Fish-specific auth code exists anywhere; a bug in token handling would be a shared-infrastructure fix, not a per-module one.

### Permission Model

Two permission codes gate the module: `fish:view`, `fish:manage` — read via `usePermissions()`, same as Companies:

- **List** — `fish:manage` hides "New Fish" (header action + genuinely-empty-state's CTA) and the row-level Edit/Delete actions; `fish:view` gates the row-level View action and whether a row click navigates at all.
- **Detail/Create/Edit pages** check their own required permission (`fish:view` for Detail, `fish:manage` for Create/Edit) *before* rendering anything else, returning a plain `ErrorState` instead of the page body — hooks are still called unconditionally above that check, per the Rules of Hooks.
- **Delete** is gated on `fish:manage` everywhere it appears (List row action, Detail page action).

Cosmetic only, same caveat as Companies — the backend re-validates every gated route regardless of what the UI hides.

### URL State

Every list control — `search`, `category`, `unit`, `status`, `page`, `pageSize`, `sort`, `direction` — lives in the URL via `useFishFilters()` (`features/fish/hooks/use-fish-filters.ts`), built on the same `nuqs` `useQueryStates()` pattern as `useCompanyFilters` — no new solution invented. `history: "push"` (Back/Forward step through prior list states), `shallow: true` (nuqs's default — no server round trip, `useFishes` reacts to the state change and refetches), and a refresh/pasted/shared URL all restore the exact list state. `sort`/`direction` are kept as two separate, readable URL params; `toFishListParams()` recombines them into the backend's single combined `-field` string only when calling the API.

`search` and `category` are debounced *before* they reach `useFishFilters` — `SearchBar` debounces internally, and `CategoryFilterField` (a small local wrapper in `fish-list-page.tsx`, the direct analog of Companies' `CityFilterField`) does the same for the Category filter. Both use `useExternalValueKey()` to remount only on a genuinely external change (Clear All, a removed chip, Back/Forward) — never on their own debounced write, which would otherwise unmount the input mid-keystroke and drop focus. `status` and `unit` write immediately (one click = one deliberate action = one correct history stop).

### Search

`SearchBar` — debounced, clear button, `Escape` to clear-and-refocus, all inherited from the shared component with no Fish-specific code. The loading slot is wired to `listQuery.isFetching` (spins on every in-flight fetch, not just the first), and a zero-result search shows a description naming the actual term (`No fish match "pomfret". Try a different search or clear your filters.`).

### Filters

`AdvancedFilter` (Popover + active-count badge) holds Status, Unit, and Category — `StatusFilter` (a generic button-group, not string-specific) is reused for both Status and Unit rather than building a second filter component, since both are small closed vocabularies with the same "pick one, click again to clear" interaction. `AppliedFilters` renders each active filter as a removable chip with one "Clear All"; the popover's own footer "Clear all" is scoped to while it's open, so there's exactly one Clear-All per visible context. Being Popover-based rather than an always-expanded panel, the whole filter row collapses naturally on narrow viewports without any Fish-specific responsive code.

### Sorting

Same controlled pattern as Companies: `filters.sort`/`filters.direction` fully drive the table's `sorting` state, and TanStack's default 3-state toggle (asc → desc → **unsorted**) is intercepted in `onSortingChange` so the "unsorted" step flips direction on the current column instead of clearing it (this list has no unsorted concept — the backend always sorts by something). The "Created At" column carries an explicit `id: "created_at"` distinct from its `accessorKey: "createdAt"` for the same reason as Companies: without it, a header click would send `sort=createdAt` to a backend that only recognizes snake_case.

### Table Polish

Verified against the shared `DataTable`/`useDataTable` (Sprint 2) with no Fish-specific overrides: sticky header (the component's own default), `stickyActionColumn` (pins the kebab menu), server-side sorting/pagination (`manualSorting`/`manualPagination` default `true`), and all four Loading/Empty/No-Results/Error states rendered inside `<tbody>` so the header never disappears mid-fetch.

### CRUD Flow

```
List (search/filter/sort/paginate)
  ├─ row action / row click "View" ──────────▶ Detail (read-only)
  ├─ row action "Edit" ───────────────────────▶ Edit (FishForm, pre-filled)
  ├─ row action "Delete" ─────────────────────▶ DeleteConfirmationDialog ──▶ useDeleteFish()
  └─ primary action "New Fish" ────────────────▶ Create (FishForm, empty)

Detail
  ├─ primary action "Edit" ───────────────────▶ Edit
  └─ secondary action "Delete" ────────────────▶ DeleteConfirmationDialog ──▶ useDeleteFish()
```

`FishForm` is the single shared form for both Create and Edit — Fish Name, Fish Code, Local Name, Scientific Name, Category, Unit, Status, HSN Code, Default Purchase/Sale Rate, Description — same zod validation (mirroring the backend's own checks: HSN 4/6/8 digits, rate precision to 4 decimals) and the same submit/error handling (422 → `mapServerErrorsToForm`, anything else → `toastError`) as `CompanyForm`. `useCreateFish`/`useUpdateFish`/`useDeleteFish` invalidate `fishKeys.lists()` on success (`useUpdateFish` also invalidates `fishKeys.detail(id)`, `useDeleteFish` removes it outright); `useDeleteFish` owns the entire delete outcome (invalidate, `toastSuccess`, navigate to `/fish`) so the Detail page's Delete button and the List page's row-action Delete behave identically. The List page's own stale-page-after-delete correction (page rewinds if it points past the new last page once a fetch confirms it) is inherited verbatim from the Companies pattern.

Every action is permission-gated — see "Permission Model" above.

**Explicitly out of scope** (per the Sprint 4 brief): Activity Timeline, Audit History, Attachments, Export, PDF. None of these are wired to the Fish module.

### Production Polish (Sprint 4 Session 4)

A review pass over the whole module against the same checklist the Companies QA pass used (URL state, search/filter UX, table polish, responsive layout, accessibility, performance) — fix only what's found, no new CRUD scope. Since every piece was built by deliberately mirroring an already-hardened Companies implementation rather than a fresh one, most of the checklist was already satisfied; real gaps found and fixed:

- **Unformatted rate values** — `FishDetailPage` displayed `fish.defaultPurchaseRate`/`defaultSaleRate` as raw wire strings (`"450.0000"`) instead of using the already-built `formatRate()` (`utils/format-number.ts`, NUMERIC(12,4) precision) the way every other rate/quantity/currency value in the app does. Fixed.
- **Repeated derivation** — `toFishStatus(fish.isActive)` was computed three separate times across the Detail page (badge, twice in the description list). Hoisted to one `status` value computed once per render.
- **Verified clean, no changes needed:** all 8 URL params (`search`/`category`/`unit`/`status`/`page`/`pageSize`/`sort`/`direction`) already synced correctly; no hardcoded colors/hex values in `features/fish/` (grepped); no dead code or unused exports; every form field already had a proper `label` (the exact bug class the Companies pass found in its Notes field doesn't recur here — checked field-by-field); every spinner already carries `motion-reduce:animate-none`; dialogs/dropdowns/comboboxes all inherit Radix's focus trap and keyboard support unchanged; responsive collapsing (table horizontal scroll, form grid to single column, detail cards to single column, filter popover collapse) all inherited correctly from the unmodified Sprint 2 component library.
- **Barrel export gap** — `features/fish/index.ts` had not been updated in Sessions 2–3 to export `FishForm`, the Create/Edit/Detail pages, the mutation hooks, or the form schema — only Session 1's list-page surface was ever re-exported. Brought fully up to date to match `features/companies/index.ts`'s completeness.
- **Not done:** no live browser/screen-reader session was run for this pass, same caveat as the Companies QA pass — findings came from static code review of every file in `features/fish/` plus its call sites, not fresh empirical testing of every breakpoint/theme combination.

### Final QA Pass (Sprint 4 Session 5)

The closing hardening pass, mirroring the Companies module's own Sprint 3 Session 5 process exactly — a full CRUD/permissions/responsive/dark-mode/accessibility/performance/cleanup review with a directive to fix only what's found, not add scope, and to mark the module complete once satisfied.

- **CRUD audit** — re-verified List, View, Create, Edit, Delete, permissions, search, filters, sorting, pagination, URL state, and all four Loading/Error/Empty/No-Results states, this time including the Create/Edit pages specifically (Session 4's pass focused mainly on List/Detail). All correct; no code changes required beyond the one comment fix below.
- **Stale comment** — `fish-form-schema.ts`'s doc comment on the `status` field still read "this session keeps the same Status select UX... (reusing FISH_STATUS_OPTIONS from Session 1)", a session-relative reference that had gone stale across three subsequent sessions. Reworded to state the fact plainly instead of anchoring it to when it was written.
- **Dark mode** — re-confirmed via grep across all of `features/fish/`: zero hardcoded colors (`text-gray-*`, `bg-white`, hex/`rgb()`/`hsl()` literals), every visual treatment (Badge variants, borders, muted text) comes from the same semantic Tailwind tokens the rest of the app themes off. Nothing in the module can render inconsistently between light/dark because nothing in it makes its own color decision.
- **Responsive** — re-checked Desktop/Laptop/Tablet/Mobile breakpoints across List (table horizontal scroll + toolbar wrap), Detail (two-column info cards collapsing to one), and Form (`FormGrid` two-column collapsing to one) — all inherited unmodified from the Sprint 2 component library, since the Fish module never overrides a breakpoint or grid-column value itself.
- **Accessibility** — re-verified keyboard navigation, focus order (natural DOM order everywhere, no manual `tabIndex`), `aria-invalid`/`aria-describedby` wiring on every form field (including the Combobox-based Unit/Status selects, which get both from `FormField`'s render props same as a plain `Input`), dialog focus trap (inherited from Radix `AlertDialog`), and reduced motion (`motion-reduce:animate-none` present on every spinner). No gaps found.
- **Performance** — re-checked React Query usage (`keepPreviousData` on the list query, `enabled: Boolean(id)` gating the detail query, correct `fishKeys.lists()`/`fishKeys.detail(id)` invalidation on every mutation), memoization (columns/row-actions/sorting all stable via `useMemo`/`useCallback`), and found no further duplicate renders or duplicate helpers beyond what Session 4 already fixed.
- **Code cleanup** — no unused imports, no dead code, no duplicate constants/mappings found (grepped and manually traced every export in the module's barrel back to a real call site). One stale comment fixed (above); nothing else warranted a change.

**Fish module marked complete** — full CRUD against the live backend, URL-synced list state, and two rounds of hardening (production polish + final QA), matching the Companies module's own bar for "production-ready for its stated scope."

### Extension Guidelines (for the next Masters module)

Fish proved the Companies pattern replicates cleanly to a second module. Building the next one (Boats, per `08_FRONTEND_IMPLEMENTATION_PLAN.md`'s sequencing) should follow the same shape:

1. **Copy the folder structure verbatim** — `types/`, `services/`, `hooks/`, `schemas/`, `constants/`, `components/`, `pages/`, `index.ts` — and rename, don't restructure.
2. **Check the backend's actual permission codes before assuming Companies' four-code shape.** Fish's `view`/`manage` split vs. Companies' `view`/`create`/`edit`/`delete` was a real, deliberate backend difference (`ARCHITECTURE.md` §9.2) — read the module's `permissions.py` and router `Depends(require_permission(...))` calls first, and gate the UI on whatever actually exists rather than copying Companies' code names by rote.
3. **Watch for fields with no direct backend equivalent** — Fish's `status` (client-only, derived from `is_active`) is the pattern for any other module where the natural UI concept doesn't map 1:1 onto a backend column: define the client vocabulary in `constants/`, convert at exactly the two boundaries (list-params mapper, form-payload mapper), and never let the raw backend shape leak into the URL/form field name unless it already matches.
4. **Reuse `authenticatedBackendRequest()` for every BFF route** without exception — no module should re-implement token attachment.
5. **Run the two-pass QA rhythm** — a production-polish pass (URL state, search/filter UX, table polish, accessibility, performance — fix what's found) followed by a final QA pass before calling a module done (CRUD re-audit, dark mode, responsive, cleanup, documentation) — rather than treating either as optional.

## Boat Module (Sprint 5) — Complete

The third business module — full CRUD (List/Create/Edit/Detail/Delete) against the live backend, `features/boats/` (mirrors `app/modules/boats/` on the backend). Built session-by-session by mirroring the Companies/Fish architecture rather than redesigning anything, per the sprint's explicit brief; this section documents the module as it stands now, not session-by-session. **Status: production-ready for its stated scope** — see "Explicitly out of scope" below for what's deliberately not built.

### Architecture

```
features/boats/
  types/boat.ts              # BackendBoat (snake_case, wire shape) + Boat (camelCase, client shape)
                              # + mapBackendBoat() + BoatCreateRequest/BoatUpdateRequest/BoatListParams
  services/boat-service.ts   # listBoats / getBoat / createBoat / updateBoat / deleteBoat
  hooks/                     # useBoats, useBoat, useCreateBoat, useUpdateBoat, useDeleteBoat,
                              # useBoatFilters (URL state, see below)
  schemas/
    boat-filters.ts          # BoatFilters shape + toBoatListParams() mapper
    boat-form-schema.ts      # zod schema, BoatFormValues, form <-> Boat/request payload mappers
  constants/                 # boat-status.ts, query-keys.ts (boatKeys)
  components/                # boat-columns.tsx, boat-row-actions.tsx, boat-form.tsx
  pages/                     # boat-list-page.tsx, boat-detail-page.tsx, boat-create-page.tsx, boat-edit-page.tsx
  index.ts                   # barrel — the module's public surface
```

`app/(authenticated)/boats/{page.tsx, new/page.tsx, [id]/page.tsx, [id]/edit/page.tsx}` are thin route wrappers, same as Companies/Fish. `app/api/boats/{route.ts, [id]/route.ts}` are the BFF proxy routes — GET/POST on the collection route, GET/PUT/DELETE on the `[id]` route, all built on the same `authenticatedBackendRequest()` Companies established rather than re-implementing token attachment.

**Permission model matches Companies, not Fish.** The backend defines four separate codes for boats — `boat:view`, `boat:create`, `boat:edit`, `boat:delete` (`app/modules/boats/permissions.py`) — not Fish's coarser `view`/`manage` split. This was verified by reading the actual permissions module before wiring any UI gate, per the Fish module's own "extension guideline" (don't assume the next module's permission shape by rote).

**No company relationship.** A boat is owned by the tenant only (`tenant_id`) — a `Company` is a customer (the buyer on an invoice), never a boat owner. An earlier build of this module (Sprint 5 Sessions 1–5) incorrectly gave `Boat` a required `company_id` foreign key with a full `AsyncSelect` picker in the form and a resolved name on the Detail page; that was a business-model error, not a UI choice, and was removed wholesale in a dedicated correction — see "Business Model Correction" below for what changed and why. Nothing in the module talks to `features/companies/` anymore.

### Permission Model

- **List** — `boat:create` hides "New Boat" (header action + genuinely-empty-state's CTA); `boat:view`/`boat:edit`/`boat:delete` each independently hide their respective row action, and `boat:view` additionally gates whether a row click navigates at all.
- **Detail/Create/Edit pages** check their own required permission (`boat:view`/`boat:create`/`boat:edit`) *before* rendering anything else, returning a plain `ErrorState` instead of the page body — hooks are still called unconditionally above that check, per the Rules of Hooks (same pattern as Companies/Fish).
- **Delete** is gated on `boat:delete` everywhere it appears (List row action, Detail page action).

Cosmetic only, same caveat as Companies/Fish — the backend re-validates every gated route regardless of what the UI hides (`ARCHITECTURE.md` §9.3).

### URL State

Every list control — `search`, `boatType`, `status`, `insuranceExpired`, `licenseExpired`, `page`, `pageSize`, `sort`, `direction` — lives in the URL via `useBoatFilters()` (`features/boats/hooks/use-boat-filters.ts`), built on the same `nuqs` `useQueryStates()` pattern as `useCompanyFilters`/`useFishFilters` — no new solution invented. `history: "push"` (Back/Forward step through prior list states), `shallow: true` (nuqs's default — no server round trip, `useBoats` reacts to the state change and refetches), and a refresh/pasted/shared URL all restore the exact list state. `sort`/`direction` stay two separate, readable URL params; `toBoatListParams()` recombines them into the backend's single combined `-field` string only when calling the API.

`insuranceExpired`/`licenseExpired` are the module's one new parser shape: `parseAsBoolean` with **no** `.withDefault()`, so an absent param resolves to `null` (not present) rather than `false` — a genuine tri-state ("any" / "expired" / "not expired"), matching `BoatFilters.insuranceExpired: boolean | null` and rendered via the shared `BooleanFilter` (`Switch`, on/off only — checked reflects `=== true`, and unchecking always clears back to `null` rather than writing `false`, since "show me boats with valid insurance" isn't a filter this list needs).

`search` and `boatType` are debounced *before* they reach `useBoatFilters` — `SearchBar` debounces internally, and `BoatTypeFilterField` (the direct analog of Fish's `CategoryFilterField`/Companies' `CityFilterField`) does the same for the Boat Type filter, both using `useExternalValueKey()` to remount only on a genuinely external change (Clear All, a removed chip, Back/Forward) rather than on their own debounced write, which would otherwise drop focus mid-keystroke. `status` writes immediately (one click = one deliberate action).

There is no `companyId` list filter — a boat has no company relationship to filter by (see "No company relationship" above).

### Search

`SearchBar` — debounced, clear button, loading slot wired to `listQuery.isFetching`, all inherited from the shared component with no Boat-specific code. A zero-result search shows a description naming the actual term (`No boats match "falcon". Try a different search or clear your filters.`), matching Companies/Fish.

### Filters

`AdvancedFilter` (Popover + active-count badge) holds Status, Boat Type, and the two expiry `BooleanFilter`s — Popover-based rather than an always-expanded panel, so the whole filter row collapses naturally on narrow viewports with no Boat-specific responsive code. `AppliedFilters` renders each active filter (search/status/boat type/insurance/license) as a removable chip with one "Clear All"; the popover's own footer "Clear all" is scoped to while it's open, so there's exactly one Clear-All per visible context, matching Companies/Fish.

### Sorting

Same controlled pattern as Companies/Fish: `filters.sort`/`filters.direction` fully drive the table's `sorting` state, and TanStack's default 3-state toggle (asc → desc → **unsorted**) is intercepted in `onSortingChange` so the "unsorted" step flips direction on the current column instead of clearing it. The "Created At" column carries an explicit `id: "created_at"` distinct from its `accessorKey: "createdAt"` for the same reason as Companies/Fish: without it, a header click would send `sort=createdAt` to a backend that only recognizes snake_case `created_at`/`updated_at`.

### Table Polish

Verified against the shared `DataTable`/`useDataTable` (Sprint 2) with no Boat-specific overrides: sticky header (the component's own default), `stickyActionColumn` (pins the kebab menu), server-side sorting/pagination, and all four Loading/Empty/No-Results/Error states rendered inside `<tbody>` so the header never disappears mid-fetch. Row click navigates to `/boats/{id}` when `boat:view` is held, same gating as the row-level View action.

### Detail Page

`BoatDetailPage` (`components/data-display/{InfoCard,DescriptionList}` + `layout/SectionHeader` + `templates/DetailPageTemplate`, mirroring `CompanyDetailPage`/`FishDetailPage` exactly) renders three cards:

- **Details** — Boat Name, Boat Code, Registration Number, Boat Type, Capacity (`formatQuantity`, NUMERIC(12,3) precision — same formatter Fish uses for its rate fields), Status, Created At, Updated At (`formatDateTime`).
- **Engine & Compliance** — Engine Number, Engine Power (a plain `Integer` column on the backend, not `Decimal` — shown as a raw `${n} HP` rather than run through a NUMERIC-precision formatter, since there's no decimal precision to preserve), Captain Name, Captain Phone, License Number, License Expiry, Insurance Expiry (`formatDate` — calendar dates, not `formatDateTime`, since the backend stores them as `Date` not `Timestamp`).
- **Notes** — free text, or the shared `EmptyState` ("No notes added") when blank, matching Companies'/Fish's own Notes/Description card.

Status badges reuse the same `Badge` + `BOAT_STATUS_BADGE_VARIANT` pair the List page's Status column uses — one source of truth for the color mapping, never redefined per page.

### CRUD Flow

```
List (search/filter/sort/paginate)
  ├─ row action / row click "View" ──────────▶ Detail (read-only)
  ├─ row action "Edit" ───────────────────────▶ Edit (BoatForm, pre-filled)
  ├─ row action "Delete" ─────────────────────▶ DeleteConfirmationDialog ──▶ useDeleteBoat()
  └─ primary action "New Boat" ────────────────▶ Create (BoatForm, empty)

Detail
  ├─ primary action "Edit" ───────────────────▶ Edit
  └─ secondary action "Delete" ────────────────▶ DeleteConfirmationDialog ──▶ useDeleteBoat()
```

`BoatForm` is the single shared form for both Create and Edit — Boat Name, Boat Code, Registration Number, Boat Type, Capacity, Status, Engine Number, Engine Power, Captain Name, Captain Phone, License Number/Expiry, Insurance Expiry, Description — grouped into `FormSection`s ("Boat Details", "Engine & Crew", "Compliance", "Description") over `FormGrid`, the same layout primitives Companies/Fish use (see "Production Polish" below for why this wasn't true until Session 4). Validation mirrors the backend's own checks (phone 7–15 digits, capacity to 3 decimals, engine power a non-negative integer) and the same submit/error handling (422 → `mapServerErrorsToForm`, anything else → `toastError`) as `CompanyForm`/`FishForm`. `useCreateBoat`/`useUpdateBoat`/`useDeleteBoat` invalidate `boatKeys.lists()` on success (`useUpdateBoat` also invalidates `boatKeys.detail(id)`, `useDeleteBoat` removes it outright); `useDeleteBoat` owns the entire delete outcome (invalidate, `toastSuccess`, navigate to `/boats`) so the Detail page's Delete button and the List page's row-action Delete behave identically. The List page's stale-page-after-delete correction (page rewinds if it points past the new last page once a fetch confirms it) is inherited verbatim from the Companies/Fish pattern.

Every action is permission-gated — see "Permission Model" above.

**Explicitly out of scope** (per the Sprint 5 brief, through Session 4): Activity Timeline, Audit History, Attachments, Export, PDF. None of these are wired to the Boat module.

### Production Polish (Sprint 5 Session 4)

A review pass over the whole module against the same checklist the Companies/Fish polish passes used (URL state, search/filter UX, table polish, detail page formatting, responsive layout, accessibility, performance) — fix only what's found, no new CRUD scope. Unlike Fish (which mirrored an already-hardened Companies build closely enough to need only two small fixes), this pass found a genuine structural gap in the form:

- **`BoatForm` didn't use the shared `FormSection`/`FormGrid` layout primitives.** It was built with raw `<div className="grid grid-cols-1 gap-4 sm:grid-cols-2">` markup instead — a different collapse breakpoint (`sm:` vs. `FormGrid`'s `md:`, meaning tablet-portrait users got squeezed into two columns where every other form in the app stays single-column), different spacing tokens (`gap-4` vs. `FormGrid`'s `gap-x-4 gap-y-5`), and no section grouping (`CompanyForm`/`FishForm` both divide their fields into titled `FormSection`s; the Boat form was one flat block). Rebuilt using `FormSection` + `FormGrid`, split into "Boat Details" / "Engine & Crew" / "Compliance" / "Description" — now byte-for-byte consistent with how Companies/Fish compose the same primitives.
- **Unformatted capacity in the List table** — `boat-columns.tsx`'s Capacity column rendered the raw wire string (`"12000.000"`) instead of `formatQuantity()` (`utils/format-number.ts`, NUMERIC(12,3) precision), the same formatter the Detail page already used correctly. Fixed, so List and Detail now agree on presentation.
- **Unmemoized option-list mapping** — `BoatForm`'s `company_id` `AsyncSelect` options array was rebuilt via a fresh `.map()`/`.unshift()` on every render regardless of whether the underlying query data had changed. Wrapped in `useMemo`, keyed on the two query results. *(The `company_id` field itself, and this whole option-list mechanism, was removed in Session 6 — see "Business Model Correction" below. Kept here as an accurate record of what this session actually did.)*
- **Verified clean, no changes needed:** all 9 URL params (`search`/`boatType`/`status`/`insuranceExpired`/`licenseExpired`/`page`/`pageSize`/`sort`/`direction`) already synced correctly, including the two boolean tri-state params; no hardcoded colors/hex values in `features/boats/` (grepped); every spinner already carries `motion-reduce:animate-none`; dialogs (`DeleteConfirmationDialog`)/dropdowns (row actions)/comboboxes (`AsyncSelect`/`SearchableSelect`) all inherit Radix's focus trap and keyboard support unchanged; `DataTableRowActions` already stops row-click propagation so opening the kebab menu never also navigates; responsive collapsing (table horizontal scroll, detail cards to single column, filter popover collapse) all inherited correctly from the unmodified Sprint 2 component library — the Detail page and List page never override a breakpoint themselves, only the Form did (fixed above).
- **Not done:** no live browser/screen-reader session was run for this pass, same caveat as the Companies/Fish polish passes — findings came from static code review of every file in `features/boats/` plus its call sites, not fresh empirical testing of every breakpoint/theme combination.

### Final QA Pass (Sprint 5 Session 5)

The closing hardening pass, mirroring the Companies/Fish modules' own Session 5 process exactly — a full CRUD/permissions/responsive/dark-mode/accessibility/performance/cleanup review with a directive to fix only what's found, not add scope, and to mark the module complete once satisfied.

- **CRUD audit** — re-verified List, View, Create, Edit, Delete, permissions, search, filters, sorting, pagination, URL state, and all four Loading/Error/Empty/No-Results states. All correct; no code changes required beyond the two stale comments below.
- **Two stale comments** — `boat-service.ts`'s doc comment still read "Sprint 5 Session 1 built list/get; Session 2 adds create/update... **Delete is still out of scope**," which had gone factually wrong the moment `deleteBoat()` was added in Session 3 (the comment sat directly above the method it contradicted). `boat-list-page.tsx`'s doc comment similarly read "Sprint 5 Session 3 completes the CRUD workflow," a session-relative description of what changed rather than a plain statement of current behavior — the same class of staleness the Fish module's own Session 5 pass fixed in `fish-form-schema.ts`. Both reworded to state the current facts plainly, with no reference to which session added them.
- **Dark mode** — re-confirmed via grep across all of `features/boats/`: zero hardcoded colors (`text-gray-*`, `bg-white`, hex/`rgb()`/`hsl()` literals), no `console.log`/`TODO`/`FIXME` left behind either. Every visual treatment (Badge variants, borders, muted text) comes from the same semantic Tailwind tokens the rest of the app themes off, same as Companies/Fish.
- **Responsive** — re-checked Desktop/Laptop/Tablet/Mobile breakpoints across List (table horizontal scroll + toolbar wrap), Detail (two-column info cards collapsing to one), and Form (`FormGrid` two-column collapsing to one, fixed in Session 4) — all inherited unmodified from the Sprint 2 component library.
- **Accessibility** — re-verified keyboard navigation, focus order, `aria-invalid`/`aria-describedby` wiring on every form field (including the `AsyncSelect`/`SearchableSelect`-based Company/Status fields, which get both from `FormField`'s render props same as a plain `Input`), dialog focus trap (inherited from Radix `AlertDialog`), and reduced motion (`motion-reduce:animate-none` present on every spinner). No gaps found.
- **Performance** — re-checked React Query usage (`keepPreviousData` on the list query, `enabled: Boolean(id)` gating the detail/company queries, correct `boatKeys.lists()`/`boatKeys.detail(id)` invalidation on every mutation), memoization (columns/row-actions/sorting/company-options all stable via `useMemo`/`useCallback`, the last one fixed in Session 4), and found no further duplicate renders or duplicate helpers.
- **Code cleanup** — no unused imports, no dead code, no duplicate constants/mappings found (grepped and manually traced every export in the module's barrel back to a real call site — `index.ts` was already complete, unlike Fish's own Session 4 barrel gap). Two stale comments fixed (above); nothing else warranted a change.

**Boat module marked complete** — full CRUD against the live backend, URL-synced list state (9 params, including two genuinely tri-state booleans), and two rounds of hardening (production polish + final QA), matching the Companies/Fish modules' own bar for "production-ready for its stated scope." *(This session's build still had the `company_id` foreign key to `companies` described in Sessions 1–5 above — a business-model error, corrected in Session 6; see "Business Model Correction" below.)*

### Business Model Correction (Sprint 5 Session 6)

A dedicated domain-model fix, not a feature session — `Boat` had a required `company_id` foreign key to `companies` from the module's very first session onward (see the now-removed "Company Relationship" section that used to sit above, and the annotations left in the Sessions 4/5 notes above for the historical record). That was wrong: per `ARCHITECTURE.md`'s own Context section and Business Model, a `Company` is a **customer** — the buyer on an invoice — never a boat owner. The correct flow is `Tenant → Boats → Trips → Trip Catch → Invoice → Company (customer) → Payment`; purchasing stays `Supplier → Purchase Bill → Supplier Payment`, entirely unrelated to boats. A boat is owned by `tenant_id` alone.

**What was removed, end to end:**

- **Backend** — `boats.company_id` column, its FK/index, `Boat.company` / `Company.boats` relationships, `BoatService._ensure_company_exists()` (and its `CompanyService` cross-module dependency), `BoatCompanyNotFoundError`, every `company_id` reference in the boat schemas/repository/router (request/response bodies, list filter, OpenAPI examples/descriptions). A new Alembic migration (`e2b8f4a91c6d_drop_boats_company_id`) drops the column/FK/index non-destructively — every other boat column and row is untouched (verified live: 11 pre-existing boat rows survived the upgrade with the column gone, and the downgrade path was also verified to restore it). Every backend test that built a boat fixture (unit, integration, and the cross-module ones in the trip/invoice/payment test suites that provision a boat as a prerequisite) had its `company_id` argument/fixture stripped — `company_id` remains everywhere it's legitimately used for `Invoice`/`Payment`'s real customer relationship, untouched.
- **Frontend** — `Boat`/`BackendBoat`/`BoatCreateRequest`/`BoatUpdateRequest`/`BoatListParams` all lost `company_id`/`companyId`. `BoatForm` lost its entire "Owning Company" `AsyncSelect` field, the two `companyService`/`useQuery` lookups backing it (search + id-scoped resolve), the merged/memoized options list, and the `companyService` import outright — the form is back to a single `FormSection`/`FormGrid` shape with no cross-feature dependency. `BoatDetailPage` lost its "Company" row and `useCompany(boat.companyId)` lookup. `boat-service.ts` lost the `company_id` query-string param. No Boat file imports anything from `features/companies/` anymore.
- **Documentation** — `ARCHITECTURE.md` §5.2's `boats` table sketch (which had specified `owner_company_id FK companies NULL` from the start — the origin of the mistake) now carries an "As built" note stating the corrected ownership model and the real implemented column set. This README's Boat Module section (above) was edited in place for every claim that described *current* architecture (Architecture, Detail Page, CRUD Flow, URL State, Extension Guidelines); the Sessions 4/5 sections were left as historical record of what was actually built then, with inline annotations pointing here rather than being rewritten.

**Verification:** full backend suite (2445 tests), `ruff`, `mypy --strict` all clean; frontend `lint`/`type-check`/`build` all clean. No compatibility shim, no deprecated-but-kept field, no TODO — the relationship is gone, not hidden.

### Extension Guidelines (for the next module)

For the next module (Trips, per `08_FRONTEND_IMPLEMENTATION_PLAN.md`'s sequencing — which references both `boats` and `companies` for real, legitimate reasons: a trip has a `boat_id`, and its catch is eventually sold to a `Company` via an invoice):

1. **Copy the folder structure verbatim**, same as Fish's own guideline — `types/`, `services/`, `hooks/`, `schemas/`, `constants/`, `components/`, `pages/`, `index.ts`.
2. **Check the backend's actual permission codes first** — don't assume either the Companies four-code shape or the Fish two-code shape; Boats happened to match Companies, but that was verified, not assumed.
3. **Verify a cross-feature foreign key against the actual business model before building it** — this module's biggest lesson, and the reason Session 6 exists at all. A field compiling, validating, and rendering correctly proves nothing about whether the relationship it encodes is real; `ARCHITECTURE.md`'s Business Model section is the source of truth for who owns what, and it should have been checked before `company_id` was ever added to the `Boat` schema. When a cross-feature reference *is* legitimate (e.g. Trip → Boat, Invoice → Company), import the other feature's service/hook directly (`companyService`, `useCompany`) rather than duplicating a lookup — there's no shared "entity selector registry" in this codebase.
4. **Always build forms out of `FormSection`/`FormGrid`, never a raw grid `div`** — Session 4's finding, still valid. The visual result of a raw grid can look identical at a glance; check new form components against `CompanyForm`/`FishForm` specifically, not just "does it look like a form."
5. **Run the same two-pass QA rhythm** — production-polish pass followed by a Final QA pass before calling a module done — rather than treating either as optional or conflating them. Neither pass caught the `company_id` design error, because both were scoped to *how the module was built*, not *whether the schema it was built against was correct* — a reminder that QA checklists catch execution bugs, not requirements bugs. When in doubt about a schema decision, check the architecture doc, not just the code that already implements it.

## Current Status

**Sprint 1 (Sessions 1–5)** — engineering foundation, authentication, the application shell, global UX infrastructure, and reusable page templates. **Sprint 2 (Sessions 1–5)** — the full reusable Component Library: Enterprise Data Table, Form Components, Filtering/Search/Pagination, Charts & Reporting, and a finalization pass. **Sprint 3 (Sessions 1–5) — complete** — the Companies module: full CRUD (List/Create/Edit/Detail/Delete) against the live backend, URL-synced list state, UX polish, and a final QA/hardening pass — see "Companies Module" above. **Sprint 4 (Sessions 1–5) — complete** — the Fish module: full CRUD built by deliberately mirroring the Companies architecture, URL-synced list state, a production-polish pass, and a final QA/hardening pass — see "Fish Module" above. **Sprint 5 (Sessions 1–6) — complete** — the Boat module: full CRUD, URL-synced list state, a production-polish pass, a final QA/hardening pass, and a Session 6 business-model correction (removed an incorrectly-added `company_id` boat-ownership field — a boat belongs to the tenant only) — see "Boat Module" above. The Companies module proved the reusable library out end-to-end; Fish proved the *pattern itself* replicates to a second module with a different (coarser) permission model; Boats proved that even a completed, QA-passed module can carry a business-model defect that only a domain-level review catches, not a code-level one.

- Project scaffold, TypeScript strict mode, ESLint, Tailwind v4.
- shadcn/ui configured (New York style, Slate base color, CSS variables).
- Theme system (light/dark/system via next-themes), now switchable via the topbar `ThemeSwitcher`.
- TanStack Query client + provider (dev-only devtools); retry only on network/server errors for reads, never for mutations.
- Two HTTP clients: `src/lib/api-client.ts` (direct-to-backend; unused by Companies and every module that needs auth, for the reason documented above — kept for any future genuinely-public/unauthenticated backend call) and `src/lib/bff-client.ts` (same-origin — auth **and** all business data, e.g. Companies, go through this) — both share one error-normalization pipeline (`src/lib/http-error.ts`, `src/lib/create-http-client.ts`). Business-data BFF routes (`app/api/companies/**`) attach the caller's token server-side via `src/lib/auth/authenticated-backend-request.ts`.
- Full authentication — see above.
- Full application shell — Sidebar, Top Navigation, Breadcrumbs, permission-aware navigation — see above.
- A mock-data Dashboard (`(authenticated)/dashboard`) proving the whole stack end-to-end: auth guard → shell → `SummaryGrid`/`MetricCard` KPIs → permission-filtered quick actions — not yet the real, backend-wired Dashboard (still pending the backend's reporting endpoints).
- Formatting utilities matching the backend's Decimal precision (currency: 2dp, quantity: 3dp, rate: 4dp).
- Full global UX infrastructure — loading/skeletons, empty/error states, dialogs, toasts, shared page components, error-handling hooks — see above.
- Full reusable page templates and navigation infrastructure — List/Detail/Form/Settings/Report templates, Toolbars, Filter Bar, data-display primitives — see above.
- The Enterprise Data Table (`src/components/data-table/`) — see above. `@tanstack/react-table` added as a dependency in Sprint 2 Session 1.
- Enterprise Form Components (`src/components/form/`) — see above. `react-day-picker`, `cmdk` added as dependencies in Sprint 2 Session 2.
- Filtering, Search & Pagination (`src/components/filters/`, `src/components/pagination/`, three new hooks) — see above.
- Charts & Reporting Components (`src/components/charts/`, `src/components/reports/`, `src/components/dashboard/`) — see above. `recharts` already present as a dependency.
- Sprint 2 Session 5's component library finalization pass — consistency/accessibility/dark-mode/documentation audit across all of the above — see above.
- The Companies module (`src/features/companies/`) — see "Companies Module" above. `nuqs` added as a dependency in Sprint 3 Session 4 for URL-synced list state.
- The Fish module (`src/features/fish/`) — see "Fish Module" above. No new dependencies; proves the Companies pattern replicates to a module with a coarser (`view`/`manage`) permission model and no dedicated `status` column.
- The Boat module (`src/features/boats/`) — see "Boat Module" above. No new dependencies; proves the pattern extends to a module with a genuinely tri-state boolean filter (`insuranceExpired`/`licenseExpired`). Two rounds of hardening (production polish + final QA) complete, same bar as Companies/Fish, plus a Session 6 business-model correction that removed an incorrect `company_id` foreign key added in Sessions 1–5 — a boat is owned by the tenant only, never by a `Company` (a customer) — see "Business Model Correction" above.

Next up: the next Masters module per `08_FRONTEND_IMPLEMENTATION_PLAN.md`'s sequencing (Trips, ...), following the same pattern the Companies, Fish, and Boat modules now establish.
