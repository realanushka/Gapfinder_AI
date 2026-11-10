"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { SyllabiProvider, syllabusLabel, useSyllabi } from "@/lib/syllabi";

/** Ordered to match the core loop: Upload -> Test -> Diagnose -> Plan -> Re-test. */
const NAV_ITEMS = [
  { href: "/upload", label: "Upload", icon: "📥" },
  { href: "/topics", label: "Topic Map", icon: "🗺️" },
  { href: "/quiz", label: "Quiz", icon: "✍️" },
  { href: "/gap-report", label: "Gap Report", icon: "🩺" },
  { href: "/plan", label: "Plan", icon: "🗓️" },
  { href: "/explain", label: "Explain", icon: "💡" },
  { href: "/dashboard", label: "Dashboard", icon: "📈" },
  { href: "/how-it-works", label: "How it works", icon: "⚙️" },
] as const;

/**
 * Protected shell: sidebar nav plus the client-side auth gate.
 *
 * This is a Client Component because auth state lives in localStorage, which
 * means it renders nothing until the session resolves. That is also why
 * `partialPrefetching` is disabled in next.config.ts -- Next cannot validate
 * instant navigation for a segment gated this way.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner label="Checking your session…" />
      </div>
    );
  }

  // The redirect above is in flight; render nothing rather than a flash of UI.
  if (!user) return null;

  // The syllabi list is fetched with the user's token, so it can only be
  // provided once the session has resolved.
  return (
    <SyllabiProvider>
      <AppShell>{children}</AppShell>
    </SyllabiProvider>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { syllabi } = useSyllabi();
  const pathname = usePathname();

  if (!user) return null;

  return (
    <div className="flex flex-1 flex-col lg:flex-row">
      <aside className="shrink-0 border-b border-border bg-surface lg:w-60 lg:border-r lg:border-b-0">
        <div className="flex items-center gap-2 px-5 py-4">
          <span aria-hidden className="text-lg">
            🔍
          </span>
          <span className="font-semibold tracking-tight">GapFinder AI</span>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-brand-soft font-medium text-brand"
                    : "text-muted hover:bg-surface-muted hover:text-foreground"
                }`}
              >
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {syllabi.length > 0 ? (
          <div className="px-3 pb-3">
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted">
              Syllabi
            </p>
            <nav aria-label="Saved syllabi" className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
              {syllabi.map((syllabus) => {
                const href = `/syllabus/${syllabus.document_id}`;
                const active = pathname === href;
                return (
                  <Link
                    key={syllabus.document_id}
                    href={href}
                    aria-current={active ? "page" : undefined}
                    title={syllabus.filename}
                    className={`flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors ${
                      active
                        ? "bg-brand-soft font-medium text-brand"
                        : "text-muted hover:bg-surface-muted hover:text-foreground"
                    }`}
                  >
                    <span aria-hidden>📘</span>
                    <span className="truncate">{syllabusLabel(syllabus.subject)}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        ) : null}

        <div className="hidden border-t border-border px-5 py-4 lg:block">
          <p className="truncate text-sm font-medium">{user.name}</p>
          <p className="truncate text-xs text-muted">{user.email}</p>
          <button
            onClick={logout}
            className="mt-2 text-xs text-muted underline hover:text-foreground"
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 px-6 py-8 lg:px-10">
        <div className="mx-auto max-w-4xl">{children}</div>
      </main>
    </div>
  );
}
