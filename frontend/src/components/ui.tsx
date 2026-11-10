import type { ReactNode } from "react";

import type { MasteryStatus } from "@/lib/types";

/* --- layout ------------------------------------------------------------ */

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-8">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {subtitle ? <p className="mt-1.5 text-sm text-muted">{subtitle}</p> : null}
    </header>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-surface p-5 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

/* --- controls ---------------------------------------------------------- */

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({
  variant = "primary",
  className = "",
  disabled,
  children,
  ...rest
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-brand text-white hover:bg-brand-hover"
      : "border border-border bg-surface hover:bg-surface-muted";

  return (
    <button className={`${base} ${styles} ${className}`} disabled={disabled} {...rest}>
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-muted">{hint}</span> : null}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand";

/* --- status ------------------------------------------------------------ */

const STATUS_META: Record<MasteryStatus, { label: string; dot: string; chip: string }> = {
  weak: { label: "Weak", dot: "🔴", chip: "bg-weak-soft text-weak" },
  medium: { label: "Medium", dot: "🟡", chip: "bg-medium-soft text-medium" },
  strong: { label: "Strong", dot: "🟢", chip: "bg-strong-soft text-strong" },
};

export function StatusBadge({ status }: { status: MasteryStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${meta.chip}`}
    >
      <span aria-hidden>{meta.dot}</span>
      {meta.label}
    </span>
  );
}

export function statusColorVar(status: MasteryStatus): string {
  return `var(--${status})`;
}

/* --- feedback ---------------------------------------------------------- */

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 text-sm text-muted" role="status">
      <span className="size-4 animate-spin rounded-full border-2 border-border border-t-brand" />
      {label ?? "Loading…"}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-weak/30 bg-weak-soft px-4 py-3 text-sm text-weak"
    >
      {message}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card className="text-center">
      <p className="font-medium">{title}</p>
      <p className="mx-auto mt-1.5 max-w-prose text-sm text-muted">{description}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </Card>
  );
}

/* --- citations --------------------------------------------------------- */

/** Renders "Chapter 3, Section 3.2, p. 45" from the parts the backend returns. */
export function formatCitation(parts: {
  chapter?: string | null;
  section?: string | null;
  page?: number | null;
}): string {
  const pieces = [parts.chapter, parts.section].filter(Boolean) as string[];
  if (parts.page != null) pieces.push(`p. ${parts.page}`);
  return pieces.join(", ");
}

export function CitationChip({ text }: { text: string }) {
  if (!text) return null;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-brand-soft px-2 py-1 font-mono text-xs text-brand">
      <span aria-hidden>📖</span>
      {text}
    </span>
  );
}
