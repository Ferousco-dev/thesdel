import { useEffect } from "react";

import { SiteFooter } from "../../components/SiteFooter";
import { SitePageHeader } from "../../components/SitePageHeader";
import "../../styles/landing.css";

// No contact form — there's no backend endpoint to receive one yet
// (a form nobody's inbox actually reads is worse than none, per
// anti-slop-design's Forms rule). Direct contact details instead.
export function ContactPage() {
  useEffect(() => {
    document.body.classList.add("landing-page");
    return () => document.body.classList.remove("landing-page");
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 antialiased">
      <SitePageHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Contact</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Get in touch
        </h1>
        <p className="mt-6 text-base leading-relaxed text-slate-600">
          Thesdel is a small team — email is the fastest way to reach us for anything: a bug
          report, a question about a market launch, or a partnership inquiry.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          <div className="rounded-2xl border border-violet-100 bg-violet-50/60 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Email</h2>
            <a
              href="mailto:info@thesdel.com"
              className="mt-2 block text-lg font-semibold text-violet-600 hover:text-violet-700"
            >
              info@thesdel.com
            </a>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-violet-50/60 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Phone</h2>
            <a
              href="tel:+2347084174994"
              className="mt-2 block text-lg font-semibold text-violet-600 hover:text-violet-700"
            >
              (234) 708 417 4994
            </a>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-violet-50/60 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Based in</h2>
            <p className="mt-2 text-lg font-semibold text-slate-900">Lagos, Nigeria</p>
          </div>
        </div>

        <p className="mt-10 text-sm leading-relaxed text-slate-500">
          For a bug report or account issue, include what you were trying to do and, if you can,
          the approximate time it happened — that's usually enough for us to find it in our logs.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
