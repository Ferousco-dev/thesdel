import { useEffect } from "react";
import { Link } from "react-router-dom";

import { SiteFooter } from "../../components/SiteFooter";
import { SitePageHeader } from "../../components/SitePageHeader";
import "../../styles/landing.css";

// Real questions a skeptical prospective user would actually ask, answered
// specifically — including the ones with an honest "not yet" answer,
// per anti-slop-design's FAQ rule. No generated Q&A filler.
const FAQS: { question: string; answer: React.ReactNode }[] = [
  {
    question: "What happens when I hit my monthly AI regeneration cap?",
    answer:
      "Litheral tells you the cap is reached and shows the date it resets — the app never fails silently or deducts a use for a request that didn't actually run.",
  },
  {
    question: "Does regenerating a study block cost me a use if it fails?",
    answer:
      "An attempt is logged the moment you request it, before we know if it succeeds, so a retry after a failure is still counted against your cap — this stops someone from bypassing the cap by triggering repeated failures on purpose.",
  },
  {
    question: "Can my class rep see my personal timetable or study plan?",
    answer:
      "No. A rep can only see the class-level timetable and post announcements. Your personal timetable, study plan, and (on Pro) your routines are visible only to you.",
  },
  {
    question: "What happens if I lose signal while using the app?",
    answer:
      "Your own timetable is cached on your device, so you can still see today's classes read-only. Editing, joining a class, and any Litheral action need a connection.",
  },
  {
    question: "Is there a way to delete my account?",
    answer: (
      <>
        Yes — see our{" "}
        <Link to="/privacy" className="font-semibold text-violet-600 hover:text-violet-700">
          Privacy Policy
        </Link>{" "}
        for exactly what happens to your data when you do.
      </>
    ),
  },
];

export function SupportPage() {
  useEffect(() => {
    document.body.classList.add("landing-page");
    return () => document.body.classList.remove("landing-page");
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 antialiased">
      <SitePageHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Support</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Common questions
        </h1>
        <p className="mt-6 text-base leading-relaxed text-slate-600">
          Can't find what you need here?{" "}
          <Link to="/contact" className="font-semibold text-violet-600 hover:text-violet-700">
            Contact us directly
          </Link>{" "}
          — a real person reads every email.
        </p>

        <dl className="mt-10 space-y-8">
          {FAQS.map((faq) => (
            <div key={faq.question} className="border-b border-slate-200 pb-8 last:border-0">
              <dt className="text-lg font-bold text-slate-900">{faq.question}</dt>
              <dd className="mt-2 text-base leading-relaxed text-slate-600">{faq.answer}</dd>
            </div>
          ))}
        </dl>
      </main>
      <SiteFooter />
    </div>
  );
}
