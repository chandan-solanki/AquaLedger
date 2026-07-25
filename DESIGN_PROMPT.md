# FishERP — UI Design Mockup Prompt

This is a self-contained prompt. Copy everything in the code block below and paste it into a new Claude conversation to generate an interactive HTML mockup of the FishERP application.

---

```
You are a senior product designer and front-end engineer. Design and build an interactive,
self-contained HTML mockup for "FishERP" — a production-grade ERP system for the seafood
industry, used by fish traders, wholesalers, exporters, boat owners, and seafood companies.

This is a data-dense B2B business application, not a consumer app. The tone is professional,
trustworthy, and efficient — closer to a banking/accounting dashboard than a marketing site.
Users enter dozens of invoices and trip records a day, so clarity, density, and keyboard-friendly
forms matter more than decoration.

═══════════════════════════════════════════════════════════════════
TECH & COMPONENT LANGUAGE TO MATCH
═══════════════════════════════════════════════════════════════════
The real app is built with Next.js 15, React 19, TypeScript, Tailwind CSS, and shadcn/ui
("new-york" style). Design every screen using that visual vocabulary — buttons, inputs, selects,
tables, cards, badges, tabs, dialogs/modals, dropdown menus, avatars, a slide-out sheet for mobile
nav, a command palette (⌘K) for global search, toasts, and skeleton loaders. Use an outlined icon
set in the style of lucide-react. Do not invent a different visual language.

═══════════════════════════════════════════════════════════════════
DESIGN SYSTEM (define and apply consistently — no existing branding exists yet)
═══════════════════════════════════════════════════════════════════
Palette: a neutral slate base with a teal/ocean accent (evokes the seafood/maritime domain
without being kitschy or overly literal — no cartoon fish, no beachy gradients).

Provide full light AND dark theme token sets (CSS variables), both meeting WCAG AA contrast.
Avoid pure black or pure white — use soft off-white / deep slate instead. Suggested tokens:

  Light theme:
    --background: slate-50        --foreground: slate-900
    --card: white                 --border: slate-200
    --primary: teal-600           --primary-foreground: white
    --muted: slate-100            --muted-foreground: slate-500
    --accent: teal-50             --destructive: red-600
    --success: emerald-600        --warning: amber-500       --info: blue-600

  Dark theme:
    --background: slate-950       --foreground: slate-100
    --card: slate-900             --border: slate-800
    --primary: teal-400           --primary-foreground: slate-950
    --muted: slate-800            --muted-foreground: slate-400
    --accent: teal-950            --destructive: red-500
    --success: emerald-500        --warning: amber-400       --info: blue-400

Typography: a clean sans-serif (Inter/Geist-style). Use tabular/monospaced-figure numerals for
ALL money, quantity, and rate values so columns of numbers align — this matters a lot in an ERP.
Clear heading hierarchy; compact-but-readable table row density (this is a data entry tool, not
a spacious landing page).

Status/lifecycle badge colors — apply these consistently everywhere a status appears:
  draft = slate/gray · issued = blue · posted = blue · partially paid = amber · paid = emerald
  overdue = red · cancelled = muted red/gray (subdued, not alarming) · cheque pending = amber
  cheque cleared = emerald · cheque bounced = red

Build a working light/dark theme toggle (sun/moon icon in the topbar) that live-switches all
screens.

═══════════════════════════════════════════════════════════════════
INFORMATION ARCHITECTURE — full sitemap to design
═══════════════════════════════════════════════════════════════════
This maps directly to FishERP's backend modules. Design navigation for ALL of these, and build
out full mockup screens for the ones marked ★ (see "Screens to fully build" below).

Auth
  - Login ★

Dashboard ★
  - KPI cards: total receivables outstanding, total payables outstanding, trips currently at sea,
    boats with expiring license/insurance, recent invoices, recent payments, quick profit snapshot
  - Small charts (revenue trend, receivables aging) and an alerts/notifications panel

Masters
  - Companies — customer master (fields: code, name, GSTIN, PAN, address, company type
    customer/supplier/both, credit limit, credit days, outstanding balance, status) ★
  - Suppliers — separate vendor master used for purchase bills (code, name, GSTIN, contact,
    credit days, outstanding balance, status)
  - Fish — item master (code, name, local name, category, unit kg/box/piece/ton, default
    purchase/sale rate, HSN code, active flag)

Operations
  - Boats — registration, license/insurance expiry (flag boats with expired/expiring documents),
    captain info, ownership type
  - Trips — list (status: planned/departed/returned/cancelled) + detail page with tabs for
    Overview, Catches (fish landed by grade A/B/C with caught/available/sold/waste quantities),
    Expenses (diesel/ice/food/labour/harbour/etc.), and a profit summary

Finance
  - Invoices (sales) — list + Invoice Editor ★ (see detailed spec below)
  - Payments (customer receipts) — list + record-payment screen with invoice allocation
  - Purchase Bills (vendor bills) — list + bill editor (mirrors the invoice editor, but line
    items have no fish/trip-catch link — just description/qty/rate/tax)
  - Supplier Payments — list + record-payment screen with purchase-bill allocation

Insights (backend not built yet — show as "Coming Soon" nav entries, still fully placed in the IA)
  - Reports & Analytics
  - Documents

Settings
  - Company/tenant profile
  - Users & Roles (RBAC roles: super_admin, admin, manager, accountant, operator — show a
    permissions matrix concept)
  - Fish categories, expense categories, invoice/payment numbering sequences

Account menu (avatar dropdown, top-right)
  - Profile, Change Password, Logout

═══════════════════════════════════════════════════════════════════
APP SHELL / NAVIGATION
═══════════════════════════════════════════════════════════════════
Left sidebar (collapsible to icon-only rail):
  - Grouped by section headers matching the IA above (Masters / Operations / Finance / Insights)
  - Active-route highlighting, section grouping with subtle dividers
  - Design as if nav items can be role-gated (e.g. Settings only visible to admin roles) — you
    don't need real logic, just make the sidebar look like it supports this
  - On mobile/narrow viewports, collapses into a slide-out drawer (hamburger trigger)

Top bar:
  - Left: tenant/company name (+ placeholder logo mark)
  - Center or left-of-actions: global search input styled as a command palette trigger ("⌘K
    Search companies, invoices, trips…")
  - Right: theme toggle, notification bell (with a badge count), user avatar menu

Breadcrumbs on all detail/edit pages (e.g. Trips / TRP-2024-0142).

═══════════════════════════════════════════════════════════════════
REUSABLE PAGE PATTERNS
═══════════════════════════════════════════════════════════════════
Apply these two patterns consistently across every module rather than designing each ad hoc:

1) LIST pages: page header (title + primary "+ New" button) → filter bar (free-text search,
   status dropdown, date range) → sortable data table with status badges and a row kebab menu
   (View/Edit/Delete) → pagination footer. Include an empty-state design and a loading-skeleton
   state, not just the happy path with data.

2) DETAIL pages: header with entity title, status badge, and lifecycle action buttons (e.g.
   "Issue Invoice", "Post Payment") → tabbed or sectioned body → related-records tables where
   relevant (e.g. a Trip detail's Catches and Expenses tabs).

═══════════════════════════════════════════════════════════════════
THE INVOICE EDITOR (design this one in the most detail — it's the core screen of the app)
═══════════════════════════════════════════════════════════════════
- Header: company selector (searchable), invoice date, due date, draft/issued status badge
- Dynamic line-items table: fish selector (searchable autocomplete), a linked trip-catch
  reference (since invoice lines pull from available boat-catch stock), quantity, unit, rate,
  discount %, tax rate, and a live-calculated line total — add/remove rows inline, Enter-to-add-row
  keyboard flow
- Right-side or bottom totals panel: subtotal, discount, taxable amount, CGST/SGST/IGST
  breakdown, transport charge, other charges, round-off, grand total, paid amount, balance due —
  all recalculating live as line items change
- Footer actions: Save Draft, Issue Invoice (issuing should read as a locking/finalizing action —
  e.g. a confirm dialog, since issued invoices become immutable)

Also design the mirror screens more briefly:
- Payment recording screen: payment amount, method, reference, and a table of the customer's
  open invoices where the user allocates the payment across one or more of them, with a running
  "unallocated" balance
- Purchase Bill editor: same shape as the invoice editor minus the fish/trip-catch linkage
- Supplier Payment screen: mirrors the payment/allocation screen for purchase bills

═══════════════════════════════════════════════════════════════════
SCREENS TO FULLY BUILD (make these clickable/navigable within the mockup)
═══════════════════════════════════════════════════════════════════
At minimum, build these as real, navigable views within one interactive mockup (use JS to switch
between views — sidebar links should actually work):
  1. Login
  2. Dashboard
  3. Companies — list view
  4. Invoices — list view
  5. Invoice Editor — create/edit view (the detailed screen above)
  6. Trip detail — with its Overview/Catches/Expenses tabs

For every other item in the sitemap, at least include it as a working sidebar link (even if it
routes to a simple placeholder/"Coming Soon" screen for Reports and Documents).

═══════════════════════════════════════════════════════════════════
DATA
═══════════════════════════════════════════════════════════════════
Populate every screen with realistic, seafood-industry-appropriate sample data — real-sounding
company names (exporters/wholesalers), fish names (pomfret, tuna, shrimp/prawn, mackerel, squid),
boat names, Indian GSTIN-shaped codes, and plausible INR amounts — not lorem ipsum or "Company A".

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════
Produce a single self-contained HTML file (inline CSS and JS, no external network dependencies)
that:
  - Implements the sidebar + topbar app shell described above
  - Lets me click through the sidebar to navigate between the screens listed in "Screens to fully
    build," plus placeholder screens for everything else in the IA
  - Has a working light/dark theme toggle affecting the whole app
  - Is responsive down to a laptop/tablet width (this is a desktop-first data tool, but shouldn't
    break above ~1024px; a basic mobile drawer nav is a nice-to-have, not the priority)
```
