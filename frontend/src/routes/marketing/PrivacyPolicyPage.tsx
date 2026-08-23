import { useEffect } from "react";

import { SiteFooter } from "../../components/SiteFooter";
import { SitePageHeader } from "../../components/SitePageHeader";
import "../../styles/landing.css";

// Content mirrors the backend's docs/PRIVACY.md — this is the same "why
// collected" table and retention policy, written in plain language for a
// user rather than an engineer. Keep the two in sync if either changes.
export function PrivacyPolicyPage() {
  useEffect(() => {
    document.body.classList.add("landing-page");
    return () => document.body.classList.remove("landing-page");
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 antialiased">
      <SitePageHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Privacy</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Privacy Policy
        </h1>
        <p className="mt-4 text-sm text-slate-400">Last updated August 2026.</p>

        <p className="mt-6 text-base leading-relaxed text-slate-600">
          We only collect what a specific feature of Thesdel needs to work — nothing is collected
          "because it might be useful later." This page explains what that is.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">What we collect</h2>
        <ul className="mt-4 space-y-3 text-base leading-relaxed text-slate-600">
          <li>
            <strong className="text-slate-900">Account info</strong> — email, password (stored as
            a salted hash, never in plain text), display name.
          </li>
          <li>
            <strong className="text-slate-900">Timetable and class data</strong> — the classes,
            times, and locations you enter, and which classes you've joined.
          </li>
          <li>
            <strong className="text-slate-900">Study and routine inputs (Premium/Pro)</strong> —
            subjects, priorities, exam dates, and, on Pro, your routine schedule. Premium's study
            planner never has access to your Pro routine data, even if you're on Pro.
          </li>
          <li>
            <strong className="text-slate-900">AI usage records</strong> — which Litheral feature
            you used and when, so we can enforce monthly caps and understand our own AI costs.
          </li>
          <li>
            <strong className="text-slate-900">Device/session data</strong> — enough to keep you
            signed in and let you sign out of a specific device.
          </li>
        </ul>

        <h2 className="mt-10 text-xl font-bold text-slate-900">What we don't do</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          We don't sell your data. We don't share your timetable, study plans, or routines with
          the ad network shown to Free-tier users — the server only tells the ad SDK whether
          you're eligible to see an ad, nothing about what's actually in your account.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">How long we keep it</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          AI usage records are kept for about 13 months, as an audit trail, then automatically
          deleted. Your timetable and announcement content is kept until you delete it or delete
          your account.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Deleting your account</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Deleting your account removes your personal information (email, name) and deactivates
          your login immediately. Your Thesdel Score and badges are anonymized and kept as part of
          season history rather than deleted outright — this keeps leaderboards and season results
          accurate for everyone else, without keeping anything that identifies you.
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Third parties we use</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          An LLM API provider, used only to help parse a pasted or uploaded timetable into
          structured data — never for the core scheduling logic. Email and push-notification
          providers, used only to deliver messages you'd expect (verification, security alerts,
          class announcements).
        </p>

        <h2 className="mt-10 text-xl font-bold text-slate-900">Questions</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Email <a href="mailto:info@thesdel.com" className="font-semibold text-violet-600 hover:text-violet-700">info@thesdel.com</a> for
          anything not covered here.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
