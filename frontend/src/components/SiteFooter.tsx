import { FaFacebook, FaInstagram, FaLinkedin, FaXTwitter } from "react-icons/fa6";
import { Link } from "react-router-dom";

// Shared footer for the landing page and every standalone content page
// (About, Contact, Support, Privacy, Terms, Cookies) — extracted so the
// six new pages don't each duplicate this block, per RULES.md #8.
export function SiteFooter() {
  return (
    <footer className="brand-footer border-t border-violet-500/20 text-slate-400">
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-2 lg:grid-cols-[1.35fr_0.8fr_0.8fr_1fr] lg:gap-16">
          <div>
            <Link to="/" className="flex items-center gap-2 text-slate-50">
              <svg className="h-9 w-9" viewBox="0 0 40 40" fill="none" aria-hidden="true">
                <path
                  d="M9 17.5 6.5 14l4.8-.6L14 9l3 3.4 3-3.4 2.7 4.4 4.8.6-2.5 3.5v7.2c0 5.1-3.6 8.3-9 8.3s-9-3.2-9-8.3v-7.2Z"
                  fill="#FFB385"
                />
                <circle cx="13.5" cy="21" r="2" fill="#1E120B" />
                <circle cx="26.5" cy="21" r="2" fill="#1E120B" />
                <path d="M15 27c2.8 1.5 7.2 1.5 10 0" stroke="#1E120B" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
              <span className="text-lg font-bold">Thesdel</span>
            </Link>
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-violet-100/70">
              At Thesdel, we believe that learning should be as unique as you are. Our AI-powered
              platform creates personalized lessons designed to meet your goals, pace, and
              interests.
            </p>
          </div>
          <div>
            <h3 className="font-semibold tracking-tight text-white">Product</h3>
            <ul className="mt-4 space-y-3 text-sm">
              <li>
                <Link to="/about" className="transition hover:text-white">
                  About Us
                </Link>
              </li>
              <li>
                <Link to="/contact" className="transition hover:text-white">
                  Contact Us
                </Link>
              </li>
              <li>
                <Link to="/support" className="transition hover:text-white">
                  Customer Support
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold tracking-tight text-white">Legal</h3>
            <ul className="mt-4 space-y-3 text-sm">
              <li>
                <Link to="/privacy" className="transition hover:text-white">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link to="/terms" className="transition hover:text-white">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link to="/cookies" className="transition hover:text-white">
                  Cookie Settings
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold tracking-tight text-white">Contact Us</h3>
            <ul className="mt-4 space-y-3 text-sm">
              <li className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                  <path
                    strokeLinecap="round"
                    d="M6.5 4.5h3l1.5 4-2 1.5a15 15 0 0 0 5 5l1.5-2 4 1.5v3c0 1-1 1.5-2 1.5C11 19 5 13 5 6.5c0-1 .5-2 1.5-2Z"
                  />
                </svg>
                (234) 708 417 4994
              </li>
              <li className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                  <rect x="3.5" y="5" width="17" height="14" rx="2" />
                  <path d="m4 7 8 6 8-6" />
                </svg>
                info@thesdel.com
              </li>
              <li className="flex items-start gap-2">
                <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                  <path d="M19 10c0 5-7 10-7 10S5 15 5 10a7 7 0 1 1 14 0Z" />
                  <circle cx="12" cy="10" r="2" />
                </svg>
                <span>Lagos, Nigeria</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-6 border-t border-slate-800 pt-8 md:flex-row">
          <p className="text-xs text-slate-500">
            © {new Date().getFullYear()} Thesdel. All rights reserved.
          </p>
          {/* No real social accounts exist yet — these stay inert (no
              href, aria-hidden) rather than link to a fake/placeholder
              profile. Swap to real <a> links the day an account exists. */}
          <div className="flex items-center gap-3">
            <span
              className="flex h-10 w-10 items-center justify-center rounded-full border border-violet-300/30 opacity-50"
              aria-hidden="true"
            >
              <FaXTwitter className="h-4 w-4" />
            </span>
            <span
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 opacity-50"
              aria-hidden="true"
            >
              <FaInstagram className="h-4 w-4" />
            </span>
            <span
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 opacity-50"
              aria-hidden="true"
            >
              <FaFacebook className="h-4 w-4" />
            </span>
            <span
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 opacity-50"
              aria-hidden="true"
            >
              <FaLinkedin className="h-4 w-4" />
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
