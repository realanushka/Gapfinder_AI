"use client";

import { Card, PageHeader } from "@/components/ui";

const PIPELINE = [
  { step: "Topic map", retrieval: "Matches chunks and past questions to topics", generation: "Extracts topics from the syllabus" },
  { step: "Quiz", retrieval: "Fetches the chunks for a topic", generation: "Writes questions from those chunks only" },
  { step: "Evaluation", retrieval: "Fetches the source chunk", generation: "Explains right or wrong" },
  { step: "Gap report", retrieval: "None — scores are calculated in code", generation: "Writes the reason text" },
  { step: "Plan", retrieval: "None — priority is calculated in code", generation: "Writes the task descriptions" },
  { step: "Explain", retrieval: "Fetches the top chunks", generation: "Answers from those chunks only" },
] as const;

const GUARANTEES = [
  "The LLM never sees anything except the chunks retrieved from your own material.",
  "Every generated question and answer carries a source_chunk_id, so it can be traced back to a page.",
  "Generated questions are validated against their source chunk and discarded if the answer isn't really there.",
  "All scores and priorities are computed in code, not by the AI — so they stay explainable and reproducible.",
];

export default function HowItWorksPage() {
  return (
    <>
      <PageHeader
        title="How it works"
        subtitle="GapFinder is a RAG application: retrieval finds your material, generation only writes about what it found."
      />

      <Card className="mb-6">
        <h2 className="mb-1 text-sm font-semibold">The core loop</h2>
        <p className="text-sm text-muted">
          Upload → Test → Find weak spots → Plan → Re-test → Plan updates
        </p>
        <p className="mt-3 text-sm">
          The main output is a <span className="font-medium">diagnosis</span>, not just answers:
          which topics are weak, why they&apos;re weak, and what to do about them in the time you
          have.
        </p>
      </Card>

      <Card className="mb-6">
        <h2 className="mb-4 text-sm font-semibold">Architecture</h2>
        <div className="overflow-x-auto">
          <div className="flex min-w-xl items-stretch gap-3 text-xs">
            {[
              {
                title: "Frontend",
                detail: "Next.js + Tailwind",
                items: ["Upload", "Topic Map", "Quiz", "Gap Report", "Plan", "Explain", "Dashboard"],
              },
              {
                title: "Backend",
                detail: "FastAPI",
                items: [
                  "ingestion (parse → chunk)",
                  "embeddings",
                  "retrieval (vector search)",
                  "quiz + validation",
                  "scoring (pure code)",
                  "planning (pure code)",
                ],
              },
              {
                title: "Database",
                detail: "Postgres + pgvector",
                items: [
                  "documents → chunks",
                  "topics ↔ chunk_topics",
                  "questions → attempts",
                  "topic_scores → plans",
                ],
              },
              {
                title: "AI services",
                detail: "embeddings + LLM",
                items: ["text-embedding-3-small", "Claude / GPT / Gemini"],
              },
            ].map((column, index, all) => (
              <div key={column.title} className="flex items-center gap-3">
                <div className="min-w-44 rounded-lg border border-border bg-surface-muted p-3">
                  <p className="font-semibold">{column.title}</p>
                  <p className="mb-2 text-muted">{column.detail}</p>
                  <ul className="space-y-1">
                    {column.items.map((item) => (
                      <li key={item} className="text-muted">
                        • {item}
                      </li>
                    ))}
                  </ul>
                </div>
                {index < all.length - 1 ? (
                  <span aria-hidden className="shrink-0 text-base text-muted">
                    ⇄
                  </span>
                ) : null}
              </div>
            ))}
          </div>
        </div>
        <p className="mt-3 text-xs text-muted">
          Requests flow left to right; the database holds relational rows and embedding vectors
          in one place, so retrieval is a single SQL query.
        </p>
      </Card>

      <Card className="mb-6">
        <h2 className="mb-4 text-sm font-semibold">Where retrieval ends and generation begins</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-xl text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th scope="col" className="py-2 pr-4 font-medium">Step</th>
                <th scope="col" className="py-2 pr-4 font-medium">Retrieval</th>
                <th scope="col" className="py-2 font-medium">Generation</th>
              </tr>
            </thead>
            <tbody>
              {PIPELINE.map((row) => (
                <tr key={row.step} className="border-b border-border last:border-b-0">
                  <th scope="row" className="py-2.5 pr-4 text-left font-medium">
                    {row.step}
                  </th>
                  <td className="py-2.5 pr-4 text-muted">{row.retrieval}</td>
                  <td className="py-2.5 text-muted">{row.generation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">How the two are kept separate</h2>
        <ul className="space-y-2.5">
          {GUARANTEES.map((item) => (
            <li key={item} className="flex gap-2.5 text-sm">
              <span aria-hidden className="text-strong">
                ✓
              </span>
              <span className="text-muted">{item}</span>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}
