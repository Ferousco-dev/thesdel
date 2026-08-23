# AGENTS.md — Thesdel Frontend

Instruction manual for AI coding agents working in this directory. Read
this and [RULES.md](RULES.md) before writing any UI code.

## What this is

React + TypeScript + Vite, mobile-first, talking to the FastAPI backend in
the parent directory (`../app`). The backend is fully built for Free-tier
+ Litheral V1 (Premium study plans, Pro life organizer) — see
`../docs/API.md` for the complete endpoint list and `../docs/ARCHITECTURE.md`
for how the whole system fits together. This directory is a **scaffold**:
wiring (auth, API client, routing, theming, tier-gating pattern) is done
and working; the actual screens are placeholders marked `TODO` waiting on
real design and implementation.

Source of product truth: `Thesdel_Frontend_Spec.docx` (ask the user for it
if it's not in your context — every screen described below references its
section numbers). Do not invent screens or flows it doesn't describe
without checking with the user first.

## Before you touch anything

1. **Load the `anti-slop-design` skill before writing any UI code** —
   this product needs a distinctive, premium feel (orange/black brand,
   data-dense timetables), not a generic AI-template look. This is a
   standing instruction, not optional.
2. Read `src/lib/api/types.ts` and `src/lib/api/endpoints.ts` — every
   backend shape and call you need already exists there, typed. Don't
   hand-roll a `fetch()` call; call an existing `endpoints.ts` function or
   add a new one following the same pattern.
3. Read the relevant section of `Thesdel_Frontend_Spec.docx` for the
   screen you're building before designing it — §2 (brand/design system),
   §3 (navigation), §4 (Free), §5 (Premium/Litheral study), §6 (Pro/Litheral
   life), §7 (profile/progression), §9 (empty/loading/error states), §10
   (accessibility).

## Directory map

```
src/
├── App.tsx                 route table
├── main.tsx                entry point
├── styles/theme.css         design tokens (CSS variables) — §2.2-2.3
├── lib/
│   ├── theme.ts              light/dark + Pro accent-swap logic — §6.4
│   ├── auth/AuthContext.tsx   auth state, login/register/logout
│   └── api/
│       ├── client.ts          fetch wrapper: auth header, 401-refresh-retry
│       ├── errors.ts          ApiError — mirrors backend's error envelope
│       ├── tokenStore.ts       token persistence (read the comment — it's
│       │                       a documented tradeoff, not a final decision)
│       ├── types.ts             typed backend response/request shapes
│       └── endpoints.ts          one function per backend endpoint
├── components/
│   ├── BottomNav.tsx           primary nav — §3
│   ├── TierGate.tsx            tier-gating UI pattern — §3, §5, §6
│   └── UpgradePrompt.tsx        shown by TierGate — placeholder, needs design
└── routes/
    ├── RootLayout.tsx           auth guard + nav shell
    ├── LoginPage.tsx             §4.1 (partial — needs the class-path choice)
    ├── TimetablePage.tsx          §4.4 (day-list only — needs week-grid, detail sheet)
    ├── ClassesPage.tsx             §4.3, §4.5 — TODO, not started
    ├── LitheralPage.tsx             §5, §6 — TODO, not started
    └── ProfilePage.tsx               §7 — TODO, not started
```

## Working against the backend

- The backend runs locally via `docker compose up --build` from the repo
  root (`../docker-compose.yml`) — API at `http://localhost:8000`, docs at
  `http://localhost:8000/docs`. Set `VITE_API_BASE_URL` in `.env.local`
  (copy `.env.example`) to point at it.
- Every backend error response has the shape `{error_code, message,
  request_id, details}` — see `../docs/API.md` §4. Always branch on
  `error.errorCode` (a stable string), never on `error.message` (safe UI
  copy that can change wording).
- Tier gating is enforced server-side — a UI hiding a button is a UX
  affordance, not security. `TierGate` exists so gated features stay
  *visible but locked*, per Frontend Spec §3 ("keeps upgrade paths
  discoverable"), matching how the backend keeps the request valid but
  returns `403 upgrade_required`.
- AI-backed actions (study generate/regenerate, life generate/adjust) can
  return `429 cap_reached` — the response includes `details.resets_at`.
  Frontend Spec §5.3 requires showing remaining count, not just failing;
  `GET /v1/usage/ai` (see `endpoints.ts` → `getAiUsage`) gives you that
  count to display proactively, not just react to a 429.
- Idempotency: `../docs/API.md` §8 lists which mutations should carry an
  `Idempotency-Key` header (join class, AI generation calls). `client.ts`
  supports passing one via `opts.idempotencyKey` — generate a UUID per
  user action (not per render) and reuse it across retries of that same
  action.

## Coding rules

See `RULES.md` for the full list. Highlights specific to this codebase:

- Never call `fetch`/`apiRequest` directly from a component — go through
  `lib/api/endpoints.ts`. That file is the single place the
  frontend/backend contract lives; keeping it there is what makes a
  backend shape change a one-file frontend fix instead of a grep-and-pray.
- Never hardcode a color, spacing, or font value that already has a token
  in `theme.css` — use the CSS variable. Pro's accent-swap and dark mode
  both depend on nothing bypassing the token layer.
- Never build a gated screen without wrapping it in `TierGate` at the
  point where the backend also gates it — check `../docs/API.md` §3 for
  which endpoints require which tier.
- Never assume a network call succeeds — every screen needs a loading
  state, an empty state (Frontend Spec §9), and an error state before it's
  done. "It works when the API is up and I'm signed in" is not done.

## Definition of done for a screen

1. Matches the relevant Frontend Spec section (ask if a detail is
   ambiguous — don't invent product behavior).
2. Passed through `anti-slop-design` review before you call it finished.
3. Loading/empty/error states all handled (§9).
4. Meets the accessibility bar in §10 (44×44pt tap targets, color never
   the only signal, WCAG AA contrast — check orange-on-dark specifically).
5. Mobile-first, degrades gracefully to tablet/desktop if you test it
   there.
6. Talks to the real backend through `endpoints.ts` — no mocked data left
   in a "finished" screen.
