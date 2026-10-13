# QueueLess Pulse design system

The approved Lovable healthcare prototype is adapted into the existing React, Lucide, Radix Dialog and CSS components. No UI framework, hosted font or simulated queue engine was added. `frontend/src/tokens.css` defines navy `#0e2d43`, teal `#007f86`, pale background `#f3f9f9`, mint accents and semantic status colors. The Inter-first system font stack works without a network font download. Text and icons accompany status colors.

## Purposeful shells

Patient entry uses a quiet brand/recovery header and a service card with live queue facts. Direct service QR links bypass selection; legitimate multi-business/service choices remain. The private token page is centered around its number, position, estimate and real transition history. Internal-role navigation is absent from public pages.

Doctor and Reception use compact workspace/account headers, without a universal sidebar or duplicate breadcrumbs. Doctor places duty controls above four factual indicators, a navy active consultation and a FIFO waiting list. Reception places a real service QR beside permission-controlled walk-in issuance, then shows real queue activity. Owner uses Overview, Team & Services, Reviews and Settings. Team, service and branch controls are meaningful expandable groups inside management. Display has a dedicated navy kiosk shell and public information only.

## Shared components

`components/system.tsx` provides page headers, KPI cards, status badges, token display, action toolbars, empty states, icon controls, tooltips, drawers, confirmation dialogs, filter/date/search controls, pagination, labeled data tables, keyboard tabs and QR cards. Existing buttons, forms, feedback, toast and connection components remain shared. Domain components compose these primitives with their existing API data and mutation handlers.

The eye illustration in `components/eye-artwork.tsx` is decorative SVG adapted from the approved prototype. Instance-specific SVG IDs prevent collisions. It carries no metrics, identity or queue state. Generic services receive a generic illustration and truthful service copy.

## Responsive and accessible behavior

Operational columns stack when space is constrained. Patient entry stacks at 620px; Doctor and Owner analytics stack at 800px; Reception stacks at 620px. KPI grids reduce columns without obscuring facts. The five review widths are 1440, 1366, 768, 390 and 360px. Controls have a 44px minimum target; data tables scroll inside labeled keyboard regions. Body overflow is not hidden to disguise layout defects. QR and ticket printing use explicit print scopes.

Visible focus rings, reduced motion and safe-area padding remain. Radix dialogs trap and restore focus. Owner tabs implement Arrow Left/Right, Home/End and roving focus with associated panels; hidden panels retain unsaved fields. Frontend connection feedback and retry states reflect actual requests. Automated WCAG 2.2 AA checks supplement keyboard and visual review; they are not a compliance certification.

## Real data and compatibility

Hourly arrivals/completions come from the Owner operations API, with a readable data table. Empty dates show an explicit empty state, never fabricated bars. Today is evaluated in the business timezone; historical completed tickets remain date-filterable. Public Display does not expose private ticket links, patient identities or credentials. Backend transactions, role checks, assignments, CSRF, recovery ownership and migrations are unchanged by this reconstruction. See `LOVABLE_COMPONENT_MAPPING.md`, `UX_ROUTE_INVENTORY.md` and `HOSPITAL_WORKFLOWS.md`.
