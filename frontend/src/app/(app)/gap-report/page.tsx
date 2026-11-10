"use client";

import Link from "next/link";
import { useCallback } from "react";

import {
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
  StatusBadge,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { TopicGapCard } from "@/lib/types";
import { useApiData } from "@/lib/useApiData";

function GapCard({ card }: { card: TopicGapCard }) {
  const percent = Math.round(card.score * 100);

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-medium">{card.topic_name}</h3>
          <p className="mt-0.5 text-xs text-muted">
            Scored {percent}%
            {card.exam_weight > 0
              ? ` · appears ${card.exam_weight}× in past papers`
              : " · no past-paper data"}
          </p>
        </div>
        <StatusBadge status={card.status} />
      </div>

      {/* Score bar, coloured by the same status the badge shows. */}
      <div
        className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-surface-muted"
        role="img"
        aria-label={`${card.topic_name} score: ${percent} percent`}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${percent}%`, backgroundColor: `var(--${card.status})` }}
        />
      </div>

      <p className="mt-3 text-sm">{card.reason}</p>

      <div className="mt-4 flex gap-4 text-xs font-medium">
        <Link href={`/explain?topic=${card.topic_id}`} className="text-brand hover:underline">
          Revise this
        </Link>
        <Link href={`/quiz?topic=${card.topic_id}`} className="text-brand hover:underline">
          Retake quiz
        </Link>
      </div>
    </Card>
  );
}

export default function GapReportPage() {
  const fetchReport = useCallback(() => api.gapReport(), []);
  const { data: cards, loading, error } = useApiData(fetchReport);

  const weakCount = (cards ?? []).filter((card) => card.status === "weak").length;

  return (
    <>
      <PageHeader
        title="Gap report"
        subtitle="Your diagnosis, weakest topics first — with the reason behind each score."
      />

      {loading ? <Spinner label="Scoring your topics…" /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {!loading && !error && cards?.length === 0 ? (
        <EmptyState
          title="Nothing to diagnose yet"
          description="Take a diagnostic quiz first — the gap report is built from your answers."
          action={
            <Link
              href="/quiz"
              className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover"
            >
              Take a quiz
            </Link>
          }
        />
      ) : null}

      {cards && cards.length > 0 ? (
        <>
          <Card className="mb-6">
            <p className="text-sm">
              {weakCount > 0 ? (
                <>
                  <span className="font-semibold text-weak">{weakCount} weak topic</span>
                  {weakCount === 1 ? " needs" : "s need"} attention first. Your plan will
                  prioritise them by exam weight.
                </>
              ) : (
                <span className="font-semibold text-strong">
                  No weak topics — you&apos;re in good shape.
                </span>
              )}{" "}
              <Link href="/plan" className="font-medium text-brand hover:underline">
                Generate a revision plan →
              </Link>
            </p>
          </Card>

          <div className="space-y-4">
            {cards.map((card) => (
              <GapCard key={card.topic_id} card={card} />
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}
