"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, EmptyState, ErrorBanner, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { TopicProgress } from "@/lib/types";
import { useApiData } from "@/lib/useApiData";

/**
 * Fixed 8-slot categorical order (see globals.css). Assigned in sequence by
 * topic, never cycled -- a 9th topic folds out of the chart rather than
 * reusing a hue, which would be indistinguishable under CVD.
 */
const SERIES_VARS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
];
const MAX_PLOTTED_SERIES = SERIES_VARS.length;

interface ChartRow {
  attempt: number;
  [topicName: string]: number | null;
}

/** Backend returns per-topic history; Recharts needs one row per attempt. */
function pivot(topics: TopicProgress[]): ChartRow[] {
  const attempts = [
    ...new Set(topics.flatMap((t) => t.history.map((h) => h.attempt_no))),
  ].sort((a, b) => a - b);

  return attempts.map((attempt) => {
    const row: ChartRow = { attempt };
    for (const topic of topics) {
      const point = topic.history.find((h) => h.attempt_no === attempt);
      // null (not 0) so Recharts breaks the line instead of plotting a dip
      // for an attempt where the topic simply wasn't tested.
      row[topic.topic_name] = point ? Math.round(point.score * 100) : null;
    }
    return row;
  });
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number; color?: string }[];
  label?: string | number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-md">
      <p className="mb-1.5 font-semibold">Attempt {label}</p>
      {payload
        .filter((entry) => entry.value != null)
        .map((entry) => (
          <p key={entry.name} className="flex items-center gap-2 py-0.5">
            <span
              aria-hidden
              className="size-2 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            {/* Text stays in ink tokens; the dot carries identity. */}
            <span className="text-muted">{entry.name}</span>
            <span className="ml-auto font-medium tabular-nums">{entry.value}%</span>
          </p>
        ))}
    </div>
  );
}

export default function DashboardPage() {
  const fetchDashboard = useCallback(() => api.dashboard(), []);
  const { data, loading, error } = useApiData(fetchDashboard);
  const [showTable, setShowTable] = useState(false);

  const plotted = useMemo(
    () => (data?.topics ?? []).slice(0, MAX_PLOTTED_SERIES),
    [data],
  );
  const rows = useMemo(() => pivot(plotted), [plotted]);
  const hiddenCount = (data?.topics.length ?? 0) - plotted.length;

  return (
    <>
      <PageHeader
        title="Progress"
        subtitle="How your topic scores have moved across quiz attempts."
      />

      {loading ? <Spinner /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {!loading && !error && data?.topics.length === 0 ? (
        <EmptyState
          title="No attempts recorded yet"
          description="Take a quiz, then retake it later — this page charts the difference between attempts."
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

      {data && data.topics.length > 0 ? (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2">
            {/* Hero figure: the one number the dashboard leads with. */}
            <Card>
              <p className="text-sm text-muted">Exam readiness</p>
              <p className="mt-1 text-5xl font-semibold tracking-tight">
                {Math.round(data.readiness_percent)}
                <span className="text-2xl text-muted">%</span>
              </p>
              <p className="mt-1 text-xs text-muted">
                Share of your topics currently rated strong.
              </p>
            </Card>

            <Card>
              <p className="text-sm text-muted">Moved weak → strong</p>
              <p className="mt-1 text-3xl font-semibold tracking-tight">
                {data.weak_to_strong_count}
              </p>
              <p className="mt-1 text-xs text-muted">
                Topics that started weak and are now strong.
              </p>
            </Card>
          </div>

          <Card>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Score by attempt</h2>
              <button
                onClick={() => setShowTable((value) => !value)}
                className="text-xs font-medium text-brand hover:underline"
              >
                {showTable ? "Show chart" : "Show table"}
              </button>
            </div>

            {/* Legend is always present for 2+ series: identity never rests on
                color alone. Text wears ink tokens; the dot carries the hue. */}
            {plotted.length > 1 ? (
              <ul className="mb-4 flex flex-wrap gap-x-4 gap-y-2">
                {plotted.map((topic, index) => (
                  <li key={topic.topic_id} className="flex items-center gap-2 text-xs">
                    <span
                      aria-hidden
                      className="h-0.5 w-4 shrink-0 rounded-full"
                      style={{ backgroundColor: SERIES_VARS[index] }}
                    />
                    <span className="text-muted">{topic.topic_name}</span>
                  </li>
                ))}
              </ul>
            ) : null}

            {showTable ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-md text-sm">
                  <caption className="sr-only">
                    Topic score percentage by quiz attempt
                  </caption>
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Topic
                      </th>
                      {rows.map((row) => (
                        <th
                          key={row.attempt}
                          scope="col"
                          className="py-2 pr-4 text-right font-medium tabular-nums"
                        >
                          #{row.attempt}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {plotted.map((topic) => (
                      <tr key={topic.topic_id} className="border-b border-border last:border-b-0">
                        <th scope="row" className="py-2 pr-4 text-left font-normal">
                          {topic.topic_name}
                        </th>
                        {rows.map((row) => {
                          const value = row[topic.topic_name];
                          return (
                            <td
                              key={row.attempt}
                              className="py-2 pr-4 text-right tabular-nums text-muted"
                            >
                              {value == null ? "—" : `${value}%`}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: -16 }}>
                    {/* Hairline, solid, recessive -- never dashed. */}
                    <CartesianGrid stroke="var(--chart-grid)" strokeWidth={1} vertical={false} />
                    <XAxis
                      dataKey="attempt"
                      tickFormatter={(value) => `#${value}`}
                      stroke="var(--chart-axis)"
                      tick={{ fill: "var(--chart-muted)", fontSize: 12 }}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <YAxis
                      domain={[0, 100]}
                      ticks={[0, 25, 50, 75, 100]}
                      tickFormatter={(value) => `${value}%`}
                      stroke="var(--chart-axis)"
                      tick={{ fill: "var(--chart-muted)", fontSize: 12 }}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<ChartTooltip />}
                      cursor={{ stroke: "var(--chart-axis)", strokeWidth: 1 }}
                    />
                    {plotted.map((topic, index) => (
                      <Line
                        key={topic.topic_id}
                        type="monotone"
                        dataKey={topic.topic_name}
                        stroke={SERIES_VARS[index]}
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        connectNulls={false}
                        // >=8px marker carrying a 2px surface ring so dots stay
                        // legible where lines cross.
                        dot={{
                          r: 4,
                          fill: SERIES_VARS[index],
                          stroke: "var(--surface)",
                          strokeWidth: 2,
                        }}
                        activeDot={{
                          r: 6,
                          fill: SERIES_VARS[index],
                          stroke: "var(--surface)",
                          strokeWidth: 2,
                        }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Never cap coverage silently. */}
            {hiddenCount > 0 ? (
              <p className="mt-3 text-xs text-muted">
                Showing {plotted.length} of {data.topics.length} topics — the colour palette
                seats 8 series safely. See the{" "}
                <Link href="/gap-report" className="font-medium text-brand hover:underline">
                  gap report
                </Link>{" "}
                for all of them.
              </p>
            ) : null}
          </Card>
        </>
      ) : null}
    </>
  );
}
