# QueueLess Pulse Design System

The design system uses existing React, Radix Dialog, Lucide and CSS. No new UI framework or externally hosted font is needed. `frontend/src/tokens.css` defines colors, semantic surfaces, type, spacing, radii, elevation, motion, control sizes and layout widths. System fonts provide an offline-safe fallback for Inter.

Navy `#112B43` establishes navigation and primary text; teal `#007F86` indicates primary actions. Success, warning and error foregrounds are darkened for readable text on soft surfaces. CALLED is informational; COMPLETED is success; WAITING and ON BREAK are warning. Text labels accompany color.

`components/system.tsx` contains PageHeader, Breadcrumbs, KPIStatCard, StatusBadge, TokenDisplay, ActionToolbar, EmptyState, IconButton, AccessibleTooltip, Drawer, ConfirmationDialog, FilterBar, Search, DateFilter, Pagination, DataTable and QRDisplayCard. Existing Button, Form, Dialog, loading, errors, toast and connection components remain shared. Domain service/queue/patient cards compose these primitives rather than duplicate their visual behavior.

Desktop navigation uses a 232px sidebar. At 900px and below, a modal navigation drawer replaces the horizontal scroller. All form and button controls have a 44px minimum target. At 700px, operational columns stack; at 480px forms use one column. Body overflow is not hidden to disguise layout defects; scrollable data tables are labeled keyboard regions. Dialogs use Radix focus trapping and focus restoration.

Keyboard focus uses a visible teal ring; dark navigation uses a lighter ring. Reduced-motion disables nonessential animation and transitions. Safe-area padding supports Android. Foreground live data always has connection feedback and error/retry behavior. Accessibility targets WCAG 2.2 AA; automated checks complement keyboard/manual visual checks and are not a compliance certification.

Compatibility: existing URLs, accessible action labels and the legacy Flask interface remain available. This checkpoint changes presentation and common components only; it does not alter authorization or persisted queue semantics.
