# RULES.md — Frontend Engineering Rules

These apply on top of the repo-root `../RULES.md` (read that too — the
security/data-boundary rules there still apply; the backend enforces them,
but the frontend must not work around or contradict them). This file adds
frontend-specific rules.

## Security & trust boundary

1. Never trust a client-side tier/role check as authorization — it's a UX
   affordance only. The backend re-checks everything server-side (see
   `../docs/SECURITY.md` §4). Don't skip building a `TierGate` just
   because "the backend will reject it anyway" — an ungated UI that lets a
   Free user submit a request they'll get a 403 for is still a bad
   experience and defeats the point of §3's upgrade-prompt pattern.
2. Never put a secret, API key, or credential in frontend code or an env
   var prefixed `VITE_` — anything with that prefix is bundled into the
   public JS and readable by anyone. `VITE_API_BASE_URL` is fine (it's not
   a secret); an API key would not be.
3. Never send more data to the backend than the screen actually needs to
   collect — matches the backend's data-minimization stance
   (`../docs/PRIVACY.md` §1). Don't add a form field "because it might be
   useful" without checking with the user first.

## API contract discipline

4. Never call `fetch` directly — always go through `lib/api/endpoints.ts`.
   If an endpoint you need isn't there yet, add it there, typed against
   `lib/api/types.ts`, matching the backend's actual Pydantic schema (check
   `../app/*/schemas.py` or `../docs/API.md`, don't guess the shape).
5. Never assume a backend response shape without checking it against
   `../app/*/schemas.py` or `../docs/API.md` first — if the frontend and
   backend disagree on a field name, fix it in `types.ts` to match the
   backend, not the other way around, since the backend is the source of
   truth for the contract.
6. If you need a backend change (new endpoint, new field, different
   validation) to build a screen properly, say so and describe what's
   needed — don't fake it with a client-side workaround that produces
   wrong data or bypasses a validation rule the backend enforces for a
   reason.

## Code quality

7. No prop-drilling more than two levels — reach for context (see
   `AuthContext` for the pattern) instead.
8. No inline style objects duplicated across files — if the same style
   shows up twice, it's a component or a CSS class, not a copy-paste.
9. No `any` — if a backend shape is genuinely dynamic, model it as a
   discriminated union in `types.ts`, don't escape-hatch around it.
10. No component file over ~200 lines — split by concern (a
    `TimetableWeekGrid` is not the same component as the day it's inside
    of `TimetablePage`).
11. No dead placeholder code left after a screen is "done" — a finished
    screen has no `TODO` comments describing itself; TODOs are fine for
    genuinely out-of-scope future work, not for the thing you were asked
    to build.

## Design

12. Never ship a screen without running it past the `anti-slop-design`
    skill first — see `AGENTS.md`'s Definition of Done.
13. Never introduce a new color, font, or spacing value outside
    `theme.css`'s tokens without updating that file first — a one-off
    inline hex code is exactly what breaks Pro's accent-swap and dark
    mode.
14. Orange is an accent/CTA color, never a background flood — Frontend
    Spec §2.4. If a screen is "mostly orange," that's a design review
    finding, not a style preference.

## Testing

15. A screen that fetches data needs at least one test covering its
    loading → success and loading → error paths (see `vitest` in
    `package.json`; add `@testing-library/react` if/when the first
    component test is written — it's not installed yet since no component
    tests exist).
16. Don't remove or weaken a type to make a build pass — fix the actual
    mismatch between what the backend sends and what the type says.

## Git

17. Don't mix a screen implementation with an unrelated dependency bump
    or a refactor of shared `lib/` code in the same change unless the
    screen genuinely required the `lib/` change.
