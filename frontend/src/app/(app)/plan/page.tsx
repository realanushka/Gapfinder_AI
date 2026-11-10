"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import {
  Button,
  Card,
  CitationChip,
  EmptyState,
  ErrorBanner,
  Field,
  PageHeader,
  Spinner,
  StatusBadge,
  inputClass,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { PlanChange, PlanResponse } from "@/lib/types";
import { toMessage, useApiData } from "@/lib/useApiData";

/** "Algebra moved from Weak to Medium ✅" -- Step 8.5's visible plan update. */
function ChangeList({ changes }: { changes: PlanChange[] }) {
  if (changes.length === 0) return null;

  return (
    <Card className="mb-6">
      <h2 className="mb-3 text-sm font-semibold">What changed since your last attempt</h2>
      <ul className="space-y-2.5">
        {changes.map((change) => (
          <li key={change.topic_id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{change.topic_name}</span>
            <span className="text-muted">moved from</span>
            <StatusBadge status={change.from_status} />
            <span className="text-muted">to</span>
            <StatusBadge status={change.to_status} />
            <span aria-hidden>{change.improved ? "✅" : "⚠️"}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function DayCard({ day, tasks }: PlanResponse["days"][number]) {
  const totalMinutes = tasks.reduce((sum, task) => sum + task.minutes, 0);

  return (
    <Card>
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="font-medium">Day {day}</h3>
        <span className="text-xs text-muted">{totalMinutes} min</span>
      </div>

      {tasks.length === 0 ? (
        <p className="text-sm text-muted">Rest day — nothing scheduled.</p>
      ) : (
        <ul className="space-y-3">
          {tasks.map((task, index) => (
            <li key={`${task.topic_id}-${index}`} className="flex gap-3">
              <span className="mt-0.5 shrink-0 rounded-md bg-surface-muted px-2 py-0.5 font-mono text-xs text-muted">
                {task.minutes}m
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{task.topic_name}</span>
                <span className="block text-sm text-muted">{task.description}</span>
                {task.citation ? (
                  <span className="mt-1.5 block">
                    <CitationChip text={task.citation} />
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function PlanPage() {
  const fetchPlan = useCallback(() => api.latestPlan(), []);
  const { data: plan, loading, error, setData } = useApiData(fetchPlan);

  const [days, setDays] = useState(5);
  const [hoursPerDay, setHoursPerDay] = useState(2);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setGenerateError(null);
    try {
      setData(await api.generatePlan(days, hoursPerDay));
    } catch (err) {
      setGenerateError(toMessage(err));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Revision plan"
        subtitle="Weak and exam-heavy topics first, fitted to the time you actually have."
      />

      <Card className="mb-8">
        <div className="space-y-4">
          {generateError ? <ErrorBanner message={generateError} /> : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Days available">
              <input
                type="number"
                min={1}
                max={60}
                className={inputClass}
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
              />
            </Field>
            <Field label="Hours per day">
              <input
                type="number"
                min={0.5}
                max={12}
                step={0.5}
                className={inputClass}
                value={hoursPerDay}
                onChange={(e) => setHoursPerDay(Number(e.target.value))}
              />
            </Field>
          </div>

          <p className="text-xs text-muted">
            Priority is computed in code as{" "}
            <code className="font-mono">(1 − mastery) × exam weight</code>, so the ordering is
            always explainable — the LLM only writes the task descriptions.
          </p>

          <Button onClick={handleGenerate} disabled={generating}>
            {generating ? "Building your plan…" : plan ? "Regenerate plan" : "Generate plan"}
          </Button>
        </div>
      </Card>

      {loading ? <Spinner /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {!loading && !error && !plan ? (
        <EmptyState
          title="No plan yet"
          description="Take a quiz so GapFinder knows your weak spots, then generate a plan above."
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

      {plan ? (
        <>
          <ChangeList changes={plan.changes ?? []} />
          <p className="mb-4 text-xs text-muted">
            Generated {new Date(plan.created_at).toLocaleString()}
          </p>
          <div className="space-y-4">
            {plan.days.map((day) => (
              <DayCard key={day.day} {...day} />
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}
