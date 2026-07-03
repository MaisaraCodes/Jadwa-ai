# Jadwa.ai — Design System

Single source of visual truth. Everything the frontend renders derives from this file.
If a value must change, change it here first, then update `tokens.css` / `tailwind.config.js`
in the same commit. This supersedes the old `teal = SME, coral = bank` rule in `CONVENTIONS.md`
(see §11 for the exact amendment).

Written for the two engineers (Maisara, Osama) and for Claude Code. Point Claude Code at this file.

---

## 1. The idea in one line

Jadwa (جدوى) is the **verdict word** — دراسة جدوى is the feasibility study a bank demands before it
trusts a number. The product *is* that verdict, rendered continuously and cross-checked. So the identity
is the **trusted third party in the room** between two parties who don't trust each other by default:
precise, evidence-first, calm. Arabic brand line (pitch + hero): **دراسة جدوى حيّة لكل طلب تمويل**
— "a living feasibility study for every financing application."

Aesthetic pillars: night + ivory + gold (Saudi without cliché), Arabic-native type, hairline borders over
heavy shadows, tabular figures wherever numbers appear, **one** confident accent per portal, and the Sadu
band as the signature element.

---

## 2. Logo & mark

The mark is a **Kufic-inspired geometric construction of ج** (jeem, the first letter of جدوى): a squared
bowl with the letter's dot rendered as a **gold diamond** — the verdict, delivered. Not calligraphy; a
built letterform. It reads at 16px.

> Optional refinement (Maisara/Osama call it): if the bowl reads slightly wide as a jeem, narrow the lower
> bar by ~6 units on each end. Current geometry below is the approved default.

### 2.1 Canonical mark — app icon / favicon (self-contained, dark tile)

```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Jadwa">
  <rect width="100" height="100" rx="24" fill="#0F1B16"/>
  <rect x="22" y="24" width="56" height="13" fill="#F1EDE1"/>
  <rect x="65" y="37" width="13" height="28" fill="#F1EDE1"/>
  <rect x="10" y="52" width="68" height="13" fill="#F1EDE1"/>
  <path d="M38 38.5 L43.5 44.5 L38 50.5 L32.5 44.5 Z" fill="#D6B36A"/>
</svg>
```

Light-tile variant: tile `#F8F6F0`, letterform `#111D18`, diamond `#A9852F`.

### 2.2 Bare mark — inline next to the wordmark (theme-driven)

Letterform inherits `currentColor`; diamond stays gold. Set `color: var(--ink)` on the wrapper.

```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="22" y="24" width="56" height="13" fill="currentColor"/>
  <rect x="65" y="37" width="13" height="28" fill="currentColor"/>
  <rect x="10" y="52" width="68" height="13" fill="currentColor"/>
  <path d="M38 38.5 L43.5 44.5 L38 50.5 L32.5 44.5 Z" fill="var(--gold)"/>
</svg>
```

### 2.3 Wordmark & lockups

- Wordmark is **live text** (never outlined) so both scripts render correctly: `Jadwa` / `جدوى` in **Zain 800**.
- Every lockup **ends with the gold diamond** — Latin: `Jadwa ◆`; Arabic (RTL): `◆ جدوى` (diamond on the leading/right side visually terminates the word). It's the brand full stop.

```svg
<!-- gold diamond terminal, 14px -->
<svg viewBox="0 0 14 14" width="13" height="13" aria-hidden="true"><path d="M7 0.5 L13.5 7 L7 13.5 L0.5 7 Z" fill="#D6B36A"/></svg>
```

- Clear space: keep min. 1× the mark's height clear on all sides.
- Don'ts: no gradient on the mark, no gold on the letterform strokes, no recolouring the diamond, never Title-Case or letter-space the Arabic wordmark.

---

## 3. Typography

Both faces are **Arabic-native and Google-hosted** (WOFF2, broad browser support). No separate Arabic font —
the same family serves LTR and RTL, so scripts never fall back to a mismatched system font.

| Role | Family | Weights | Use |
|---|---|---|---|
| Display | **Zain** | 400, 700, 800 | Wordmark, headings, big numbers, hero |
| Body / UI | **Alexandria** | 400, 500, 600 | Everything else: labels, tables, body |

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zain:wght@400;700;800&family=Alexandria:wght@400;500;600&display=swap" rel="stylesheet">
```

Fallback stacks (already in `tailwind.config.js` §5):
`display: Zain, Alexandria, system-ui, sans-serif` · `sans: Alexandria, system-ui, "Segoe UI", sans-serif`

### 3.1 Type scale

| Token | Size / line-height | Weight | Family | Notes |
|---|---|---|---|---|
| `display-xl` | 3rem / 1.05 | 800 | Zain | hero only |
| `display` | 2.25rem / 1.1 | 800 | Zain | page hero |
| `h1` | 1.875rem / 1.2 | 700 | Zain | |
| `h2` | 1.5rem / 1.25 | 700 | Zain | |
| `h3` | 1.25rem / 1.35 | 600 | Alexandria | |
| `title` | 1.125rem / 1.4 | 600 | Alexandria | card headers |
| `body` | 1rem / 1.6 (Arabic 1.9) | 400 | Alexandria | |
| `body-sm` | 0.875rem / 1.55 | 400 | Alexandria | |
| `label` | 0.8125rem / 1.4 | 500 | Alexandria | +0.01em (Latin only) |
| `overline` | 0.6875rem / 1.3 | 600 | Alexandria | +0.08em, uppercase — **Latin only** |

### 3.2 Arabic / figure rules (non-negotiable)
- Never uppercase or letter-space Arabic (`overline` is Latin-only — tracking breaks letter-joining).
- Arabic body gets extra leading (`leading-[1.9]`).
- Financial figures always **Western digits** (0–9) with `tabular-nums`, even inside Arabic labels, e.g. `1,500.50 ر.س`. Wrap figures in `dir="ltr"` when they sit in an RTL run.

---

## 4. Colour — `tokens.css`

Colours live as **semantic** CSS variables. `.dark` flips the theme; `data-portal` flips the accent.
Components reference the semantic name only, so each is authored **once** and adapts automatically.

```css
/* tokens.css — the single source of visual truth */
:root {
  /* core */
  --bg:#F8F6F0;          --surface:#FFFFFF;      --surface-2:#F1EEE4;
  --ink:#111D18;         --text-2:#54615B;       --text-3:#8A948D;
  --line:#E4E0D3;        --line-strong:#CBC5B4;
  /* gold — brand + verification only */
  --gold:#A9852F;        --gold-strong:#8C6E28;  --gold-soft:#F2E9D2;   --on-gold:#2A2007;
  /* reserved: forensic + system status */
  --pass:#177A47;   --pass-bg:#E5F3EA;
  --review:#9C6F12; --review-bg:#F8EED8;
  --flag:#B3352A;   --flag-bg:#F9E9E7;
}
.dark {
  --bg:#0B1310;          --surface:#121D18;      --surface-2:#182620;
  --ink:#F1EDE1;         --text-2:#A9B3AB;       --text-3:#6E7A72;
  --line:#243129;        --line-strong:#33443A;
  --gold:#D6B36A;        --gold-strong:#E3C98F;  --gold-soft:#2A2415;   --on-gold:#2A1E05;
  --pass:#4CC38A;   --pass-bg:#12281C;
  --review:#E0A93E; --review-bg:#2A2110;
  --flag:#E2604F;   --flag-bg:#2B1512;
}
/* SME portal — oasis teal */
[data-portal="sme"]        { --accent:#0E7A6E; --accent-strong:#0A5F56; --accent-soft:#E0F1EE; --on-accent:#FFFFFF; }
.dark [data-portal="sme"]  { --accent:#37B3A2; --accent-strong:#5FC9BB; --accent-soft:#0F2B26; --on-accent:#07211D; }
/* Bank dashboard — falcon blue */
[data-portal="bank"]       { --accent:#2E5AA6; --accent-strong:#24478C; --accent-soft:#E5EDF9; --on-accent:#FFFFFF; }
.dark [data-portal="bank"] { --accent:#7CA4E4; --accent-strong:#9FBDEB; --accent-soft:#14233C; --on-accent:#0D1B33; }
```

### 4.1 Colour rules
- Text/headings are `--ink` on `--bg`; cards are `--surface`. Each portal tints its whole canvas via its accent-soft/surface so "which side am I on" is legible peripherally.
- **Gold has exactly three homes:** the mark's diamond, verified/brand moments (e.g. the "Every figure cross-checked by Jadwa" sign-off), and the Sadu band. Never as a generic CTA inside a portal. (Login is pre-portal — gold CTA is allowed there only.)
- `pass / review / flag` map **one-to-one** to `ForensicStatus` (`green → pass`, `yellow → review`, `red → flag`) and appear nowhere else. The brand never competes with the traffic-light verdict.

---

## 5. `tailwind.config.js`

```js
export default {
  darkMode: 'class',
  theme: { extend: {
    colors: {
      bg:'var(--bg)', surface:'var(--surface)', 'surface-2':'var(--surface-2)',
      ink:'var(--ink)', 'text-2':'var(--text-2)', 'text-3':'var(--text-3)',
      line:'var(--line)', 'line-strong':'var(--line-strong)',
      gold:{ DEFAULT:'var(--gold)', strong:'var(--gold-strong)', soft:'var(--gold-soft)' },
      'on-gold':'var(--on-gold)',
      accent:{ DEFAULT:'var(--accent)', strong:'var(--accent-strong)', soft:'var(--accent-soft)' },
      'on-accent':'var(--on-accent)',
      pass:{ DEFAULT:'var(--pass)', bg:'var(--pass-bg)' },
      review:{ DEFAULT:'var(--review)', bg:'var(--review-bg)' },
      flag:{ DEFAULT:'var(--flag)', bg:'var(--flag-bg)' },
    },
    fontFamily: {
      display: ['Zain','Alexandria','system-ui','sans-serif'],
      sans:    ['Alexandria','system-ui','"Segoe UI"','sans-serif'],
    },
    borderRadius: { lg:'8px', xl:'12px' },
  }},
}
```

---

## 6. Theming mechanics

```html
<html lang="ar" dir="rtl" class="dark">      <!-- or lang="en" dir="ltr", drop .dark for light -->
  <body>
    <div data-portal="sme"> … SME portal … </div>   <!-- accent = oasis  -->
    <div data-portal="bank"> … bank dashboard … </div> <!-- accent = falcon -->
```

- **Dark mode:** toggle `.dark` on `<html>`. Default to the OS preference on first load, persist the user's explicit choice. Bank users skew dark (trading-desk feel), SME users skew light — but both modes are fully supported everywhere.
- **Portal accent:** set `data-portal` once on the portal root. Every `bg-accent` / `text-accent` / `ring-accent` below it resolves correctly.
- **One-component rule:** a button is `bg-accent text-on-accent` — authored once, correct in all four combinations (2 portals × 2 modes). Don't fork components per portal or per mode.

---

## 7. RTL

- Set `dir` + `lang` on `<html>`; the whole layout mirrors.
- **Use logical utilities only.** Never `ml/mr/pl/pr/left/right`.

| Physical (don't) | Logical (do) |
|---|---|
| `ml-2` / `pr-4` | `ms-2` / `pe-4` |
| `left-0` | `start-0` |
| `border-l-2` | `border-s-2` |
| `text-left` | `text-start` |
| `rounded-l-none` | `rounded-s-none` |

- Digits: Western 0–9 always, `tabular-nums`, `dir="ltr"` around figures inside Arabic runs.
- Icons that imply direction (arrows, chevrons, "back") must mirror in RTL — use logical icons or flip with `[dir=rtl]:-scale-x-100`.

---

## 8. Components

Radii: `rounded-lg` (8px) controls, `rounded-xl` (12px) cards, `rounded-full` status pills only.
Borders are the primary separator (`border-line`); shadow is reserved for genuinely floating layers (menus,
dialog). Focus is always a visible 2px accent ring. Motion 150ms; nothing bounces.

### 8.1 Buttons (one primary per view)
```html
<!-- primary -->
<button class="inline-flex items-center gap-2 h-10 px-5 rounded-lg bg-accent text-on-accent
  font-medium text-sm hover:bg-accent-strong focus-visible:outline-none
  focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2
  focus-visible:ring-offset-bg transition">Approve</button>

<!-- secondary -->
<button class="… bg-transparent text-ink border border-line-strong hover:bg-surface-2 …">Request info</button>

<!-- tertiary -->
<button class="text-sm text-accent hover:underline">Back to queue</button>

<!-- reject (danger, outline) -->
<button class="… bg-transparent text-flag border border-flag/40 hover:bg-flag-bg …">Reject</button>

<!-- verified / brand action (rare, gold) -->
<button class="… bg-gold text-on-gold hover:bg-gold-strong …">Verify &amp; sign</button>
```

### 8.2 Cards & report cards
```html
<div class="bg-surface border border-line rounded-xl p-4">…</div>

<!-- report card: status edge on the START side, square on that edge -->
<div class="bg-surface border border-line border-s-[3px] border-flag rounded-xl rounded-s-none p-4">
  <h3 class="text-title font-semibold text-ink mb-3">Forensic report</h3> …
</div>
```
Edge colour = the card's forensic status: `border-pass` / `border-review` / `border-flag`.

### 8.3 Metric card
```html
<div class="bg-surface-2 rounded-xl p-3.5">
  <div class="text-xs font-medium text-text-3">Reconciled</div>
  <div class="mt-1 text-2xl font-semibold tabular-nums text-ink">17<span class="text-sm text-text-3 font-normal">/20</span></div>
</div>
```

### 8.4 Inputs
```html
<label class="block text-label text-text-2 mb-1.5">Email</label>
<input class="h-11 w-full rounded-lg bg-surface border border-line-strong px-3 text-sm text-ink
  placeholder:text-text-3 focus-visible:outline-none focus-visible:border-accent
  focus-visible:ring-2 focus-visible:ring-accent/30" placeholder="name@company.sa" />
```

### 8.5 Tables (bank queue, ledger)
- `text-sm`, header row `text-label text-text-3`, sticky (`sticky top-0 bg-surface`).
- Rows separated by `border-b border-line` — hairlines, **not** zebra.
- Numeric columns: `tabular-nums text-end`. Status lives in a badge cell, never as raw coloured text.
- Constrained widths: `table-fixed` + explicit column widths, or horizontal scroll on the wrapper.

### 8.6 Badges
```html
<!-- forensic status pill (dot + label) -->
<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-flag-bg text-flag">
  <span class="w-1.5 h-1.5 rounded-full bg-flag"></span>Review needed</span>

<!-- lifecycle pill (draft → … → approved): quiet, neutral -->
<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium
  bg-surface-2 text-text-2 border border-line">Submitted</span>
```

### 8.7 Empty states (invitation, not apology)
```html
<div class="flex flex-col items-center text-center py-12">
  <i class="ti ti-file-upload text-3xl text-accent" aria-hidden="true"></i>
  <h3 class="mt-3 text-title font-semibold text-ink">Start your first application</h3>
  <p class="mt-1 text-sm text-text-2 max-w-xs">Upload your invoices and statements — Arabic or English. Jadwa organizes the rest.</p>
  <button class="mt-4 … bg-accent text-on-accent …">Create application</button>
</div>
```
Bank empty queue headline: "No applications in the queue" · body: "Submitted applications land here, pre-scored."

### 8.8 Top bar + mode strip
3px accent strip pinned to the very top of each portal, then the bar:
```html
<div class="h-[3px] bg-accent"></div>
<header class="flex items-center justify-between h-14 px-4 bg-surface border-b border-line"> … </header>
```

### 8.9 Sadu band — the signature (also the real pipeline UI)

The six triangles **are** the six-node pipeline (`Extract → Forensic → Stress test → Market → Risk model → Record`).
Each fills as its node completes — drive it from `GET /status` `nodes_completed`. Shrunk + untitled, the same band
is the divider motif and the loading state.

Per-stage state → fill:
- **done** → `fill="var(--accent)"` (or `var(--gold)` on brand/hero surfaces)
- **active** → outline `stroke="var(--accent)"` + a small filled inner triangle
- **pending** → outline `stroke="var(--line-strong)"`, no fill

```svg
<!-- one stage; x = stage origin. Repeat 6×, map fills from state. -->
<!-- done     --> <path d="M{x} 44 L{x+32} 8 L{x+64} 44 Z" fill="var(--accent)"/>
<!-- active   --> <path d="M{x} 44 L{x+32} 8 L{x+64} 44 Z" fill="none" stroke="var(--accent)" stroke-width="2"/>
                  <path d="M{x+16} 44 L{x+32} 26 L{x+48} 44 Z" fill="var(--accent)"/>
<!-- pending  --> <path d="M{x} 44 L{x+32} 8 L{x+64} 44 Z" fill="none" stroke="var(--line-strong)" stroke-width="2"/>
```
In RTL, lay stages start→end (right→left); the SVG `<text>` labels flip with the container.

---

## 9. Status → token reference

| Domain value | Token | Light | Dark |
|---|---|---|---|
| `ForensicStatus green` | `pass` | `#177A47` on `#E5F3EA` | `#4CC38A` on `#12281C` |
| `ForensicStatus yellow` | `review` | `#9C6F12` on `#F8EED8` | `#E0A93E` on `#2A2110` |
| `ForensicStatus red` | `flag` | `#B3352A` on `#F9E9E7` | `#E2604F` on `#2B1512` |
| `Severity high/medium/low` | `flag / review / text-2` | — | — |
| lifecycle `draft…approved` | neutral lifecycle pill (§8.6) | — | — |

---

## 10. Accessibility & quality floor
- Visible keyboard focus on every interactive element (2px accent ring, §8.1). Never remove outlines without a replacement.
- Contrast: body text ≥ 4.5:1, large text/UI ≥ 3:1 — the `on-*` tokens are chosen to pass in both modes. Re-check any new accent tint.
- `@media (prefers-reduced-motion)` → disable the Sadu fill animation and any transitions.
- Every icon-only control gets an `aria-label`; decorative icons/SVG get `aria-hidden="true"`.
- Responsive down to mobile; both portals must be usable at 360px.

---

## 11. `CONVENTIONS.md` amendment (replace the Frontend section)

> **Frontend**
> - **Shared brand core:** night (`--bg` dark) / ivory (`--bg` light) / **gold**. Gold is restricted to the mark's diamond, verification/brand moments, and the Sadu band — never a generic CTA inside a portal.
> - **Two portal accents (replaces teal/coral):** `data-portal="sme"` → **oasis teal**; `data-portal="bank"` → **falcon blue**. Never blend them; the portal is unmistakable from its accent + canvas tint.
> - **`green/amber/red` are reserved for forensic/system status only** (`pass/review/flag`), mapped 1:1 to `ForensicStatus`. The brand palette never uses them.
> - **Dark + light are one system:** semantic tokens in `tokens.css`, `darkMode: 'class'`, accent via `data-portal`. Author each component **once**.
> - **RTL is default-capable:** logical Tailwind utilities only (`ms/me/ps/pe/start/end/border-s/text-start`); `dir`+`lang` on `<html>`; Western digits + `tabular-nums` for all figures.
> - Type: **Zain** (display) + **Alexandria** (body), both Arabic-native, via Google Fonts.
> - The bank dashboard still fetches the whole application in one call and reads the `unified_application_record` shape; the sandbox still sends only `deltas` and renders `RiskProjection`.

---

## 12. Copy voice
Sentence case everywhere. Active voice, verb-first CTAs ("Create application", "Request info"). No "successfully",
no "please", no exclamation marks on system copy. Errors say what happened + what to do, in the product's voice.
Empty states name the space and invite an action. Bilingual parity: every user-facing string ships in AR + EN;
the AR is primary for SME, either is fine for bank.

---

## 13. Handoff checklist for Claude Code
1. Add `tokens.css` (§4) and import it globally; extend `tailwind.config.js` (§5); add the font `<link>` (§3).
2. Set `<html lang dir class>` + a theme toggle (persisted, OS-default first load).
3. Export the mark SVGs (§2.1 tile for favicon/app icon; §2.2 bare for nav) and build the two wordmark lockups as live text.
4. Build the component library once from §8, using semantic tokens only. Verify all four states (sme/bank × light/dark).
5. Wire the Sadu band (§8.9) to `GET /status`.
6. Apply the §11 amendment to `CONVENTIONS.md` in the same PR.
