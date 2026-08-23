# Thesdel Frontend

React + TypeScript + Vite. **Start here:** [AGENTS.md](AGENTS.md) and
[RULES.md](RULES.md) before writing any code.

## Local development

Backend must be running first (from the repo root):

```bash
cd .. && docker compose up --build
```

Then, in this directory:

```bash
cp .env.example .env.local
npm install
npm run dev
```

App: http://localhost:5173

## Scripts

- `npm run dev` — dev server with HMR
- `npm run build` — typecheck + production build
- `npm run typecheck` — type-check only
- `npm run lint` — ESLint
- `npm test` — Vitest

## Status

This is a **scaffold**, not a finished app. Wiring (auth, API client,
routing, theming, tier-gating pattern) works end to end against the real
backend. The actual screens (`src/routes/*`) are placeholders marked
`TODO` — see [AGENTS.md](AGENTS.md) for what's built vs. what's next, and
`Thesdel_Frontend_Spec.docx` for the full product spec each screen should
match.
