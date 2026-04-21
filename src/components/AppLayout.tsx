import { NavLink, Outlet } from "react-router-dom";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? "bg-slate-100 text-slate-900"
      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
  }`;

export function AppLayout() {
  return (
    <div className="min-h-screen bg-[#fafafa]">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-baseline gap-2">
              <span className="text-sm font-semibold tracking-tight text-slate-900">
                TrendScout
              </span>
              <span className="rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-800 ring-1 ring-inset ring-emerald-600/15">
                Live
              </span>
            </NavLink>
            <nav className="hidden sm:flex items-center gap-1">
              <NavLink to="/" className={navLinkClass} end>
                Live radar
              </NavLink>
              <NavLink to="/watchlist" className={navLinkClass}>
                Watchlist
              </NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="hidden sm:inline">Amazon signals refresh</span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-1 font-medium text-emerald-800 ring-1 ring-inset ring-emerald-600/15">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              Live
            </span>
          </div>
        </div>
        <div className="sm:hidden border-t border-slate-100 px-4 py-2 flex gap-1">
          <NavLink to="/" className={navLinkClass} end>
            Radar
          </NavLink>
          <NavLink to="/watchlist" className={navLinkClass}>
            Watchlist
          </NavLink>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200/80 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 text-xs text-slate-500">
          TrendScout Live surfaces illustrative Amazon-inspired signals for
          buyer workflows. Not affiliated with Amazon.
        </div>
      </footer>
    </div>
  );
}
