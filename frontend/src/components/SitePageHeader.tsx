import { Link } from "react-router-dom";

// Minimal header for standalone content pages (About, Contact, Support,
// Privacy, Terms, Cookies) — the full marketing nav belongs on the
// landing page only; these pages just need a way back home.
export function SitePageHeader() {
  return (
    <header className="border-b border-slate-200/70 bg-slate-50">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="flex min-h-11 items-center gap-2" aria-label="Thesdel home">
          <svg className="h-9 w-9" viewBox="0 0 40 40" fill="none" aria-hidden="true">
            <defs>
              <linearGradient id="logoGradient" x1="5" y1="4" x2="35" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#E8590C" />
                <stop offset="1" stopColor="#FFB385" />
              </linearGradient>
            </defs>
            <path
              d="M9 17.5 6.5 14l4.8-.6L14 9l3 3.4 3-3.4 2.7 4.4 4.8.6-2.5 3.5v7.2c0 5.1-3.6 8.3-9 8.3s-9-3.2-9-8.3v-7.2Z"
              fill="url(#logoGradient)"
            />
            <path
              d="M9 20c-3.2 0-4.8 1.5-4.8 3.9 0 2.5 2 3.9 4.8 3.9M31 20c3.2 0 4.8 1.5 4.8 3.9 0 2.5-2 3.9-4.8 3.9"
              stroke="#FFB385"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx="13.5" cy="21" r="2" fill="white" />
            <circle cx="26.5" cy="21" r="2" fill="white" />
            <path d="M15 27c2.8 1.5 7.2 1.5 10 0" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span className="text-lg font-bold tracking-tight text-violet-700">Thesdel</span>
        </Link>
        <Link to="/" className="text-sm font-medium text-slate-600 transition hover:text-violet-600">
          ← Back to home
        </Link>
      </div>
    </header>
  );
}
