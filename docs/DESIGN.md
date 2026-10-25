# PaySetu: Design System and UX Guidelines

| Field | Value |
| --- | --- |
| Status | Draft v1.3: "Warm Ledger" visual direction adopted on 25 Oct 2026 (final redesign; reference: the Aceternity Schedule marketing template's general style, no assets copied), replacing v1.2 "Oxford Blue + Stone". Contrast verified for every token pair in use (Section 2.1). All non-colour requirements are unchanged |
| Scope | Supplier web app (mobile-first), Buyer Cost Page, Advocate view, generated PDFs |
| Rule | When this document and an individual screen disagree, this document wins. Change the document first, then the screen |

---

## 1. Visual Direction

### 1.1 The idea: a calm, warm, precise workspace ("Warm Ledger")

*Adopted 25 Oct 2026 for the final redesign. It replaces "Oxford Blue + Stone" (v1.2), which replaced the v1.1 blue-and-white palette; the principles in 1.2 stand.*

PaySetu should feel like a **mature, human-centred B2B product** for people who are not lawyers: warm white surfaces, charcoal type, crisp black primary buttons and a single orange accent used sparingly for emphasis. The visual reference is the general style of Aceternity's Schedule marketing template (white and warm off-white, bold controlled headings, thin borders, soft radius, bento feature sections, a faint peach gradient in marketing sections). Its branding and assets are not copied.

| Do | Don't |
| --- | --- |
| White cards (8–14px radius, 1px `rule` border, a hairline `shadow-card`) on a warm `canvas` | Glassmorphism, heavy shadows, gradient-covered dashboards |
| **One primary (black) action per view**; everything else secondary (outlined) or a text link | Several black buttons competing on one screen |
| Orange only for emphasis: a dot, an active-navigation bar, a headline word, links in `accent-strong` | Orange as body text colour at small sizes, or as a status colour |
| A faint peach radial gradient only in the landing hero and the sign-in pages | Gradients inside the working app |
| Bento sections on the landing page with real explanations and clearly labelled sample content | Fake statistics, testimonials, user counts or "AI" claims |
| Numbers and dates as the hero content, in tabular figures | Charts, scores or progress meters that are not backed by data |
| Plain language with the legal reference available on demand (glossaries, "Why this date?") | Legal jargon up front |

### 1.2 Design principles

1. **Dates first.** Acceptance date, due date and days remaining are the most important information on any case screen. They are always visible without scrolling on a phone.
2. **One next action.** Each case screen shows exactly one primary "next step" based on its state. Other actions are secondary.
3. **Show the proof.** Wherever a file or event appears, its hash and recorded time are one tap away. Integrity is visible, not hidden in settings.
4. **Nothing leaves without a look.** Anything that goes to a buyer or advocate is previewed in full and approved with a deliberate action. The UI never sends on a single accidental tap.
5. **Honest labels.** Simulated, sandbox, draft and illustrative content is labelled every time it appears, in the same visual style.
6. **Built for the gate.** Core capture works one-handed on a mid-range Android phone in daylight, with large touch targets and the camera one tap away.
7. **Explain, don't advise.** Legal explanations use "PaySetu reads the Act as…" phrasing and link to the rule ID. They never use "you will win" or "you are entitled to" without qualification.

---

## 2. Color

### 2.1 Tokens

All colors are referenced by token name, never by raw hex in components (`frontend/src/app/globals.css`). The MVP has a light theme only (PRD D9).

| Token | Hex | Use |
| --- | --- | --- |
| `canvas` | `#FAFAF8` | Page background of the app; alternating landing sections |
| `surface` | `#FFFFFF` | Cards, panels, inputs, header, sidebar, landing background |
| `surface-subtle` | `#F5F5F3` | Quiet panels, active navigation, upload zones |
| `surface-hover` / `surface-sunken` | `#EEEDEA` | Hover, hash wells, skeletons, neutral badges |
| `peach` | `#FFF2E9` | Gradient tint and highlight panels (marketing, auth, amount callouts) |
| `rule` | `#E6E5E1` | Card borders, dividers (decorative) |
| `rule-strong` | `#D4D3CE` | Timelines, secondary-button borders (decorative; the button text identifies it) |
| `control` | `#858585` | Boundaries of inputs, selects and checkboxes (3:1 or more on every surface, WCAG 1.4.11) |
| `ink` | `#262626` | Primary text |
| `ink-muted` | `#5E5E5E` | Secondary text, labels |
| `ink-faint` | `#737373` | Placeholders inside white inputs and decorative icons only |
| `primary` / `primary-hover` | `#262626` / `#000000` | Black primary buttons; filled timeline markers |
| `accent` | `#F28B53` | **Decorative only**: dots, active-navigation bar, next-step rule, day-strip "today", gradients |
| `accent-display` | `#D9622A` | Large headline emphasis only (24px bold and up) |
| `accent-strong` | `#A4471A` | Orange text and links at any size |
| `info` / `info-tint` (= `primary-tint`) | `#A4471A` / `#FFF2E9` | Notices, "Calculated by PaySetu" labels |
| `success` / `success-tint` | `#2B6E47` / `#E8F3EC` | Verified, met, settled |
| `warning` / `warning-tint` | `#8A5710` / `#FBF1DF` | Warnings, pending legal review, demo and sample labels |
| `danger` / `danger-tint` | `#B42318` / `#FCECEA` | Genuine errors, integrity failure |
| `focus` | `#A4471A` | Focus ring (2px, offset 2px) |

**Verified contrast (WCAG 2.2, relative-luminance formula; computed 25 Oct 2026 from `globals.css`):**

| Foreground | `surface` | `canvas` | `surface-subtle` | `surface-hover` | `peach` |
| --- | --- | --- | --- | --- | --- |
| `ink` | 15.1 | 14.5 | 13.9 | 12.9 | 13.8 |
| `ink-muted` | 6.5 | 6.2 | 5.9 | 5.5 | 5.9 |
| `ink-faint` (placeholders only) | 4.7 | 4.5 | 4.3 ✗ | 4.1 ✗ | 4.3 ✗ |
| `accent-strong` / `info` / `focus` | 6.0 | 5.8 | 5.5 | 5.1 | 5.5 |
| `accent-display` (large text only) | 3.7 | 3.5 | – | – | 3.3 |
| `accent` (decorative only) | 2.4 | 2.3 | 2.2 | 2.1 | 2.2 |
| `control` (boundary) | 3.7 | 3.5 | 3.4 | 3.2 | 3.4 |
| `success` / `warning` / `danger` | 6.1 / 6.1 / 6.6 | 5.9 / 5.8 / 6.3 | 5.6 / 5.6 / 6.0 | 5.2 / 5.2 / 5.6 | – |

White on `primary` 15.1:1. Status colours on their own tints: success 5.4, warning 5.4, danger 5.7; `ink` 13.2+ and `ink-muted` 5.7+ on every tint. ✗ = below 4.5:1, so that pair is not used for text. `accent` (#F28B53) fails even the 3:1 large-text minimum on white, so it never carries text: orange words use `accent-display` (large) or `accent-strong` (any size).

Retired: the v1.2 Oxford Blue and brass tokens (`brass` became `accent`).

### 2.2 Rules

- Text contrast is at least 4.5:1 against its background, and at least 3:1 for large text and UI boundaries (inputs and other controls use `control`). Use only pairs marked as passing in 2.1; verify any new pair before use.
- Status is never shown by color alone. Every status color comes with an icon and/or a text label.
- **Red (`danger`) is only for genuine errors and evidence-integrity failures.** Verified and sealed states are green (`success`); pending legal review, demo and simulated labels are amber (`warning`).
- Tints are for backgrounds only. Text on a tint uses the matching strong token (e.g. `warning` text on `warning-tint`).
- **Overdue** is shown as a `warning` badge with text, not a red headline (it is a status, not a system error). **Interest** figures use `ink` with an "Illustrative" label. Do not color interest green; it is not income yet.

---

## 3. Typography

### 3.1 Typefaces

| Role | Family | Why |
| --- | --- | --- |
| UI and body | **Geist Sans** (variable weight; 400, 500, 600 and 700 for marketing headlines) | Clear at small sizes, precise and neutral; loaded with `next/font/google` |
| Hashes, references, code | **Geist Mono** | Distinguishes 0/O and 1/l; makes hashes readable |
| Future Hindi | To be chosen (Geist has no Devanagari); a Devanagari face with matching metrics must be selected before Hindi ships | – |

Fonts are self-hosted through the framework's font optimisation; there are no runtime calls to font CDNs. Fallback: `system-ui, sans-serif`.

### 3.2 Scale (rem, base 16px)

Values are the `--text-*` tokens in `frontend/src/app/globals.css`.

| Token | Size / line height | Weight | Use |
| --- | --- | --- | --- |
| `display` | 1.75 / 2.25 | 600 | Financial figures (28px); max one per card |
| `h1` | 1.875 / 2.375 | 600 | Page title (30px); the landing hero uses 36–56px bold |
| `h2` | 1.25 / 1.75 | 600 | Section title (20px) |
| `h3` | 1 / 1.5 | 600 | Card title (16px) |
| `body` | 0.9375 / 1.5 | 400 | Default text (15px) |
| `body-strong` | 0.9375 / 1.5 | 500 | Emphasis, labels in key-value lists |
| `small` | 0.8125 / 1.25 | 400 | Secondary text, helper text, table cells (13px) |
| `caption` | 0.75 / 1 | 500 | Badges, timestamps, legal footnotes (12px; minimum size for any text) |
| `mono` | 0.8125 / 1.25 | 400 | Hashes, case references (Geist Mono) |

### 3.3 Number and date formatting

| Kind | Format | Example |
| --- | --- | --- |
| Money | `Rs` + Indian grouping, no decimals by default; paise shown in calculation tables only | Rs 5,00,000 / Rs 93,407.12 |
| Dates | `DD MMM YYYY` | 01 Nov 2026 |
| Date with day number | `DD MMM YYYY · Day N` | 16 Nov 2026 · Day 15 |
| Timestamps | `DD MMM YYYY, HH:mm IST` | 01 Nov 2026, 14:32 IST |
| Relative | Only alongside an absolute date | "in 3 days (04 Nov 2026)" |
| Hash (short) | First 8 + `…` + last 4, mono | `9f2c41ab…e07d` |
| Case reference | `PS-YYYY-NNNN`, mono | PS-2026-0042 |
| Rates | Two decimals + `% a year` | 17.25% a year |

All numbers in tables, amounts and dates use **tabular figures** (`font-variant-numeric: tabular-nums`).

---

## 4. Spacing and Layout

### 4.1 Spacing scale

Base unit is 4px. Allowed values: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64`. No other values.

| Use | Value |
| --- | --- |
| Inside compact controls (badge) | 4 / 8 |
| Inside inputs and buttons | 12 vertical × 16 horizontal |
| Between related fields | 16 |
| Between form sections / cards | 24 |
| Page section gaps | 32 (mobile) / 48 (desktop) |
| Page side gutter | 16 (mobile) / 24 (tablet) / 32 (desktop) |

### 4.2 Shape and elevation

- Radius: `8px` for inputs, buttons and small controls; `12px` for cards and dialogs; `999px` for pills (badges) only. Nothing larger.
- Elevation: borders (`rule`) by default. Shadows are only for floating layers (dialogs, menus, toasts): one shadow token, `0 4px 16px rgba(27,36,48,0.12)`.
- Cards: white `surface` with a 1px `rule` border on the `canvas` background. Lists and timelines inside a card use 1px `rule` dividers, not a card per row.

### 4.3 Grid and widths

| Breakpoint | Width | Columns | Navigation |
| --- | --- | --- | --- |
| `sm` (default) | < 640px | 4 | Top bar + bottom tab bar |
| `md` | ≥ 640px | 8 | Top bar + bottom tab bar |
| `lg` | ≥ 1024px | 12 | Left sidebar (240px) + top bar |
| `xl` | ≥ 1280px | 12 | Same; content max width 1120px |

- Reading content (letters, legal pages, the Buyer Cost Page) is capped at **720px**.
- Forms are capped at **560px** for a single column. Desktop may use two columns only for short paired fields (e.g. invoice number + date).
- No horizontal page scroll at any width ≥ 320px. Wide tables become stacked rows on `sm` (see 5.12).

---

## 5. Components

Every screen is built from these components. A new component needs a reason recorded in this section first.

### 5.1 Button

| Variant | Look | Use |
| --- | --- | --- |
| `primary` | `primary` fill, white text | The single next action on a screen or dialog |
| `secondary` | `surface` fill, `rule-strong` border, `ink` text | Other actions |
| `ghost` | Text only, `primary` color | Tertiary/inline actions |
| `danger` | `danger` fill, white text | Destructive confirmations only (revoke, close case) |

- Height 44px (48px for the mobile primary in the sticky action bar). Minimum width 88px.
- States: default, hover, pressed, focus-visible (focus ring), disabled (40% opacity, `aria-disabled`, explained by helper text), loading (spinner replaces the leading icon, label stays, button disabled).
- Labels are verbs that describe the outcome: "Approve and send", "Record objection", "Generate pack". Never "Submit" or "OK".
- At most **one** `primary` button visible per view region.

### 5.2 Inputs

- Label above the field, always visible (no placeholder-as-label). Helper text below in `small`/`ink-muted`. The error replaces the helper text in `danger`, with an icon.
- Height 44px; 16px font size (prevents iOS zoom).
- **Specialised fields:**
  - `MoneyField`: `Rs` prefix, numeric keyboard (`inputmode="decimal"`), live Indian grouping on blur, stores paise.
  - `DateField`: native date picker on mobile; shows the formatted date and day-of-week beside it; enforces min/max (e.g. no future delivery dates).
  - `UdyamField`, `GSTINField`: uppercase, mono, format mask, validated on blur.
  - `Select`: native select on mobile.
  - `RadioCards`: for 2–4 options with explanations (e.g. deal type: "Verbal / no written terms" vs "Written terms").
  - `Textarea`: for summaries and notes, with a character count when limited.
- Required fields are marked "(required)" in the label text. Optional fields are left unmarked only when most fields are required. Be consistent within a form.

### 5.3 File capture and upload: `EvidenceUploader`

- On mobile, two buttons: **Take photo** (opens the camera via `capture`) and **Choose file**. On desktop: a drop zone plus a "Choose file" button.
- An evidence type `Select` is required before upload. It is pre-filled from context (e.g. "Delivery challan" on the new-delivery form).
- Each file row shows: name, size, progress bar → then "Sealed" with a `HashChip` once the server confirms the hash.
- Never show a client-side preview edit, crop or rotate tool. Evidence is stored as captured.
- A rejected file shows the reason inline and keeps the other files.

### 5.4 `HashChip`

- A mono short hash (`9f2c41ab…e07d`) in a `surface-sunken` well, with a small check icon once the server has confirmed the hash.
- Tap/click opens a popover with: the full hash (selectable), the algorithm (SHA-256), the recorded time, and a "Copy" button (with a "Copied" confirmation announced to screen readers).

### 5.5 `StatusBadge`

A pill with an icon and a text label. Fixed vocabulary:

| Status | Tone | Icon |
| --- | --- | --- |
| Window open | `info` | clock |
| Window closing (≤3 days) | `warning` | clock-alert |
| Objection raised | `warning` | flag |
| Accepted (deemed / acknowledged / objection removed) | `success` | check |
| Not due | neutral (`surface-sunken`/`ink-muted`) | calendar |
| Overdue | `danger` | alert |
| Settled | `success` | check-double |
| Closed | neutral | archive |
| Draft / Approved / Sent / Send failed / Sent manually | neutral / `info` / `success` / `danger` / `success` | — |
| Simulated / Demo | `warning` | flask |
| Sealed / Integrity verified | `success` | shield-check |
| Integrity failed | `danger` | shield-alert |

### 5.6 `DayStrip`: the DeemedClock visual (signature component)

- A horizontal strip of 16 equal cells, **Day 0 to Day 15**, on a `surface-sunken` track.
- Elapsed days are filled `primary-tint`; today has a `primary` outline and a "Today" caption; Day 15 is labelled "Last day to object".
- An objection marker (flag icon, `warning`) sits on the day it was received. Acknowledgements get a check marker.
- Below the strip, one sentence states the state: "Day 6 of 15 · 9 days left for the buyer to object in writing."
- After Day 15, the strip collapses to a single completed bar with the acceptance result: "Deemed accepted on 01 Nov 2026 (no written objection by Day 15)."
- Accessible as an ordered list with text for each marker. The visual is `aria-hidden`; the sentence is the accessible label.
- On phones narrower than 360px, the cells become 8px wide with labels only on Day 0, today and Day 15.

### 5.7 `KeyDates` panel

- A vertical register of rows: label (left, `ink-muted`) and value (right, tabular, `body-strong`), with a "Why?" link on each legal date opening a `LegalNote`.
- Rows: Delivered · Last day to object · Acceptance date · Payment due · Interest from · Indicative limitation.
- Unknown values show "Not fixed yet" with the reason, never a blank or a dash alone.

### 5.8 `AmountSummary`

- Rows: Invoice amount · Paid so far · Outstanding · Interest to [date] (Illustrative) · **Total claimable** (emphasised with a top rule).
- An "As of" `DateField` (default today) when interactive.
- A "See calculation" link opens the period-by-period table.

### 5.9 `LegalNote`

- An inline callout with an `info-tint` background and a left 3px `info` border.
- Structure: plain explanation (1–3 sentences) → "Basis: MSMED Act s.2(b) · Rule R3" in `small` → "PaySetu's reading. Confirm with counsel." in `caption`.
- Used for every "Why this date?" explanation, and on the Buyer Cost Page.

### 5.10 `NextActionCard`

- Appears at the top of the case overview: a title ("Send the delivery intimation"), one sentence of reason, one primary button.
- The content is chosen by rule from case state (see 9.4). It is never empty: if nothing is pending, show "Nothing to do now. We'll show the next step on [date]."

### 5.11 `Timeline`

- A vertical ruled list in time order (newest first by default, toggle to oldest first).
- Each row shows: time (IST), actor ("You", "System", "Advocate link: A. Sharma", "Buyer link"), event description, and a `HashChip` for the event hash. Linked evidence or communications show as inline links.
- Backdated or "recorded later" events show a `warning` caption: "Recorded 5 days after delivery".
- An integrity status banner at the top: "Chain verified 01 Nov 2026, 14:32 IST" (`success`) or "Not verified since last change" (neutral) or "Chain broken at entry #14" (`danger`).

### 5.12 `DataList` (table on desktop, stacked on mobile)

- Desktop: a table with a `surface-sunken` header, 1px row rules and right-aligned numbers.
- Mobile: each row becomes a block with a title line (primary field + `StatusBadge`) and 2–3 key-value lines. The whole block is tappable (44px+ height).
- Sorting via column headers on desktop and a "Sort" select on mobile. Filters sit in a collapsible bar.

### 5.13 `ChecklistItem`

- Status icon (met check / missing circle / warning triangle / not-applicable dash) + title + level tag ("Required" or "Recommended") + a one-line action. An action button opens the relevant screen or uploader.
- A summary header: "7 of 9 required items complete". **Never** a percentage gauge, score or probability.

### 5.14 `ApprovalReview` (dialog or full-screen on mobile)

Used before sending any communication or creating any share link.

1. A full preview of exactly what will be sent or shared (the rendered letter, or the list of what the recipient will see).
2. Recipient details.
3. A required checkbox with specific wording: "I have read this letter and approve sending it to [buyer email] in the name of [supplier legal name]."
4. A primary button with the specific verb: "Approve and send". It stays disabled until the box is checked.
5. A secondary "Back to edit" button.

### 5.15 `ShareLinkCard`

- Purpose (Buyer cost page / Advocate), recipient, created date, expiry with countdown, status (Active / Expired / Revoked), view count, "Copy link", "View access log", and "Revoke" (`danger`, with confirmation).

### 5.16 `Banner`

| Kind | Use |
| --- | --- |
| `SimulatedBanner` | Persistent, top of the app, when the server runs with any simulated provider: "Demo mode: emails and verifications are simulated." (`warning` tone) |
| `OfflineBanner` | "You're offline. Changes will not be saved." |
| `DisclaimerFooter` | On every page: "PaySetu prepares evidence. It is not legal advice." + link |

### 5.17 Feedback components

- **Toast:** bottom-centre on mobile, bottom-right on desktop; auto-dismiss after 5s for success, persistent for errors; max 2 stacked; `role="status"` (success) or `role="alert"` (error).
- **Skeleton:** `surface-sunken` blocks matching the final layout shape; subtle shimmer that is disabled under reduced motion.
- **Spinner:** only inside buttons or for an operation under 3s; longer operations use `StepProgress`.
- **StepProgress:** named steps with current-step text (used for pack generation and integrity verification).
- **EmptyState:** a one-line title, one sentence of why it matters, one primary action. A small line icon is optional. No illustrations.
- **ErrorState:** what happened (plain words), what the user can do, a "Retry" button, and a support reference (request ID) in `caption`.

### 5.18 Icons

- A single icon set: Lucide (outline, 1.5px stroke), 20px in UI and 16px inline.
- Icons always accompany text, except standard universal controls (close, menu, copy). Those have `aria-label`s.

---

## 6. Navigation

### 6.1 Supplier app

| Mobile bottom tabs (≤1023px) | Desktop sidebar (≥1024px) |
| --- | --- |
| Home · Cases · **[+] New delivery** (centre, raised, `primary`) · Buyers · More | Home · Cases · New delivery (button) · Buyers · Settings, with the supplier name and logout at the bottom |

- The top bar shows the page title, a back arrow on detail pages, and the `SimulatedBanner` above it when active.
- **Case detail sub-navigation:** horizontal scrollable tabs: Overview · Evidence · Responses · Payments · Letters · Checklist · Timeline · Share. The active tab is underlined in `primary`. Tabs are routes (deep-linkable).
- **Breadcrumbs:** desktop only, on case and buyer detail pages.

### 6.2 External pages (Buyer, Advocate)

- No app navigation. A simple header with the PaySetu wordmark, a "Shared by [supplier legal name]" line, and a link expiry notice. Footer disclaimer.

---

## 7. Forms

1. One column, top to bottom, in the order the user has the information (e.g. the challan in hand → invoice number first).
2. Group into sections with `h3` headings when the form has more than 6 fields.
3. Validate on blur and on submit; never on each keystroke. On submit errors, move focus to an error summary at the top that links to each field.
4. Preserve input on any error, including network failure.
5. Smart defaults: delivery date = today; evidence type from context; deal type = verbal (the most common informal case). Defaults are visible and editable.
6. **New delivery form** (speed-critical):
   - Step order: Buyer (search-or-create inline) → Invoice number → Invoice date → Amount → Delivery date → Deal type → Photo/file → Save.
   - A sticky bottom action bar on mobile with **Save delivery**.
   - Optional fields (description, location, agreed terms when verbal) are collapsed under "More details".
   - After save: go to the case overview with a success toast and the `NextActionCard` "Send the delivery intimation".
7. Destructive or irreversible actions (revoke link, close case, exclude evidence, approve letter) need a confirmation dialog that names the object. Exclusion and closing also require a reason field.

---

## 8. Loading, Empty and Error States

Follow PRD Section 13 for content. Visual rules:

| State | Rule |
| --- | --- |
| Initial page load | Skeleton in the final layout shape; never a full-page spinner |
| Under 300 ms | Show nothing (avoid flicker) |
| Action under 3 s | Button loading state |
| Action over 3 s | `StepProgress` with step names; the user can leave the page and gets a toast when done (for pack generation) |
| Empty | `EmptyState` component; the primary action matches the screen's purpose |
| Field error | Inline below the field + error summary on submit |
| Request error | `ErrorState` within the affected region only; the rest of the page stays usable |
| Not found / no access | Same message for both, to avoid leaking existence |
| Session expired | Redirect to login with "Your session ended. Sign in to continue." and return to the same page afterwards |
| Integrity mismatch | Not styled as a system error: a `danger` result panel listing the items, with an explanation of what it means and what to do |

---

## 9. Interactions and Motion

### 9.1 Motion rules

- Durations: 120 ms (hover, press), 200 ms (expand, collapse, tabs), 250 ms (dialogs, sheets). Easing: `cubic-bezier(0.2, 0, 0, 1)`.
- Motion explains a change of state or place. It is never decorative. No parallax, no bouncing, no number count-up animations on amounts.
- `prefers-reduced-motion: reduce` → all transitions become instant fades of 0 ms to 100 ms; skeleton shimmer is off.

### 9.2 Feedback

- Every tap gives visible feedback within 100 ms (pressed state).
- Optimistic UI is allowed only for non-legal, reversible actions (e.g. filters). Anything that writes to the timeline waits for server confirmation before showing success.
- Copying a link or hash shows a "Copied" inline confirmation for 2s.

### 9.3 Sealing moment

When an evidence upload is confirmed, the row's progress bar turns into a `HashChip` with a brief 200 ms fade. This is the one deliberate "delight" moment in the product. It reinforces that the file is now sealed. No confetti.

### 9.4 Next-action rules (`NextActionCard`)

In priority order, the first matching rule wins:

1. Integrity failed → "Review integrity problem"
2. Objection raised → "Resolve the objection and record when it was removed"
3. Intimation not sent and window open → "Send the delivery intimation"
4. Required checklist evidence missing → "Upload [missing item]"
5. Overdue and no demand → "Send a demand letter"
6. Overdue and demand sent → "Generate the Sealed Pack"
7. Pack exists and case still overdue → "Share with your advocate or file on the ODR portal"
8. Not due → "Nothing to do now. Payment is due on [date]."
9. Settled → "Close this case"

---

## 10. Responsive Behaviour

| Element | `sm`/`md` | `lg`/`xl` |
| --- | --- | --- |
| Navigation | Bottom tabs + top bar | Sidebar + top bar |
| Case overview | Single column: NextAction → DayStrip → KeyDates → AmountSummary | Two columns: left (NextAction, DayStrip, KeyDates), right (AmountSummary, Checklist summary, recent timeline) |
| Data tables | Stacked rows | Tables |
| Dialogs | Full-screen sheets sliding up | Centred dialog, max 560px (letters: 800px) |
| Primary form action | Sticky bottom bar | Inline at the end of the form |
| Letter preview | Full width, zoomable PDF image | Side-by-side edit and preview |

- Minimum supported width: 320px. Touch targets ≥ 44×44px, with ≥ 8px between adjacent targets.
- Test on a 360×800 Android viewport as the primary design size.

---

## 11. Accessibility Requirements (WCAG 2.2 AA)

1. Semantic HTML first: real `button`, `a`, `label`, `table`, and headings in order (one `h1` per page).
2. Every input has a programmatic label. Errors are linked via `aria-describedby` and announced.
3. Visible focus on every interactive element (2px `focus` ring with 2px offset). Focus is never removed.
4. Full keyboard operation. Dialogs trap focus, close on Escape and return focus to the trigger.
5. Color is never the only signal (see 2.2). Contrast meets 4.5:1 for text and 3:1 for UI elements.
6. Live regions: toasts, upload completion and integrity results are announced politely; errors assertively.
7. Text resizes to 200% without loss of content; the layout reflows at 320px CSS width.
8. Dates are announced in full ("1 November 2026"), not as "01/11".
9. Hashes have an accessible label ("SHA-256 hash, starts 9f2c41ab, ends e07d"), with the full value available to copy.
10. Generated PDFs: tagged where the library allows, real text (not images of text), a logical reading order, and document language set to English.
11. No time limits on user input, other than session expiry with warning.
12. Respect `prefers-reduced-motion`.

---

## 12. Page-Level Layout Guidance

### 12.1 Landing (`/`)

A single column, max 720px wide. Content: the product name; one sentence of what it does; three short points (record the delivery, keep sealed proof, export a claim pack); a clear "what PaySetu is not" line; Sign up and Log in buttons; the disclaimer. No stock imagery.

### 12.2 Onboarding (`/onboarding`)

Three short steps with a step indicator: **Business** (legal name, Udyam, class, activity, registration date) → **Contact and signatory** → **Review and consent** (eligibility summary panel + consent checkbox). The eligibility summary uses `StatusBadge` + `LegalNote`, one line per rule.

### 12.3 Dashboard (`/app`)

1. Greeting line with the supplier's trade name (small, not a hero).
2. **Needs attention** list (DataList) with a badge and the next action per case. If empty: "Nothing needs attention today."
3. Totals row: three key-value blocks (Outstanding · Overdue · Illustrative interest), not charts.
4. Recent cases (5) + "View all".

### 12.4 New delivery (`/app/cases/new`)

A single column form (Section 7.6), the camera button prominent, and a sticky Save on mobile.

### 12.5 Case overview (`/app/cases/[id]`)

Header: case reference (mono), buyer name, invoice number, and the `StatusBadge`s (acceptance + payment). Then the layout from Section 10. The single `display`-size figure is:

- the window countdown while the window is open
- the due date while the case is not yet due
- the total claimable once overdue

### 12.6 Evidence (`/app/cases/[id]/evidence`)

`EvidenceUploader` at the top; a DataList grouped by evidence type (invoice, delivery, order, communications, responses, payments, other); each row has the type, name, received time, `HashChip` and a menu (Download, Exclude). Excluded items are collapsed under "Excluded (N)". A "Verify integrity" secondary button with the last result.

### 12.7 Responses, Payments, Letters

Each is a list + one primary "Record…" or "Prepare…" action that opens a form sheet. Letters show their lifecycle with `StatusBadge`s; opening a draft goes to an edit + preview layout; approval uses `ApprovalReview`.

### 12.8 Checklist

The summary header, then the required items, then the recommended items. Each item has an action button.

### 12.9 Share (`/app/cases/[id]/share`)

Three sections:

1. **Sealed Packs:** versions list with the manifest `HashChip`, created time, simulated flag, and Download.
2. **Advocate links:** `ShareLinkCard`s + "Share with an advocate".
3. **Buyer cost links:** `ShareLinkCard`s + "Create buyer link".

### 12.10 Buyer Cost Page (`/b/[token]`)

Max 720px, print-friendly (it prints cleanly to A4). Order:

1. "Payment statement from [supplier]".
2. Invoice block.
3. KeyDates (read-only).
4. AmountSummary as of today.
5. Three `LegalNote`s (s.16, s.19, s.43B(h)).
6. Supplier contact details.
7. Disclaimer and expiry notice.

Tone is factual and non-threatening: no red headline, and "Overdue" appears only as a badge.

### 12.11 Advocate view (`/a/[token]`)

Header with the supplier and case reference, plus the link expiry. Then:

- a case summary (KeyDates + AmountSummary)
- a pack download (with manifest hash)
- a "Verify integrity" button
- a read-only timeline
- the evidence list with hashes (download only via the pack)

A consent statement: "Shared by [supplier] with [advocate name] on [date]."

### 12.12 Generated documents (PDF)

- A4, 20 mm margins. Geist Sans 10.5 pt body; Geist Mono for hashes. (No PDF is generated yet: the evaluation build exports Markdown and JSON inside the evidence-pack ZIP.)
- Header: supplier legal name, Udyam number and case reference. Footer: page X of Y, generation time, manifest or content hash, and "Generated by PaySetu. Not legal advice."
- Drafts (the s.63 certificate, any template not yet counsel-approved) carry a diagonal light-grey "DRAFT" watermark and a top notice.
- Simulated items carry a "SIMULATED" label wherever they appear.

---

## 13. Content and Voice

- Plain English at about a Class 8 reading level. Short sentences. Address the supplier as "you".
- Legal terms are introduced once with a plain meaning, e.g. "day of acceptance: the date the law treats the buyer as having accepted your goods".
- Use the "PaySetu reads the Act as…" or "Under rule R3…" pattern. Avoid "guaranteed", "will win", "legally binding" and "court-ready".
- Buyer-facing copy is respectful and factual. It never accuses ("you have defaulted"). Use "payment was due on…".
- Error messages say what happened and what to do; no codes in the main text.
- All user-facing strings are kept in a single message catalogue (to allow future Hindi).
