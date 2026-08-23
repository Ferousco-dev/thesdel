import { useEffect } from "react";
import { Link } from "react-router-dom";

import { SiteFooter } from "../../components/SiteFooter";
import { SitePageHeader } from "../../components/SitePageHeader";
import "../../styles/landing.css";

export function AboutPage() {
  useEffect(() => {
    document.body.classList.add("landing-page");
    return () => document.body.classList.remove("landing-page");
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 antialiased">
      <SitePageHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">About</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Thesdel starts with the thing every student already has to manage
        </h1>
        <p className="mt-6 text-base leading-relaxed text-slate-600">
          Most student apps start with a feature and hope a timetable shows up somewhere inside it.
          Thesdel starts the other way around: your class timetable is the whole product on day
          one, free, and everything else — study planning, life scheduling — is built to read that
          timetable and work around it, not replace it.
        </p>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          We're launching first for students in Nigeria, Pakistan, and Sri Lanka. That decision
          shapes real engineering choices, not just marketing copy: your timetable is cached on
          your device so it stays viewable on a bad connection, and every AI feature has a hard
          monthly cap because unpredictable AI cost is the fastest way to kill a product built for
          cost-sensitive markets.
        </p>
        <h2 className="mt-10 text-xl font-bold text-slate-900">Three tiers, three questions</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Free answers "what classes do I have?" Premium adds Litheral, our planning engine, to
          answer "when should I study?" by reading your timetable and slotting study time into the
          gaps. Pro extends Litheral to your whole week — routines, church, gym, work, sleep —
          answering "how do I run my whole week?" without ever hiding a conflict it can't resolve.
        </p>
        <h2 className="mt-10 text-xl font-bold text-slate-900">Where things stand</h2>
        <p className="mt-4 text-base leading-relaxed text-slate-600">
          Thesdel is pre-launch. The core timetable, class, and Litheral planning features are
          built and working end to end. Pricing per market and a few product decisions are still
          being finalized — see our{" "}
          <Link to="/terms" className="font-semibold text-violet-600 hover:text-violet-700">
            Terms of Service
          </Link>{" "}
          for what's confirmed today.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
