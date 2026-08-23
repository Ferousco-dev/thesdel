import { useEffect } from "react";
import { Link } from "react-router-dom";

import { SiteFooter } from "../../components/SiteFooter";
import { SitePageHeader } from "../../components/SitePageHeader";
import "../../styles/landing.css";

// Reflects what the app actually does today — no third-party analytics or
// tracking cookies exist yet, so this page says that plainly instead of
// presenting a generic cookie-consent banner for cookies we don't set.
export function CookieSettingsPage() {
  useEffect(() => {
    document.body.classList.add("landing-page");
    return () => document.body.classList.remove("landing-page");
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 antialiased">
      <SitePageHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Legal</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Cookies &amp; local storage
        </h1>
        <p className="mt-4 text-sm text-slate-400">Last updated August 2026.</p>

        <p className="mt-6 text-base leading-relaxed text-slate-600">
          Thesdel doesn't use tracking or advertising cookies today. There's nothing to opt out of
          on that front — we simply don't set them.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">
          What we do store on your device
        </h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          To keep you signed in, the app stores your session tokens in your browser's local
          storage rather than a cookie. This is what lets you reload the page without being logged
          out. It's readable only by Thesdel's own code running in your browser, not by other
          websites.
        </p>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Your own timetable is also cached on your device, so it stays viewable if you lose your
          connection — see our{" "}
          <Link to="/privacy" className="font-semibold text-violet-600 hover:text-violet-700">
            Privacy Policy
          </Link>{" "}
          for how long that's kept.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Free-tier ads</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Free-tier accounts see ads served by a third-party ad network. That network may set its
          own cookies according to its own policy — we don't control that directly, and we don't
          pass it any of your account data beyond a simple "this account is eligible for ads" flag.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">If this changes</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          If we ever add analytics or tracking cookies, this page will describe exactly what's
          set, why, and how to opt out, before that change ships — not after.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
