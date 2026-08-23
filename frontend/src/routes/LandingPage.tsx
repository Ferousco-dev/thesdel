import { useEffect, useState } from "react";

import heroStudent1 from "../assets/hero-student-1.png";
import heroStudent2 from "../assets/hero-student-2.png";
import heroStudent3 from "../assets/hero-student-3.png";
import { SiteFooter } from "../components/SiteFooter";
import "../styles/landing.css";

// Landing page — ported from the design provided, with the brand name
// changed to Thesdel and the color overrides in ../styles/landing.css
// swapped from violet/pink to orange/black. Structure, copy, and layout
// are otherwise unchanged from the original.
export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    document.body.classList.add("landing-page");
    return () => document.body.classList.remove("landing-page");
  }, []);

  return (
    <div className="scroll-smooth bg-slate-50 text-slate-900 antialiased">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-violet-700 focus:px-5 focus:py-3 focus:text-white"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-slate-50/90 backdrop-blur-md">
        <nav
          className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
          aria-label="Main navigation"
        >
          <a
            href="#home"
            className="flex min-h-11 items-center gap-2"
            aria-label="Thesdel home"
          >
            <svg
              className="h-9 w-9"
              viewBox="0 0 40 40"
              fill="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient
                  id="logoGradient"
                  x1="5"
                  y1="4"
                  x2="35"
                  y2="36"
                  gradientUnits="userSpaceOnUse"
                >
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
              <path
                d="M15 27c2.8 1.5 7.2 1.5 10 0"
                stroke="white"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-lg font-bold tracking-tight text-violet-700">
              Thesdel
            </span>
          </a>
          <div className="hidden items-center gap-7 md:flex">
            <a
              href="#home"
              className="text-sm font-medium text-slate-600 transition hover:text-violet-600"
            >
              Home
            </a>
            <a
              href="#about"
              className="text-sm font-medium text-slate-600 transition hover:text-violet-600"
            >
              About
            </a>
            <a
              href="#explore"
              className="text-sm font-medium text-slate-600 transition hover:text-violet-600"
            >
              Grade &amp; Topics
            </a>
            <a
              href="#empower"
              className="text-sm font-medium text-slate-600 transition hover:text-violet-600"
            >
              AI Tutor
            </a>
            <a
              href="#pricing"
              className="text-sm font-medium text-slate-600 transition hover:text-violet-600"
            >
              Pricing
            </a>
          </div>
          <div className="hidden items-center gap-3 md:flex">
            <a
              href="#contact"
              className="rounded-full border border-slate-200 bg-slate-50 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-violet-200 hover:text-violet-600"
            >
              Contact Us
            </a>
            <a
              href="#pricing"
              className="rounded-full bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 hover:shadow-md"
            >
              Sign Up
            </a>
          </div>
          <button
            id="menu-button"
            type="button"
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-slate-200 text-slate-700 md:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={
              menuOpen ? "Close navigation menu" : "Open navigation menu"
            }
            onClick={() => setMenuOpen((open) => !open)}
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
        </nav>
        <div
          id="mobile-menu"
          className={`${menuOpen ? "" : "hidden"} border-t border-slate-200/70 bg-slate-50 px-4 pb-5 pt-3 md:hidden`}
        >
          <div className="mx-auto flex max-w-7xl flex-col gap-1">
            <a
              href="#home"
              onClick={() => setMenuOpen(false)}
              className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-violet-50 hover:text-violet-600"
            >
              Home
            </a>
            <a
              href="#about"
              onClick={() => setMenuOpen(false)}
              className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-violet-50 hover:text-violet-600"
            >
              About
            </a>
            <a
              href="#explore"
              onClick={() => setMenuOpen(false)}
              className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-violet-50 hover:text-violet-600"
            >
              Grade &amp; Topics
            </a>
            <a
              href="#empower"
              onClick={() => setMenuOpen(false)}
              className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-violet-50 hover:text-violet-600"
            >
              AI Tutor
            </a>
            <a
              href="#pricing"
              onClick={() => setMenuOpen(false)}
              className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-violet-50 hover:text-violet-600"
            >
              Pricing
            </a>
            <a
              href="#pricing"
              onClick={() => setMenuOpen(false)}
              className="mt-2 rounded-full bg-violet-600 px-5 py-3 text-center text-sm font-semibold text-white"
            >
              Sign Up
            </a>
          </div>
        </div>
      </header>

      <main id="main-content">
        <section
          id="home"
          className="hero-wash overflow-hidden px-4 pb-20 pt-20 sm:px-6 lg:px-8 lg:pb-28 lg:pt-28"
        >
          <div className="mx-auto max-w-7xl">
            <div className="relative mx-auto max-w-5xl text-center">
              <svg
                className="absolute -left-2 top-8 h-5 w-5 text-violet-400 sm:left-8"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="m12 2 1.7 7.2L21 11l-7.3 1.8L12 20l-1.7-7.2L3 11l7.3-1.8L12 2Z" />
              </svg>
              <svg
                className="absolute right-0 top-36 h-4 w-4 text-fuchsia-300 sm:right-10"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="m12 2 1.7 7.2L21 11l-7.3 1.8L12 20l-1.7-7.2L3 11l7.3-1.8L12 2Z" />
              </svg>
              <svg
                className="absolute bottom-0 left-1/4 h-3 w-3 text-violet-300"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="m12 2 1.7 7.2L21 11l-7.3 1.8L12 20l-1.7-7.2L3 11l7.3-1.8L12 2Z" />
              </svg>
              <p className="mb-5 text-xs font-bold uppercase tracking-[0.22em] text-violet-600">
                Personalized learning, made joyful
              </p>
              <h1 className="text-5xl font-bold leading-[1.08] tracking-tight text-slate-900 md:text-6xl lg:text-7xl">
                Transform Your
                <br />
                <span className="gradient-text">Learning Experience</span>
                <br />
                with Thesdel
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-base font-medium leading-relaxed text-slate-500 sm:text-lg">
                At Thesdel, we harness the power of conversational AI to make
                learning engaging and efficient. Discover personalized lessons
                that adapt to your needs and unlock your potential today!
              </p>
              <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
                <a
                  href="#pricing"
                  className="rounded-full bg-violet-600 px-8 py-3.5 text-center text-sm font-semibold text-white shadow-lg shadow-violet-200 transition hover:scale-[1.02] hover:bg-violet-700 focus:outline-none focus:ring-4 focus:ring-violet-200"
                >
                  Begin Free Evaluation
                </a>
                <a
                  href="#pricing"
                  className="rounded-full border border-slate-200 bg-slate-50 px-8 py-3.5 text-center text-sm font-semibold text-slate-700 shadow-sm transition hover:scale-[1.02] hover:border-violet-200 hover:text-violet-700 focus:outline-none focus:ring-4 focus:ring-violet-100"
                >
                  Start 14 Days Trial
                </a>
              </div>
            </div>
            <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 items-end gap-8 sm:grid-cols-3 sm:gap-5 lg:gap-8">
              <div className="relative mx-auto w-full max-w-xs pt-5 sm:max-w-none sm:-rotate-2">
                <div className="absolute inset-x-4 bottom-0 top-8 rounded-3xl bg-blue-100" />
                <img
                  className="relative mx-auto h-64 w-52 object-contain object-bottom sm:h-72 lg:h-80"
                  src={heroStudent1}
                  alt="Student smiling, carrying a laptop and backpack"
                />
              </div>
              <div className="relative mx-auto w-full max-w-xs pt-2 sm:max-w-none">
                <div className="absolute inset-x-2 bottom-0 top-5 rounded-3xl bg-emerald-100" />
                <img
                  className="relative mx-auto h-72 w-56 object-contain object-bottom sm:h-80 lg:h-96"
                  src={heroStudent2}
                  alt="Student smiling, holding a stack of folders and wearing a backpack"
                />
              </div>
              <div className="relative mx-auto w-full max-w-xs pt-5 sm:max-w-none sm:rotate-2">
                <div className="absolute inset-x-4 bottom-0 top-8 rounded-3xl bg-rose-100" />
                <img
                  className="relative mx-auto h-64 w-52 object-contain object-bottom sm:h-72 lg:h-80"
                  src={heroStudent3}
                  alt="Student wearing glasses, smiling and holding a stack of books"
                />
              </div>
            </div>
          </div>
        </section>

        <section
          id="explore"
          className="bg-slate-50 px-4 py-20 sm:px-6 lg:py-24"
        >
          <div className="mx-auto max-w-7xl text-center">
            <span className="inline-block rounded-full bg-violet-50 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-violet-600">
              Explore
            </span>
            <h2 className="mx-auto mt-4 max-w-3xl text-3xl font-bold leading-tight tracking-tight text-slate-900 md:text-4xl">
              Comprehensive Learning for JK to Grade 8 – English, Math, French,
              and Exam Prep
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm font-medium leading-relaxed text-slate-500 sm:text-base">
              Thesdel harnesses the power of conversational AI to create a
              personalized learning experience. Our platform adapts to each
              student's needs, ensuring efficient and effective learning.
            </p>
            <a
              href="#empower"
              className="mx-auto mt-8 inline-flex items-center gap-2 rounded-full bg-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 hover:shadow-md"
            >
              Explore Topics
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 12h13m-4-4 4 4-4 4"
                />
              </svg>
            </a>
          </div>
        </section>

        <section
          id="empower"
          className="bg-slate-50 px-4 py-20 sm:px-6 lg:py-24"
        >
          <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-14 lg:grid-cols-2 lg:gap-16">
            <div>
              <span className="inline-block rounded-full bg-violet-50 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-violet-600">
                Empower
              </span>
              <h2 className="mt-4 max-w-xl text-4xl font-bold leading-tight tracking-tight text-slate-900">
                Unlock Your Learning Potential with Thesdel
              </h2>
              <div className="mt-8 space-y-6">
                <article className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M8 10h8M8 14h5m7-2a8 8 0 0 1-8 8 8.5 8.5 0 0 1-3.7-.8L4 20l.8-4.3A8 8 0 1 1 20 12Z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900">
                      Interactive Learning with 24/7 AI Support
                    </h3>
                    <p className="mt-1 text-sm leading-relaxed text-slate-500">
                      Thesdel offers real-time, personalized learning. With
                      text-to-speech and speech-to-text, students interact
                      naturally instead of just typing answers into a box.
                    </p>
                    <a
                      href="#pricing"
                      className="mt-2 inline-block text-sm font-semibold text-violet-600 hover:text-violet-700"
                    >
                      Learn more →
                    </a>
                  </div>
                </article>
                <article className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4 19V5m0 14h16M8 16v-4m4 4V8m4 8V6"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900">
                      Comprehensive Progress Tracking for Parents
                    </h3>
                    <p className="mt-1 text-sm leading-relaxed text-slate-500">
                      Parents receive detailed reports tracking student
                      progress. Thesdel keeps families informed step-by-step.
                    </p>
                    <a
                      href="#pricing"
                      className="mt-2 inline-block text-sm font-semibold text-violet-600 hover:text-violet-700"
                    >
                      Learn more →
                    </a>
                  </div>
                </article>
                <article className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    >
                      <circle cx="12" cy="12" r="9" />
                      <path
                        strokeLinecap="round"
                        d="M3 12h18M12 3c2.3 2.5 3.4 5.5 3.4 9s-1.1 6.5-3.4 9c-2.3-2.5-3.4-5.5-3.4-9S9.7 5.5 12 3Z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900">
                      Thesdel MultiLingo: Learn in Your Language
                    </h3>
                    <p className="mt-1 text-sm leading-relaxed text-slate-500">
                      Thesdel MultiLingo lets students learn in their preferred
                      language, making education more accessible and inclusive.
                    </p>
                    <a
                      href="#pricing"
                      className="mt-2 inline-block text-sm font-semibold text-violet-600 hover:text-violet-700"
                    >
                      Learn more →
                    </a>
                  </div>
                </article>
                <article className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    >
                      <circle cx="12" cy="12" r="8.5" />
                      <circle cx="12" cy="12" r="3" />
                      <path
                        strokeLinecap="round"
                        d="M12 3.5V6M12 18v2.5M3.5 12H6M18 12h2.5"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900">
                      Dynamic Learning Pathways &amp; Assessments
                    </h3>
                    <p className="mt-1 text-sm leading-relaxed text-slate-500">
                      Dynamic learning pathways adjust to increasing levels of
                      difficulty, delivering personalized questions and
                      automatic homework grading as a student progresses.
                    </p>
                    <a
                      href="#pricing"
                      className="mt-2 inline-block text-sm font-semibold text-violet-600 hover:text-violet-700"
                    >
                      Learn more →
                    </a>
                  </div>
                </article>
              </div>
            </div>
            <div id="about" className="relative">
              <div className="overflow-hidden rounded-3xl shadow-md">
                <img
                  className="aspect-[4/3] w-full object-cover"
                  src="https://images.unsplash.com/photo-1597933471507-1ca5765185d8?q=80&w=1000&auto=format&fit=crop"
                  alt="Child looking at schoolwork on a laptop at home"
                  loading="lazy"
                />
              </div>
              <button
                type="button"
                aria-label="Play Thesdel overview video"
                className="absolute left-1/2 top-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-slate-50 text-violet-600 shadow-xl transition hover:scale-105"
              >
                <svg
                  className="ml-1 h-7 w-7"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M8 5.5v13l10-6.5-10-6.5Z" />
                </svg>
              </button>
              <p className="mt-4 text-center text-xs font-bold uppercase tracking-[0.22em] text-slate-400">
                How it works
              </p>
            </div>
          </div>
        </section>

        <section
          id="benefits"
          className="bg-violet-50/40 px-4 py-20 sm:px-6 lg:py-24"
        >
          <div className="mx-auto max-w-7xl">
            <div className="text-center">
              <span className="inline-block rounded-full bg-violet-50 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-violet-600">
                Benefits
              </span>
              <h2 className="mx-auto mt-4 max-w-3xl text-3xl font-bold leading-tight tracking-tight text-slate-900 md:text-4xl">
                Every Student Thrives with the Right Start - Find the Best Early
                Education Here
              </h2>
            </div>
            <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
              <article className="rounded-3xl border border-violet-100 bg-violet-50/60 p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
                <img
                  className="mb-6 aspect-[4/3] w-full rounded-2xl object-cover"
                  src="https://images.unsplash.com/photo-1577897113292-3b95936e5206?q=80&w=800&auto=format&fit=crop"
                  alt="Family gathered around a table playing a game together"
                  loading="lazy"
                />
                <h3 className="text-lg font-bold text-slate-900">
                  For Families
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">
                  Families benefit from personalized learning across subjects
                  with Thesdel. 24/7 support keeps parents in the loop with
                  real-time progress reports, ensuring they stay engaged in
                  their child's education.
                </p>
                <a
                  href="#pricing"
                  className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-violet-600 hover:text-violet-700"
                >
                  Learn More →
                </a>
              </article>
              <article className="rounded-3xl border border-violet-100 bg-violet-50/60 p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
                <img
                  className="mb-6 aspect-[4/3] w-full rounded-2xl object-cover"
                  src="https://images.unsplash.com/photo-1577896851231-70ef18881754?q=80&w=800&auto=format&fit=crop"
                  alt="Teacher at a chalkboard with students raising their hands"
                  loading="lazy"
                />
                <h3 className="text-lg font-bold text-slate-900">
                  For Schools
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">
                  Thesdel integrates teachers seamlessly and offers training for
                  easy adoption. The platform supports curriculum customization,
                  providing complete transparency for teachers, administrators,
                  and parents to track student progress.
                </p>
                <a
                  href="#pricing"
                  className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-violet-600 hover:text-violet-700"
                >
                  Learn More →
                </a>
              </article>
              <article className="rounded-3xl border border-violet-100 bg-violet-50/60 p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
                <img
                  className="mb-6 aspect-[4/3] w-full rounded-2xl object-cover"
                  src="https://images.unsplash.com/photo-1583468982228-19f19164aee2?q=80&w=800&auto=format&fit=crop"
                  alt="Teacher reading a book one-on-one with a young student"
                  loading="lazy"
                />
                <h3 className="text-lg font-bold text-slate-900">
                  For Educators
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">
                  Thesdel provides an easily adaptable curriculum that can be
                  re-branded for your institution. Teachers are fully integrated
                  into the learning process, with Thesdel delivering detailed,
                  actionable progress reports.
                </p>
                <a
                  href="#pricing"
                  className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-violet-600 hover:text-violet-700"
                >
                  Learn More →
                </a>
              </article>
            </div>
          </div>
        </section>

        <section className="bg-slate-50 px-4 py-20 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-7xl">
            <p className="text-center text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
              Powered By
            </p>
            {/* Text wordmarks only — no attempted icon/logo recreation.
                Redrawing another company's trademarked mark from memory
                risks getting it wrong; a plain name credit is accurate
                either way. */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-x-10 gap-y-5 text-slate-400 sm:gap-x-14">
              <span className="text-lg font-bold tracking-tight">Claude</span>
              <span className="text-lg font-bold tracking-tight">Gemini</span>
              <span className="text-lg font-bold tracking-tight">Groq</span>
              <span className="text-lg font-bold tracking-tight">Mistral</span>
              <span className="text-lg font-bold tracking-tight">DeepSeek</span>
              <span className="text-sm font-medium italic">and others</span>
            </div>
          </div>
        </section>

        <section className="bg-slate-50 px-4 py-20 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-4xl text-center">
            <span className="inline-block rounded-full bg-violet-50 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-violet-600">
              Testimonial
            </span>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
              See What Parent Are Saying
            </h2>
            <div
              className="mt-6 text-6xl leading-none text-violet-200"
              aria-hidden="true"
            >
              ❝
            </div>
            <blockquote className="mx-auto mt-2 max-w-3xl text-xl font-medium leading-relaxed text-slate-600 md:text-2xl">
              "Thesdel transformed my learning experience. The AI tutor made
              complex topics easy to understand and engaging!"
            </blockquote>
            <img
              className="mx-auto mt-8 h-16 w-16 rounded-full border-4 border-slate-50 object-cover shadow-md"
              src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=200&auto=format&fit=crop"
              alt="Caitlyn King"
              loading="lazy"
            />
            <p className="mt-4 font-bold text-slate-900">Caitlyn King</p>
            <p className="text-sm text-slate-400">Head of Design, Layers</p>
            <div
              className="mt-6 flex justify-center gap-2"
              aria-label="Testimonial 1 of 3"
            >
              <span className="h-2 w-2 rounded-full bg-violet-600" />
              <span className="h-2 w-2 rounded-full bg-slate-300" />
              <span className="h-2 w-2 rounded-full bg-slate-300" />
            </div>
          </div>
        </section>

        <section id="pricing" className="bg-slate-50 px-4 pb-24 sm:px-6">
          <div className="mx-auto max-w-5xl rounded-3xl bg-violet-600 px-8 py-12 text-center shadow-sm md:py-16">
            <h2 className="text-3xl font-bold tracking-tight text-white">
              Unlock Your Full Learning Potential With Thesdel
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-violet-100 sm:text-base">
              Join Thesdel today and experience transformative, personalized
              learning through our innovative AI-driven platform. Empower your
              learning journey and take the next step toward success.
            </p>
            <a
              href="#contact"
              className="mt-8 inline-block rounded-full bg-slate-50 px-8 py-3.5 text-sm font-bold text-violet-600 transition hover:bg-violet-50 hover:shadow-md"
            >
              Start 14 Days Free Trial
            </a>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
