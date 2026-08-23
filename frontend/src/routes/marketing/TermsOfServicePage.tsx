import { useEffect } from "react";

import { SiteFooter } from "../../components/SiteFooter";
import { SitePageHeader } from "../../components/SitePageHeader";
import "../../styles/landing.css";

export function TermsOfServicePage() {
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
          Terms of Service
        </h1>
        <p className="mt-4 text-sm text-slate-400">Last updated August 2026.</p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">The short version</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Free means free — no card required, no trial that quietly turns into a charge. Paid
          tiers unlock features, not unlimited AI compute: every Litheral action has a monthly
          cap, shown to you in the app. You can delete your account at any time.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Your account</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          You're responsible for keeping your password secure and for what happens under your
          account if you share access to it. Tell us right away if you think someone else has
          access to your account.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Tiers and billing</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Free tier features (timetable, classes, announcements) are free indefinitely. Premium
          and Pro are paid subscriptions, priced per country — we haven't finalized pricing for
          every launch market yet, and you'll always see the exact price for your account before
          you're asked to pay anything. Your tier is only ever changed by a verified payment
          confirmation, never by a client-side setting.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Acceptable use</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Don't use Thesdel to impersonate someone else's class, post content that isn't yours to
          post as a class rep, or try to work around the AI usage caps (for example, by
          intentionally triggering failed requests to avoid a cap deduction — attempts are logged
          and capped regardless of outcome). We can suspend an account for clear abuse.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Referrals</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          If we introduce a referral reward, it will always be a flat reward for you, tied to
          referrals you personally bring in — never a structure where you earn from someone else's
          referrals. We're not building anything that resembles a pyramid structure, in any market.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Changes</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          We'll update this page if these terms change materially, and update the date at the top.
          Continuing to use Thesdel after a change means you accept the update.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
